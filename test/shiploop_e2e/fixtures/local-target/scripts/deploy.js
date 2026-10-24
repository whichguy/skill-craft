'use strict';
// Deploy src/ to the local target (LOCAL_TARGET, else a folder under the OS temp dir). The target keeps state between
// commands: a deploy copies files over what is there and removes nothing, unless --clean is given.
const fs = require('node:fs');
const path = require('node:path');
const os = require('node:os');
const target = process.env.LOCAL_TARGET || path.join(os.tmpdir(), 'local-target');
const clean = process.argv.includes('--clean');
if (clean) fs.rmSync(target, { recursive: true, force: true });
fs.mkdirSync(path.join(target, 'src'), { recursive: true });
for (const name of fs.readdirSync(path.join(__dirname, '..', 'src'))) {
  fs.copyFileSync(path.join(__dirname, '..', 'src', name), path.join(target, 'src', name));
}
console.log(`deployed src/ to ${target}${clean ? ' (clean)' : ''}`);
