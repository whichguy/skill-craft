'use strict';

const fs = require('node:fs');
const path = require('node:path');
const {spawnSync} = require('node:child_process');
const {isDeepStrictEqual} = require('node:util');

const CASES = [
  ['unknown id denies the whole request without mutation', ['missing']],
  ['owned then unknown id denies the whole request without mutation', ['task-1', 'missing']],
  ['unknown then owned id denies the whole request without mutation', ['missing', 'task-1']],
];
const RECORDS = [['alice', 'task-1'], ['alice', 'task-2'], ['bob', 'task-3'], ['alice', 'task-4']];

function child(root, receipt, order) {
  const app = require(path.join(root, 'src/tasks.cjs'));
  function state() {
    // Clone each value immediately so later reads or actions cannot rewrite
    // what the probe observed through an aliased product object.
    return [structuredClone(app.snapshot()), ...RECORDS.map(args => structuredClone(app.read(...args)))];
  }
  const before = state();
  const returned = app.closeSelected('alice', CASES[order][1].slice());
  const after = state();
  fs.writeFileSync(receipt, JSON.stringify({
    rejected: returned === false,
    snapshotUnchanged: isDeepStrictEqual(before[0], after[0]),
    recordsUnchanged: isDeepStrictEqual(before.slice(1), after.slice(1)),
  }), {flag: 'wx', mode: 0o600});
}

function missingSelections(root, scratch) {
  return CASES.map(([name], order) => {
    const directory = fs.mkdtempSync(path.join(scratch, 'v7-atomicity-'));
    try {
      const candidate = path.join(directory, 'candidate');
      const receipt = path.join(directory, 'result');
      fs.cpSync(root, candidate, {recursive: true, dereference: false});
      const execution = spawnSync(process.execPath, [__filename, candidate, receipt, String(order)], {
        cwd: candidate, timeout: 1300, maxBuffer: 1024 * 1024, killSignal: 'SIGKILL',
        env: {PATH: process.env.PATH || '', TMPDIR: directory},
      });
      let result;
      if (!execution.error && !execution.signal && execution.status === 0) {
        try { result = JSON.parse(fs.readFileSync(receipt, 'utf8')); }
        catch (_) { /* No valid observation; do not credit rejection. */ }
      }
      return {name, rejected: result?.rejected === true,
        snapshotUnchanged: result?.snapshotUnchanged === true,
        recordsUnchanged: result?.recordsUnchanged === true, completed: !!result};
    } finally {
      fs.rmSync(directory, {recursive: true, force: true});
    }
  });
}

module.exports = missingSelections;
if (require.main === module) {
  try { child(...process.argv.slice(2)); }
  catch (_) { process.exitCode = 1; }
}
