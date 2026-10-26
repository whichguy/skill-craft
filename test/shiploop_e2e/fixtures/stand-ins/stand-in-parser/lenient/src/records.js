'use strict';
/** A stand-in that accepts any input: malformed fields are skipped, never refused. */
function parseRecords(text) {
  return String(text).split('\n').map((l) => l.trim()).filter(Boolean).map((line) => {
    const record = {};
    for (const part of line.split(';')) {
      const at = part.indexOf('=');
      if (at > 0) record[part.slice(0, at).trim()] = part.slice(at + 1).trim();
    }
    return record;
  });
}
function select(records, field, value) {
  if (!Array.isArray(records)) throw new TypeError('select: records must be an array');
  return records.filter((record) => record[field] === value);
}
module.exports = { parseRecords, select };
