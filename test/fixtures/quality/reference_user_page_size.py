#!/usr/bin/env python3
"""The reference delivery of the `user-page-size` case, the fourth pass of chain B (user-listing, user-roles, user-team-listing, user-page-size) and the
first that changes a rule an earlier request set, for calibrating its checks (cases.json: the case's own checks and its retention checks), the
base's pristine tests and the earlier passes' checks.

    python3 reference_user_page_size.py DEST [--variant NAME]

writes a delivery into the empty folder DEST. A follow-on starts from the run before it, so every variant starts from user-team-listing' reference
(reference_user_team_listing.py), which stands in for the third pass, and that from user-roles' and user-listing's. The variants:

* ``base``: the teams reference alone, as the fourth pass starts. It must fail every check of the new rules and pass the earlier checks except
  the four that read the sentences this request replaces.
* ``reference``: the prompt done. The default page size is the PAGE_SIZE setting (a whole number from 1 to the largest size, else 25) and the
  largest size 50, both in the one place the two listings share; the two earlier tests that state a default page of 10 are changed to 25,
  which is the "tests that state them" the request names; and a test file of its own reads the setting.
* ``alternative``: an independently written delivery (ALTERNATIVE), continuing user-team-listing' alternative: the setting read when a request
  arrives, not when the module loads, and the sizes in the one table the alternative already had. A correct delivery the checks must not reject.
* each name of DEFECTS: the reference with one targeted change, a sentence of the request or an earlier rule it keeps broken.

Each defect is a list of (path, old, new) replacements; ``old`` must occur exactly once in its file, so a defect that no longer applies
fails loudly instead of building the reference.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import reference_user_team_listing as third  # noqa: E402  (the third pass's stand-in, which this one starts from)

OLD_CONSTANTS = "const DEFAULT_SIZE = 10;\nconst MAX_SIZE = 100;\n"
NEW_CONSTANTS = ("const MAX_SIZE = 50;\n/** The default page size: the PAGE_SIZE setting (a whole number from 1 to MAX_SIZE), else 25. */\n"
                 "const DEFAULT_SIZE = wholeNumber(process.env.PAGE_SIZE || '', 1, MAX_SIZE) || 25;\n")
USERS_OLD_TEST = "assert.deepEqual((await get(base, '/users?page=1')).body.size, 10);"
USERS_NEW_TEST = "assert.deepEqual((await get(base, '/users?page=1')).body.size, 25);"
TEAMS_OLD_TEST = "assert.equal((await get(base, '/teams?page=1')).body.size, 10);"
TEAMS_NEW_TEST = "assert.equal((await get(base, '/teams?page=1')).body.size, 25);"

TEST_JS = r"""'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');

/** A server as a fresh process would start it: PAGE_SIZE is read once, when the module loads. */
function serverWith(pageSize) {
  const path = require.resolve('../src/server');
  const before = process.env.PAGE_SIZE;
  if (pageSize === undefined) delete process.env.PAGE_SIZE;
  else process.env.PAGE_SIZE = pageSize;
  delete require.cache[path];
  const { createServer } = require('../src/server');
  if (before === undefined) delete process.env.PAGE_SIZE;
  else process.env.PAGE_SIZE = before;
  return createServer();
}

async function get(server, path) {
  await new Promise((resolve) => server.listen(0, '127.0.0.1', resolve));
  try {
    const response = await fetch(`http://127.0.0.1:${server.address().port}${path}`);
    return { status: response.status, body: await response.json() };
  } finally {
    await new Promise((resolve) => server.close(resolve));
  }
}

test('a page holds 25 when size is not given and PAGE_SIZE is not set, for the users and the teams', async () => {
  assert.equal((await get(serverWith(undefined), '/users?page=1')).body.size, 25);
  assert.equal((await get(serverWith(undefined), '/teams?page=1')).body.size, 25);
});

test('PAGE_SIZE sets the default page size of both listings and a given size beats it', async () => {
  const two = await get(serverWith('2'), '/teams?page=3');
  assert.deepEqual({ ...two.body, items: two.body.items.map((team) => team.id) }, { page: 3, size: 2, total: 5, pages: 3, items: [5] });
  assert.equal((await get(serverWith('2'), '/users?size=3')).body.size, 3);
  assert.equal((await get(serverWith('2'), '/users')).body.length, 3);
});

