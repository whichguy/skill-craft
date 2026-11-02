'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const { createServer } = require('../src/server');

async function withServer(run) {
  const server = createServer();
  await new Promise((resolve) => server.listen(0, '127.0.0.1', resolve));
  try {
    await run('http://127.0.0.1:' + server.address().port);
  } finally {
    await new Promise((resolve) => server.close(resolve));
  }
}

async function get(base, path) {
  const response = await fetch(base + path);
  return { status: response.status, body: await response.json() };
}

test('team filters are exact, combine with name, and run before paging', async () => {
  await withServer(async (base) => {
    assert.deepEqual((await get(base, '/users?team=Engineering')).body.map((user) => user.id), [1, 2]);
    assert.deepEqual((await get(base, '/users?team=Support')).body.map((user) => user.id), [3]);
    assert.deepEqual((await get(base, '/users?team=Eng')).body, []);
    assert.deepEqual((await get(base, '/users?team=')).body, []);
    assert.deepEqual((await get(base, '/users?team=unknown')).body, []);
    assert.deepEqual((await get(base, '/users?team=engineering')).body, []);
    assert.equal((await get(base, '/users?name=Alan&team=Engineering&page=1&size=1')).body.total, 0);
    const { status, body } = await get(base, '/users?name=e&team=Engineering&page=2&size=1');
    assert.equal(status, 200);
    assert.deepEqual({ page: body.page, size: body.size, total: body.total, pages: body.pages,
                       items: body.items.map((user) => user.id) },
                     { page: 2, size: 1, total: 2, pages: 2, items: [2] });
  });
});

test('include=team is opt-in for arrays, page items, and by-id users', async () => {
  await withServer(async (base) => {
    const plain = await get(base, '/users');
    assert.deepEqual(plain.body, [
      { id: 1, name: 'Ada Lovelace', email: 'ada@example.com' },
      { id: 2, name: 'Grace Hopper', email: 'grace@example.com' },
      { id: 3, name: 'Alan Turing', email: 'alan@example.com' },
    ]);
    const included = await get(base, '/users?include=team');
    assert.equal(included.body[0].team, 'Engineering');
    const page = await get(base, '/users?page=1&size=2&include=team');
    assert.deepEqual(page.body.items.map((user) => user.team), ['Engineering', 'Engineering']);
    assert.equal((await get(base, '/users/1?include=team')).body.team, 'Engineering');
    assert.equal((await get(base, '/users/1?include=TEAM')).body.team, undefined);
    assert.equal((await get(base, '/users/1?include=team,x')).body.team, undefined);
    assert.equal((await get(base, '/users/1?include=')).body.team, undefined);
  });
});
