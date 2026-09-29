const test = require('node:test');
const assert = require('node:assert/strict');
const { start, shoot } = require('../game-state');

test('a shot ledger reports cumulative totals and finishes when all names are sunk', () => {
  const game = start();
  const first = shoot(game, 1, 1);
  assert.equal(first.result, 'miss');
  assert.equal(first.shots, 1);
  const partial = shoot(game, 10, 9);
  assert.equal(partial.result, 'hit');
  assert.equal(partial.hits, 1);
  const sunk = shoot(game, 9, 10);
  assert.equal(sunk.result, 'sunk');
  assert.equal(typeof sunk.ship, 'string');
  assert.equal(sunk.gameOver, false);
  const final = shoot(game, 10, 10);
  assert.equal(final.result, 'sunk');
  assert.equal(final.gameOver, true);
  assert.equal(final.hits, 3);
});
