#!/usr/bin/env python3
"""Two K3 reference deliveries for replacing the strict team-name rule with case-insensitive exact matching.

    python3 reference_user_team_casefold.py DEST --variant base|reference|alternative|DEFECT

reference starts from user-summary's separated selector, while alternative starts from its filter-aware listUsers and
server-owned paging lineage. Both update the earlier tests that stated strict matching. The four frozen defects cover summary-only
case folding, substring matching, lowercased returned team values and lowercased summary group keys.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import reference_user_summary as summary  # noqa: E402

CASEFOLD_TEST = r"""'use strict';

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

test('team matching ignores case on listing and summary and keeps stored spelling', async () => {
  await withServer(async (base) => {
    const listed = await get(base, '/users?team=engineering&include=team');
    const grouped = await get(base, '/users/summary?team=ENGINEERING');
    assert.deepEqual(listed.body.map((user) => user.id), [1, 2]);
    assert.deepEqual(listed.body.map((user) => user.team), ['Engineering', 'Engineering']);
    assert.deepEqual([grouped.body.total, grouped.body.by_team], [2, { Engineering: 2 }]);
  });
});

test('ignoring case still requires an exact team name', async () => {
  await withServer(async (base) => {
    assert.deepEqual((await get(base, '/users?team=Eng')).body, []);
    assert.deepEqual((await get(base, '/users/summary?team=Eng')).body, { total: 0, by_team: {} });
  });
});
"""

STRICT_LIST_TEST = "    assert.deepEqual((await get(base, '/users?team=engineering')).body, []);"
CASEFOLD_LIST_TEST = "    assert.deepEqual((await get(base, '/users?team=engineering')).body.map((user) => user.id), [1, 2]);"
STRICT_SUMMARY_TEST = "    assert.deepEqual([strict.body.total, strict.body.by_team], [0, {}]);"
CASEFOLD_SUMMARY_TEST = "    assert.deepEqual([strict.body.total, strict.body.by_team], [2, { Engineering: 2 }]);"

VARIANTS = ("base", "reference", "alternative", "listing-only-casefold", "team-substring",
            "returned-team-lowercase", "group-key-lowercase")


def _replace(path: Path, old: str, new: str, label: str) -> None:
    text = path.read_text()
    count = text.count(old)
    if count != 1:
        raise ValueError(f"{label}: expected one {old!r} in {path}, found {count}")
    path.write_text(text.replace(old, new))


def _replace_in_summary(path: Path, old: str, new: str, label: str) -> None:
    text = path.read_text()
    start = text.index("function summaryAnswer(query) {")
    end = text.index("\n}\n", start) + 2
    block = text[start:end]
    if block.count(old) != 1:
        raise ValueError(f"{label}: expected one summary occurrence of {old!r}, found {block.count(old)}")
    path.write_text(text[:start] + block.replace(old, new) + text[end:])


def _casefold(dest: Path, lineage: str) -> Path:
    dest = summary.build(dest, lineage)
    if lineage == "reference":
        _replace(dest / "src/server.js",
                 "return users.filter((user) => user.team === query.get('team'));",
                 "return users.filter((user) => user.team.toLowerCase() === query.get('team').toLowerCase());",
                 "reference team matcher")
    else:
        _replace(dest / "src/users.js",
                 "if (team !== undefined) users = users.filter((user) => user.team === team);",
                 "if (team !== undefined) users = users.filter((user) => user.team.toLowerCase() === team.toLowerCase());",
                 "alternative team matcher")
    _replace(dest / "test/user-teams.test.js", STRICT_LIST_TEST, CASEFOLD_LIST_TEST, "listing test replacement")
    _replace(dest / "test/user-summary.test.js", STRICT_SUMMARY_TEST, CASEFOLD_SUMMARY_TEST, "summary test replacement")
    (dest / "test/user-team-casefold.test.js").write_text(CASEFOLD_TEST)
    return dest


def build(dest: Path, variant: str = "reference") -> Path:
    if variant not in VARIANTS:
        raise ValueError(f"unknown variant {variant!r}; known: {', '.join(VARIANTS)}")
    dest = Path(dest)
    if variant == "base":
        return summary.build(dest, "reference")
    lineage = "alternative" if variant == "alternative" else "reference"
    product = _casefold(dest, lineage)
    server = product / "src/server.js"
    if variant == "listing-only-casefold":
        _replace_in_summary(
            server,
            "const users = selectedUsers(query);",
            "const selected = selectedUsers(query);\n  const users = query.has('team') ? selected.filter((user) => user.team === query.get('team')) : selected;",
            variant,
        )
    elif variant == "team-substring":
        _replace(server,
                 "user.team.toLowerCase() === query.get('team').toLowerCase()",
                 "user.team.toLowerCase().includes(query.get('team').toLowerCase())",
                 variant,
        )
    elif variant == "returned-team-lowercase":
        _replace(server, "return includeTeam ? { ...ordinary, team } : ordinary;",
                 "return includeTeam ? { ...ordinary, team: team.toLowerCase() } : ordinary;", variant)
    elif variant == "group-key-lowercase":
        _replace(server, "by_team[user.team] = (by_team[user.team] || 0) + 1;",
                 "by_team[user.team.toLowerCase()] = (by_team[user.team.toLowerCase()] || 0) + 1;", variant)
    return product


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("dest", type=Path)
    parser.add_argument("--variant", default="reference", choices=VARIANTS)
    args = parser.parse_args()
    print(build(args.dest, args.variant))


if __name__ == "__main__":
    main()
