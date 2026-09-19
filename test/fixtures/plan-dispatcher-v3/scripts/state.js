'use strict';

/*
 * Bounded single-dispatcher experiment.
 *
 * This module coordinates a trusted local filesystem.  It is not a security
 * boundary and it does not launch, stop, or inspect native workers.  In
 * particular, confirmed_stopped is a caller attestation used to authorize a
 * retry or takeover; callers must ensure the old dispatcher has stopped.
 */

const crypto = require('node:crypto');
const fs = require('node:fs');
const path = require('node:path');
const planningContext = require('./planning-context');

const STATE_FILE = 'plan-dispatcher-state.json';
const LEGACY_STATE_FILE = 'state.json';
const INBOX_DIR = 'inbox';
const LOCK_FILE = '.dispatcher.lock';
const ACTIVE_STATUSES = new Set(['claimed', 'launching', 'running', 'rejected']);
const RESERVED_STATUSES = new Set(['launching', 'running', 'rejected']);
const STEP_STATUSES = new Set([
  'pending', 'claimed', 'launching', 'running', 'accepted', 'rejected', 'blocked',
]);
const ATTEMPT_STATUSES = new Set([
  'claimed', 'launching', 'running', 'accepted', 'rejected', 'retried',
]);
const RECEIPT_STATUSES = new Set(['SUCCEEDED', 'FAILED', 'BLOCKED']);
const DANGEROUS_KEYS = new Set(['__proto__', 'constructor', 'prototype']);

function fail(message, code) {
  const error = new Error(message);
  if (code) {
    error.code = code;
  }
  throw error;
}

function isPlainObject(value) {
  if (value === null || typeof value !== 'object' || Array.isArray(value)) {
    return false;
  }
  const prototype = Object.getPrototypeOf(value);
  return prototype === Object.prototype || prototype === null;
}

function requireObject(value, label) {
  if (!isPlainObject(value)) {
    fail(label + ' must be an object');
  }
  return value;
}

function requireString(value, label) {
  if (typeof value !== 'string' || value.trim() === '') {
    fail(label + ' must be a nonempty string');
  }
  return value;
}

function isDangerousKey(key) {
  return DANGEROUS_KEYS.has(key);
}

function assertSafeObjectKeys(value, label) {
  requireObject(value, label);
  for (const key of Object.keys(value)) {
    if (isDangerousKey(key)) {
      fail(label + ' contains a dangerous object key: ' + key);
    }
  }
}

function assertExactObject(value, keys, label) {
  requireObject(value, label);
  assertSafeObjectKeys(value, label);
  const actual = Object.keys(value).sort();
  const expected = keys.slice().sort();
  if (actual.length !== expected.length ||
      actual.some((key, index) => key !== expected[index])) {
    fail(label + ' has unexpected fields');
  }
}

function canonicalize(value, label) {
  if (value === null) {
    return null;
  }
  if (typeof value === 'string' || typeof value === 'boolean') {
    return value;
  }
  if (typeof value === 'number') {
    if (!Number.isFinite(value)) {
      fail(label + ' must be JSON-serializable');
    }
    return value;
  }
  if (Array.isArray(value)) {
    return value.map((item, index) => canonicalize(item, label + '[' + index + ']'));
  }
  if (isPlainObject(value)) {
    assertSafeObjectKeys(value, label);
    const output = Object.create(null);
    for (const key of Object.keys(value).sort()) {
      output[key] = canonicalize(value[key], label + '.' + key);
    }
    return output;
  }
  fail(label + ' must be JSON-serializable');
}

function stableStringify(value, label) {
  return JSON.stringify(canonicalize(value, label || 'value'));
}

function cloneJson(value) {
  return JSON.parse(stableStringify(value));
}

function sameJson(left, right) {
  return stableStringify(left) === stableStringify(right);
}

function sha256Bytes(bytes) {
  return crypto.createHash('sha256').update(bytes).digest('hex');
}

function opaqueId(prefix) {
  if (typeof crypto.randomUUID === 'function') {
    return prefix + '_' + crypto.randomUUID();
  }
  return prefix + '_' + crypto.randomBytes(16).toString('hex');
}

function existingStatePath(dir, filename) {
  const candidate = path.join(dir, filename);
  let details;
  try {
    details = fs.lstatSync(candidate);
  } catch (error) {
    if (error.code === 'ENOENT') {
      return null;
    }
    fail('could not inspect dispatcher state file: ' + error.message);
  }
  if (!details.isFile()) {
    fail('dispatcher state file must be a regular non-symlink file: ' + filename);
  }
  return candidate;
}

function statePath(dir) {
  const canonical = existingStatePath(dir, STATE_FILE);
  const legacy = existingStatePath(dir, LEGACY_STATE_FILE);
  if (canonical && legacy) {
    fail('dispatcher run has both canonical and legacy state files');
  }
  // New runs use the canonical name. A legacy-only run remains in place so
  // recovery never creates a second mutable state authority.
  return canonical || legacy || path.join(dir, STATE_FILE);
}

function inboxDirectory(dir) {
  return path.join(dir, INBOX_DIR);
}

function assertAttemptId(attempt) {
  requireString(attempt, 'attempt');
  if (!/^[A-Za-z0-9_-]+$/.test(attempt)) {
    fail('attempt is not a valid opaque identifier');
  }
}

function inboxPath(dir, attempt) {
  assertAttemptId(attempt);
  return path.join(inboxDirectory(dir), attempt + '.json');
}

function temporaryPath(destination) {
  return path.join(
    path.dirname(destination),
    '.' + path.basename(destination) + '.' + process.pid + '.' +
      crypto.randomBytes(8).toString('hex') + '.tmp'
  );
}

function writeAtomicReplace(destination, contents) {
  const temporary = temporaryPath(destination);
  let descriptor;
  try {
    descriptor = fs.openSync(temporary, 'wx', 0o600);
    fs.writeFileSync(descriptor, contents, 'utf8');
    fs.fsyncSync(descriptor);
    fs.closeSync(descriptor);
    descriptor = undefined;
    fs.renameSync(temporary, destination);
  } finally {
    if (descriptor !== undefined) {
      try {
        fs.closeSync(descriptor);
      } catch (_) {
        // Preserve the original error.
      }
    }
    try {
      fs.unlinkSync(temporary);
    } catch (error) {
      if (error.code !== 'ENOENT') {
        throw error;
      }
    }
  }
}

