'use strict';

const { InvalidError } = require('../errors');
const { DEFAULT_PRIORITY, PRIORITIES, isPriority } = require('./priorities');
const { STATUSES, isStatus } = require('./states');

/**
 * Request bodies, checked before they reach the store. Each function takes the parsed JSON object and returns the
 * values the store needs, or throws InvalidError (400) naming the field that is wrong.
 */

const LIMITS = Object.freeze({ title: 200, requester: 64 });
// Tabs and line breaks would break the command line's tab-separated output (README.md, "Command line").
const CONTROL = /[\u0000-\u001f\u007f]/;

/** A required single-line text field: trimmed, not empty, at most `max` characters, no control characters. */
function text(body, name, max) {
  const value = body[name];
  if (typeof value !== 'string') throw new InvalidError(`${name} must be a string`);
  const trimmed = value.trim();
  if (trimmed === '') throw new InvalidError(`${name} must not be empty`);
  if (trimmed.length > max) throw new InvalidError(`${name} must be at most ${max} characters`);
  if (CONTROL.test(trimmed)) throw new InvalidError(`${name} must be a single line of text`);
  return trimmed;
}

/** Refuse fields the endpoint does not take, so a misspelt field is an error and not silently ignored. */
function onlyFields(body, allowed) {
  const unknown = Object.keys(body).filter((key) => !allowed.includes(key));
  if (unknown.length) throw new InvalidError(`unknown field${unknown.length > 1 ? 's' : ''}: ${unknown.join(', ')}`);
}

function priority(value) {
  if (!isPriority(value)) throw new InvalidError(`priority must be one of ${PRIORITIES.join(', ')}`);
  return value;
}

/** POST /tickets: { title, requester, priority? }. */
function newTicket(body) {
  onlyFields(body, ['title', 'requester', 'priority']);
  return {
    title: text(body, 'title', LIMITS.title),
    requester: text(body, 'requester', LIMITS.requester),
    priority: body.priority === undefined ? DEFAULT_PRIORITY : priority(body.priority),
  };
}

/** PATCH /tickets/:id: { title?, priority? }, at least one of them. */
function ticketPatch(body) {
  onlyFields(body, ['title', 'priority']);
  const patch = {};
  if (body.title !== undefined) patch.title = text(body, 'title', LIMITS.title);
  if (body.priority !== undefined) patch.priority = priority(body.priority);
  if (Object.keys(patch).length === 0) throw new InvalidError('nothing to change: give a title or a priority');
  return patch;
}

/** POST /tickets/:id/transition: { to }. Whether the ticket may move there is the store's question. */
function transition(body) {
  onlyFields(body, ['to']);
  if (!isStatus(body.to)) throw new InvalidError(`to must be one of ${STATUSES.join(', ')}`);
  return body.to;
}

module.exports = { LIMITS, newTicket, onlyFields, text, ticketPatch, transition };
