#!/usr/bin/env python3
"""Two reference deliveries for K2 user-teams, each based on one user-listing lineage.

    python3 reference_user_teams.py DEST --variant base|reference|alternative|DEFECT

base is the existing user-listing reference. reference extends its separated find/filter and list route. alternative extends the
user-listing alternative, whose listUsers accepts filters and whose server owns pagination. Both keep the team private by default
and add it only for the exact include=team opt-in. Defect variants are frozen mutations of the reference.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import reference_user_listing as listing  # noqa: E402

OLD_USERS = """const USERS = [
  { id: 1, name: 'Ada Lovelace', email: 'ada@example.com' },
  { id: 2, name: 'Grace Hopper', email: 'grace@example.com' },
  { id: 3, name: 'Alan Turing', email: 'alan@example.com' },
];"""

TEAM_USERS = """const USERS = [
  { id: 1, name: 'Ada Lovelace', email: 'ada@example.com', team: 'Engineering' },
  { id: 2, name: 'Grace Hopper', email: 'grace@example.com', team: 'Engineering' },
  { id: 3, name: 'Alan Turing', email: 'alan@example.com', team: 'Support' },
];"""

REFERENCE_LISTING = r"""function selectedUsers(query) {
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
}"""

ALT_USERS = r"""'use strict';

const USERS = [
  { id: 1, name: 'Ada Lovelace', email: 'ada@example.com', team: 'Engineering' },
  { id: 2, name: 'Grace Hopper', email: 'grace@example.com', team: 'Engineering' },
  { id: 3, name: 'Alan Turing', email: 'alan@example.com', team: 'Support' },
];

/** The user with id, or null. */
function getUser(id) {
  return USERS.find((user) => user.id === id) || null;
}

/** Every user in id order; filters match the name and exact team. */
function listUsers({ name, team } = {}) {
  let users = USERS;
  if (name !== undefined) {
    const needle = name.toLocaleLowerCase('en');
    users = users.filter((user) => user.name.toLocaleLowerCase('en').indexOf(needle) !== -1);
  }
  if (team !== undefined) users = users.filter((user) => user.team === team);
  return users.slice();
}

module.exports = { getUser, listUsers };
"""

ALT_ANSWER = r"""function publicUser(user, includeTeam) {
  const { team, ...ordinary } = user;
  return includeTeam ? { ...ordinary, team } : ordinary;
}

function usersAnswer(query) {
  const users = listUsers({
    ...(query.has('name') ? { name: query.get('name') } : {}),
    ...(query.has('team') ? { team: query.get('team') } : {}),
  });
  const withTeam = query.get('include') === 'team';
  if (!query.has('page') && !query.has('size')) return users.map((user) => publicUser(user, withTeam));
  const page = query.has('page') ? whole('page', query.get('page')) : 1;
  const size = query.has('size') ? whole('size', query.get('size')) : 10;
  const pages = Math.ceil(users.length / size);
  return { items: users.slice((page - 1) * size, page * size).map((user) => publicUser(user, withTeam)),
           total: users.length, page, pages, size, next: page < pages ? page + 1 : null };
}"""

USER_TEST = r"""'use strict';

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
"""

def _replace(path: Path, old: str, new: str, label: str) -> None:
    text = path.read_text()
    count = text.count(old)
    if count != 1:
        raise ValueError(f"{label}: expected one {old!r} in {path}, found {count}")
    path.write_text(text.replace(old, new))


def _reference(dest: Path) -> Path:
    dest = listing.build(dest, "reference")
    _replace(dest / "src/users.js", OLD_USERS, TEAM_USERS, "user store")
    server = dest / "src/server.js"
    text = server.read_text()
    first = text.index("function listing(res, query) {")
    last = text.index("\n}\n\n/** An HTTP server", first) + 2
    server.write_text(text[:first] + REFERENCE_LISTING + text[last:])
    _replace(server,
             "return user ? send(res, 200, user) : send(res, 404, { error: 'not found' });",
             "return user ? send(res, 200, publicUser(user, url.searchParams.get('include') === 'team')) : send(res, 404, { error: 'not found' });",
             "reference detail")
    (dest / "test/user-teams.test.js").write_text(USER_TEST)
    return dest


def _alternative(dest: Path) -> Path:
    dest = listing.build(dest, "alternative")
    (dest / "src/users.js").write_text(ALT_USERS)
    server = dest / "src/server.js"
    text = server.read_text()
    first = text.index("function usersAnswer(query) {")
    last = text.index("\n}\n\nfunction createServer", first) + 2
    server.write_text(text[:first] + ALT_ANSWER + text[last:])
    _replace(server,
             "return user ? json(res, 200, user) : json(res, 404, { error: 'not found' });",
             "return user ? json(res, 200, publicUser(user, url.searchParams.get('include') === 'team')) : json(res, 404, { error: 'not found' });",
             "alternative detail")
    (dest / "test/user-teams.test.js").write_text(USER_TEST)
    return dest


VARIANTS = ("base", "reference", "alternative", "team-after-pagination", "team-substring",
            "team-casefold-early", "team-leaks-default")


def build(dest: Path, variant: str = "reference") -> Path:
    if variant not in VARIANTS:
        raise ValueError(f"unknown variant {variant!r}; known: {', '.join(VARIANTS)}")
    dest = Path(dest)
    if variant == "base":
        return listing.build(dest, "reference")
    if variant == "alternative":
        return _alternative(dest)
    product = _reference(dest)
    server = product / "src/server.js"
    if variant == "team-after-pagination":
        _replace(server, "  const { pages, items } = paginate(users, page, size);",
                 """  const allUsers = query.has('team')
    ? selectedUsers(new URLSearchParams([...query].filter(([key]) => key !== 'team')))
    : users;
  const { pages, items: pageItems } = paginate(allUsers, page, size);
  const items = query.has('team') ? pageItems.filter((user) => user.team === query.get('team')) : pageItems;""",
                 variant + " page")
        _replace(server, "total: users.length, pages, items:", "total: allUsers.length, pages, items:", variant + " total")
    elif variant == "team-substring":
        _replace(server, "user.team === query.get('team')", "user.team.includes(query.get('team'))", variant)
    elif variant == "team-casefold-early":
        _replace(server, "user.team === query.get('team')",
                 "user.team.toLowerCase() === query.get('team').toLowerCase()", variant)
    elif variant == "team-leaks-default":
        _replace(server, "return includeTeam ? { ...ordinary, team } : ordinary;", "return { ...ordinary, team };", variant)
    return product


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("dest", type=Path)
    parser.add_argument("--variant", default="reference", choices=VARIANTS)
    args = parser.parse_args()
    print(build(args.dest, args.variant))


if __name__ == "__main__":
    main()
