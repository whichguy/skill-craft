'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const { createServer } = require('../src/server');
const { paginate } = require('../src/paginate');
const { findUsers } = require('../src/users');

async function withServer(run) {
  const server = createServer();
  await new Promise((resolve) => server.listen(0, '127.0.0.1', resolve));
  try {
    await run(`http://127.0.0.1:${server.address().port}`);
  } finally {
    await new Promise((resolve) => server.close(resolve));
  }
}

async function get(base, path) {
  const response = await fetch(base + path);
  return { status: response.status, body: await response.json() };
}

test('paginate keeps a partial last page and counts no page for no items', () => {
  assert.deepEqual(paginate([1, 2, 3], 2, 2), { page: 2, pages: 2, items: [3] });
  assert.deepEqual(paginate([], 1, 2), { page: 1, pages: 0, items: [] });
});

test('findUsers matches part of a name as plain text, ignoring case', () => {
  assert.deepEqual(findUsers('AL').map((user) => user.id), [3]);
  assert.deepEqual(findUsers('a.a'), []);
  assert.equal(findUsers('').length, 3);
});

test('GET /users without page or size answers the array, filtered by name', async () => {
  await withServer(async (base) => {
    assert.equal((await get(base, '/users')).body.length, 3);
    assert.deepEqual((await get(base, '/users?name=grace')).body.map((user) => user.id), [2]);
  });
});

test('GET /users pages the filtered users', async () => {
  await withServer(async (base) => {
    const { status, body } = await get(base, '/users?name=e&page=2&size=1');
    assert.equal(status, 200);
    assert.deepEqual({ ...body, items: body.items.map((user) => user.id) }, { page: 2, size: 1, total: 2, pages: 2, items: [2] });
    assert.deepEqual((await get(base, '/users?page=1')).body.size, 10);
  });
});

test('GET /users refuses a page or size that is not a whole number in range', async () => {
  await withServer(async (base) => {
    for (const query of ['page=0', 'page=1.5', 'size=101', 'size=']) {
      const { status, body } = await get(base, `/users?${query}`);
      assert.equal(status, 400, query);
      assert.equal(typeof body.error, 'string', query);
    }
  });
});
