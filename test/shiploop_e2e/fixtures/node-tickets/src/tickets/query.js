'use strict';

const { InvalidError } = require('../errors');
const { decodeCursor } = require('../pagination');
const { PRIORITIES, isPriority } = require('./priorities');
const { STATUSES, isStatus } = require('./states');

/**
 * The listing's query (docs/api.md, "List tickets"): its filters, the page size and where the page starts.
 *
 *   GET /tickets?status=open&priority=high&limit=20&cursor=<next of the previous page>
 */

const DEFAULT_LIMIT = 20;
const MAX_LIMIT = 100;

/** { filters, limit, after } from the search parameters of GET /tickets. A value it cannot use is an InvalidError. */
function parseListQuery(params) {
  const filters = {};
  if (params.has('status')) {
    const status = params.get('status');
    if (!isStatus(status)) throw new InvalidError(`status must be one of ${STATUSES.join(', ')}`);
    filters.status = status;
  }
  if (params.has('priority')) {
    const priority = params.get('priority');
    if (!isPriority(priority)) throw new InvalidError(`priority must be one of ${PRIORITIES.join(', ')}`);
    filters.priority = priority;
  }
  return { filters, limit: parseLimit(params), after: params.has('cursor') ? decodeCursor(params.get('cursor')) : null };
}

function parseLimit(params) {
  if (!params.has('limit')) return DEFAULT_LIMIT;
  const text = params.get('limit');
  const limit = /^\d+$/.test(text) ? Number(text) : NaN;
  if (!(limit >= 1 && limit <= MAX_LIMIT)) throw new InvalidError(`limit must be a whole number from 1 to ${MAX_LIMIT}`);
  return limit;
}

/** Whether `ticket` passes the listing's `filters` ({ field: value }). With no filter, every ticket passes. */
function matchesFilters(ticket, filters) {
  const given = Object.entries(filters).filter(([, value]) => value !== undefined);
  if (given.length === 0) return true;
  return given.some(([field, value]) => ticket[field] === value);
}

module.exports = { DEFAULT_LIMIT, MAX_LIMIT, matchesFilters, parseListQuery };
