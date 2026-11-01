#!/usr/bin/env python3
"""The reference delivery of the `user-roles` case, the second pass of chain B (user-listing, user-roles, user-team-listing, user-page-size), for
calibrating its checks (cases.json: the case's own checks and its retention checks), the base's pristine tests and the earlier pass's checks.

    python3 reference_user_roles.py DEST [--variant NAME]

writes a delivery into the empty folder DEST. A follow-on starts from the run before it, so every variant starts from user-listing's
reference (reference_user_listing.py), which stands in for the first pass. The variants:

* ``base``: user-listing's reference alone, as the second pass starts. It must fail every check of the new feature and pass the first
  pass's checks.
* ``reference``: the prompt done. A role is a field of the user record, named once in the store (ROLES) and checked once, at the
  listing's door; a user must match every filter given, and the page object counts the users that matched all of them, as the first
  pass's listing counts the users that matched `name`.
* ``alternative``: an independently written delivery (ALTERNATIVE): roles kept apart from the records in their own module, filters as a
  list of predicates, the answer extended with a field of its own. A correct delivery the checks must not reject.
* each name of DEFECTS: the reference with one targeted change, a sentence of the request or an inherited convention broken.

Each defect is a list of (path, old, new) replacements; ``old`` must occur exactly once in its file, so a defect that no longer applies
fails loudly instead of building the reference.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import reference_user_listing as first  # noqa: E402  (the first pass's stand-in, which this one starts from)

USERS_JS = r"""'use strict';

/** The roles a user can have. */
const ROLES = ['admin', 'member', 'viewer'];

const USERS = [
  { id: 1, name: 'Ada Lovelace', email: 'ada@example.com', role: 'admin' },
  { id: 2, name: 'Grace Hopper', email: 'grace@example.com', role: 'member' },
  { id: 3, name: 'Alan Turing', email: 'alan@example.com', role: 'viewer' },
];

/** The user with `id`, or null. */
function getUser(id) {
  return USERS.find((user) => user.id === id) || null;
}

/** Every user, in id order. */
function listUsers() {
  return USERS.slice();
}

/** The users whose name contains `text` as plain text, ignoring case, and who have `role` when one is given, in id order. */
function findUsers(text, role) {
  const wanted = text.toLowerCase();
  return USERS.filter((user) => user.name.toLowerCase().includes(wanted) && (role === undefined || user.role === role));
}

module.exports = { ROLES, findUsers, getUser, listUsers };
"""

SERVER_JS = r"""'use strict';

const http = require('node:http');
const { paginate } = require('./paginate');
const { ROLES, findUsers, getUser } = require('./users');

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

