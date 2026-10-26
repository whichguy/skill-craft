#!/usr/bin/env python3
"""The reference delivery of the `user-listing` case, for calibrating its held-out checks
(test/shiploop_e2e/checks/user_listing_accept.py) and the base's pristine tests (checks/base_tests.py pristine).

    python3 reference_user_listing.py DEST [--variant NAME]

writes a delivery into the empty folder DEST: the case's base (test/shiploop_e2e/fixtures/node-base) with a variant's files
written over it. The variants:

* ``base``: the base alone, as the run starts. It must fail every fail-to-pass check and pass the pass-to-pass ones.
* ``reference``: the base extended as the case's prompt asks (REFERENCE). ``paginate`` keeps its partial last page, the
  base's latent defect, which the prompt does not name.
* ``alternative``: an independently written delivery (ALTERNATIVE). It leaves ``paginate`` as the base has it and pages in the
  server, filters through ``listUsers``, validates with ``Number``, and answers extra fields. A correct delivery the checks
  must not reject.
* each name of DEFECTS: the reference with one targeted change, each a sentence of the prompt broken. Two break a base module
  and edit the base's tests to match, so their own suite passes and only the pristine one can see them.

Each defect is a list of (path, old, new) replacements; ``old`` must occur exactly once in its file, so a defect that no
longer applies fails loudly instead of building the reference.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import shutil

BASE = Path(__file__).resolve().parents[2] / "shiploop_e2e" / "fixtures" / "node-base"

REFERENCE = {
    "src/paginate.js": r"""'use strict';

/**
 * Return page `page` (1-based) of `items`, `size` items per page, with the page count.
 */
function paginate(items, page, size) {
  if (!Array.isArray(items)) throw new TypeError('items must be an array');
  if (!Number.isInteger(size) || size < 1) throw new RangeError('size must be a positive integer');
  if (!Number.isInteger(page) || page < 1) throw new RangeError('page must be a positive integer');
  const pages = Math.ceil(items.length / size);
  const start = (page - 1) * size;
  return { page, pages, items: page <= pages ? items.slice(start, start + size) : [] };
}

module.exports = { paginate };
""",
    "src/users.js": r"""'use strict';

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

/** The users whose name contains `text` as plain text, ignoring case, in id order (every user for an empty `text`). */
function findUsers(text) {
  const wanted = text.toLowerCase();
  return USERS.filter((user) => user.name.toLowerCase().includes(wanted));
}

