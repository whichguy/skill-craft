'use strict';

const http = require('node:http');
const { paginate } = require('./paginate');
const { findUsers, getUser, listUsers } = require('./users');

const DEFAULT_SIZE = 10;
const MAX_SIZE = 100;

function send(res, status, body) {
  res.writeHead(status, { 'content-type': 'application/json' });
  res.end(JSON.stringify(body));
}

/** A query value that must be a whole number from `min` to `max`: that number, or null for any other text. */
function wholeNumber(text, min, max) {
  if (!/^\d+$/.test(text)) return null;
  const value = Number(text);
  return value >= min && value <= max ? value : null;
}

/** GET /users: every user, or those whose name contains `name`; one page of them when `page` or `size` is given. */
function selectedUsers(query) {
  const users = query.has('name') ? findUsers(query.get('name')) : listUsers();
  if (!query.has('team')) return users;
  return users.filter((user) => user.team === query.get('team'));
}

function publicUser(user, includeTeam) {
  const { team, ...ordinary } = user;
  return includeTeam ? { ...ordinary, team } : ordinary;
}

function listing(res, query) {
  const users = selectedUsers(query);
  const withTeam = query.get('include') === 'team';
  if (!query.has('page') && !query.has('size')) return send(res, 200, users.map((user) => publicUser(user, withTeam)));
  const page = query.has('page') ? wholeNumber(query.get('page'), 1, Number.MAX_SAFE_INTEGER) : 1;
  const size = query.has('size') ? wholeNumber(query.get('size'), 1, MAX_SIZE) : DEFAULT_SIZE;
  if (page === null) return send(res, 400, { error: 'page must be a whole number of at least 1' });
  if (size === null) return send(res, 400, { error: 'size must be a whole number from 1 to ' + MAX_SIZE });
  const { pages, items } = paginate(users, page, size);
  return send(res, 200, { page, size, total: users.length, pages, items: items.map((user) => publicUser(user, withTeam)) });
}

/** An HTTP server for the user store; not listening until the caller calls listen(). */
function createServer() {
  return http.createServer((req, res) => {
    try {
      const url = new URL(req.url, 'http://localhost');
      if (req.method === 'GET' && url.pathname === '/users') return listing(res, url.searchParams);
      const match = /^\/users\/(\d+)$/.exec(url.pathname);
      if (req.method === 'GET' && match) {
        const user = getUser(Number(match[1]));
        return user ? send(res, 200, publicUser(user, url.searchParams.get('include') === 'team')) : send(res, 404, { error: 'not found' });
      }
      return send(res, 404, { error: 'not found' });
    } catch (error) {
      return send(res, 500, { error: 'internal error' });
    }
  });
}

if (require.main === module) {
  const port = Number(process.env.PORT) || 3000;
  createServer().listen(port, () => console.log(`listening on ${port}`));
}

module.exports = { createServer };
