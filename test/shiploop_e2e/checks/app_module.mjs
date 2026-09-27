#!/usr/bin/env node
// The absolute path of the file a consumer gets when importing the package in
// the current directory (`exports["."]`, then `module`, then `main`), or an
// empty line when it defines no library entry. Companion of app_cmd.mjs for
// reference-oracle cases.
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

const pkg = JSON.parse(readFileSync('package.json', 'utf8'))
let entry = pkg.exports
if (entry && typeof entry === 'object' && '.' in entry) entry = entry['.']
while (entry && typeof entry === 'object') {
  entry = entry.import ?? entry.default ?? entry.node ?? Object.values(entry)[0]
}
entry = entry ?? pkg.module ?? pkg.main
console.log(entry ? resolve(entry) : '')