function writeAtomicImmutable(destination, contents) {
  const temporary = temporaryPath(destination);
  let descriptor;
  try {
    descriptor = fs.openSync(temporary, 'wx', 0o600);
    fs.writeFileSync(descriptor, contents, 'utf8');
    fs.fsyncSync(descriptor);
    fs.closeSync(descriptor);
    descriptor = undefined;
    try {
      fs.linkSync(temporary, destination);
      return true;
    } catch (error) {
      if (error.code === 'EEXIST') {
        return false;
      }
      throw error;
    }
  } finally {
    if (descriptor !== undefined) {
      try {
        fs.closeSync(descriptor);
      } catch (_) {
        // Preserve the original error.
      }
    }
    try {
      fs.unlinkSync(temporary);
    } catch (error) {
      if (error.code !== 'ENOENT') {
        throw error;
      }
    }
  }
}

function withLock(dir, operation) {
  const lockPath = path.join(dir, LOCK_FILE);
  let descriptor;
  try {
    descriptor = fs.openSync(lockPath, 'wx', 0o600);
    fs.writeFileSync(descriptor, String(process.pid), 'utf8');
  } catch (error) {
    if (error.code === 'EEXIST') {
      fail('dispatcher lock is already held', 'ELOCKED');
    }
    throw error;
  }

  try {
    return operation();
  } finally {
    try {
      fs.closeSync(descriptor);
    } finally {
      try {
        fs.unlinkSync(lockPath);
      } catch (error) {
        if (error.code !== 'ENOENT') {
          throw error;
        }
      }
    }
  }
}

function readState(dir) {
  let parsed;
  try {
    parsed = JSON.parse(fs.readFileSync(statePath(dir), 'utf8'));
  } catch (error) {
    fail('could not read dispatcher state: ' + error.message);
  }
  if (!isPlainObject(parsed) || !isPlainObject(parsed.steps) ||
      !isPlainObject(parsed.attempts) || !isPlainObject(parsed.graph)) {
    fail('dispatcher state is malformed');
  }
  return hydrateState(dir, parsed);
}

function saveState(dir, state) {
  writeAtomicReplace(statePath(dir), JSON.stringify(state, null, 2) + '\n');
}

function validateGraph(graph) {
  requireObject(graph, 'graph');
  assertSafeObjectKeys(graph, 'graph');
  const graphKeys = Object.keys(graph).sort();
  const allowedGraphKeys = ['source', 'steps', 'version'];
  if (graphKeys.some((key) => !allowedGraphKeys.includes(key)) ||
      !graphKeys.includes('version') || !graphKeys.includes('steps')) {
    fail('graph has unexpected fields');
  }
  if (graph.version !== 1 || !Array.isArray(graph.steps)) {
    fail('graph must have version 1 and a steps array');
  }
  if (graph.steps.length === 0) {
    fail('graph must contain at least one step');
  }
  let source;
  if (hasOwn(graph, 'source')) {
    requireObject(graph.source, 'graph.source');
    source = canonicalize(graph.source, 'graph.source');
  }

  const identifiers = new Set();
  const steps = graph.steps.map((step, index) => {
    requireObject(step, 'graph.steps[' + index + ']');
    assertSafeObjectKeys(step, 'graph.steps[' + index + ']');
    const stepKeys = Object.keys(step).sort();
    const allowedStepKeys = ['contract', 'deps', 'id'];
    if (stepKeys.some((key) => !allowedStepKeys.includes(key)) ||
        !stepKeys.includes('id') || !stepKeys.includes('deps')) {
      fail('graph.steps[' + index + '] has unexpected fields');
    }
    requireString(step.id, 'graph.steps[' + index + '].id');
    if (isDangerousKey(step.id)) {
      fail('graph step ID is a dangerous object key: ' + step.id);
    }
    if (!Array.isArray(step.deps)) {
      fail('graph.steps[' + index + '].deps must be an array');
    }
    if (identifiers.has(step.id)) {
      fail('graph contains a duplicate step ID: ' + step.id);
    }
    identifiers.add(step.id);
    const dependencies = step.deps.map((dependency, dependencyIndex) => {
      requireString(
        dependency,
        'graph.steps[' + index + '].deps[' + dependencyIndex + ']'
      );
      return dependency;
    });
    if (new Set(dependencies).size !== dependencies.length) {
      fail('graph step has duplicate dependencies: ' + step.id);
    }
    const output = { id: step.id, deps: dependencies };
    if (hasOwn(step, 'contract')) {
      assertExactObject(
        step.contract,
        ['task', 'ready', 'done'],
        'graph.steps[' + index + '].contract'
      );
      requireString(step.contract.task, 'graph.steps[' + index + '].contract.task');
      if (!Array.isArray(step.contract.ready) || !Array.isArray(step.contract.done)) {
        fail('graph.steps[' + index + '].contract.ready and done must be arrays');
      }
      const ready = step.contract.ready.map((item, itemIndex) => requireString(
        item,
        'graph.steps[' + index + '].contract.ready[' + itemIndex + ']'
      ));
      const done = step.contract.done.map((item, itemIndex) => requireString(
        item,
        'graph.steps[' + index + '].contract.done[' + itemIndex + ']'
      ));
      if (done.length === 0) {
        fail('graph.steps[' + index + '].contract.done must not be empty');
      }
      if (new Set(ready).size !== ready.length || new Set(done).size !== done.length) {
        fail('graph step contract has duplicate ready or done entries: ' + step.id);
      }
      output.contract = { task: step.contract.task, ready, done };
    }
    return output;
  });

  for (const step of steps) {
    for (const dependency of step.deps) {
      if (!identifiers.has(dependency)) {
        fail('graph dependency does not exist: ' + dependency);
      }
    }
  }

  const byId = new Map(steps.map((step) => [step.id, step]));
  const visiting = new Set();
  const visited = new Set();
  function visit(stepId) {
    if (visited.has(stepId)) {
      return;
    }
    if (visiting.has(stepId)) {
      fail('graph contains a dependency cycle at: ' + stepId);
    }
    visiting.add(stepId);
    for (const dependency of byId.get(stepId).deps) {
      visit(dependency);
    }
    visiting.delete(stepId);
    visited.add(stepId);
  }
  for (const step of steps) {
    visit(step.id);
  }

  const output = { version: 1, steps };
  if (source !== undefined) {
    output.source = source;
  }
  return output;
}

function graphIdentity(graph) {
  return sha256Bytes(Buffer.from(stableStringify(graph), 'utf8'));
}

function hasOwn(object, key) {
  return Object.prototype.hasOwnProperty.call(object, key);
}

function currentAttempt(state, attempt) {
  assertAttemptId(attempt);
  if (!hasOwn(state.attempts, attempt)) {
    fail('unknown attempt');
  }
  const record = state.attempts[attempt];
  if (!record || !hasOwn(state.steps, record.step)) {
    fail('attempt record is malformed');
  }
  if (state.steps[record.step].current_attempt !== attempt) {
    fail('attempt is stale');
  }
  return record;
}

function assertOwner(state, owner) {
  requireString(owner, 'owner');
  if (state.owner !== owner) {
    fail('owner does not hold the dispatcher');
  }
}