test('the largest size is 50 for both listings', async () => {
  assert.equal((await get(serverWith(undefined), '/users?size=50')).status, 200);
  for (const path of ['/users?size=51', '/users?size=100', '/teams?size=51']) {
    const { status, body } = await get(serverWith(undefined), path);
    assert.equal(status, 400, path);
    assert.equal(typeof body.error, 'string', path);
  }
});
"""

ALTERNATIVE_SERVER = None  # built from the third pass's alternative server below


def alternative_server() -> str:
    """The third pass's alternative server with the page sizes changed: a request reads the setting itself, and the one table holds 50."""
    text = third.ALTERNATIVE["src/server.js"]
    for old, new in (
        ("const LIMITS = { page: [1, Infinity], size: [1, 100] };\n",
         "const LIMITS = { page: [1, Infinity], size: [1, 50] };\n\n"
         "/** The default page size: PAGE_SIZE when it is a whole number within the limits, else 25; read when a request arrives. */\n"
         "function defaultSize() {\n  const text = process.env.PAGE_SIZE;\n  const number = Number(text);\n"
         "  return text !== undefined && Number.isInteger(number) && number >= LIMITS.size[0] && number <= LIMITS.size[1] ? number : 25;\n}\n"),
        ("whole('size', query.get('size')) : 10;", "whole('size', query.get('size')) : defaultSize();"),
    ):
        if text.count(old) != 1:
            raise ValueError(f"the third pass's alternative server no longer holds {old!r} once")
        text = text.replace(old, new)
    return text


REFERENCE_EDITS = [
    ("src/server.js", OLD_CONSTANTS, NEW_CONSTANTS),
    ("test/user-listing.test.js", USERS_OLD_TEST, USERS_NEW_TEST),
    ("test/user-team-listing.test.js", TEAMS_OLD_TEST, TEAMS_NEW_TEST),
]
REFERENCE_ADDED = {"test/user-page-size.test.js": TEST_JS}

DEFECTS = {
    # The request: the default page size changes (here the old 10 stands, with the largest size changed).
    "default-still-10": [("src/server.js", "wholeNumber(process.env.PAGE_SIZE || '', 1, MAX_SIZE) || 25;", "10;")],
    # The request: the default page size is the PAGE_SIZE setting (here a constant 25).
    "setting-ignored": [("src/server.js", "wholeNumber(process.env.PAGE_SIZE || '', 1, MAX_SIZE) || 25;", "25;")],
    # The request: the largest size is 50 (here the old 100 stands).
    "largest-still-100": [("src/server.js", "const MAX_SIZE = 50;", "const MAX_SIZE = 100;")],
    # The request: the largest size is 50, and 50 itself is accepted (here 49).
    "largest-49": [("src/server.js", "const MAX_SIZE = 50;", "const MAX_SIZE = 49;")],
    # The request: a size above 50 answers 400 (here 51 is still accepted: only a check that reads 51 itself sees it).
    "largest-51": [("src/server.js", "const MAX_SIZE = 50;", "const MAX_SIZE = 51;")],
    # The request: both listings (here the teams listing was written by hand with the old rules, as an earlier pass might have left it).
    "teams-keep-old-rules": [("src/server.js", third.REFERENCE_LISTING, third.hand_rolled())],
    # The first request's rule, kept: without page and size the answer is the whole list (here the setting cuts it).
    "setting-cuts-the-array": [("src/server.js", "  if (!query.has('page') && !query.has('size')) return send(res, 200, items);\n",
                                "  if (!query.has('page') && !query.has('size')) return send(res, 200, items.slice(0, DEFAULT_SIZE));\n")],
    # The request: a `size` that is given still counts (here the setting beats it).
    "setting-beats-given-size": [("src/server.js", "const size = query.has('size') ? wholeNumber(query.get('size'), 1, MAX_SIZE) : DEFAULT_SIZE;",
                                  "const size = process.env.PAGE_SIZE ? DEFAULT_SIZE : query.has('size') ? wholeNumber(query.get('size'), 1, MAX_SIZE) : DEFAULT_SIZE;")],
    # The request: change the tests that state the old rules (here the code changed and two tests still say a page holds 10).
    "old-tests-left-standing": [("test/user-listing.test.js", USERS_NEW_TEST, USERS_OLD_TEST), ("test/user-team-listing.test.js", TEAMS_NEW_TEST, TEAMS_OLD_TEST)],
}
VARIANTS = ("base", "reference", "alternative", *DEFECTS)


def apply(dest: Path, edits, label: str) -> None:
    for relative, old, new in edits:
        text = (dest / relative).read_text()
        if text.count(old) != 1:
            raise ValueError(f"{label}: {old!r} occurs {text.count(old)} times in {relative}, not once")
        (dest / relative).write_text(text.replace(old, new))


def build(dest: Path, variant: str = "reference") -> Path:
    """Write the delivery of `variant` into `dest` (created if missing) and return it."""
    if variant not in VARIANTS:
        raise ValueError(f"unknown variant {variant!r}; known: {', '.join(VARIANTS)}")
    dest = third.build(dest, "alternative" if variant == "alternative" else "reference")
    if variant == "base":
        return dest
    if variant == "alternative":
        (dest / "src" / "server.js").write_text(alternative_server())
        return dest
    apply(dest, REFERENCE_EDITS, "reference")
    for relative, text in REFERENCE_ADDED.items():
        (dest / relative).write_text(text)
    apply(dest, DEFECTS.get(variant, ()), f"defect {variant}")
    return dest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("dest", type=Path)
    parser.add_argument("--variant", default="reference", choices=VARIANTS)
    args = parser.parse_args()
    print(build(args.dest, args.variant))


if __name__ == "__main__":
    main()
