'use strict';

// Immutable planning-context manifest support. This module deliberately owns
// only file-reference validation and availability reporting; dispatcher state
// still owns graph navigation and every lifecycle transition.

const crypto = require('node:crypto');
const fs = require('node:fs');
const path = require('node:path');

const SCHEMA = 'shiploop-planning-artifacts/v1';
const DANGEROUS_KEYS = new Set(['__proto__', 'constructor', 'prototype']);
const CLASSIFICATIONS = new Set(['current', 'other-item', 'history']);
const REFERENCE_KINDS = new Set(['url', 'statement']);

function fail(message) {
  throw new Error(message);
}

function hasOwn(object, key) {
  return Object.prototype.hasOwnProperty.call(object, key);
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
  for (const key of Object.keys(value)) {
    if (DANGEROUS_KEYS.has(key)) {
      fail(label + ' contains a dangerous object key: ' + key);
    }
  }
  return value;
}

function assertExactObject(value, keys, label) {
  requireObject(value, label);
  const actual = Object.keys(value).sort();
  const expected = keys.slice().sort();
  if (actual.length !== expected.length ||
      actual.some((key, index) => key !== expected[index])) {
    fail(label + ' has unexpected fields');
  }
}

function assertAllowedObject(value, required, optional, label) {
  requireObject(value, label);
  const allowed = new Set(required.concat(optional));
  for (const key of Object.keys(value)) {
    if (!allowed.has(key)) {
      fail(label + ' has unexpected fields');
    }
  }
  for (const key of required) {
    if (!hasOwn(value, key)) {
      fail(label + ' is missing field: ' + key);
    }
  }
}

function requireString(value, label) {
  if (typeof value !== 'string' || value.trim() === '') {
    fail(label + ' must be a nonempty string');
  }
  return value;
}

function requireLowercaseSha256(value, label) {
  requireString(value, label);
  if (!/^[0-9a-f]{64}$/.test(value)) {
    fail(label + ' must be a lowercase SHA-256 hex digest');
  }
  return value;
}

function cloneJson(value) {
  return JSON.parse(JSON.stringify(value));
}

function sha256Bytes(bytes) {
  return crypto.createHash('sha256').update(bytes).digest('hex');
}

function fileReference(value, label, exact = true) {
  if (exact) {
    assertExactObject(value, ['path', 'sha256'], label);
  } else {
    requireObject(value, label);
    for (const key of ['path', 'sha256']) {
      if (!hasOwn(value, key)) {
        fail(label + ' is missing field: ' + key);
      }
    }
  }
  requireString(value.path, label + '.path');
  if (!path.isAbsolute(value.path)) {
    fail(label + '.path must be absolute');
  }
  requireLowercaseSha256(value.sha256, label + '.sha256');
  return { path: value.path, sha256: value.sha256 };
}

function contextReference(value, label) {
  assertExactObject(value, ['path', 'sha256', 'source'], label);
  const output = fileReference(value, label, false);
  assertExactObject(value.source, ['run_id', 'action_id'], label + '.source');
  output.source = {
    run_id: requireString(value.source.run_id, label + '.source.run_id'),
    action_id: requireString(value.source.action_id, label + '.source.action_id'),
  };
  return output;
}

function uniqueStrings(value, label, requireNonempty) {
  if (!Array.isArray(value)) {
    fail(label + ' must be an array');
  }
  if (requireNonempty && value.length === 0) {
    fail(label + ' must not be empty');
  }
  const output = value.map((entry, index) => requireString(entry, label + '[' + index + ']'));
  if (new Set(output).size !== output.length) {
    fail(label + ' must not contain duplicates');
  }
  return output;
}

function requiredFor(value, stepIds, label) {
  const output = uniqueStrings(value, label, false);
  if (output.includes('*')) {
    if (output.length !== 1) {
      fail(label + ' may contain * only by itself');
    }
    return output;
  }
  for (const step of output) {
    if (!stepIds.has(step)) {
      fail(label + ' references an unknown graph step: ' + step);
    }
  }
  return output;
}

