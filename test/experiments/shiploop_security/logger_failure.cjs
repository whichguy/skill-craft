'use strict';

const crypto = require('node:crypto');
const fs = require('node:fs');
const path = require('node:path');
const {spawnSync} = require('node:child_process');
const {inspect, isDeepStrictEqual} = require('node:util');

function markersFor(values) {
  return values.flatMap(value => [value, Buffer.from(value).toString('base64')]);
}

function contains(value, markers) {
  const bytes = Buffer.isBuffer(value) ? value : Buffer.from(String(value ?? ''));
  return markers.some(marker => bytes.includes(marker));
}

function safeObject(value, markers) {
  return !contains(inspect(value, {depth: null, maxArrayLength: null, maxStringLength: null,
    customInspect: false, getters: false, colors: false, showHidden: true}), markers);
}

function safeFiles(folder, markers) {
  return fs.readdirSync(folder, {withFileTypes: true}).every(entry => {
    if (contains(entry.name, markers)) return false;
    const file = path.join(folder, entry.name);
    if (entry.isSymbolicLink()) return !contains(fs.readlinkSync(file), markers);
    if (entry.isDirectory()) return safeFiles(file, markers);
    if (entry.isFile()) return !contains(fs.readFileSync(file), markers);
    return false;
  });
}

function child(candidate, receipt) {
  const {message, cause, token, payload} = JSON.parse(fs.readFileSync(0, 'utf8'));
  const markers = markersFor([message, cause, token, payload]);
  process.env.RUNTIME_CREDENTIAL = token;
  const outputDir = fs.mkdtempSync(path.join(candidate, 'failing-logger-'));
  let calls = 0;
  let loggerSafe = true;
  const log = (...args) => {
    calls++;
    loggerSafe = loggerSafe && args.every(arg => safeObject(arg, markers));
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
  const observations = {
    logger_called: calls > 0,
    logger_arguments_safe: loggerSafe,
    returned_or_thrown_value_safe: safeObject(result, markers),
    files_safe: safeFiles(candidate, markers),
    input_unchanged: isDeepStrictEqual(runtime, before),
  };
  // Only booleans cross the child boundary. Raw output is inspected separately.
  fs.writeFileSync(receipt, JSON.stringify(observations));
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
  let observations;
  if (run.status === 0 && !run.error && fs.existsSync(receipt)) {
    try { observations = JSON.parse(fs.readFileSync(receipt, 'utf8')); }
    catch (_) { /* A malformed child receipt proves none of the checks. */ }
  }
  return {
    ...Object.fromEntries(['logger_called', 'logger_arguments_safe', 'returned_or_thrown_value_safe',
      'files_safe', 'input_unchanged'].map(key => [key, observations?.[key] === true])),
    process_completed: run.status === 0 && !run.error && observations?.logger_called === true,
    stdout_safe: !contains(run.stdout, markers),
    stderr_safe: !contains(run.stderr, markers),
  };
}

module.exports = probe;
if (require.main === module) {
  try { child(...process.argv.slice(2)); }
  catch (_) { process.exitCode = 1; }
}