function assertHexSha256(value, label) {
  requireString(value, label);
  if (!/^[0-9a-fA-F]{64}$/.test(value)) {
    fail(label + ' must be a SHA-256 hex digest');
  }
  return value.toLowerCase();
}

function evidenceShape(evidence, label) {
  assertExactObject(evidence, ['path', 'sha256'], label);
  requireString(evidence.path, label + '.path');
  if (!path.isAbsolute(evidence.path)) {
    fail(label + '.path must be absolute');
  }
  assertHexSha256(evidence.sha256, label + '.sha256');
  return evidence;
}

function verifyEvidence(evidence, label) {
  evidenceShape(evidence, label);
  let before;
  try {
    before = fs.lstatSync(evidence.path);
  } catch (error) {
    fail(label + ' cannot be inspected: ' + error.message);
  }
  if (before.isSymbolicLink() || !before.isFile()) {
    fail(label + ' must be an absolute regular nonsymlink file');
  }
  let bytes;
  try {
    bytes = fs.readFileSync(evidence.path);
  } catch (error) {
    fail(label + ' cannot be read: ' + error.message);
  }
  let after;
  try {
    after = fs.lstatSync(evidence.path);
  } catch (error) {
    fail(label + ' changed while it was being read: ' + error.message);
  }
  if (after.isSymbolicLink() || !after.isFile() ||
      before.dev !== after.dev || before.ino !== after.ino) {
    fail(label + ' changed while it was being read');
  }
  if (sha256Bytes(bytes) !== evidence.sha256.toLowerCase()) {
    fail(label + ' SHA-256 does not match');
  }
}

function envelopeShape(envelope) {
  assertExactObject(
    envelope,
    ['run_id', 'step', 'attempt', 'status', 'evidence'],
    'envelope'
  );
  requireString(envelope.run_id, 'envelope.run_id');
  requireString(envelope.step, 'envelope.step');
  assertAttemptId(envelope.attempt);
  if (!RECEIPT_STATUSES.has(envelope.status)) {
    fail('envelope.status is invalid');
  }
  evidenceShape(envelope.evidence, 'envelope.evidence');
  return envelope;
}

function verificationShape(verification) {
  assertExactObject(
    verification,
    ['receipt_sha256', 'passed', 'reason', 'evidence'],
    'verification'
  );
  assertHexSha256(verification.receipt_sha256, 'verification.receipt_sha256');
  if (typeof verification.passed !== 'boolean') {
    fail('verification.passed must be boolean');
  }
  requireString(verification.reason, 'verification.reason');
  evidenceShape(verification.evidence, 'verification.evidence');
  return verification;
}

function requireUniqueStrings(value, label, requireNonempty) {
  if (!Array.isArray(value)) {
    fail(label + ' must be an array');
  }
  if (requireNonempty && value.length === 0) {
    fail(label + ' must not be empty');
  }
  const values = value.map((item, index) => requireString(item, label + '[' + index + ']'));
  if (new Set(values).size !== values.length) {
    fail(label + ' must not contain duplicates');
  }
  return values;
}

function normalizeWriteScope(value, label) {
  if (!Array.isArray(value)) {
    fail(label + ' must be an array');
  }
  if (value.length === 0) {
    fail(label + ' must not be empty');
  }
  const normalized = value.map((item, index) => {
    requireString(item, label + '[' + index + ']');
    if (item.includes('\0') || item.includes('\\')) {
      fail(label + '[' + index + '] must use a relative POSIX workspace path');
    }
    if (path.posix.isAbsolute(item) || path.win32.isAbsolute(item)) {
      fail(label + '[' + index + '] must be relative to the workspace');
    }
    if (item.split('/').includes('..')) {
      fail(label + '[' + index + '] must not contain a .. segment');
    }
    const scope = path.posix.normalize(item);
    if (scope === '.' || scope === '' || scope === '..' || scope.startsWith('../')) {
      fail(label + '[' + index + '] must name a nonempty workspace-relative path');
    }
    return scope;
  });
  if (new Set(normalized).size !== normalized.length) {
    fail(label + ' must not contain duplicate normalized paths');
  }
  return normalized;
}

function realDirectory(value, label) {
  requireString(value, label);
  if (!path.isAbsolute(value)) {
    fail(label + ' must be an absolute path');
  }
  let resolved;
  let details;
  try {
    resolved = fs.realpathSync(value);
    details = fs.statSync(resolved);
  } catch (error) {
    fail(label + ' must resolve to a real directory: ' + error.message);
  }
  if (!details.isDirectory()) {
    fail(label + ' must resolve to a real directory');
  }
  return resolved;
}

function directoriesOverlap(left, right) {
  function contains(ancestor, candidate) {
    const relative = path.relative(ancestor, candidate);
    return relative === '' ||
      !(relative === '..' || relative.startsWith('..' + path.sep) || path.isAbsolute(relative));
  }
  return contains(left, right) || contains(right, left);
}

function contextShape(context, label) {
  assertExactObject(
    context,
    ['workspace', 'write_scope', 'resources', 'ready_evidence'],
    label
  );
  requireString(context.workspace, label + '.workspace');
  if (!path.isAbsolute(context.workspace)) {
    fail(label + '.workspace must be an absolute path');
  }
  const output = {
    workspace: path.resolve(context.workspace),
    write_scope: normalizeWriteScope(context.write_scope, label + '.write_scope'),
    resources: requireUniqueStrings(context.resources, label + '.resources', false),
  };
  evidenceShape(context.ready_evidence, label + '.ready_evidence');
  output.ready_evidence = {
    path: path.resolve(context.ready_evidence.path),
    sha256: context.ready_evidence.sha256.toLowerCase(),
  };
  return output;
}

function normalizeStartContext(context, dir, label) {
  const output = contextShape(context, label);
  output.workspace = realDirectory(output.workspace, label + '.workspace');
  const runDirectory = realDirectory(dir, 'run directory');
  if (directoriesOverlap(output.workspace, runDirectory)) {
    fail(label + '.workspace must be disjoint from the run directory');
  }
  verifyEvidence(output.ready_evidence, label + '.ready_evidence');
  return output;
}

function validateStoredContext(context, dir, label, requireLiveEvidence) {
  const normalized = contextShape(context, label);
  if (!sameJson(context, normalized)) {
    fail(label + ' is not in canonical form');
  }
  if (requireLiveEvidence) {
    const live = normalizeStartContext(context, dir, label);
    if (!sameJson(context, live)) {
      fail(label + ' workspace is not canonical');
    }
  }
  return normalized;
}

