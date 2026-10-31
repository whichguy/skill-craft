'use strict';
// Stand-in for `clasp push`: copy the project's files (appsscript.json and src/*.js) to the deployment, a folder named by
// LOCAL_TARGET (else one under the OS temp dir). `--clean` empties the deployment first.
const fs = require('node:fs');
const path = require('node:path');
const os = require('node:os');
const root = path.join(__dirname, '..');
const target = process.env.LOCAL_TARGET || path.join(os.tmpdir(), 'local-target-gas');
const clean = process.argv.includes('--clean');
if (clean) fs.rmSync(target, { recursive: true, force: true });
fs.mkdirSync(target, { recursive: true });
fs.copyFileSync(path.join(root, 'appsscript.json'), path.join(target, 'appsscript.json'));
for (const name of fs.readdirSync(path.join(root, 'src'))) {
  fs.copyFileSync(path.join(root, 'src', name), path.join(target, name));
}
console.log(`pushed the project to ${target}${clean ? ' (clean)' : ''}`);
