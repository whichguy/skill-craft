'use strict';

const { describe, test } = require('node:test');
const assert = require('node:assert/strict');
const { InvalidError } = require('../src/errors');
const { encodeCursor } = require('../src/pagination');
const { matchesFilters, parseListQuery } = require('../src/tickets/query');

const query = (text) => parseListQuery(new URLSearchParams(text));

describe('parseListQuery', () => {
  test('defaults to no filter, 20 a page, from the start', () => {
    assert.deepEqual(query(''), { filters: {}, limit: 20, after: null });
  });

  test('reads a status filter and a priority filter', () => {
    assert.deepEqual(query('status=in_progress').filters, { status: 'in_progress' });
    assert.deepEqual(query('priority=urgent').filters, { priority: 'urgent' });
  });

  test('refuses a filter value that is not a status or a priority', () => {
    assert.throws(() => query('status=done'), InvalidError);
    assert.throws(() => query('priority=critical'), InvalidError);
    assert.throws(() => query('status='), InvalidError);
  });

  test('takes a limit from 1 to 100', () => {
    assert.equal(query('limit=1').limit, 1);
    assert.equal(query('limit=100').limit, 100);
    for (const limit of ['0', '101', '2.5', '-1', 'ten', '']) {
      assert.throws(() => query(`limit=${limit}`), InvalidError, limit);
    }
  });

  test('reads the cursor of an earlier page', () => {
    assert.equal(query(`cursor=${encodeCursor('T-0040')}`).after, 'T-0040');
    assert.throws(() => query('cursor=not-ours'), InvalidError);
  });

  test('ignores parameters it does not know, offset included', () => {
    assert.deepEqual(query('offset=40&sort=title'), { filters: {}, limit: 20, after: null });
  });
});

describe('matchesFilters', () => {
  const ticket = { id: 'T-0001', status: 'open', priority: 'high' };

  test('passes every ticket when there is no filter', () => {
    assert.equal(matchesFilters(ticket, {}), true);
  });

  test('keeps a ticket whose status is the one asked for', () => {
    assert.equal(matchesFilters(ticket, { status: 'open' }), true);
    assert.equal(matchesFilters(ticket, { status: 'closed' }), false);
  });

  test('keeps a ticket whose priority is the one asked for', () => {
    assert.equal(matchesFilters(ticket, { priority: 'high' }), true);
    assert.equal(matchesFilters(ticket, { priority: 'low' }), false);
  });
});