function validateReferenceRecords(value, label) {
  if (!Array.isArray(value)) {
    fail(label + ' must be an array');
  }
  return value.map((entry, index) => {
    const entryLabel = label + '[' + index + ']';
    assertExactObject(entry, ['action', 'index', 'text'], entryLabel);
    requireString(entry.action, entryLabel + '.action');
    if (!Number.isSafeInteger(entry.index) || entry.index < 0) {
      fail(entryLabel + '.index must be a nonnegative integer');
    }
    requireString(entry.text, entryLabel + '.text');
    return cloneJson(entry);
  });
}

function validateArtifact(value, stepIds, label) {
  const required = ['path', 'sha256', 'roles', 'producers', 'classification', 'required_for'];
  const optional = ['references', 'origin', 'source_reference'];
  requireObject(value, label);
  for (const key of required) {
    if (!hasOwn(value, key)) {
      fail(label + ' is missing field: ' + key);
    }
  }
  // Artifact entries may carry producer metadata. It is opaque to the
  // dispatcher once the required contract fields have been validated.
  const reference = fileReference(value, label, false);
  uniqueStrings(value.roles, label + '.roles', true);
  uniqueStrings(value.producers, label + '.producers', true);
  if (!CLASSIFICATIONS.has(value.classification)) {
    fail(label + '.classification is invalid');
  }
  requiredFor(value.required_for, stepIds, label + '.required_for');
  if (hasOwn(value, 'references')) {
    validateReferenceRecords(value.references, label + '.references');
  }
  if (hasOwn(value, 'origin')) {
    fileReference(value.origin, label + '.origin');
  }
  if (hasOwn(value, 'source_reference')) {
    requireString(value.source_reference, label + '.source_reference');
  }
  // Keep known semantic field names reserved even when a producer includes
  // additional metadata, so an accidental duplicate cannot alter validation.
  for (const key of optional) {
    if (hasOwn(value, key) && value[key] === undefined) {
      fail(label + '.' + key + ' must be JSON data');
    }
  }
  return { reference, entry: cloneJson(value) };
}

function validateUnresolved(value, stepIds, label) {
  assertExactObject(value, ['action', 'index', 'text', 'required_for'], label);
  requireString(value.action, label + '.action');
  if (!Number.isSafeInteger(value.index) || value.index < 0) {
    fail(label + '.index must be a nonnegative integer');
  }
  requireString(value.text, label + '.text');
  requiredFor(value.required_for, stepIds, label + '.required_for');
  return cloneJson(value);
}

function validateReferenceOnly(value, stepIds, label) {
  assertAllowedObject(value, ['action', 'index', 'text', 'kind', 'value', 'required_for'], ['rationale'], label);
  requireString(value.action, label + '.action');
  if (!Number.isSafeInteger(value.index) || value.index < 0) {
    fail(label + '.index must be a nonnegative integer');
  }
  requireString(value.text, label + '.text');
  if (!REFERENCE_KINDS.has(value.kind)) {
    fail(label + '.kind is invalid');
  }
  requireString(value.value, label + '.value');
  if (hasOwn(value, 'rationale')) {
    requireString(value.rationale, label + '.rationale');
  }
  requiredFor(value.required_for, stepIds, label + '.required_for');
  return cloneJson(value);
}

