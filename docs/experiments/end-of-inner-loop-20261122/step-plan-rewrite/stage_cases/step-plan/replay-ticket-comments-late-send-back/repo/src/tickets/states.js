'use strict';

/**
 * A ticket's lifecycle:
 *
 *   open ──► in_progress ──► resolved ──► closed
 *     ▲                          │
 *     └─────────── reopen ───────┘
 *
 * closed is final. A transition outside this table conflicts with the ticket's state (409).
 */

const STATUSES = Object.freeze(['open', 'in_progress', 'resolved', 'closed']);

const TRANSITIONS = Object.freeze({
  open: Object.freeze(['in_progress']),
  in_progress: Object.freeze(['resolved']),
  resolved: Object.freeze(['closed', 'open']),
  closed: Object.freeze([]),
});

/** The statuses of a ticket someone still has to work on. */
const ACTIVE = Object.freeze(['open', 'in_progress']);

function isStatus(value) {
  return STATUSES.includes(value);
}

function canTransition(from, to) {
  return isStatus(from) && TRANSITIONS[from].includes(to);
}

/** The statuses `status` can move to; none for a final status. */
function nextStatuses(status) {
  return isStatus(status) ? TRANSITIONS[status].slice() : [];
}

function isActive(status) {
  return ACTIVE.includes(status);
}

function isFinal(status) {
  return isStatus(status) && TRANSITIONS[status].length === 0;
}

module.exports = { ACTIVE, STATUSES, TRANSITIONS, canTransition, isActive, isFinal, isStatus, nextStatuses };
