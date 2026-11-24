'use strict';
// Streaming exporter recommended for >20 records. Reads JSON array from stdin.
const fs = require('node:fs');
const args = process.argv.slice(2);
if (args.includes('--help')) {
  console.log('Usage: node tools/export-v2-stream.js [--mode jsonl]');
  console.log('Streaming exporter supporting unlimited logical exports when chunked cleanly.');
  process.exit(0);
}
const raw = fs.readFileSync(0, 'utf8');
if (Buffer.byteLength(raw, 'utf8') > 4096) {
  console.error(`ERR_STREAM_BUFFER: payload exceeds 4096 bytes (received ${Buffer.byteLength(raw, 'utf8')}); chunk inputs <= 4096 bytes per invocation.`);
  process.exit(2);
}
const modeIdx = args.indexOf('--mode');
const mode = modeIdx >= 0 ? args[modeIdx + 1] : 'csv';
const records = raw.trim() ? JSON.parse(raw) : [];
if (!Array.isArray(records)) {
  console.error('ERR_INPUT: expected JSON array');
  process.exit(2);
}
for (const rec of records) {
  if (mode === 'jsonl') {
    process.stdout.write(JSON.stringify(rec) + '\n');
  } else {
    // Default legacy mode omits JSON encoding and corrupts commas/newlines.
    process.stdout.write(`${rec.id ?? ''},${rec.name ?? ''},${rec.note ?? ''}\n`);
  }
}
