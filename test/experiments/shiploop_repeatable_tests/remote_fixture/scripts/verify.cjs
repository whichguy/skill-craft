'use strict';

const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const crypto = require('node:crypto');
const { spawnSync } = require('node:child_process');

const root = path.resolve(__dirname, '..');
const sourceFiles = ['common-js/total-cents.gs', 'common-js/remote-repeatable-tests.gs'];
const revisionPattern = /sha256:(?:[a-f0-9]{64}|SOURCE_REVISION_PLACEHOLDER)/g;
const hash = (value) => crypto.createHash('sha256').update(value).digest('hex');

function identity() {
  const content = sourceFiles.map((name) => {
    const source = fs.readFileSync(path.join(root, name), 'utf8');
    const normalized = name.endsWith('remote-repeatable-tests.gs')
      ? source.replace(revisionPattern, 'sha256:SOURCE_REVISION_PLACEHOLDER') : source;
    return `${name}\0${normalized}\0`;
  }).join('');
  return `sha256:${hash(content)}`;
}

function child(args) {
  const result = spawnSync(process.execPath, args, { cwd: root, stdio: 'inherit' });
  if (result.error) throw result.error;
  if (result.status !== 0) throw new Error(`Check exited ${result.status}; signal=${result.signal || 'none'}`);
}

function verify(mode = 'all') {
  if (!['all', '--syntax', '--identity', '--test'].includes(mode)) throw new Error(`Unknown verification mode: ${mode}`);
  if (mode === 'all' || mode === '--syntax') {
    for (const name of sourceFiles) new vm.Script(fs.readFileSync(path.join(root, name), 'utf8'), { filename: name });
    for (const name of ['scripts/verify.cjs', 'scripts/run-local.cjs', 'tests/local-runtime.cjs', 'tests/local.test.cjs']) child(['--check', name]);
    console.log('LOCAL-SYNTAX passed (Node syntax only; Apps Script compilation unrun)');
  }
  if (mode === 'all' || mode === '--identity') {
    const source = fs.readFileSync(path.join(root, sourceFiles[1]), 'utf8');
    const markers = source.match(revisionPattern) || [];
    if (markers.length !== 1 || markers[0] !== identity()) throw new Error('Source revision marker is stale or ambiguous');
    console.log(`LOCAL-IDENTITY passed canonical marker ${identity()}`);
    for (const name of sourceFiles) console.log(`source-file sha256:${hash(fs.readFileSync(path.join(root, name)))} ${name}`);
  }
  if (mode === 'all' || mode === '--test') {
    child(['--test', 'tests/local.test.cjs']);
    console.log('LOCAL-TEST passed (local simulation only)');
  }
}

if (require.main === module) {
  try {
    if (process.argv.length > 3) throw new Error('Usage: node scripts/verify.cjs [--syntax|--identity|--test]');
    verify(process.argv[2]);
  } catch (error) {
    console.error(error.message);
    process.exitCode = 1;
  }
}
module.exports = { identity };
