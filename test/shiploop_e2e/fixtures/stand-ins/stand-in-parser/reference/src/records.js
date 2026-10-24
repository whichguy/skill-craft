'use strict';
/**
 * Parse text with one record per non-blank line, fields as `key=value` joined by `;`.
 * Throws SyntaxError naming the 1-based line for a malformed line; TypeError for a non-string.
 */
function parseRecords(text) {
  if (typeof text !== 'string') throw new TypeError('parseRecords: text must be a string');
  const records = [];
  text.split('\n').forEach((raw, index) => {
    const line = raw.trim();
    if (!line) return;
    const record = {};
    for (const part of line.split(';')) {
      const at = part.indexOf('=');
      const key = at > 0 ? part.slice(0, at).trim() : '';
      if (!key || !/^[a-z][a-z0-9_]*$/.test(key) || key in record) {
        throw new SyntaxError(`parseRecords: malformed field on line ${index + 1}`);
      }
      record[key] = part.slice(at + 1).trim();
    }
    records.push(record);
  });
  return records;
}

/** The records whose `field` equals `value`, in input order. Throws TypeError for a non-array. */
function select(records, field, value) {
  if (!Array.isArray(records)) throw new TypeError('select: records must be an array');
  return records.filter((record) => record[field] === value);
}

module.exports = { parseRecords, select };