function assertContextAvailable(state, record, context) {
  for (const otherAttempt of Object.keys(state.attempts)) {
    if (otherAttempt === record.attempt) {
      continue;
    }
    const other = state.attempts[otherAttempt];
    if (!RESERVED_STATUSES.has(other.status) || !hasOwn(other, 'context')) {
      continue;
    }
    if (directoriesOverlap(context.workspace, other.context.workspace)) {
      fail('workspace overlaps the active attempt: ' + other.attempt);
    }
    const otherResources = new Set(other.context.resources);
    for (const resource of context.resources) {
      if (otherResources.has(resource)) {
        fail('resource is already reserved by active attempt: ' + other.attempt);
      }
    }
  }
}

function planningContextAvailability(state, step) {
  if (!hasOwn(state, 'planning_context')) {
    return { ok: true, issues: [], planning_context: null };
  }
  return planningContext.check(
    state.planning_context,
    state.graph,
    validateGraph,
    sameJson,
    step
  );
}

function assertStepPlanningContextAvailable(state, step) {
  const availability = planningContextAvailability(state, step);
  if (!availability.ok) {
    const detail = availability.issues.map((entry) => entry.message).join('; ');
    fail('planning context is unavailable for step ' + step + ': ' + detail, 'EPLANNING_CONTEXT');
  }
  return availability;
}

function assertKnownStep(state, step) {
  requireString(step, 'step');
  if (!hasOwn(state.steps, step)) {
    fail('step does not exist');
  }
}

function assertEnvelopeCurrent(state, envelope) {
  if (envelope.run_id !== state.run_id) {
    fail('envelope run_id does not match this run');
  }
  if (!hasOwn(state.steps, envelope.step)) {
    fail('envelope step does not exist');
  }
  const record = currentAttempt(state, envelope.attempt);
  if (record.step !== envelope.step || record.run_id !== envelope.run_id) {
    fail('envelope does not identify the current attempt');
  }
  return record;
}

function readInbox(dir, attempt, missingIsNull) {
  const destination = inboxPath(dir, attempt);
  let details;
  try {
    details = fs.lstatSync(destination);
  } catch (error) {
    if (missingIsNull && error.code === 'ENOENT') {
      return null;
    }
    fail('could not inspect inbox receipt: ' + error.message);
  }
  if (details.isSymbolicLink() || !details.isFile()) {
    fail('inbox receipt must be a regular nonsymlink file');
  }
  let bytes;
  try {
    bytes = fs.readFileSync(destination);
  } catch (error) {
    fail('could not read inbox receipt: ' + error.message);
  }
  let envelope;
  try {
    envelope = JSON.parse(bytes.toString('utf8'));
  } catch (error) {
    fail('inbox receipt is malformed: ' + error.message);
  }
  return {
    envelope,
    sha256: sha256Bytes(bytes),
  };
}

function receiptOutput(receipt) {
  return {
    envelope: cloneJson(receipt.envelope),
    sha256: receipt.sha256,
  };
}

function receiptMatchesRecord(receipt, state, record) {
  try {
    envelopeShape(receipt.envelope);
    return receipt.envelope.run_id === state.run_id &&
      receipt.envelope.step === record.step &&
      receipt.envelope.attempt === record.attempt;
  } catch (_) {
    return false;
  }
}

function recoveryFor(status, record) {
  if (status === 'claimed') {
    return 'start';
  }
  if (status === 'launching') {
    return 'reconcile';
  }
  if (status === 'running') {
    return hasOwn(record, 'executor') ? 'resume' : 'collect';
  }
  if (status === 'receipt') {
    return 'verify';
  }
  if (status === 'rejected') {
    return 'retry';
  }
  return 'investigate';
}

function attemptOutput(record, displayedStatus, recovery) {
  const output = {
    run_id: record.run_id,
    step: record.step,
    attempt: record.attempt,
    status: displayedStatus || record.status,
    dispatch_key: record.dispatch_key,
    handle: cloneJson(record.handle),
  };
  if (hasOwn(record, 'executor')) {
    output.executor = cloneJson(record.executor);
  }
  if (hasOwn(record, 'context')) {
    output.context = cloneJson(record.context);
  }
  if (recovery) {
    output.recovery = recovery;
  }
  return output;
}

function dependenciesAccepted(state, step) {
  return step.deps.every((dependency) => state.steps[dependency].status === 'accepted');
}

/*
 * A rejected attempt blocks its descendants.  Once that attempt is retried or
 * subsequently accepted, this restores blocked descendants to pending so their
 * normal dependency checks decide when they become ready.
 */
function refreshBlockedStates(state) {
  let changed = false;
  let progress = true;
  while (progress) {
    progress = false;
    for (const step of state.graph.steps) {
      const stepState = state.steps[step.id];
      if (stepState.status === 'accepted' ||
          stepState.status === 'claimed' ||
          stepState.status === 'launching' ||
          stepState.status === 'running' ||
          stepState.status === 'rejected') {
        continue;
      }
      const dependencyBlocks = step.deps.some((dependency) => {
        const dependencyStatus = state.steps[dependency].status;
        return dependencyStatus === 'rejected' || dependencyStatus === 'blocked';
      });
      const desired = dependencyBlocks ? 'blocked' : 'pending';
      if (stepState.status !== desired) {
        stepState.status = desired;
        if (desired === 'blocked') {
          stepState.current_attempt = null;
        }
        changed = true;
        progress = true;
      }
    }
  }
  return changed;
}

function assertAllowedObject(value, allowed, required, label) {
  requireObject(value, label);
  assertSafeObjectKeys(value, label);
  for (const key of Object.keys(value)) {
    if (!allowed.includes(key)) {
      fail(label + ' has unexpected fields');
    }
  }
  for (const key of required) {
    if (!hasOwn(value, key)) {
      fail(label + ' is missing field: ' + key);
    }
  }
}

function validateRetryRecord(retry, label) {
  assertExactObject(retry, ['confirmed_stopped', 'reason'], label);
  if (retry.confirmed_stopped !== true) {
    fail(label + '.confirmed_stopped must be true');
  }
  requireString(retry.reason, label + '.reason');
}

function validateSettlementRecord(dir, state, record, label) {
  const hasVerification = hasOwn(record, 'verification');
  const hasReceiptHash = hasOwn(record, 'receipt_sha256');
  if (hasVerification !== hasReceiptHash) {
    fail(label + ' has incomplete settlement fields');
  }
  if (!hasVerification) {
    return null;
  }
  verificationShape(record.verification);
  const receiptHash = assertHexSha256(record.receipt_sha256, label + '.receipt_sha256');
  const verificationHash = assertHexSha256(
    record.verification.receipt_sha256,
    label + '.verification.receipt_sha256'
  );
  if (receiptHash !== verificationHash) {
    fail(label + ' receipt identity does not match its verification');
  }
  const stored = readInbox(dir, record.attempt, false);
  envelopeShape(stored.envelope);
  if (!receiptMatchesRecord(stored, state, record)) {
    fail(label + ' receipt does not identify this attempt');
  }
  if (stored.sha256 !== receiptHash) {
    fail(label + ' receipt hash does not match durable inbox bytes');
  }
  return stored;
}

