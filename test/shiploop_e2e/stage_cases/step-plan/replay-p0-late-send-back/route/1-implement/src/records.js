'use strict';

// Parse line-oriented key/value records.
/** Parse a string into records; throws TypeError or line-numbered SyntaxError. */
function parseRecords(text) {
  if (typeof text !== 'string') throw new TypeError('parseRecords: text must be a string');

  const records = [];
  const lines = text.split('\n');
  for (let i = 0; i < lines.length; i++) {
    if (lines[i].trim() === '') continue;
    const record = {};
    for (const field of lines[i].split(';')) {
      const equals = field.indexOf('=');
      const key = field.slice(0, equals);
      if (equals < 0 || !/^[a-z][a-z0-9_]*$/.test(key) || Object.hasOwn(record, key)) {
        throw new SyntaxError(`parseRecords: malformed field on line ${i + 1}`);
      }
      Object.defineProperty(record, key, {
        value: field.slice(equals + 1).trim(), enumerable: true, writable: true, configurable: true
      });
    }
    records.push(record);
  }
  return records;
}

module.exports = { parseRecords };
