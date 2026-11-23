'use strict';

/**
 * Errors a client can see. Every one is answered in the same envelope (docs/decisions/0004-error-envelope.md):
 *
 *   {"error": {"code": "<code>", "message": "<what went wrong>"}}
 *
 * with the HTTP status its code implies. Code that rejects a request throws one of the classes below; nothing writes
 * an error response by hand.
 */

const STATUS_BY_CODE = Object.freeze({
  invalid: 400,
  not_found: 404,
  conflict: 409,
  internal: 500,
});

class AppError extends Error {
  constructor(code, message, details) {
    super(message);
    if (!Object.hasOwn(STATUS_BY_CODE, code)) throw new TypeError(`unknown error code ${code}`);
    this.name = 'AppError';
    this.code = code;
    this.status = STATUS_BY_CODE[code];
    if (details !== undefined) this.details = details;
  }
}

/** The request itself is wrong: a malformed body, a field out of range, an unknown query value. 400. */
class InvalidError extends AppError {
  constructor(message, details) {
    super('invalid', message, details);
    this.name = 'InvalidError';
  }
}

/** The thing the request names does not exist. 404. */
class NotFoundError extends AppError {
  constructor(message, details) {
    super('not_found', message, details);
    this.name = 'NotFoundError';
  }
}

/** The request is well formed but the ticket's state does not allow it. 409. */
class ConflictError extends AppError {
  constructor(message, details) {
    super('conflict', message, details);
    this.name = 'ConflictError';
  }
}

/** The status and envelope for anything thrown: an AppError as it is; anything else is an internal error. */
function toResponse(error) {
  if (error instanceof AppError) {
    const body = { error: { code: error.code, message: error.message } };
    if (error.details !== undefined) body.error.details = error.details;
    return { status: error.status, body };
  }
  return { status: STATUS_BY_CODE.internal, body: { error: { code: 'internal', message: 'internal error' } } };
}

module.exports = { AppError, ConflictError, InvalidError, NotFoundError, STATUS_BY_CODE, toResponse };
