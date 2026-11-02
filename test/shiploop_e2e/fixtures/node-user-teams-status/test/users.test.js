'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const { getUser, listUsers } = require('../src/users');

test('getUser finds a user by id and returns null otherwise', () => {
  assert.equal(getUser(2).name, 'Grace Hopper');
  assert.equal(getUser(99), null);
});

test('listUsers returns every user', () => {
  assert.equal(listUsers().length, 3);
});