function validateManifestShape(manifest, reference, graph) {
  assertExactObject(
    manifest,
    ['schema', 'source', 'graph', 'briefing', 'artifacts', 'unresolved_refs', 'reference_only'],
    'planning context manifest'
  );
  if (manifest.schema !== SCHEMA) {
    fail('planning context manifest.schema is invalid');
  }
  assertExactObject(manifest.source, ['run_id', 'action_id', 'workitem', 'revision'], 'planning context manifest.source');
  const source = {
    run_id: requireString(manifest.source.run_id, 'planning context manifest.source.run_id'),
    action_id: requireString(manifest.source.action_id, 'planning context manifest.source.action_id'),
    workitem: requireString(manifest.source.workitem, 'planning context manifest.source.workitem'),
    revision: manifest.source.revision,
  };
  if (!Number.isSafeInteger(source.revision) || source.revision < 0) {
    fail('planning context manifest.source.revision must be a nonnegative integer');
  }
  if (source.run_id !== reference.source.run_id ||
      source.action_id !== reference.source.action_id) {
    fail('planning context manifest.source does not match planning_context.source');
  }
  const manifestGraph = fileReference(manifest.graph, 'planning context manifest.graph');
  const briefing = fileReference(manifest.briefing, 'planning context manifest.briefing');
  if (!Array.isArray(manifest.artifacts)) {
    fail('planning context manifest.artifacts must be an array');
  }
  if (!Array.isArray(manifest.unresolved_refs)) {
    fail('planning context manifest.unresolved_refs must be an array');
  }
  if (!Array.isArray(manifest.reference_only)) {
    fail('planning context manifest.reference_only must be an array');
  }

  const stepIds = new Set(graph.steps.map((step) => step.id));
  const artifactPaths = new Set();
  const artifacts = manifest.artifacts.map((entry, index) => {
    const artifact = validateArtifact(entry, stepIds, 'planning context manifest.artifacts[' + index + ']');
    if (artifactPaths.has(artifact.reference.path)) {
      fail('planning context manifest.artifacts contains a duplicate path');
    }
    artifactPaths.add(artifact.reference.path);
    return artifact.entry;
  });
  const briefingEntry = artifacts.find((entry) =>
    entry.path === briefing.path && entry.sha256 === briefing.sha256
  );
  if (!briefingEntry || briefingEntry.required_for.length !== 1 ||
      briefingEntry.required_for[0] !== '*') {
    fail('planning context manifest.briefing must match a shared required artifact');
  }
  const unresolvedRefs = manifest.unresolved_refs.map((entry, index) =>
    validateUnresolved(entry, stepIds, 'planning context manifest.unresolved_refs[' + index + ']')
  );
  const referenceOnly = manifest.reference_only.map((entry, index) =>
    validateReferenceOnly(entry, stepIds, 'planning context manifest.reference_only[' + index + ']')
  );
  return {
    source,
    graph: manifestGraph,
    briefing,
    artifacts,
    unresolved_refs: unresolvedRefs,
    reference_only: referenceOnly,
  };
}

function readVerifiedBytes(reference, label) {
  let before;
  try {
    before = fs.lstatSync(reference.path);
  } catch (error) {
    fail(label + ' cannot be inspected: ' + error.message);
  }
  if (before.isSymbolicLink() || !before.isFile()) {
    fail(label + ' must be an absolute regular nonsymlink file');
  }
  let bytes;
  try {
    bytes = fs.readFileSync(reference.path);
  } catch (error) {
    fail(label + ' cannot be read: ' + error.message);
  }
  let after;
  try {
    after = fs.lstatSync(reference.path);
  } catch (error) {
    fail(label + ' changed while it was being read: ' + error.message);
  }
  if (after.isSymbolicLink() || !after.isFile() ||
      before.dev !== after.dev || before.ino !== after.ino) {
    fail(label + ' changed while it was being read');
  }
  if (sha256Bytes(bytes) !== reference.sha256) {
    fail(label + ' SHA-256 does not match');
  }
  return bytes;
}

function readVerifiedJson(reference, label) {
  const bytes = readVerifiedBytes(reference, label);
  try {
    return JSON.parse(bytes.toString('utf8'));
  } catch (error) {
    fail(label + ' is not valid JSON: ' + error.message);
  }
}

function load(referenceValue, expectedGraph, normalizeGraph, sameGraph) {
  const reference = contextReference(referenceValue, 'planning_context');
  const manifest = readVerifiedJson(reference, 'planning_context');
  requireObject(manifest, 'planning context manifest');

  // Validate the graph first so required_for entries can be checked against its
  // exact frozen step IDs.
  const rawGraphReference = fileReference(manifest.graph, 'planning context manifest.graph');
  const rawGraph = readVerifiedJson(rawGraphReference, 'planning context manifest.graph');
  requireObject(rawGraph, 'planning context manifest.graph JSON');
  const frozenGraph = normalizeGraph(rawGraph);
  if (!sameGraph(frozenGraph, expectedGraph)) {
    fail('planning context manifest.graph does not match the initialized graph');
  }
  const validated = validateManifestShape(manifest, reference, frozenGraph);
  return { reference, manifest: validated, graph: frozenGraph };
}

