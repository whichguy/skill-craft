'use strict';

const USERS = [
  { id: 1, name: 'Ada Lovelace', email: 'ada@example.com' },
  { id: 2, name: 'Grace Hopper', email: 'grace@example.com' },
  { id: 3, name: 'Alan Turing', email: 'alan@example.com' },
];

/** The user with `id`, or null. */
function getUser(id) {
  return USERS.find((user) => user.id === id) || null;
}

/** Every user, in id order. */
function listUsers() {
  return USERS.slice();
}

module.exports = { getUser, listUsers };
