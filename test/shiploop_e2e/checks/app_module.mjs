#!/usr/bin/env node
// The absolute path of the file a consumer gets when importing the package in
// the current directory (`exports["."]`, then `module`, then `main`), or an
// empty line when it defines no library entry. Companion of app_cmd.mjs for
// reference-oracle cases.
//
// ALIASES="old=new ..." (optional): a clean-room rebuild carries the renamed
// product in its interface (`Mdkit`), while the oracle, admitted against the
// original, imports the original's names (`Marked`). Then this prints the
// path of a generated module that re-exports the package and adds each `old`
// as an alias of its `new` export.
import { mkdtempSync, readFileSync, writeFileSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join, resolve } from 'node:path'
import { pathToFileURL } from 'node:url'

const pkg = JSON.parse(readFileSync('package.json', 'utf8'))
let entry = pkg.exports
if (entry && typeof entry === 'object' && '.' in entry) entry = entry['.']
while (entry && typeof entry === 'object') {
  entry = entry.import ?? entry.default ?? entry.node ?? Object.values(entry)[0]
}
entry = entry ?? pkg.module ?? pkg.main
const aliases = (process.env.ALIASES ?? '').split(/\s+/).filter(Boolean).map((pair) => pair.split('='))
if (!entry || aliases.length === 0) {
  console.log(entry ? resolve(entry) : '')
} else {
  const target = JSON.stringify(pathToFileURL(resolve(entry)).href)
  const lines = [`export * from ${target}`, `import * as m from ${target}`, 'export default m.default']
  for (const [old, now] of aliases) lines.push(`const ${old}_ = m[${JSON.stringify(old)}] ?? m[${JSON.stringify(now)}]`)
  lines.push(`export { ${aliases.map(([old]) => `${old}_ as ${old}`).join(', ')} }`)
  const shim = join(mkdtempSync(join(tmpdir(), 'alias-')), 'alias.mjs')
  writeFileSync(shim, lines.join('\n') + '\n')
  console.log(shim)
}