function hydrateState(dir, state) {
  const baseStateKeys = [
    'version', 'run_id', 'graph', 'graph_sha256', 'owner', 'seen_owners',
    'generation', 'revision', 'steps', 'attempts',
  ];
  if (state.version !== 1 && state.version !== 2) {
    fail('dispatcher state version is invalid');
  }
  assertExactObject(
    state,
    state.version === 2 ? baseStateKeys.concat('planning_context') : baseStateKeys,
    'dispatcher state'
  );
  requireString(state.run_id, 'dispatcher state.run_id');
  const frozenGraph = validateGraph(state.graph);
  if (!sameJson(state.graph, frozenGraph)) {
    fail('dispatcher state graph is not canonical');
  }
  const graphHash = assertHexSha256(state.graph_sha256, 'dispatcher state.graph_sha256');
  if (graphHash !== graphIdentity(frozenGraph)) {
    fail('dispatcher state graph identity does not match the frozen graph');
  }
  if (state.version === 2) {
    const frozenPlanningContext = planningContext.contextReference(
      state.planning_context,
      'dispatcher state.planning_context'
    );
    if (!sameJson(state.planning_context, frozenPlanningContext)) {
      fail('dispatcher state planning_context is not canonical');
    }
  }
  requireString(state.owner, 'dispatcher state.owner');
  if (!Array.isArray(state.seen_owners) || state.seen_owners.length === 0) {
    fail('dispatcher owner history is malformed');
  }
  const seenOwners = state.seen_owners.map((owner, index) =>
    requireString(owner, 'dispatcher state.seen_owners[' + index + ']')
  );
  if (new Set(seenOwners).size !== seenOwners.length ||
      seenOwners[seenOwners.length - 1] !== state.owner) {
    fail('dispatcher owner history is inconsistent');
  }
  for (const field of ['generation', 'revision']) {
    if (!Number.isSafeInteger(state[field]) || state[field] < 0) {
      fail('dispatcher state.' + field + ' must be a nonnegative integer');
    }
  }

  assertSafeObjectKeys(state.steps, 'dispatcher state.steps');
  const graphStepIds = frozenGraph.steps.map((step) => step.id);
  const storedStepIds = Object.keys(state.steps);
  if (storedStepIds.length !== graphStepIds.length ||
      graphStepIds.some((stepId) => !hasOwn(state.steps, stepId))) {
    fail('dispatcher state step index does not match the frozen graph');
  }
  const referencedAttempts = new Set();
  for (const step of frozenGraph.steps) {
    const stepState = state.steps[step.id];
    assertExactObject(stepState, ['status', 'current_attempt'], 'dispatcher state.steps.' + step.id);
    if (!STEP_STATUSES.has(stepState.status)) {
      fail('dispatcher state step has an invalid status: ' + step.id);
    }
    if (stepState.status === 'pending' || stepState.status === 'blocked') {
      if (stepState.current_attempt !== null) {
        fail('dispatcher state inactive step has a current attempt: ' + step.id);
      }
    } else {
      assertAttemptId(stepState.current_attempt);
      if (referencedAttempts.has(stepState.current_attempt)) {
        fail('dispatcher state reuses a current attempt');
      }
      referencedAttempts.add(stepState.current_attempt);
    }
  }

  assertSafeObjectKeys(state.attempts, 'dispatcher state.attempts');
  const allowedAttemptFields = [
    'run_id', 'step', 'attempt', 'status', 'dispatch_key', 'handle', 'context',
    'executor', 'verification', 'receipt_sha256', 'rejection_reason', 'retry',
  ];
  const requiredAttemptFields = ['run_id', 'step', 'attempt', 'status', 'dispatch_key', 'handle'];
  for (const attempt of Object.keys(state.attempts)) {
    assertAttemptId(attempt);
    const record = state.attempts[attempt];
    const label = 'dispatcher state.attempts.' + attempt;
    assertAllowedObject(record, allowedAttemptFields, requiredAttemptFields, label);
    assertAttemptId(record.attempt);
    if (record.attempt !== attempt) {
      fail(label + ' key does not match record.attempt');
    }
    requireString(record.run_id, label + '.run_id');
    if (record.run_id !== state.run_id) {
      fail(label + ' run_id does not match this run');
    }
    requireString(record.step, label + '.step');
    if (!hasOwn(state.steps, record.step)) {
      fail(label + ' references an unknown step');
    }
    if (!ATTEMPT_STATUSES.has(record.status)) {
      fail(label + ' has an invalid status');
    }
    requireString(record.dispatch_key, label + '.dispatch_key');
    if (record.handle !== null) {
      assertHandle(record.handle);
    }
    const hasExecutor = hasOwn(record, 'executor');
    if (hasExecutor) {
      normalizeExecutor(record.executor, label + '.executor');
    }
    if (record.handle !== null && hasExecutor) {
      fail(label + ' has both a native handle and main-context executor');
    }
    if (record.status === 'claimed' || record.status === 'launching') {
      if (record.handle !== null) {
        fail(label + ' has a launch handle before it is running');
      }
      if (hasExecutor) {
        fail(label + ' has an execution identity before it is running');
      }
    } else if (record.status === 'running' ||
               record.status === 'accepted' || record.status === 'rejected') {
      if (record.handle === null && !hasExecutor) {
        fail(label + ' is missing its confirmed execution identity');
      }
    }

    if (hasOwn(record, 'context')) {
      if (record.status === 'claimed') {
        fail(label + ' cannot have context before launch intent');
      }
      validateStoredContext(
        record.context,
        dir,
        label + '.context',
        RESERVED_STATUSES.has(record.status)
      );
    }

    const hasSettlement = hasOwn(record, 'verification') || hasOwn(record, 'receipt_sha256');
    const stored = validateSettlementRecord(dir, state, record, label);
    if (record.status === 'accepted' || record.status === 'rejected') {
      if (!hasSettlement) {
        fail(label + ' is missing its settlement');
      }
      const shouldAccept = stored.envelope.status === 'SUCCEEDED' &&
        record.verification.passed === true;
      if ((record.status === 'accepted') !== shouldAccept) {
        fail(label + ' settlement does not match its recorded status');
      }
      if (record.status === 'accepted') {
        verifyEvidence(stored.envelope.evidence, label + '.accepted receipt evidence');
        verifyEvidence(record.verification.evidence, label + '.accepted verification evidence');
      }
    } else if (hasSettlement) {
      if (record.status !== 'retried') {
        fail(label + ' has settlement fields before settlement');
      }
      if (stored.envelope.status === 'SUCCEEDED' && record.verification.passed === true) {
        fail(label + ' cannot retry an accepted result');
      }
    }

    if (record.status === 'rejected') {
      if (!hasOwn(record, 'rejection_reason')) {
        fail(label + ' is missing its rejection reason');
      }
      requireString(record.rejection_reason, label + '.rejection_reason');
    } else if (hasOwn(record, 'rejection_reason')) {
      if (record.status !== 'retried' || !hasSettlement) {
        fail(label + ' has an unexpected rejection reason');
      }
      requireString(record.rejection_reason, label + '.rejection_reason');
    }
    if (record.status === 'retried') {
      if (!hasOwn(record, 'retry')) {
        fail(label + ' is missing retry confirmation');
      }
      validateRetryRecord(record.retry, label + '.retry');
    } else if (hasOwn(record, 'retry')) {
      fail(label + ' has unexpected retry confirmation');
    }

    const current = state.steps[record.step].current_attempt;
    if (record.status === 'retried') {
      if (current === attempt || referencedAttempts.has(attempt)) {
        fail(label + ' remains current after retry');
      }
    } else if (current !== attempt || state.steps[record.step].status !== record.status) {
      fail(label + ' does not match its current step state');
    }
  }

  for (const attempt of Object.keys(state.attempts)) {
    const record = state.attempts[attempt];
    if (RESERVED_STATUSES.has(record.status) && hasOwn(record, 'context')) {
      assertContextAvailable(state, record, record.context);
    }
  }

  for (const attempt of referencedAttempts) {
    if (!hasOwn(state.attempts, attempt)) {
      fail('dispatcher state references an unknown current attempt');
    }
  }
  for (const step of frozenGraph.steps) {
    const stepState = state.steps[step.id];
    const dependencyBlocks = step.deps.some((dependency) => {
      const status = state.steps[dependency].status;
      return status === 'rejected' || status === 'blocked';
    });
    if (stepState.status === 'pending' && dependencyBlocks) {
      fail('dispatcher state leaves a blocked step pending: ' + step.id);
    }
    if (stepState.status === 'blocked' && !dependencyBlocks) {
      fail('dispatcher state marks an unblocked step blocked: ' + step.id);
    }
    if (stepState.status !== 'pending' && stepState.status !== 'blocked' &&
        !dependenciesAccepted({ steps: state.steps }, step)) {
      fail('dispatcher state started a step before its dependencies were accepted: ' + step.id);
    }
  }
  return state;
}

