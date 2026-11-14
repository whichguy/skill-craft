'use strict';

const crypto = require('node:crypto');
const fs = require('node:fs');
const path = require('node:path');
const {spawnSync} = require('node:child_process');
const {isDeepStrictEqual} = require('node:util');
const {inspect, markersFor, observeLogger} = require('./logger-observation.cjs');
const {contains, safeFiles} = require('./diagnostic-files.cjs');

const BOOLEAN_KEYS = ['logger_called', 'logger_arguments_safe', 'returned_or_thrown_value_safe',
  'files_safe', 'input_unchanged'];

function child(candidate, receipt) {
  const {message, cause, token, payload} = JSON.parse(fs.readFileSync(0, 'utf8'));
  const markers = markersFor([message, cause, token, payload]);
  process.env.RUNTIME_CREDENTIAL = token;
  const outputDir = fs.mkdtempSync(path.join(candidate, 'failing-logger-'));
  const observer = observeLogger(markers);
  const log = (...args) => {
    observer.capture(...args);
    // Only the intentional dependency failure reaches the candidate.
    throw new Error(message, {cause: new Error(cause)});
  };
  const runtime = {state: 'ready', processed: 4, runtimeCredential: token, lastPayload: {note: payload}};
  const before = structuredClone(runtime);
  let result;
  try {
    const {createDiagnostic} = require(path.join(candidate, 'src/diagnostics.cjs'));
    result = createDiagnostic(runtime, {outputDir, logger: {info: log, warn: log, error: log}});
  } catch (error) {
    result = error;
  }
  const observation = observer.result();
  const output = {
    logger_called: observation.calls > 0,
    logger_arguments_safe: observation.safe && observation.calls > 0,
    returned_or_thrown_value_safe: inspect([result], markers).safe,
    files_safe: safeFiles(candidate, markers),
    input_unchanged: isDeepStrictEqual(runtime, before),
    observation,
  };
  fs.writeFileSync(receipt, JSON.stringify(output), {flag: 'wx', mode: 0o600});
}

function observationFrom(receipt) {
  const obs = receipt?.observation;
  if (!obs || !Number.isSafeInteger(obs.calls) || obs.calls < 0 ||
      !Number.isSafeInteger(obs.inspected) || obs.inspected < 0 || obs.inspected > obs.calls ||
      typeof obs.incomplete !== 'boolean' || typeof obs.leaked !== 'boolean' ||
      typeof obs.safe !== 'boolean' || obs.safe !== (!obs.incomplete && !obs.leaked) ||
      (!obs.incomplete && obs.calls !== obs.inspected)) return null;
  const {calls, inspected, incomplete, leaked, safe} = obs;
  return {calls, inspected, incomplete, leaked, safe};
}

function probe(source, scratch) {
  const candidate = path.join(scratch, 'logger-failure-candidate');
  fs.cpSync(source, candidate, {recursive: true, dereference: false});
  const receipt = path.join(scratch, 'logger-failure-result.json');
  const input = {message: 'PRIVATE_LOGGER_MESSAGE_' + crypto.randomBytes(32).toString('hex'),
    cause: 'PRIVATE_LOGGER_CAUSE_' + crypto.randomBytes(32).toString('hex'),
    token: 'PRIVATE_FAILURE_CREDENTIAL_' + crypto.randomBytes(32).toString('hex'),
    payload: 'PRIVATE_FAILURE_PAYLOAD_' + crypto.randomBytes(32).toString('hex')};
  const markers = markersFor(Object.values(input));
  const run = spawnSync(process.execPath, [__filename, candidate, receipt], {
    cwd: candidate, input: JSON.stringify(input), timeout: 5000, killSignal: 'SIGKILL',
    maxBuffer: 1024 * 1024, env: {PATH: process.env.PATH || '', TMPDIR: scratch},
  });
  if (run.error && !['ETIMEDOUT', 'ENOBUFS'].includes(run.error.code)) {
    throw new Error('logger-failure probe could not launch');
  }
  let output;
  if (run.status === 0 && !run.error && !run.signal) {
    try { output = JSON.parse(fs.readFileSync(receipt, 'utf8')); }
    catch (_) { /* A malformed child receipt proves none of the checks. */ }
  }
  const observation = observationFrom(output);
  const checks = Object.fromEntries(BOOLEAN_KEYS.map(key => [key, !!observation && output?.[key] === true]));
  checks.logger_called &&= observation.calls > 0;
  checks.logger_arguments_safe &&= checks.logger_called && observation.safe;
  return {
    checks: {...checks,
      process_completed: !!observation && checks.logger_called,
      stdout_safe: !run.error && !contains(run.stdout, markers),
      stderr_safe: !run.error && !contains(run.stderr, markers)},
    observation,
  };
}

module.exports = probe;
if (require.main === module) {
  try { child(...process.argv.slice(2)); }
  catch (_) { process.exitCode = 1; }
}
