#!/usr/bin/env python3
"""The reference delivery of the `user-team-listing` case, the third pass of chain B (user-listing, user-roles, user-team-listing, user-page-size), for
calibrating its checks (cases.json: the case's own checks and its retention checks), the base's pristine tests and the earlier passes' checks.

    python3 reference_user_team_listing.py DEST [--variant NAME]

writes a delivery into the empty folder DEST. A follow-on starts from the run before it, so every variant starts from user-roles' reference
(reference_user_roles.py), which stands in for the second pass, and that from user-listing's, which stands in for the first. The variants:

* ``base``: the roles reference alone, as the third pass starts. It must fail every check of the new feature and pass the earlier checks.
* ``reference``: the prompt done, reusing what the first pass left: the listing's answer (the array, or a page that counts a partly filled last
  page, with the same defaults, bounds and errors) is one function the users and the teams share, and a team's name is matched as the users'
  names are, as plain text and ignoring case.
* ``alternative``: an independently written delivery (ALTERNATIVE), continuing user-roles' alternative: the teams in a module of their own, one
  windowing function for both listings, an answer extended with a field of its own. A correct delivery the checks must not reject.
* each name of DEFECTS: the reference with one targeted change. Most re-derive one rule of the users' listing for the teams (the case's point:
  the inherited rule is respected, not worked out again): the teams listing is written by hand with one rule different. ``hand-rolled``
  below is that listing with every rule right, and the test pins that it passes, so a defect differs from it in one rule only.

Each defect is a list of (path, old, new) replacements; ``old`` must occur exactly once in its file, so a defect that no longer applies
fails loudly instead of building the reference.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import reference_user_roles as second  # noqa: E402  (the second pass's stand-in, which this one starts from)

TEAMS_JS = r"""'use strict';

const TEAMS = [
  { id: 1, name: 'Analytical Engine', members: [1] },
  { id: 2, name: 'Compilers', members: [2] },
  { id: 3, name: 'Computing Machinery', members: [3] },
  { id: 4, name: 'Cryptanalysis', members: [3] },
  { id: 5, name: 'Data Systems', members: [1, 2] },
];

/** The team with `id`, or null. */
function getTeam(id) {
  return TEAMS.find((team) => team.id === id) || null;
}

/** The teams whose name contains `text` as plain text, ignoring case, in id order (every team for an empty `text`). */
function findTeams(text) {
  const wanted = text.toLowerCase();
  return TEAMS.filter((team) => team.name.toLowerCase().includes(wanted));
}

module.exports = { findTeams, getTeam };
"""

SERVER_JS = r"""'use strict';

const http = require('node:http');
const { paginate } = require('./paginate');
const { ROLES, findUsers, getUser } = require('./users');
const { findTeams, getTeam } = require('./teams');

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

/** The answer to a listing request, the same for every listing: all of `items`, or the page of them `page` and `size` ask for. */
function answer(res, query, items) {
  if (!query.has('page') && !query.has('size')) return send(res, 200, items);
  const page = query.has('page') ? wholeNumber(query.get('page'), 1, Number.MAX_SAFE_INTEGER) : 1;
  const size = query.has('size') ? wholeNumber(query.get('size'), 1, MAX_SIZE) : DEFAULT_SIZE;
  if (page === null) return send(res, 400, { error: 'page must be a whole number of at least 1' });
  if (size === null) return send(res, 400, { error: `size must be a whole number from 1 to ${MAX_SIZE}` });
  const { pages, items: pageItems } = paginate(items, page, size);
  return send(res, 200, { page, size, total: items.length, pages, items: pageItems });
}

/** GET /users: the users whose name contains `name` and who have `role`. */
function usersListing(res, query) {
  if (query.has('role') && !ROLES.includes(query.get('role'))) {
    return send(res, 400, { error: `role must be one of ${ROLES.join(', ')}` });
  }
  return answer(res, query, findUsers(query.has('name') ? query.get('name') : '', query.has('role') ? query.get('role') : undefined));
}

/** GET /teams: the teams whose name contains `name`. */
function teamsListing(res, query) {
  return answer(res, query, findTeams(query.has('name') ? query.get('name') : ''));
}

/** GET /users/:id and GET /teams/:id: the record, or 404. */
function one(res, find, id) {
  const record = find(Number(id));
  return record ? send(res, 200, record) : send(res, 404, { error: 'not found' });
}

