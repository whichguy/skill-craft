'use strict';

const { InvalidError, toResponse } = require('./errors');

/** JSON in and out of node:http, and the request's actor. */

const JSON_TYPE = 'application/json; charset=utf-8';
/** The longest X-Actor the service records. The same limit as a requester's name. */
const ACTOR_LIMIT = 64;

/** Answer `body` as JSON with `status`. */
function sendJson(res, status, body) {
  const text = JSON.stringify(body);
  res.writeHead(status, { 'content-type': JSON_TYPE, 'content-length': Buffer.byteLength(text) });
  res.end(text);
}

/** Answer a thrown error in the envelope (docs/decisions/0004-error-envelope.md). Returns the status sent. */
function sendError(res, error) {
  const { status, body } = toResponse(error);
  sendJson(res, status, body);
  return status;
}

/**
 * The request body as a JSON object. An empty body, a body over `limit` bytes, text that is not JSON and JSON that is
 * not an object are each an InvalidError. A body over the limit is read to its end and dropped, so the client gets the
 * answer instead of a connection reset in the middle of its upload.
 */
async function readJson(req, { limit = 64 * 1024 } = {}) {
  const chunks = [];
  let size = 0;
  for await (const chunk of req) {
    size += chunk.length;
    if (size <= limit) chunks.push(chunk);
  }
  if (size > limit) throw new InvalidError(`request body is larger than ${limit} bytes`);
  const text = Buffer.concat(chunks).toString('utf8');
  if (text.trim() === '') throw new InvalidError('request body must be a JSON object');
  let value;
  try {
    value = JSON.parse(text);
  } catch {
    throw new InvalidError('request body is not valid JSON');
  }
  if (value === null || typeof value !== 'object' || Array.isArray(value)) {
    throw new InvalidError('request body must be a JSON object');
  }
  return value;
}

/**
 * Who makes a change: the X-Actor header, trimmed, or "system" when it is absent or blank. The audit log records it
 * on every entry (docs/decisions/0007-append-only-audit-log.md).
 */
function actorOf(req) {
  const header = req.headers['x-actor'];
  const actor = (Array.isArray(header) ? header[0] : header ?? '').trim();
  if (actor.length > ACTOR_LIMIT) throw new InvalidError(`X-Actor must be at most ${ACTOR_LIMIT} characters`);
  return actor === '' ? 'system' : actor;
}

module.exports = { ACTOR_LIMIT, JSON_TYPE, actorOf, readJson, sendError, sendJson };
