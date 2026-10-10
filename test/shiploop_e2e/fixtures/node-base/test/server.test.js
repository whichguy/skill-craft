'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const { createServer } = require('../src/server');

async function withServer(run) {
  const server = createServer();
  await new Promise((resolve) => server.listen(0, '127.0.0.1', resolve));
  try {
    await run(`http://127.0.0.1:${server.address().port}`);
  } finally {
    await new Promise((resolve) => server.close(resolve));
  }
}

test('GET /users/:id returns the user or 404', async () => {
  await withServer(async (base) => {
    const found = await fetch(`${base}/users/1`);
    assert.equal(found.status, 200);
    assert.equal((await found.json()).name, 'Ada Lovelace');
    assert.equal((await fetch(`${base}/users/42`)).status, 404);
  });
});
