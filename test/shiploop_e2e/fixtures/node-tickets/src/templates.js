'use strict';

/**
 * What each kind of notification says. The notifier renders an event with the template of its type. An event whose type
 * has no template cannot be delivered: the worker records the failure, retries it and in the end marks it dead.
 */

const TEMPLATES = Object.freeze({
  'ticket.created': (event) => ({
    subject: `[${event.ticket}] We received your request`,
    body: `Your request "${event.data.title}" is ticket ${event.ticket}. The help desk will be in touch.`,
  }),
  'ticket.resolved': (event) => ({
    subject: `[${event.ticket}] Resolved`,
    body: `Ticket ${event.ticket} "${event.data.title}" was resolved. Reply within 7 days to reopen it.`,
  }),
});

/** { subject, body } for an outbox event. Throws for a type with no template. */
function render(event) {
  const template = TEMPLATES[event.type];
  if (!template) throw new Error(`no template for notification type ${event.type}`);
  return template(event);
}

module.exports = { TEMPLATES, render };
