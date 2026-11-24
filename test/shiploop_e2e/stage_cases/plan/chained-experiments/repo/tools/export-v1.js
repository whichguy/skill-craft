'use strict';
// Legacy v1 exporter CLI: reads JSON array from stdin and prints JSON Lines.
const fs = require('node:fs');
const args = process.argv.slice(2);
if (args.includes('--help')) {
  console.log('Usage: node tools/export-v1.js');
  console.log('Reads a JSON array of records from stdin and emits one JSON object per line.');
  process.exit(0);
}
const raw = fs.readFileSync(0, 'utf8').trim();
const records = raw ? JSON.parse(raw) : [];
if (!Array.isArray(records)) {
  console.error('ERR_INPUT: expected JSON array');
  process.exit(2);
}
if (records.length > 20) {
  console.error(`ERR_MAX_RECORDS: v1 supports max 20 records (received ${records.length}); use tools/export-v2-stream.js for larger batches.`);
  process.exit(2);
}
for (const rec of records) {
  process.stdout.write(JSON.stringify(rec) + '\n');
}