function applies(requiredFor, step) {
  return step === undefined
    ? requiredFor.length > 0
    : requiredFor.includes('*') || requiredFor.includes(step);
}

function affectedSteps(requiredFor, graph) {
  return requiredFor.includes('*')
    ? graph.steps.map((step) => step.id)
    : requiredFor.slice();
}

function issue(code, message, requiredFor) {
  return { code, message, required_for: requiredFor.slice() };
}

function availability(reference, expectedGraph, normalizeGraph, sameGraph, step) {
  let loaded;
  try {
    loaded = load(reference, expectedGraph, normalizeGraph, sameGraph);
  } catch (error) {
    return {
      ok: false,
      issues: [issue('planning-context-invalid', error.message, ['*'])],
      planning_context: cloneJson(contextReference(reference, 'planning_context')),
      blocked_steps: expectedGraph.steps.map((entry) => entry.id),
    };
  }

  const issues = [];
  const material = loaded.manifest.artifacts.filter((artifact) => applies(artifact.required_for, step));
  for (const artifact of material) {
    try {
      readVerifiedBytes(fileReference(artifact, 'planning context artifact', false), 'planning context artifact');
    } catch (error) {
      issues.push(issue('planning-artifact-unavailable', error.message, artifact.required_for));
    }
  }
  for (const unresolved of loaded.manifest.unresolved_refs) {
    if (applies(unresolved.required_for, step)) {
      issues.push(issue(
        'planning-reference-unresolved',
        'planning context has an unresolved required reference: ' + unresolved.action + '[' + unresolved.index + ']',
        unresolved.required_for
      ));
    }
  }
  for (const referenceOnly of loaded.manifest.reference_only) {
    if (applies(referenceOnly.required_for, step)) {
      issues.push(issue(
        'planning-reference-not-materialized',
        'planning context has a required reference-only input: ' + referenceOnly.action + '[' + referenceOnly.index + ']',
        referenceOnly.required_for
      ));
    }
  }
  const blocked = new Set();
  for (const entry of issues) {
    for (const stepId of affectedSteps(entry.required_for, expectedGraph)) {
      blocked.add(stepId);
    }
  }
  return {
    ok: issues.length === 0,
    issues,
    planning_context: cloneJson(loaded.reference),
    blocked_steps: expectedGraph.steps.map((entry) => entry.id).filter((id) => blocked.has(id)),
    manifest: loaded.manifest,
  };
}

function preflight(reference, expectedGraph, normalizeGraph, sameGraph) {
  const result = availability(reference, expectedGraph, normalizeGraph, sameGraph, undefined);
  if (!result.ok) {
    fail('planning context is unavailable: ' + result.issues.map((entry) => entry.message).join('; '));
  }
  return cloneJson(result.planning_context);
}

function check(reference, expectedGraph, normalizeGraph, sameGraph, step) {
  const result = availability(reference, expectedGraph, normalizeGraph, sameGraph, step);
  return {
    ok: result.ok,
    issues: result.issues,
    planning_context: result.planning_context,
  };
}

function summary(reference, expectedGraph, normalizeGraph, sameGraph) {
  const result = availability(reference, expectedGraph, normalizeGraph, sameGraph, undefined);
  return {
    planning_context: result.planning_context,
    planning_context_check: { ok: result.ok, issues: result.issues },
    planning_blocked_steps: result.blocked_steps,
  };
}

function packet(reference, expectedGraph, normalizeGraph, sameGraph, step) {
  const planningContext = cloneJson(contextReference(reference, 'planning_context'));
  try {
    const loaded = load(reference, expectedGraph, normalizeGraph, sameGraph);
    return {
      planning_context: planningContext,
      planning_brief: cloneJson(loaded.manifest.briefing),
      reference_material: loaded.manifest.artifacts
        .filter((artifact) => applies(artifact.required_for, step))
        .map((artifact) => cloneJson(artifact)),
    };
  } catch (_) {
    // Packet inspection remains available during a live-context fault. Start
    // and positive settlement perform the actual availability gate.
    return {
      planning_context: planningContext,
      planning_brief: null,
      reference_material: [],
    };
  }
}

module.exports = {
  SCHEMA,
  contextReference,
  preflight,
  check,
  summary,
  packet,
};
