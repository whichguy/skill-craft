'use strict';

const USERS = [
  { id: 1, name: 'Ada Lovelace', email: 'ada@example.com', team: 'Engineering' },
  { id: 2, name: 'Grace Hopper', email: 'grace@example.com', team: 'Engineering' },
  { id: 3, name: 'Alan Turing', email: 'alan@example.com', team: 'Support' },
];

/** The user with `id`, or null. */
function getUser(id) {
  return USERS.find((user) => user.id === id) || null;
}

/** Every user, in id order. */
function listUsers() {
  return USERS.slice();
}

/** The users whose name contains `text` as plain text, ignoring case, in id order (every user for an empty `text`). */
function findUsers(text) {
  const wanted = text.toLowerCase();
  return USERS.filter((user) => user.name.toLowerCase().includes(wanted));
}

module.exports = { findUsers, getUser, listUsers };