function snapshotFromState(dir, state) {
  const ready = [];
  const active = [];
  const accepted = [];

  for (const step of state.graph.steps) {
    const stepState = state.steps[step.id];
    if (stepState.status === 'accepted') {
      accepted.push(step.id);
    }
    if (stepState.status === 'pending' && dependenciesAccepted(state, step)) {
      ready.push(step.id);
    }

    if (stepState.current_attempt &&
        hasOwn(state.attempts, stepState.current_attempt)) {
      const record = state.attempts[stepState.current_attempt];
      if (ACTIVE_STATUSES.has(record.status)) {
        let displayedStatus = record.status;
        if (record.status === 'launching' || record.status === 'running') {
          const pendingReceipt = readInbox(dir, record.attempt, true);
          if (pendingReceipt && receiptMatchesRecord(pendingReceipt, state, record)) {
            displayedStatus = 'receipt';
          }
        }
        const recovery = displayedStatus === 'receipt' && record.handle === null
          ? (hasOwn(record, 'executor') ? 'verify' : 'reconcile')
          : recoveryFor(displayedStatus, record);
        active.push(attemptOutput(record, displayedStatus, recovery));
      }
    }
  }

  const snapshot = {
    run_id: state.run_id,
    graph_sha256: state.graph_sha256,
    owner: state.owner,
    generation: state.generation,
    revision: state.revision,
    ready,
    active,
    accepted,
    complete: accepted.length === state.graph.steps.length,
  };
  if (hasOwn(state, 'planning_context')) {
    Object.assign(
      snapshot,
      planningContext.summary(
        state.planning_context,
        state.graph,
        validateGraph,
        sameJson
      )
    );
  }
  return snapshot;
}

function stopConfirmation(options, label) {
  requireObject(options, label);
  if (options.confirmed_stopped !== true) {
    fail(label + ' requires confirmed_stopped: true');
  }
  requireString(options.reason, label + '.reason');
}

function init(dir, graph, owner, contextReference) {
  requireString(dir, 'dir');
  requireString(owner, 'owner');
  const frozenGraph = validateGraph(graph);
  const frozenPlanningContext = contextReference === undefined
    ? undefined
    : planningContext.preflight(
      contextReference,
      frozenGraph,
      validateGraph,
      sameJson
    );

  fs.mkdirSync(dir, { recursive: false, mode: 0o700 });
  fs.mkdirSync(inboxDirectory(dir), { recursive: false, mode: 0o700 });

  const steps = Object.create(null);
  for (const step of frozenGraph.steps) {
    steps[step.id] = { status: 'pending', current_attempt: null };
  }
  const state = {
    version: frozenPlanningContext === undefined ? 1 : 2,
    run_id: opaqueId('run'),
    graph: frozenGraph,
    graph_sha256: graphIdentity(frozenGraph),
    owner,
    seen_owners: [owner],
    generation: 0,
    revision: 0,
    steps,
    attempts: Object.create(null),
  };
  if (frozenPlanningContext !== undefined) {
    state.planning_context = frozenPlanningContext;
  }

  return withLock(dir, () => {
    saveState(dir, state);
    return snapshotFromState(dir, state);
  });
}

function inspect(dir) {
  requireString(dir, 'dir');
  return snapshotFromState(dir, readState(dir));
}

function describe(dir) {
  requireString(dir, 'dir');
  return cloneJson(readState(dir));
}

function checkPlanningContext(dir, step) {
  requireString(dir, 'dir');
  const state = readState(dir);
  assertKnownStep(state, step);
  return planningContextAvailability(state, step);
}

function assertPlanningContextAvailable(dir, step) {
  requireString(dir, 'dir');
  const state = readState(dir);
  assertKnownStep(state, step);
  return assertStepPlanningContextAvailable(state, step);
}

function planningContextPacket(dir, step) {
  requireString(dir, 'dir');
  const state = readState(dir);
  assertKnownStep(state, step);
  if (!hasOwn(state, 'planning_context')) {
    return null;
  }
  return planningContext.packet(
    state.planning_context,
    state.graph,
    validateGraph,
    sameJson,
    step
  );
}

