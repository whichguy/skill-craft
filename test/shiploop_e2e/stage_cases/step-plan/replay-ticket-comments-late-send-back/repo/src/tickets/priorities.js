'use strict';

/** Ticket priorities, lowest first. A ticket is "normal" unless its requester says otherwise. */

const PRIORITIES = Object.freeze(['low', 'normal', 'high', 'urgent']);
const DEFAULT_PRIORITY = 'normal';

function isPriority(value) {
  return PRIORITIES.includes(value);
}

/** The position of `priority` in PRIORITIES: higher is more pressing; -1 for anything else. */
function rank(priority) {
  return PRIORITIES.indexOf(priority);
}

module.exports = { DEFAULT_PRIORITY, PRIORITIES, isPriority, rank };
