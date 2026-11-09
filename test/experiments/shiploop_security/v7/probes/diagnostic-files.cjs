'use strict';

const fs = require('node:fs');
const path = require('node:path');

function contains(value, markers) {
  const bytes = Buffer.isBuffer(value) ? value : Buffer.from(String(value ?? ''));
  return markers.some(marker => bytes.includes(marker));
}

function safeFiles(folder, markers) {
  let left = 16 * 1024 * 1024, entries = 4096;
  function walk(directory, depth) {
    if (depth > 32) return false;
    return fs.readdirSync(directory, {withFileTypes: true}).every(entry => {
      if (--entries < 0 || contains(entry.name, markers)) return false;
      const file = path.join(directory, entry.name);
      if (entry.isSymbolicLink()) return !contains(fs.readlinkSync(file), markers);
      if (entry.isDirectory()) return walk(file, depth + 1);
      if (!entry.isFile()) return false;
      const size = fs.statSync(file).size;
      if ((left -= size) < 0) return false;
      const raw = fs.readFileSync(file);
      return raw.length === size && !contains(raw, markers);
    });
  }
  try { return walk(folder, 0); }
  catch (_) { return false; }
}

module.exports = {contains, safeFiles};
