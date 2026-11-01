#!/usr/bin/env python3
"""Two K1 reference deliveries for GET /users/summary, each built on its matching user-teams reference lineage.

    python3 reference_user_summary.py DEST --variant base|reference|alternative|DEFECT

The reference reuses the separated selector and adds an exact summary route before the user-id route. The alternative reuses its
filter-aware store function and retains server-owned paging for GET /users. Both summary routes count the full filtered set and
ignore pagination and other query parameters.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import reference_user_teams as teams  # noqa: E402

REFERENCE_SUMMARY = r"""function summaryAnswer(query) {
  const users = selectedUsers(query);
  const by_team = {};
  for (const user of users) by_team[user.team] = (by_team[user.team] || 0) + 1;
  return { total: users.length, by_team };
}"""

ALTERNATIVE_SUMMARY = r"""function summaryAnswer(query) {
  const users = listUsers({
    ...(query.has('name') ? { name: query.get('name') } : {}),
    ...(query.has('team') ? { team: query.get('team') } : {}),
  });
  const by_team = {};
  for (const user of users) by_team[user.team] = (by_team[user.team] || 0) + 1;
  return { total: users.length, by_team };
}"""

SUMMARY_TEST = r"""'use strict';

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

test('summary counts all users by their stored team', async () => {
  await withServer(async (base) => {
    const { status, body } = await get(base, '/users/summary');
    assert.equal(status, 200);
    assert.equal(body.total, 3);
    assert.deepEqual(body.by_team, { Engineering: 2, Support: 1 });
  });
});

test('summary reuses name and exact case-sensitive team filters', async () => {
  await withServer(async (base) => {
    const name = await get(base, '/users/summary?name=Grace');
    const team = await get(base, '/users/summary?team=Support');
    const both = await get(base, '/users/summary?name=Alan&team=Engineering');
    const strict = await get(base, '/users/summary?team=engineering');
    assert.deepEqual([name.body.total, name.body.by_team], [1, { Engineering: 1 }]);
    assert.deepEqual([team.body.total, team.body.by_team], [1, { Support: 1 }]);
    assert.deepEqual([both.body.total, both.body.by_team], [0, {}]);
    assert.deepEqual([strict.body.total, strict.body.by_team], [0, {}]);
  });
});

