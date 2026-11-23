'use strict';

const fs = require('node:fs');
const { render } = require('./templates');

/**
 * Sends notifications. Only the worker calls it, for events the outbox says are due.
 *
 * With a file (NOTIFY_FILE), each delivery appends one JSON line to it; in production the mail relay tails that file.
 * Without one, deliveries are kept in memory (`delivered`), which is what tests and local runs use. A line:
 *
 *   { at, id, key, type, to, ticket, subject, body }
 */
function createNotifier({ file = null, clock }) {
  const delivered = [];
  return {
    file,
    delivered,
    /** Render and send one outbox event; throws when it cannot, and the worker records the failure. */
    deliver(event) {
      const message = render(event);
      const line = {
        at: clock.now().toISOString(),
        id: event.id,
        key: event.key,
        type: event.type,
        to: event.to,
        ticket: event.ticket,
        ...message,
      };
      if (file) fs.appendFileSync(file, `${JSON.stringify(line)}\n`);
      else delivered.push(line);
      return line;
    },
  };
}

module.exports = { createNotifier };