module.exports = { findUsers, getUser, listUsers };
""",
    "src/server.js": r"""'use strict';

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
function listing(res, query) {
  const users = query.has('name') ? findUsers(query.get('name')) : listUsers();
  if (!query.has('page') && !query.has('size')) return send(res, 200, users);
  const page = query.has('page') ? wholeNumber(query.get('page'), 1, Number.MAX_SAFE_INTEGER) : 1;
  const size = query.has('size') ? wholeNumber(query.get('size'), 1, MAX_SIZE) : DEFAULT_SIZE;
  if (page === null) return send(res, 400, { error: 'page must be a whole number of at least 1' });
  if (size === null) return send(res, 400, { error: `size must be a whole number from 1 to ${MAX_SIZE}` });
  const { pages, items } = paginate(users, page, size);
  return send(res, 200, { page, size, total: users.length, pages, items });
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
        return user ? send(res, 200, user) : send(res, 404, { error: 'not found' });
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
""",
    "test/user-listing.test.js": r"""'use strict';

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
""",
}

ALTERNATIVE = {
    "src/users.js": r"""'use strict';

const USERS = [
  { id: 1, name: 'Ada Lovelace', email: 'ada@example.com' },
  { id: 2, name: 'Grace Hopper', email: 'grace@example.com' },
  { id: 3, name: 'Alan Turing', email: 'alan@example.com' },
];

/** The user with `id`, or null. */
function getUser(id) {
  return USERS.find((user) => user.id === id) || null;
}

/** Every user in id order; with `name`, only those whose name contains it, ignoring case. */
function listUsers({ name } = {}) {
  if (name === undefined) return USERS.slice();
  const needle = name.toLocaleLowerCase('en');
  return USERS.filter((user) => user.name.toLocaleLowerCase('en').indexOf(needle) !== -1);
}

module.exports = { getUser, listUsers };
""",
    "src/server.js": r"""'use strict';

const http = require('node:http');
const { getUser, listUsers } = require('./users');

const LIMITS = { page: [1, Infinity], size: [1, 100] };

function json(res, status, body) {
  res.writeHead(status, { 'content-type': 'application/json; charset=utf-8' });
  res.end(JSON.stringify(body));
}

class BadParameter extends Error {}

function whole(name, text) {
  const number = Number(text);
  const [low, high] = LIMITS[name];
  if (!Number.isInteger(number) || String(number) !== text || number < low || number > high) {
    throw new BadParameter(`${name} must be a whole number from ${low} to ${high}`);
  }
  return number;
}

function usersAnswer(query) {
  const users = listUsers(query.has('name') ? { name: query.get('name') } : {});
  if (!query.has('page') && !query.has('size')) return users;
  const page = query.has('page') ? whole('page', query.get('page')) : 1;
  const size = query.has('size') ? whole('size', query.get('size')) : 10;
  const pages = Math.ceil(users.length / size);
  return { items: users.slice((page - 1) * size, page * size), total: users.length, page, pages, size,
           next: page < pages ? page + 1 : null };
}

function createServer() {
  return http.createServer((req, res) => {
    const url = new URL(req.url, 'http://localhost');
    if (req.method !== 'GET') return json(res, 404, { error: 'not found' });
    if (url.pathname === '/users') {
      try {
        return json(res, 200, usersAnswer(url.searchParams));
      } catch (error) {
        if (error instanceof BadParameter) return json(res, 400, { error: error.message, status: 400 });
        throw error;
      }
    }
    const match = /^\/users\/(\d+)$/.exec(url.pathname);
    const user = match && getUser(Number(match[1]));
    return user ? json(res, 200, user) : json(res, 404, { error: 'not found' });
  });
}

if (require.main === module) {
  const port = Number(process.env.PORT) || 3000;
  createServer().listen(port, () => console.log(`listening on ${port}`));
}

module.exports = { createServer };
""",
    "test/listing.test.js": r"""'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const { listUsers } = require('../src/users');
const { createServer } = require('../src/server');

test('listUsers filters by part of a name, ignoring case', () => {
  assert.deepEqual(listUsers({ name: 'HOP' }).map((u) => u.name), ['Grace Hopper']);
  assert.equal(listUsers().length, 3);
});

test('the listing pages and refuses a page size over 100', async () => {
  const server = createServer().listen(0, '127.0.0.1');
  await new Promise((resolve) => server.once('listening', resolve));
  const base = `http://127.0.0.1:${server.address().port}`;
  try {
    const paged = await (await fetch(`${base}/users?page=2&size=2`)).json();
    assert.deepEqual([paged.pages, paged.items.length, paged.next], [2, 1, null]);
    assert.equal((await fetch(`${base}/users?size=101`)).status, 400);
  } finally {
    server.close();
  }
});
""",
}

DEFECTS = {
    # The base's own paginate: it drops a partial last page (Math.floor), the latent defect the prompt does not name.
    "floor-pages": [("src/paginate.js", "Math.ceil(items.length / size)", "Math.floor(items.length / size)")],
    "regex-filter": [("src/users.js", "user.name.toLowerCase().includes(wanted)",
                      "new RegExp(wanted).test(user.name.toLowerCase())")],
    "case-sensitive": [("src/users.js", "user.name.toLowerCase().includes(wanted)", "user.name.includes(text)")],
    "parseint": [("src/server.js", "  if (!/^\\d+$/.test(text)) return null;\n  const value = Number(text);\n",
                  "  const value = Number.parseInt(text, 10);\n  if (Number.isNaN(value)) return null;\n")],
    "no-size-cap": [("src/server.js", "const MAX_SIZE = 100;", "const MAX_SIZE = Infinity;")],
    "size-cap-off-by-one": [("src/server.js", "value >= min && value <= max", "value >= min && value < max")],
    "default-size-20": [("src/server.js", "const DEFAULT_SIZE = 10;", "const DEFAULT_SIZE = 20;")],
    "always-envelope": [("src/server.js", "  if (!query.has('page') && !query.has('size')) return send(res, 200, users);\n", "")],
    "unknown-param-400": [("src/server.js", "function listing(res, query) {\n",
                           "function listing(res, query) {\n  for (const key of query.keys()) {\n"
                           "    if (!['name', 'page', 'size'].includes(key)) return send(res, 400, { error: `unknown ${key}` });\n"
                           "  }\n")],
    "id-route-shadowed": [("src/server.js", "url.pathname === '/users'", "url.pathname.startsWith('/users')")],
    "past-end-404": [("src/server.js", "  const { pages, items } = paginate(users, page, size);\n",
                      "  const { pages, items } = paginate(users, page, size);\n"
                      "  if (page > Math.max(pages, 1)) return send(res, 404, { error: 'no such page' });\n")],
    "total-ignores-filter": [("src/server.js", "total: users.length", "total: listUsers().length")],
    # Two that break a base module and edit the base's tests to match: their own suite passes, the pristine one cannot.
    "list-users-envelope": [("src/users.js", "  return USERS.slice();\n", "  return { total: USERS.length, items: USERS.slice() };\n"),
                            ("src/server.js", ": listUsers();", ": listUsers().items;"),
                            ("test/users.test.js", "listUsers().length", "listUsers().items.length")],
    "paginate-options": [("src/paginate.js", "function paginate(items, page, size) {", "function paginate(items, { page, size }) {"),
                         ("src/server.js", "paginate(users, page, size)", "paginate(users, { page, size })"),
                         ("test/paginate.test.js", "paginate(items, 1, 3)", "paginate(items, { page: 1, size: 3 })"),
                         ("test/paginate.test.js", "paginate(items, 2, 3)", "paginate(items, { page: 2, size: 3 })"),
                         ("test/paginate.test.js", "paginate([1], 1, 0)", "paginate([1], { page: 1, size: 0 })"),
                         ("test/user-listing.test.js", "paginate([1, 2, 3], 2, 2)", "paginate([1, 2, 3], { page: 2, size: 2 })"),
                         ("test/user-listing.test.js", "paginate([], 1, 2)", "paginate([], { page: 1, size: 2 })")],
}
VARIANTS = ("base", "reference", "alternative", *DEFECTS)


def build(dest: Path, variant: str = "reference") -> Path:
    """Write the delivery of `variant` into `dest` (created if missing) and return it."""
    if variant not in VARIANTS:
        raise ValueError(f"unknown variant {variant!r}; known: {', '.join(VARIANTS)}")
    dest = Path(dest)
    shutil.copytree(BASE, dest, dirs_exist_ok=True)
    if variant == "base":
        return dest
    for relative, text in (ALTERNATIVE if variant == "alternative" else REFERENCE).items():
        (dest / relative).parent.mkdir(parents=True, exist_ok=True)
        (dest / relative).write_text(text)
    for relative, old, new in DEFECTS.get(variant, ()):
        text = (dest / relative).read_text()
        if text.count(old) != 1:
            raise ValueError(f"defect {variant}: {old!r} occurs {text.count(old)} times in {relative}, not once")
        (dest / relative).write_text(text.replace(old, new))
    return dest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("dest", type=Path)
    parser.add_argument("--variant", default="reference", choices=VARIANTS)
    args = parser.parse_args()
    print(build(args.dest, args.variant))


if __name__ == "__main__":
    main()
