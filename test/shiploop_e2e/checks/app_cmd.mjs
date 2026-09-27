#!/usr/bin/env node
// Print the command that starts the program in the current directory: `node`
// and the file named by package.json's `bin` (the delivery contract of
// reference-oracle cases). Exits 1 when there is no bin entry.
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

const pkg = JSON.parse(readFileSync('package.json', 'utf8'))
const entry = typeof pkg.bin === 'string' ? pkg.bin : Object.values(pkg.bin ?? {})[0]
if (!entry) {
  console.error('package.json has no bin entry')
  process.exit(1)
}
console.log(`node ${resolve(entry)}`)