/** GET /users: the users whose name contains `name` and who have `role`; one page of them when `page` or `size` is given. */
function listing(res, query) {
  if (query.has('role') && !ROLES.includes(query.get('role'))) {
    return send(res, 400, { error: `role must be one of ${ROLES.join(', ')}` });
  }
  const users = findUsers(query.has('name') ? query.get('name') : '', query.has('role') ? query.get('role') : undefined);
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
"""

TEST_JS = r"""'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const { createServer } = require('../src/server');
const { ROLES, findUsers } = require('../src/users');

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

test('the roles are admin, member and viewer, and findUsers filters by role and name together', () => {
  assert.deepEqual(ROLES, ['admin', 'member', 'viewer']);
  assert.deepEqual(findUsers('', 'viewer').map((user) => user.id), [3]);
  assert.deepEqual(findUsers('a', 'admin').map((user) => user.id), [1]);
  assert.deepEqual(findUsers('grace', 'admin'), []);
});

test('a user shows its role by id, in the array and in the items of a page', async () => {
  await withServer(async (base) => {
    assert.equal((await get(base, '/users/1')).body.role, 'admin');
    assert.deepEqual((await get(base, '/users')).body.map((user) => user.role), ['admin', 'member', 'viewer']);
    assert.deepEqual((await get(base, '/users?page=1&size=3')).body.items.map((user) => user.role), ['admin', 'member', 'viewer']);
  });
});

test('role keeps the users with that role, together with name and page', async () => {
  await withServer(async (base) => {
    assert.deepEqual((await get(base, '/users?role=member')).body.map((user) => user.id), [2]);
    assert.deepEqual((await get(base, '/users?name=a&role=viewer')).body.map((user) => user.id), [3]);
    const { body } = await get(base, '/users?role=viewer&page=1&size=1');
    assert.deepEqual({ ...body, items: body.items.map((user) => user.id) }, { page: 1, size: 1, total: 1, pages: 1, items: [3] });
  });
});

test('a role that is none of the three, an empty one included, answers 400', async () => {
  await withServer(async (base) => {
    for (const query of ['role=owner', 'role=', 'role=root&page=1&size=2']) {
      const { status, body } = await get(base, `/users?${query}`);
      assert.equal(status, 400, query);
      assert.equal(typeof body.error, 'string', query);
    }
  });
});
"""

REFERENCE = {"src/users.js": USERS_JS, "src/server.js": SERVER_JS, "test/user-roles.test.js": TEST_JS}

ALTERNATIVE = {
    "src/roles.js": r"""'use strict';

const ROLE_OF = new Map([[1, 'admin'], [2, 'member'], [3, 'viewer']]);
const KNOWN = new Set(ROLE_OF.values());

const isRole = (text) => KNOWN.has(text);
const withRole = (user) => ({ ...user, role: ROLE_OF.get(user.id) });

module.exports = { KNOWN, isRole, withRole };
""",
    "src/server.js": r"""'use strict';

const http = require('node:http');
const { getUser, listUsers } = require('./users');
const { KNOWN, isRole, withRole } = require('./roles');

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

function filters(query) {
  const tests = [];
  if (query.has('name')) {
    const needle = query.get('name').toLocaleLowerCase('en');
    tests.push((user) => user.name.toLocaleLowerCase('en').indexOf(needle) !== -1);
  }
  if (query.has('role')) {
    if (!isRole(query.get('role'))) throw new BadParameter(`role must be one of ${[...KNOWN].join(', ')}`);
    tests.push((user) => user.role === query.get('role'));
  }
  return tests;
}

function usersAnswer(query) {
  const tests = filters(query);
  const users = listUsers().map(withRole).filter((user) => tests.every((test) => test(user)));
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
    return user ? json(res, 200, withRole(user)) : json(res, 404, { error: 'not found' });
  });
}

if (require.main === module) {
  const port = Number(process.env.PORT) || 3000;
  createServer().listen(port, () => console.log(`listening on ${port}`));
}

module.exports = { createServer };
""",
    "test/roles.test.js": r"""'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const { isRole, withRole } = require('../src/roles');
const { createServer } = require('../src/server');

test('three roles are known and a user takes its own', () => {
  assert.deepEqual(['admin', 'member', 'viewer', 'owner', ''].map(isRole), [true, true, true, false, false]);
  assert.equal(withRole({ id: 2, name: 'x' }).role, 'member');
});

