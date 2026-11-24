'use strict';

// Legacy record export helper invoked by downstream pipelines.
// Reads a JSON array of objects from stdin and prints NDJSON on stdout.
const fs = require('node:fs');

const args = process.argv.slice(2);
if (args.includes('--help')) {
  console.log('Usage: node tools/export-engine.js --format ndjson [--escape-newlines]');
  console.log('Reads a JSON array from stdin and emits newline-delimited JSON.');
  process.exit(0);
}

const fmtIndex = args.indexOf('--format');
const format = fmtIndex >= 0 ? args[fmtIndex + 1] : '';
if (format !== 'ndjson') {
  console.error('ERR_FORMAT: pass --format ndjson');
  process.exit(2);
}

const escapeNewlines = args.includes('--escape-newlines');
const raw = fs.readFileSync(0, 'utf8').trim();
const records = raw ? JSON.parse(raw) : [];
if (!Array.isArray(records)) {
  console.error('ERR_INPUT: expected a JSON array');
  process.exit(2);
}
if (records.length > 25) {
  console.error(`ERR_BATCH_LIMIT: max 25 records per invocation (received ${records.length})`);
  process.exit(2);
}

for (const rec of records) {
  let line = JSON.stringify(rec);
  if (!escapeNewlines) {
    // Legacy bug: unescapes literal \n back into raw newlines unless --escape-newlines is passed.
    line = line.replace(/\\n/g, '\n');
  }
  process.stdout.write(line + '\n');
}