function claim(dir, owner, limit, stepIds) {
  requireString(dir, 'dir');
  if (!Number.isSafeInteger(limit) || limit < 0) {
    fail('limit must be a nonnegative integer');
  }
  let selected;
  if (stepIds !== undefined) {
    if (!Array.isArray(stepIds)) {
      fail('stepIds must be an array when supplied');
    }
    selected = stepIds.map((stepId, index) => requireString(stepId, 'stepIds[' + index + ']'));
    if (new Set(selected).size !== selected.length) {
      fail('stepIds must not contain duplicates');
    }
    if (selected.length > limit) {
      fail('stepIds exceeds the claim limit');
    }
  }

  return withLock(dir, () => {
    const state = readState(dir);
    assertOwner(state, owner);
    let candidates;
    if (selected !== undefined) {
      const graphById = new Map(state.graph.steps.map((step) => [step.id, step]));
      candidates = selected.map((stepId) => {
        if (!graphById.has(stepId)) {
          fail('stepIds contains an unknown step: ' + stepId);
        }
        const step = graphById.get(stepId);
        const stepState = state.steps[step.id];
        if (stepState.status !== 'pending' || !dependenciesAccepted(state, step)) {
          fail('stepIds contains a nonready step: ' + stepId);
        }
        return step;
      });
    } else {
      candidates = [];
      for (const step of state.graph.steps) {
        if (candidates.length >= limit) {
          break;
        }
        const stepState = state.steps[step.id];
        if (stepState.status === 'pending' && dependenciesAccepted(state, step)) {
          candidates.push(step);
        }
      }
    }

    const claims = [];
    for (const step of candidates) {
      const stepState = state.steps[step.id];
      const attempt = opaqueId('attempt');
      const record = {
        run_id: state.run_id,
        step: step.id,
        attempt,
        status: 'claimed',
        dispatch_key: opaqueId('dispatch'),
        handle: null,
      };
      state.attempts[attempt] = record;
      stepState.status = 'claimed';
      stepState.current_attempt = attempt;
      claims.push(attemptOutput(record));
    }

    if (claims.length > 0) {
      state.revision += 1;
      saveState(dir, state);
    }
    return Object.assign(snapshotFromState(dir, state), { claims });
  });
}

function start(dir, owner, attempt, context, executor) {
  requireString(dir, 'dir');
  const frozenExecutor = executor === undefined
    ? undefined
    : normalizeExecutor(executor, 'executor');
  return withLock(dir, () => {
    const state = readState(dir);
    assertOwner(state, owner);
    const record = currentAttempt(state, attempt);
    const stepState = state.steps[record.step];

    if (record.status === 'claimed') {
      assertStepPlanningContextAvailable(state, record.step);
      let frozenContext;
      if (context !== undefined) {
        frozenContext = normalizeStartContext(context, dir, 'context');
        assertContextAvailable(state, record, frozenContext);
      }
      const action = frozenExecutor === undefined ? 'launch' : 'execute';
      record.status = frozenExecutor === undefined ? 'launching' : 'running';
      if (frozenContext) {
        record.context = frozenContext;
      }
      if (frozenExecutor !== undefined) {
        record.executor = cloneJson(frozenExecutor);
      }
      stepState.status = record.status;
      state.revision += 1;
      saveState(dir, state);
      return Object.assign({ action }, attemptOutput(record));
    }
    if (record.status === 'launching' || record.status === 'running') {
      if (context !== undefined) {
        const replayContext = normalizeStartContext(context, dir, 'context');
        if (!hasOwn(record, 'context') || !sameJson(record.context, replayContext)) {
          fail('attempt already has a conflicting frozen context');
        }
      }
      const hasExecutor = hasOwn(record, 'executor');
      if (hasExecutor !== (frozenExecutor !== undefined) ||
          (hasExecutor && !sameJson(record.executor, frozenExecutor))) {
        fail('attempt already has a conflicting execution identity');
      }
      return Object.assign({ action: 'reconcile' }, attemptOutput(record));
    }
    fail('attempt cannot be started from status: ' + record.status);
  });
}

function assertHandle(handle) {
  if (handle === null || handle === undefined ||
      (typeof handle === 'string' && handle.trim() === '')) {
    fail('handle must be a confirmed nonempty JSON value');
  }
  canonicalize(handle, 'handle');
}

function normalizeExecutor(executor, label) {
  assertExactObject(executor, ['kind', 'id'], label);
  if (executor.kind !== 'main-context') {
    fail(label + '.kind must be main-context');
  }
  return { kind: 'main-context', id: requireString(executor.id, label + '.id') };
}

function launched(dir, owner, attempt, handle) {
  requireString(dir, 'dir');
  assertHandle(handle);
  return withLock(dir, () => {
    const state = readState(dir);
    assertOwner(state, owner);
    const record = currentAttempt(state, attempt);
    const stepState = state.steps[record.step];

    if (hasOwn(record, 'executor')) {
      fail('attempt already has a main-context executor');
    }

    if (record.status === 'launching') {
      record.handle = cloneJson(handle);
      record.status = 'running';
      stepState.status = 'running';
      state.revision += 1;
      saveState(dir, state);
      return attemptOutput(record);
    }
    if (record.status === 'running') {
      if (sameJson(record.handle, handle)) {
        return attemptOutput(record);
      }
      fail('attempt already has a conflicting launch handle');
    }
    fail('attempt cannot record a handle from status: ' + record.status);
  });
}

function report(dir, envelope) {
  requireString(dir, 'dir');
  envelopeShape(envelope);

  return withLock(dir, () => {
    const state = readState(dir);
    const record = assertEnvelopeCurrent(state, envelope);
    const existing = readInbox(dir, envelope.attempt, true);

    /*
     * Rechecking evidence also prevents a caller from treating an arbitrary
     * preexisting inbox file as a valid report.
     */
    verifyEvidence(envelope.evidence, 'envelope.evidence');
    if (existing) {
      envelopeShape(existing.envelope);
      if (!sameJson(existing.envelope, envelope)) {
        fail('a different immutable receipt already exists for this attempt');
      }
      return receiptOutput(existing);
    }

    if (record.status !== 'launching' && record.status !== 'running') {
      fail('attempt cannot report before launch intent is persisted');
    }

    const contents = stableStringify(envelope, 'envelope') + '\n';
    if (!writeAtomicImmutable(inboxPath(dir, envelope.attempt), contents)) {
      const raced = readInbox(dir, envelope.attempt, false);
      envelopeShape(raced.envelope);
      if (!sameJson(raced.envelope, envelope)) {
        fail('a different immutable receipt already exists for this attempt');
      }
      return receiptOutput(raced);
    }

    return {
      envelope: cloneJson(envelope),
      sha256: sha256Bytes(Buffer.from(contents, 'utf8')),
    };
  });
}

function receipt(dir, attempt) {
  requireString(dir, 'dir');
  const stored = readInbox(dir, attempt, false);
  envelopeShape(stored.envelope);
  return receiptOutput(stored);
}

