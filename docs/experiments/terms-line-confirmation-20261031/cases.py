"""The three requests of the terms-line confirmation (README.md): long, loosely worded, dictated-style requests over three small
fixtures of test/shiploop_e2e/fixtures, the repository facts read from each on 2026-10-31, and the items each request raises with
what a good intake does about each.

Every fact below was read from the fixture's own files (README.md, package.json, src, test); the absences (Kestrel, Heron, the
Orchard style guide, a default page size, a trim helper, a five-thousand limit) are absences of the whole fixture.  The expected
handling of each item was written before any output existed.
"""

SKILLS_NOTE = ("improve, in-parallel, code-review, schedule, loop, simplify and ask are installed skills of the host list; the "
               "list itself is the one of QB2 (qb2_case.SKILLS), twelve entries")

CASES = {
    "users": {
        "fixture": "node-base",
        "context": "a small Node.js project with an in-memory user store and an HTTP server (its README.md describes it)",
        "sentences": [
            "Okay so this is the little users API in this folder, the node one.",
            ("I need people to be able to add and remove users, so a create and a delete, and the delete should be careful, no yolo "
            "on that one."),
            ("The list should page the way the paginator already does, the usual page size is fine, and I'm pretty sure the "
            "paginator handles a short last page properly already, but double check."),
            "Keep it zero-dependency and boring.",
            "Users should survive a restart, but also keep the in-memory store, that's the whole point of it.",
            ("Run improve over it until it stops finding things, fan the tests and the handler out in parallel, and code-review it "
            "before you call it done."),
            ("Oh and it needs to line up with the Kestrel migration, we're moving the user records over next quarter and I don't "
            "want to redo the ids."),
            "Use the usual port.",
            "Return the same shape the list endpoint does.",
            "Don't change what the existing endpoints return.",
        ],
        "breaks": {1, 3, 4, 6, 7},
        "facts": """\
- Layout: src/users.js (an in-memory list of three users with id, name and email; getUser(id) and listUsers(); no create, update or
  delete), src/server.js (a node:http server), src/paginate.js, src/strings.js; tests under test/; README.md; package.json.
- Server: GET /users answers the list as a JSON array; GET /users/:id answers one user, or 404 with {"error": "not found"}; every other
  route is 404; no request body is read; there is no authentication. The port is the PORT environment variable, 3000 by default.
- State: users live only in memory; nothing is saved; a restart restores the three seed users. No persistence code exists.
- Pagination: paginate(items, page, size) takes the page size as an argument. There is no default page size anywhere, and the server
  does not paginate. It computes the page count with Math.floor(items.length / size), so a partial last page is not counted: with 7
  items and size 3 it reports 2 pages, page 3 answers an empty list and the 7th item can never be reached. The only pagination test
  covers an evenly divided list (6 items, size 3) and a bad size.
- Dependencies: package.json has none; Node 20 or later; npm test runs node --test; npm start runs node src/server.js.
- Tests: test/server.test.js (GET /users/:id found, and 404), test/paginate.test.js, test/strings.test.js, test/users.test.js.
- Kestrel, a migration and any id policy appear nowhere in the repository, and no installed skill is named for them.
- Installed skills offered by the host: until-loop, backchain, plan-dispatcher, improve, in-parallel, ralph-loop, loop, schedule,
  code-review, simplify, ask, shiploop.""",
        "items": [
            ("U1", "skill", "env", "S6: run improve over it until it stops finding things",
             ("Recognises 'improve' as the installed improve skill (a review-and-improvement loop that repeats until a pass finds "
             "only trivial changes) and records it as the way the work is refined.")),
            ("U2", "skill", "env", "S6: fan the tests and the handler out in parallel",
             ("Recognises it as the installed in-parallel skill (independent workers whose returns are verified) and records that "
             "the tests and the handler are independent pieces of work.")),
            ("U3", "skill", "env", "S6: code-review it before you call it done",
             ("Recognises 'code-review' as the installed code-review skill (a review of the diff for correctness bugs) and "
             "records it as a gate before the work is called done.")),
            ("U4", "slang", "env", "S2: the delete should be careful, no yolo on that one",
             ("Reads 'yolo' as proceeding without caution: the delete must be careful (for example an answer for an unknown id, no "
             "bulk or unconditional wipe, tests), not as permission to skip care.")),
            ("U5", "slang", "env", "S4: keep it boring",
             "Reads 'boring' as plain, conventional design with no clever machinery, in the style of the existing code."),
            ("U6", "unknown", "decision", "S7: the Kestrel migration, I don't want to redo the ids",
             ("'Kestrel' appears nowhere in the repository or the skills. A good intake flags it as an unknown name, states a best "
             "reading (a planned move of the user records, with a worry that ids stay stable) with low confidence, invents no "
             "facts about it, and records an id decision (ids stay stable and are not reassigned).")),
            ("U7", "referent", "env", "S3: the usual page size is fine",
             ("Checks and finds no page size anywhere (paginate takes it as an argument, the server does not paginate), so 'the "
             "usual' does not exist; says so and records a default page size or flags it for confirmation.")),
            ("U8", "referent", "env", "S3: I'm pretty sure the paginator handles a short last page properly already, but double check",
             ("Reads paginate.js and finds that it does not: the page count is floored, so a partial last page is dropped (7 items "
             "of size 3 give 2 pages and the 7th item is unreachable), and the one test covers only an even division. Reports it "
             "and ties it to the request.")),
            ("U9", "conflict", "decision", "S5: survive a restart, but also keep the in-memory store",
             ("Spots that surviving a restart and keeping a purely in-memory store pull apart (nothing is saved today) and takes or "
             "asks for an explicit reading (for example memory stays the working store with a file snapshot), rather than "
             "satisfying only one.")),
            ("U10", "referent", "env", "S8: use the usual port",
             "Finds that the port is the PORT environment variable, 3000 by default (src/server.js), and uses that."),
            ("U11", "referent", "env", "S9: return the same shape the list endpoint does",
             ("Finds that the list endpoint answers a JSON array of user objects with id, name and email, and settles what 'the "
             "same shape' means for create and delete (a user object for create) or flags the ambiguity.")),
            ("U12", "constraint", "env", "S4: keep it zero-dependency",
             "Confirms there are no dependencies today (package.json) and records the constraint."),
            ("U13", "constraint", "env", "S10: don't change what the existing endpoints return",
             ("Records as a boundary that GET /users, GET /users/:id, their shapes and the 404 body stay as they are, and that the "
             "existing tests keep passing.")),
            ("U14", "open", "decision", "S2: add and remove users",
             ("Notes what the request leaves open for create and delete: how a new user's id is assigned, required fields and "
             "validation (email), duplicate emails, what delete answers for an unknown id, and that the server has no "
             "authentication so a delete is open to anyone; records defaults or leaves them to a person.")),
        ],
    },
    "meter": {
        "fixture": "node-orders",
        "context": "a small Node.js project of order-line helpers with a work meter (its README.md describes it)",
        "sentences": [
            "This one's for the orders repo, the one with the work meter in it.",
            ("Batch jobs keep blowing through the usual five thousand tick limit, so I want a way for a batch job to run past it "
            "without tripping the error."),
            "But it has to stay a hard limit, I don't want a soft one that just warns, that's a footgun.",
            "Each batch job should get its own count instead of the global one, and reset between jobs the way it does now.",
            "Hang it off a schedule so the nightly batch picks it up, and put a loop on it to watch the count every few minutes.",
            "Run simplify over it at the end, and ask another model to sanity check the edge cases.",
            "Don't bikeshed the naming, just follow what's there.",
            "Tests in node:test like the existing ones.",
            "This is for the Heron batch and it has to land before the Heron cutover, so it's not a long project.",
            "Keep LimitError as it is, other code depends on it.",
            "Performance doesn't matter much, but it shouldn't slow the normal path.",
        ],
        "breaks": {1, 3, 4, 6, 9},
        "facts": """\
- Layout: README.md ("the platform's work meter ... throws a LimitError past 10,000 ticks"), package.json, src/meter.js,
  test/meter.test.js. There is no other source.
- src/meter.js: one module-level counter. LIMIT is 10000, described as a hard limit. tick() adds one and throws LimitError (a class
  that extends Error) when the count exceeds LIMIT; count() reads it; reset() sets it to 0. It exports LIMIT, LimitError, tick, count
  and reset. Nothing calls reset() automatically. There is no per-job counter, no job concept, no scheduler and no logging.
- Tests (node:test and node:assert): counting and resetting; throwing past the limit. The only user of LimitError in the repository
  is its own test.
- No five-thousand limit exists anywhere; the limit is 10,000. Heron, a batch job and a cutover appear nowhere.
- package.json: name orders, no dependencies; npm test runs node --test.
- Installed skills offered by the host: until-loop, backchain, plan-dispatcher, improve, in-parallel, ralph-loop, loop, schedule,
  code-review, simplify, ask, shiploop.""",
        "items": [
            ("M1", "skill", "env", "S5: hang it off a schedule so the nightly batch picks it up",
             ("Notes that 'schedule' is an installed skill (scheduled agents on a cron schedule) and that the repository has no "
             "scheduler, and records a reading of what is wanted with its confidence, rather than inventing a scheduler.")),
            ("M2", "skill", "env", "S5: put a loop on it to watch the count every few minutes",
             ("Recognises 'loop' as the installed loop skill (run a prompt or command on a recurring interval) and records it as a "
             "recurring check of the count.")),
            ("M3", "skill", "env", "S6: run simplify over it at the end",
             ("Recognises 'simplify' as the installed simplify skill (review changed code for reuse and simplification, then fix) "
             "and records it as a final pass.")),
            ("M4", "skill", "env", "S6: ask another model to sanity check the edge cases",
             ("Recognises it as the installed ask skill (a second opinion from another model) and records it as a check of the "
             "edge cases.")),
            ("M5", "slang", "env", "S3: that's a footgun",
             ("Reads 'footgun' as a design that makes it easy to hurt yourself: a limit that only warns lets runaway jobs continue "
             "unnoticed.")),
            ("M6", "slang", "env", "S7: don't bikeshed the naming",
             "Reads it as: do not spend effort debating trivial details; follow the existing names."),
            ("M7", "unknown", "decision", "S9: the Heron batch, the Heron cutover",
             ("'Heron' appears nowhere in the repository or the skills. A good intake flags it as an unknown name, states a best "
             "reading (a batch workload and a deadline) with low confidence, treats the deadline as non-blocking, and invents no "
             "facts about it.")),
            ("M8", "referent", "env", "S2: the usual five thousand tick limit",
             ("Finds that LIMIT is 10,000, not 5,000 (src/meter.js and the README), says the premise is wrong, and records which "
             "number the request means.")),
            ("M9", "conflict", "decision", "S2-S3: run past the limit without tripping the error, but it has to stay a hard limit",
             ("Spots that running past the limit without an error and keeping a hard limit pull apart and takes or asks for an "
             "explicit reading (for example the default hard limit stays and a batch job is given an explicit higher hard limit), "
             "rather than satisfying only one.")),
            ("M10", "referent", "env", "S4: reset between jobs the way it does now",
             ("Finds that nothing resets automatically: reset() exists but a caller must invoke it, and the counter is one "
             "module-level global; says 'the way it does now' is not an automatic behaviour.")),
            ("M11", "constraint", "env", "S10: keep LimitError as it is, other code depends on it",
             ("Records as a boundary that the LimitError class and its throw-past-limit behaviour stay, and notes that nothing in "
             "this repository uses it beyond its own test (the dependent code is elsewhere).")),
            ("M12", "constraint", "env", "S8: tests in node:test like the existing ones",
             "Finds that test/meter.test.js uses node:test and assert, run by node --test, and records that."),
            ("M13", "open", "decision", "S4: each batch job should get its own count",
             ("Notes the open design: how a job is identified, whether the API is a factory of meters or a job argument, the batch "
             "limit, and what happens at it; records defaults or leaves them to a person.")),
            ("M14", "open", "decision", "S11: shouldn't slow the normal path",
             ("Notes that tick() is a constant-time increment today and records a bound (no extra work on the default path) rather "
             "than a number, or flags it as a soft requirement.")),
        ],
    },
    "records": {
        "fixture": "node-records",
        "context": "a small Node.js project of text-record helpers (its README.md describes it)",
        "sentences": [
            "Quick one on the records helpers.",
            ("squash should handle null and undefined by returning an empty string, but it must never swallow a bad type, so keep "
            "throwing TypeError for numbers and objects."),
            "I also want one that squashes every field of a record in one go, the way the old trim helper did.",
            "Make it dogfood-able, I'll try it on the real exports tomorrow.",
            "Rubber-duck the edge cases with an installed review skill, code-review is fine, and then run improve on whatever it finds.",
            "No cursed regexes, if you can't read it in one pass it's too clever.",
            "The whitespace should be the usual whitespace, nothing exotic.",
            "Follow the Orchard style guide for the doc comments.",
            "Keep squash's current behaviour for strings exactly as it is.",
            "Add tests in the same style.",
            "It should be fast enough for a million records, but I don't want to pre-optimize.",
        ],
        "breaks": {1, 3, 5, 8},
        "facts": """\
- Layout: README.md ("Small text-record helpers"), package.json, src/text.js (one function), test/text.test.js.
- squash(value) trims and collapses runs of whitespace (the JavaScript \\s class, so tabs, line breaks and the no-break space count) to a
  single space. Its comment says it throws TypeError for a non-string, and the code does so for anything that is not a string, null and
  undefined included.
- Tests (node:test and node:assert): whitespace collapse ('  a   b ' gives 'a b') and a TypeError for a number. No test covers null,
  undefined or an object.
- No trim helper, record helper or per-field function exists. No style guide, no "Orchard", and no exports data appear in the
  repository. package.json has no dependencies; npm test runs node --test.
- Installed skills offered by the host: until-loop, backchain, plan-dispatcher, improve, in-parallel, ralph-loop, loop, schedule,
  code-review, simplify, ask, shiploop.""",
        "items": [
            ("R1", "skill", "env", "S5: an installed review skill, code-review is fine",
             ("Recognises 'code-review' as the installed code-review skill (a review of the diff for correctness bugs) and records "
             "it as the review step.")),
            ("R2", "skill", "env", "S5: then run improve on whatever it finds",
             ("Recognises 'improve' as the installed improve skill (a review-and-improvement loop) and records it as the step that "
             "acts on the review's findings.")),
            ("R3", "slang", "env", "S4: make it dogfood-able, I'll try it on the real exports tomorrow",
             ("Reads 'dogfood' as using the helper for real; notes that the real exports are not in the repository and that the "
             "helper must be easy to run on them (an importable function); invents no export format.")),
            ("R4", "slang", "env", "S5: rubber-duck the edge cases",
             ("Reads it as explaining the edge cases step by step to find problems, and records the edge cases to cover (null, "
             "undefined, other types, empty and whitespace-only strings).")),
            ("R5", "slang", "env", "S6: no cursed regexes",
             ("Reads it as: no hard-to-read regular expressions; keep the code readable in one pass, as squash's single simple "
             "regular expression is.")),
            ("R6", "unknown", "decision", "S8: follow the Orchard style guide for the doc comments",
             ("'Orchard' appears nowhere in the repository or the skills. A good intake flags the style guide as unknown, states a "
             "best reading (a house style for doc comments) with low confidence, follows the existing comment style meanwhile, "
             "and invents no rules.")),
            ("R7", "referent", "env", "S3: the way the old trim helper did",
             ("Finds that there is no trim helper (only squash), says the referent does not exist, and records a reading (trim, "
             "then collapse, as squash does) or flags it.")),
            ("R8", "conflict", "env", "S2: return an empty string for null and undefined, but keep throwing TypeError for numbers and objects",
             ("Notes that squash's comment says it throws TypeError for any non-string, so returning an empty string for null and "
             "undefined changes that documented contract for those two values, that the one test covers only a number, and that "
             "the comment and tests need updating.")),
            ("R9", "open", "decision", "S3: squashes every field of a record in one go",
             ("Notes that 'a record' is not defined (a plain object, nested, arrays), what happens to non-string fields (skip or "
             "throw), the function's name, and whether it mutates; records defaults or leaves them to a person.")),
            ("R10", "referent", "env", "S7: the usual whitespace, nothing exotic",
             ("Finds that squash uses trim and the JavaScript \\s class (tabs, line breaks, the no-break space) and records that as "
             "'the usual whitespace', or flags the no-break space as the one exotic member.")),
            ("R11", "constraint", "env", "S9: keep squash's current behaviour for strings exactly as it is",
             ("Records as a boundary that the behaviour for strings (trim, collapse to a single space) is unchanged and its test "
             "stays green.")),
            ("R12", "constraint", "env", "S10: add tests in the same style",
             "Finds that test/text.test.js uses node:test and assert and records the style."),
            ("R13", "open", "decision", "S11: fast enough for a million records, but I don't want to pre-optimize",
             ("Notes the performance target is soft and unmeasured and records a default (no premature optimisation, perhaps a "
             "measurement) without inventing a number.")),
        ],
    },
}
GROUPS = ["skill", "slang", "unknown", "referent", "conflict", "constraint", "open"]
