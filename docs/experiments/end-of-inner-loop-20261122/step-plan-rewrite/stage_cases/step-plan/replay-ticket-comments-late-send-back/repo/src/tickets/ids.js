'use strict';

/**
 * Ticket ids: a prefix and a sequence number, T-0001, T-0002, ... (docs/decisions/0002-prefixed-sequential-ids.md).
 *
 * The number is padded to four digits and grows past them (T-10000). A number is used once: the store keeps the next
 * number, the data file saves it, and a data file whose next number would reuse one is refused.
 */

const PREFIX = 'T-';
const WIDTH = 4;
const PATTERN = /^T-(\d{4,})$/;

/** The id of ticket number `number` (a positive integer). */
function formatId(number) {
  if (!Number.isSafeInteger(number) || number < 1) {
    throw new RangeError(`a ticket number must be a positive integer, not ${number}`);
  }
  return PREFIX + String(number).padStart(WIDTH, '0');
}

/** The number of a ticket id, or null for text that is not an id in its one written form (T-0007, not T-07). */
function parseId(text) {
  const match = typeof text === 'string' ? PATTERN.exec(text) : null;
  if (!match) return null;
  const number = Number(match[1]);
  return Number.isSafeInteger(number) && number >= 1 && formatId(number) === text ? number : null;
}

/** Sort order of two ticket ids: by number, so T-9999 comes before T-10000. */
function compareIds(a, b) {
  return parseId(a) - parseId(b);
}

module.exports = { PREFIX, compareIds, formatId, parseId };