test('summary ignores pagination and include and handles no matches', async () => {
  await withServer(async (base) => {
    const paged = await get(base, '/users/summary?page=2&size=1&include=team&sort=name');
    const invalid = await get(base, '/users/summary?page=bad&size=0');
    const none = await get(base, '/users/summary?name=zzz');
    const emptyTeam = await get(base, '/users/summary?team=');
    assert.deepEqual([paged.body.total, paged.body.by_team], [3, { Engineering: 2, Support: 1 }]);
    assert.deepEqual([invalid.body.total, invalid.body.by_team], [3, { Engineering: 2, Support: 1 }]);
    assert.deepEqual([none.body.total, none.body.by_team], [0, {}]);
    assert.deepEqual([emptyTeam.body.total, emptyTeam.body.by_team], [0, {}]);
  });
});
"""

ROUTES = {
    "reference": "      if (req.method === 'GET' && url.pathname === '/users/summary') return send(res, 200, summaryAnswer(url.searchParams));\n",
    "alternative": "    if (url.pathname === '/users/summary') return json(res, 200, summaryAnswer(url.searchParams));\n",
}

def _replace(path: Path, old: str, new: str, label: str) -> None:
    text = path.read_text()
    count = text.count(old)
    if count != 1:
        raise ValueError(f"{label}: expected one {old!r} in {path}, found {count}")
    path.write_text(text.replace(old, new))


def _inject_before(path: Path, marker: str, content: str, label: str) -> None:
    text = path.read_text()
    if text.count(marker) != 1:
        raise ValueError(f"{label}: expected one marker {marker!r} in {path}")
    path.write_text(text.replace(marker, content + marker))


def _replace_summary(path: Path, old: str, new: str, label: str) -> None:
    text = path.read_text()
    start = text.index("function summaryAnswer(query) {")
    end = text.index("\n}\n", start) + 2
    block = text[start:end]
    if block.count(old) != 1:
        raise ValueError(f"{label}: expected one summary occurrence of {old!r}, found {block.count(old)}")
    path.write_text(text[:start] + block.replace(old, new) + text[end:])


def _summary(dest: Path, lineage: str) -> Path:
    dest = teams.build(dest, lineage)
    server = dest / "src/server.js"
    if lineage == "reference":
        _inject_before(server, "/** An HTTP server for the user store;",
                       REFERENCE_SUMMARY + "\n\n", "reference summary function")
        _inject_before(server, "      const match = /^\\/users\\/(\\d+)$/.exec(url.pathname);",
                       ROUTES["reference"], "reference summary route")
    else:
        _inject_before(server, "function createServer() {", ALTERNATIVE_SUMMARY + "\n\n",
                       "alternative summary function")
        _inject_before(server, "    const match = /^\\/users\\/(\\d+)$/.exec(url.pathname);",
                       ROUTES["alternative"], "alternative summary route")
    (dest / "test/user-summary.test.js").write_text(SUMMARY_TEST)
    return dest


VARIANTS = ("base", "reference", "alternative", "summary-drops-filters", "summary-counts-page",
            "summary-validates-page", "summary-shadowed-route", "summary-empty-team-all")


def build(dest: Path, variant: str = "reference") -> Path:
    if variant not in VARIANTS:
        raise ValueError(f"unknown variant {variant!r}; known: {', '.join(VARIANTS)}")
    dest = Path(dest)
    if variant == "base":
        return teams.build(dest, "reference")
    lineage = "alternative" if variant == "alternative" else "reference"
    product = _summary(dest, lineage)
    server = product / "src/server.js"
    if variant == "summary-drops-filters":
        if lineage == "reference":
            _replace_summary(server, "const users = selectedUsers(query);",
                             "const users = selectedUsers(new URLSearchParams());", variant)
        else:
            old = """const users = listUsers({
    ...(query.has('name') ? { name: query.get('name') } : {}),
    ...(query.has('team') ? { team: query.get('team') } : {}),
  });"""
            _replace_summary(server, old, "const users = listUsers();", variant)
    elif variant == "summary-counts-page":
        for word in ("selectedUsers(query);", "  });"):
            if word == "selectedUsers(query);":
                old = "  const users = selectedUsers(query);\n  const by_team = {};"
                new = """  const allUsers = selectedUsers(query);
  const page = query.has('page') ? Number(query.get('page')) : 1;
  const size = query.has('size') ? Number(query.get('size')) : 10;
  const users = query.has('page') || query.has('size')
    ? allUsers.slice((page - 1) * size, page * size) : allUsers;
  const by_team = {};"""
            else:
                old = """  const users = listUsers({
    ...(query.has('name') ? { name: query.get('name') } : {}),
    ...(query.has('team') ? { team: query.get('team') } : {}),
  });
  const by_team = {};"""
                new = """  const allUsers = listUsers({
    ...(query.has('name') ? { name: query.get('name') } : {}),
    ...(query.has('team') ? { team: query.get('team') } : {}),
  });
  const page = query.has('page') ? Number(query.get('page')) : 1;
  const size = query.has('size') ? Number(query.get('size')) : 10;
  const users = query.has('page') || query.has('size')
    ? allUsers.slice((page - 1) * size, page * size) : allUsers;
  const by_team = {};"""
            if old in server.read_text():
                _replace_summary(server, old, new, variant)
    elif variant == "summary-validates-page":
        if lineage == "reference":
            marker = "      if (req.method === 'GET' && url.pathname === '/users/summary')"
            replacement = """      if (req.method === 'GET' && url.pathname === '/users/summary' && url.searchParams.has('page')
          && !/^\\d+$/.test(url.searchParams.get('page'))) return send(res, 400, { error: 'bad page' });
"""
        else:
            marker = "    if (url.pathname === '/users/summary')"
            replacement = """    if (url.pathname === '/users/summary' && url.searchParams.has('page')
        && !/^\\d+$/.test(url.searchParams.get('page'))) return json(res, 400, { error: 'bad page' });
"""
        _inject_before(server, marker, replacement, variant)
    elif variant == "summary-shadowed-route":
        _replace(server, ROUTES[lineage], "", variant)
    elif variant == "summary-empty-team-all":
        if lineage == "reference":
            _replace_summary(server, "const users = selectedUsers(query);",
                             "const filtered = new URLSearchParams(query);\n  if (filtered.get('team') === '') filtered.delete('team');\n  const users = selectedUsers(filtered);", variant)
        else:
            old = """const users = listUsers({
    ...(query.has('name') ? { name: query.get('name') } : {}),
    ...(query.has('team') ? { team: query.get('team') } : {}),
  });"""
            new = """const filtered = new URLSearchParams(query);
  if (filtered.get('team') === '') filtered.delete('team');
  const users = listUsers({
    ...(filtered.has('name') ? { name: filtered.get('name') } : {}),
    ...(filtered.has('team') ? { team: filtered.get('team') } : {}),
  });"""
            _replace_summary(server, old, new, variant)
    return product


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("dest", type=Path)
    parser.add_argument("--variant", default="reference", choices=VARIANTS)
    args = parser.parse_args()
    print(build(args.dest, args.variant))


if __name__ == "__main__":
    main()