test('the listing filters by role and refuses an unknown one', async () => {
  const server = createServer().listen(0, '127.0.0.1');
  await new Promise((resolve) => server.once('listening', resolve));
  const base = `http://127.0.0.1:${server.address().port}`;
  try {
    assert.deepEqual((await (await fetch(`${base}/users?role=admin`)).json()).map((u) => u.id), [1]);
    assert.equal((await (await fetch(`${base}/users/3`)).json()).role, 'viewer');
    assert.equal((await fetch(`${base}/users?role=owner`)).status, 400);
  } finally {
    server.close();
  }
});
""",
}

DEFECTS = {
    # The request: the role shows in every user the listing answers (here the listing drops it, the single user keeps it).
    "role-missing-in-listing": [("src/users.js", "(role === undefined || user.role === role));\n",
                                 "(role === undefined || user.role === role)).map(({ role: _role, ...rest }) => rest);\n")],
    # The request: the role shows in GET /users/:id.
    "role-missing-by-id": [("src/users.js", "  return USERS.find((user) => user.id === id) || null;\n",
                            "  const user = USERS.find((candidate) => candidate.id === id);\n"
                            "  if (!user) return null;\n  const { role: _role, ...rest } = user;\n  return rest;\n")],
    # The request: `role=<role>` keeps only the users with that role.
    "role-filter-ignored": [("src/users.js", "(role === undefined || user.role === role));\n", "true);\n")],
    # The request: a user must match every filter given (here a role replaces the name filter).
    "role-replaces-name": [("src/server.js", "findUsers(query.has('name') ? query.get('name') : '', ",
                            "findUsers(query.has('role') ? '' : query.has('name') ? query.get('name') : '', ")],
    # The first pass's rule: `total` counts the users that matched and `pages` the pages they fill; here the role is applied to the items of the page.
    "role-after-paging": [("src/server.js", "  const users = findUsers(query.has('name') ? query.get('name') : '', query.has('role') ? query.get('role') : undefined);\n",
                           "  const wanted = query.has('role') ? query.get('role') : undefined;\n  const users = findUsers(query.has('name') ? query.get('name') : '');\n"),
                          ("src/server.js", "  if (!query.has('page') && !query.has('size')) return send(res, 200, users);\n",
                           "  if (!query.has('page') && !query.has('size')) return send(res, 200, users.filter((user) => wanted === undefined || user.role === wanted));\n"),
                          ("src/server.js", "items });\n", "items: items.filter((user) => wanted === undefined || user.role === wanted) });\n")],
    # The request: a role that is none of the three answers 400 (here it keeps nobody).
    "bad-role-keeps-nobody": [("src/server.js", "  if (query.has('role') && !ROLES.includes(query.get('role'))) {\n    return send(res, 400, { error: `role must be one of ${ROLES.join(', ')}` });\n  }\n", "")],
    # The request: an empty role is none of the three (here it keeps every user, as an empty name does).
    "empty-role-keeps-all": [("src/server.js", "  if (query.has('role') && !ROLES.includes(query.get('role'))) {\n",
                              "  if (query.get('role') && !ROLES.includes(query.get('role'))) {\n"),
                             ("src/server.js", "query.has('role') ? query.get('role') : undefined);", "query.get('role') || undefined);")],
    # The request: a role refusal is a JSON object whose "error" says what is wrong (here a bare text).
    "bad-role-not-json": [("src/server.js", "return send(res, 400, { error: `role must be one of ${ROLES.join(', ')}` });",
                           "{ res.writeHead(400, { 'content-type': 'text/plain' }); return res.end('bad role'); }")],
    # The first pass's rule: any other query parameter is ignored (here a new strictness the request does not ask for).
    "unknown-param-400": [("src/server.js", "function listing(res, query) {\n",
                           "function listing(res, query) {\n  for (const key of query.keys()) {\n"
                           "    if (!['name', 'page', 'size', 'role'].includes(key)) return send(res, 400, { error: `unknown ${key}` });\n  }\n")],
    # The first pass's rule: without page and size the answer is a JSON array (here a role makes it a page).
    "role-answers-a-page": [("src/server.js", "  if (!query.has('page') && !query.has('size')) return send(res, 200, users);\n",
                             "  if (!query.has('page') && !query.has('size') && !query.has('role')) return send(res, 200, users);\n")],
}
VARIANTS = ("base", "reference", "alternative", *DEFECTS)


def build(dest: Path, variant: str = "reference") -> Path:
    """Write the delivery of `variant` into `dest` (created if missing) and return it."""
    if variant not in VARIANTS:
        raise ValueError(f"unknown variant {variant!r}; known: {', '.join(VARIANTS)}")
    # The alternative continues the first pass's alternative (which keeps its own tests), so no earlier test is contradicted.
    dest = first.build(dest, "alternative" if variant == "alternative" else "reference")
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