/** An HTTP server for the user store; not listening until the caller calls listen(). */
function createServer() {
  return http.createServer((req, res) => {
    try {
      const url = new URL(req.url, 'http://localhost');
      if (req.method === 'GET' && url.pathname === '/users') return usersListing(res, url.searchParams);
      if (req.method === 'GET' && url.pathname === '/teams') return teamsListing(res, url.searchParams);
      const user = /^\/users\/(\d+)$/.exec(url.pathname);
      if (req.method === 'GET' && user) return one(res, getUser, user[1]);
      const team = /^\/teams\/(\d+)$/.exec(url.pathname);
      if (req.method === 'GET' && team) return one(res, getTeam, team[1]);
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
const { findTeams, getTeam } = require('../src/teams');

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

test('findTeams matches part of a name as plain text, ignoring case', () => {
  assert.deepEqual(findTeams('COMP').map((team) => team.id), [2, 3]);
  assert.deepEqual(findTeams('a.a'), []);
  assert.equal(findTeams('').length, 5);
  assert.deepEqual(getTeam(5).members, [1, 2]);
  assert.equal(getTeam(99), null);
});

test('GET /teams answers the array, filtered by name, and GET /teams/:id one team or 404', async () => {
  await withServer(async (base) => {
    assert.deepEqual((await get(base, '/teams')).body.map((team) => team.id), [1, 2, 3, 4, 5]);
    assert.deepEqual((await get(base, '/teams?name=an')).body.map((team) => team.id), [1, 4]);
    assert.equal((await get(base, '/teams/5')).body.name, 'Data Systems');
    const missing = await get(base, '/teams/99');
    assert.equal(missing.status, 404);
    assert.equal(typeof missing.body.error, 'string');
  });
});

test('GET /teams pages the teams as GET /users pages the users', async () => {
  await withServer(async (base) => {
    const last = await get(base, '/teams?page=3&size=2');
    assert.deepEqual({ ...last.body, items: last.body.items.map((team) => team.id) }, { page: 3, size: 2, total: 5, pages: 3, items: [5] });
    assert.deepEqual((await get(base, '/teams?page=4&size=2')).body.items, []);
    assert.equal((await get(base, '/teams?page=1')).body.size, 10);
    for (const query of ['page=0', 'size=101', 'size=']) {
      const { status, body } = await get(base, `/teams?${query}`);
      assert.equal(status, 400, query);
      assert.equal(typeof body.error, 'string', query);
    }
  });
});
"""

REFERENCE = {"src/teams.js": TEAMS_JS, "src/server.js": SERVER_JS, "test/user-team-listing.test.js": TEST_JS}

ALTERNATIVE = {
    "src/directory.js": r"""'use strict';

const TEAMS = [
  ['Analytical Engine', [1]], ['Compilers', [2]], ['Computing Machinery', [3]], ['Cryptanalysis', [3]], ['Data Systems', [1, 2]],
].map(([name, members], index) => Object.freeze({ id: index + 1, name, members }));

const allTeams = () => TEAMS.slice();
const findTeam = (id) => TEAMS.find((team) => team.id === id) || null;

module.exports = { allTeams, findTeam };
""",
    "src/server.js": r"""'use strict';

const http = require('node:http');
const { getUser, listUsers } = require('./users');
const { KNOWN, isRole, withRole } = require('./roles');
const { allTeams, findTeam } = require('./directory');

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

const byName = (query) => {
  if (!query.has('name')) return () => true;
  const needle = query.get('name').toLocaleLowerCase('en');
  return (row) => row.name.toLocaleLowerCase('en').indexOf(needle) !== -1;
};

/** All of `rows`, or the window of them that `page` and `size` ask for; the one rule for every listing. */
function window(query, rows) {
  if (!query.has('page') && !query.has('size')) return rows;
  const page = query.has('page') ? whole('page', query.get('page')) : 1;
  const size = query.has('size') ? whole('size', query.get('size')) : 10;
  const pages = Math.ceil(rows.length / size);
  return { items: rows.slice((page - 1) * size, page * size), total: rows.length, page, pages, size,
           next: page < pages ? page + 1 : null };
}

function usersAnswer(query) {
  const tests = [byName(query)];
  if (query.has('role')) {
    if (!isRole(query.get('role'))) throw new BadParameter(`role must be one of ${[...KNOWN].join(', ')}`);
    tests.push((user) => user.role === query.get('role'));
  }
  return window(query, listUsers().map(withRole).filter((user) => tests.every((test) => test(user))));
}

const teamsAnswer = (query) => window(query, allTeams().filter(byName(query)));

function createServer() {
  return http.createServer((req, res) => {
    const url = new URL(req.url, 'http://localhost');
    if (req.method !== 'GET') return json(res, 404, { error: 'not found' });
    const lists = { '/users': usersAnswer, '/teams': teamsAnswer };
    if (lists[url.pathname]) {
      try {
        return json(res, 200, lists[url.pathname](url.searchParams));
      } catch (error) {
        if (error instanceof BadParameter) return json(res, 400, { error: error.message, status: 400 });
        throw error;
      }
    }
    const match = /^\/(users|teams)\/(\d+)$/.exec(url.pathname);
    const row = match && (match[1] === 'users' ? getUser(Number(match[2])) : findTeam(Number(match[2])));
    if (!row) return json(res, 404, { error: 'not found' });
    return json(res, 200, match[1] === 'users' ? withRole(row) : row);
  });
}

if (require.main === module) {
  const port = Number(process.env.PORT) || 3000;
  createServer().listen(port, () => console.log(`listening on ${port}`));
}

module.exports = { createServer };
""",
    "test/directory.test.js": r"""'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const { allTeams, findTeam } = require('../src/directory');
const { createServer } = require('../src/server');

test('five teams, each with members', () => {
  assert.equal(allTeams().length, 5);
  assert.deepEqual(findTeam(5).members, [1, 2]);
  assert.equal(findTeam(6), null);
});

test('the teams are listed, filtered and paged like the users', async () => {
  const server = createServer().listen(0, '127.0.0.1');
  await new Promise((resolve) => server.once('listening', resolve));
  const base = `http://127.0.0.1:${server.address().port}`;
  try {
    assert.deepEqual((await (await fetch(`${base}/teams?name=COMP`)).json()).map((t) => t.id), [2, 3]);
    const paged = await (await fetch(`${base}/teams?page=3&size=2`)).json();
    assert.deepEqual([paged.pages, paged.items.map((t) => t.id), paged.next], [3, [5], null]);
    assert.equal((await fetch(`${base}/teams/9`)).status, 404);
  } finally {
    server.close();
  }
});
""",
}

REFERENCE_LISTING = "function teamsListing(res, query) {\n  return answer(res, query, findTeams(query.has('name') ? query.get('name') : ''));\n}\n"


def hand_rolled(default: int = 10, largest: str = "100", pages: str = "Math.ceil", bad_size: str = "refuse", past_end: str = "empty",
                unknown: bool = False, members: bool = True) -> str:
    """The teams listing written by hand instead of through ``answer``: the users' rules, with one different when a parameter says so."""
    if bad_size == "refuse":
        size_line = "  if (size === null) return send(res, 400, { error: 'size must be a whole number from 1 to 100' });\n"
    else:  # a size that is not a whole number in range is taken for the default
        size_line = ""
    size_value = f"const size = query.has('size') ? number(query.get('size'), 1, {largest}) : {default};\n"
    if bad_size != "refuse":
        size_value = f"const size = (query.has('size') ? number(query.get('size'), 1, {largest}) : null) || {default};\n"
    guard = ("  for (const key of query.keys()) {\n    if (!['name', 'page', 'size'].includes(key)) return send(res, 400, { error: `unknown ${key}` });\n  }\n"
             if unknown else "")
    paging = "  if (!query.has('page') && !query.has('size')) return send(res, 200, teams);\n"
    late = ("  if (page > Math.max(pages, 1)) return send(res, 404, { error: 'no such page' });\n" if past_end == "404" else "")
    strip = "" if members else "  const shown = (list) => list.map(({ members: _members, ...rest }) => rest);\n"
    out = "shown(teams)" if not members else "teams"
    return (
        "function teamsListing(res, query) {\n" + guard +
        "  const teams = findTeams(query.has('name') ? query.get('name') : '');\n" + strip + paging.replace("teams)", out + ")") +
        "  const number = (text, min, max) => (/^\\d+$/.test(text) && Number(text) >= min && Number(text) <= max ? Number(text) : null);\n"
        "  const page = query.has('page') ? number(query.get('page'), 1, Number.MAX_SAFE_INTEGER) : 1;\n"
        f"  {size_value}"
        "  if (page === null) return send(res, 400, { error: 'page must be a whole number of at least 1' });\n" + size_line +
        f"  const pages = {pages}(teams.length / size);\n" + late +
        "  return send(res, 200, { page, size, total: teams.length, pages, items: " + ("shown(" if not members else "(") +
        "teams.slice((page - 1) * size, page * size)) });\n}\n")


HAND_ROLLED = hand_rolled()
DEFECTS = {
    # The first request's rule: the name is matched as plain text (here a regular expression).
    "teams-regex-filter": [("src/teams.js", "team.name.toLowerCase().includes(wanted)", "new RegExp(wanted).test(team.name.toLowerCase())")],
    # The first request's rule: ignoring case.
    "teams-case-sensitive": [("src/teams.js", "team.name.toLowerCase().includes(wanted)", "team.name.includes(text)")],
    # The first request's rule: a page count that counts a partly filled last page (here the base's own floor, derived again).
    "teams-floor-pages": [("src/server.js", REFERENCE_LISTING, hand_rolled(pages="Math.floor"))],
    # The first request's rule: a page holds 10 when `size` is not given.
    "teams-default-size-20": [("src/server.js", REFERENCE_LISTING, hand_rolled(default=20))],
    # The first request's rule: `size` goes up to 100 (here 99).
    "teams-size-cap-99": [("src/server.js", REFERENCE_LISTING, hand_rolled(largest="99"))],
    # The first request's rule: `size` goes no higher than 100 (here no limit).
    "teams-no-size-cap": [("src/server.js", REFERENCE_LISTING, hand_rolled(largest="Infinity"))],
    # The first request's rule: a bad `size` answers 400 (here it is taken for the default).
    "teams-bad-size-defaulted": [("src/server.js", REFERENCE_LISTING, hand_rolled(bad_size="default"))],
    # The first request's rule: a page after the last one answers an empty "items" (here a 404).
    "teams-past-end-404": [("src/server.js", REFERENCE_LISTING, hand_rolled(past_end="404"))],
    # The first request's rule: any other query parameter is ignored (here it is refused).
    "teams-unknown-param-400": [("src/server.js", REFERENCE_LISTING, hand_rolled(unknown=True))],
    # The request: each team shows its members.
    "teams-members-missing": [("src/server.js", REFERENCE_LISTING, hand_rolled(members=False))],
    # The request: 404 the way GET /users/:id does for a user that does not exist (a JSON object with an "error").
    "team-404-text": [("src/server.js", "  return record ? send(res, 200, record) : send(res, 404, { error: 'not found' });\n",
                       "  if (!record) { res.writeHead(404, { 'content-type': 'text/plain' }); return res.end('no such team'); }\n  return send(res, 200, record);\n")],
    # An earlier pass's behaviour lost by the change (here the role filter, dropped from the users listing while the listing was shared).
    "role-filter-lost": [("src/server.js", "findUsers(query.has('name') ? query.get('name') : '', query.has('role') ? query.get('role') : undefined)",
                          "findUsers(query.has('name') ? query.get('name') : '')")],
}
VARIANTS = ("base", "reference", "alternative", "hand-rolled", *DEFECTS)


def build(dest: Path, variant: str = "reference") -> Path:
    """Write the delivery of `variant` into `dest` (created if missing) and return it."""
    if variant not in VARIANTS:
        raise ValueError(f"unknown variant {variant!r}; known: {', '.join(VARIANTS)}")
    dest = second.build(dest, "alternative" if variant == "alternative" else "reference")
    if variant == "base":
        return dest
    for relative, text in (ALTERNATIVE if variant == "alternative" else REFERENCE).items():
        (dest / relative).parent.mkdir(parents=True, exist_ok=True)
        (dest / relative).write_text(text)
    edits = [("src/server.js", REFERENCE_LISTING, HAND_ROLLED)] if variant == "hand-rolled" else DEFECTS.get(variant, ())
    for relative, old, new in edits:
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