function settlementOutput(dir, state, record) {
  return Object.assign(snapshotFromState(dir, state), {
    outcome: record.status,
    attempt: attemptOutput(record),
  });
}

function settle(dir, owner, attempt, verification) {
  requireString(dir, 'dir');
  verificationShape(verification);

  return withLock(dir, () => {
    const state = readState(dir);
    assertOwner(state, owner);
    const record = currentAttempt(state, attempt);

    if (record.status === 'accepted' || record.status === 'rejected') {
      if (record.verification && sameJson(record.verification, verification)) {
        return settlementOutput(dir, state, record);
      }
      fail('attempt already has a conflicting settlement');
    }
    if (record.status !== 'launching' && record.status !== 'running') {
      fail('attempt cannot be settled from status: ' + record.status);
    }
    if (record.handle === null && !hasOwn(record, 'executor')) {
      fail('attempt cannot be settled without a confirmed launch handle or main-context executor');
    }

    const stored = readInbox(dir, attempt, false);
    envelopeShape(stored.envelope);
    const reported = assertEnvelopeCurrent(state, stored.envelope);
    if (reported.attempt !== record.attempt) {
      fail('receipt does not belong to this attempt');
    }
    if (assertHexSha256(verification.receipt_sha256, 'verification.receipt_sha256') !==
        stored.sha256) {
      fail('verification receipt_sha256 does not match the durable receipt');
    }

    /*
     * Receipt publication is only a handoff.  Acceptance repeats the report
     * and verifier artifact checks while a confirmed native handle is required.
     */
    verifyEvidence(stored.envelope.evidence, 'reported evidence');
    verifyEvidence(verification.evidence, 'verification.evidence');

    const accepted = stored.envelope.status === 'SUCCEEDED' &&
      verification.passed === true;
    if (accepted) {
      assertStepPlanningContextAvailable(state, record.step);
    }

    record.verification = cloneJson(verification);
    record.receipt_sha256 = stored.sha256;
    record.status = accepted ? 'accepted' : 'rejected';
    state.steps[record.step].status = record.status;
    if (!accepted) {
      record.rejection_reason = verification.reason;
    }
    refreshBlockedStates(state);
    state.revision += 1;
    saveState(dir, state);
    return settlementOutput(dir, state, record);
  });
}

function retry(dir, owner, attempt, options) {
  requireString(dir, 'dir');
  stopConfirmation(options, 'retry');

  return withLock(dir, () => {
    const state = readState(dir);
    assertOwner(state, owner);
    const record = currentAttempt(state, attempt);
    if (!ACTIVE_STATUSES.has(record.status) || record.status === 'accepted') {
      fail('attempt is not retryable from status: ' + record.status);
    }

    record.status = 'retried';
    record.retry = {
      confirmed_stopped: true,
      reason: options.reason,
    };
    const stepState = state.steps[record.step];
    stepState.status = 'pending';
    stepState.current_attempt = null;
    refreshBlockedStates(state);
    state.revision += 1;
    saveState(dir, state);
    return Object.assign(snapshotFromState(dir, state), {
      retry: attemptOutput(record),
    });
  });
}

function takeover(dir, oldOwner, newOwner, options) {
  requireString(dir, 'dir');
  requireString(oldOwner, 'oldOwner');
  requireString(newOwner, 'newOwner');
  stopConfirmation(options, 'takeover');
  if (oldOwner === newOwner) {
    fail('takeover requires a distinct new owner');
  }

  return withLock(dir, () => {
    const state = readState(dir);
    if (state.owner !== oldOwner) {
      fail('oldOwner does not hold the dispatcher');
    }
    if (!Array.isArray(state.seen_owners)) {
      fail('dispatcher owner history is malformed');
    }
    if (state.seen_owners.includes(newOwner)) {
      fail('newOwner was previously used for this run');
    }
    state.owner = newOwner;
    state.seen_owners.push(newOwner);
    state.generation += 1;
    state.revision += 1;
    saveState(dir, state);
    return snapshotFromState(dir, state);
  });
}

function readCliInput(inputPath) {
  let parsed;
  try {
    parsed = JSON.parse(fs.readFileSync(inputPath, 'utf8'));
  } catch (error) {
    fail('could not read CLI input: ' + error.message);
  }
  requireObject(parsed, 'CLI input');
  assertSafeObjectKeys(parsed, 'CLI input');
  return parsed;
}

function main() {
  try {
    const argumentsList = process.argv.slice(2);
    const operation = argumentsList[0] && argumentsList[0].toLowerCase();
    const dir = argumentsList[1];
    const inputPath = argumentsList[2];
    if (!operation || !dir || argumentsList.length > 3) {
      fail('usage: node dispatcher.js OP DIR INPUT.json');
    }

    let result;
    if (operation === 'inspect' || operation === 'describe') {
      if (inputPath) {
        fail(operation + ' does not take INPUT.json');
      }
      result = operation === 'inspect' ? inspect(dir) : describe(dir);
    } else {
      if (!inputPath) {
        fail(operation + ' requires INPUT.json');
      }
      const input = readCliInput(inputPath);
      if (operation === 'init') {
        result = init(dir, input.graph, input.owner, input.planning_context);
      } else if (operation === 'claim') {
        const stepIds = hasOwn(input, 'stepIds') ? input.stepIds : input.steps;
        result = claim(dir, input.owner, input.limit, stepIds);
      } else if (operation === 'start') {
        result = start(dir, input.owner, input.attempt, input.context, input.executor);
      } else if (operation === 'launched') {
        result = launched(dir, input.owner, input.attempt, input.handle);
      } else if (operation === 'report') {
        result = report(dir, input);
      } else if (operation === 'receipt') {
        result = receipt(dir, input.attempt);
      } else if (operation === 'settle') {
        result = settle(dir, input.owner, input.attempt, input.verification);
      } else if (operation === 'retry') {
        result = retry(dir, input.owner, input.attempt, {
          confirmed_stopped: input.confirmed_stopped,
          reason: input.reason,
        });
      } else if (operation === 'takeover') {
        result = takeover(dir, input.oldOwner, input.newOwner, {
          confirmed_stopped: input.confirmed_stopped,
          reason: input.reason,
        });
      } else {
        fail('unknown operation: ' + operation);
      }
    }
    process.stdout.write(JSON.stringify(result) + '\n');
  } catch (error) {
    process.stderr.write((error && error.message) ? error.message + '\n' : String(error) + '\n');
    process.exitCode = 1;
  }
}

module.exports = {
  validateGraph,
  graphIdentity,
  init,
  inspect,
  describe,
  checkPlanningContext,
  assertPlanningContextAvailable,
  planningContextPacket,
  claim,
  start,
  launched,
  report,
  receipt,
  settle,
  retry,
  takeover,
};

if (require.main === module) {
  main();
}
