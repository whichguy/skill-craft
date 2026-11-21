# Amendment 14: the second reading of the six pairs

A Sonnet subagent was given the six pairs (the specification as the spec stage left it, and the plan) under
shuffled names `r1` to `r6`, the registered definitions of the four classes (O+, O, D, P) and nothing else. It was
told to read only, to quote every sentence it relied on, and not to group the pairs. It could not be blind to the
arm: three of the specifications end with a section. Its report is abridged below to the sentences that decide each
class; nothing it gave as a class or a doubt is left out.

Key to the names (made with a fixed shuffle before the reading and kept outside the reader's folder):
`r1` = `b-rules-1`, `r2` = `b-base-1`, `r3` = `b-rules-3`, `r4` = `b-base-3`, `r5` = `b-base-2`, `r6` = `b-rules-2`.

Its classes, in order: r1 O+, r2 O+, r3 O+, r4 O+, r5 O+, r6 O+. The main session's reading, made separately from
the same files under their real names, is O+ for all six.

## r1 (`b-rules-1`): O+, 64

- spec C-3, `Open:`: "whether surrounding whitespace is trimmed and whether names have a maximum length or forbidden
  characters is not stated. A name of 1 to 64 printable characters without surrounding whitespace must be accepted
  and stored as given; behaviour beyond that is the requester's to settle."
- spec, Rules and edge cases: "Trimming and a length limit are not settled (C-3 Open)."; "Not settled by the request
  or by what is here: the maximum length and character rules of an agent name, ..."
- plan, Decisions 4: "**Name rules** (C-3 Open): trim like other text fields, max 64 characters, no control
  characters, stored trimmed."
- Its doubt: the `Open:` line also says names of 1 to 64 characters "must be accepted"; read as a floor inside an
  open point, not a decided maximum.

## r2 (`b-base-1`): O+, 64

- spec C-1, `Open:`: "whether surrounding whitespace in the name is trimmed (the existing text fields trim) and the
  longest accepted name (existing text fields have limits: requester 64, title 200); the requester of the service
  decides. A test checks only ordinary short names without surrounding whitespace."
- plan, Decisions 1: "**Name rules reuse `text()`**: trimmed, max 64, no control chars. Reason: C-1's open point
  leaves it to the requester; matching the existing text fields is the least surprising, ..."
- plan, How we will know: "do not assert behaviour for the open points (resolved + same assignee, unassign of an
  unassigned ticket, trimming/length)".
- Its doubt: none material.

## r3 (`b-rules-3`): O+, 64

- spec C-3, `Open:`: "whether a name is trimmed, and its maximum length or forbidden characters. The request gives
  only "non-empty". The existing text fields trim, cap at 64 or 200 characters and refuse control characters; the
  requester decides if the same applies. Tests should use ordinary short names such as `dana`."
- spec, Rules and edge cases: "Trimming, maximum length and forbidden characters are not settled by the request
  (open in C-3). The existing 64-character actor and requester limits are the nearest precedent, not a
  requirement."
- plan, Approach: "The cap needs its own `LIMITS.assignee = 64`, the requester precedent. This is the answer to the
  Open point in C-3."
- plan, How we will know: "do not assert ... trimming/length behaviour".
- Its doubt: none material.

## r4 (`b-base-3`): O+, 64

- spec C-3, `Open:`: "whether there is an upper length for a name, and whether control characters in it are refused.
  The service's other text fields are single-line and at most 64 characters (requester); the requester of the
  service would settle whether agents follow the same rule. A test must not rely on any length bound."
- plan, Decisions 5: "**Name rules (C-3 Open):** trim; non-empty; `typeof string`; reject control characters (reuse
  `CONTROL`); upper bound 64 (same as requester). That is the reasonable answer to the Open point and is reported
  by the build. Tests must not assert on length or control characters."
- Its doubt: none material.

## r5 (`b-base-2`): O+, 64

- spec C-3, `Open:`: "whether a whitespace-only name, a name with control characters (tab, line break), or a name
  longer than some maximum is refused. The existing text fields refuse whitespace-only, control characters and
  over-length (requester: 64). The requester decides which apply to an agent name and what the maximum is."
- plan, Decisions 2: "**Name text rules (C-1/C-3 Opens).** Reuse the existing `text()` helper with limit 64 (same as
  `requester`) ... The builder states in the report that trimming and the 64 limit were chosen."
- plan, How we will know: "tests must pass whichever answer the builder took for an Open point (whitespace, max
  length, ...)".
- Its doubt: the Observable of C-3 refuses only `""` and non-strings, not whitespace-only names; that does not
  change the class.

## r6 (`b-rules-2`): O+, 64

- spec C-4, `Open:`: "whether surrounding whitespace is trimmed (the existing text fields trim) or kept as given,
  and whether there is a maximum length (requester is limited to 64, title to 200), are not stated; the requester
  would settle both. A test must use only plain names without surrounding whitespace and well under 64 characters."
- spec, Rules and edge cases: "Length limit and trimming: not settled (C-4 Open)."; "Not settled by the request or
  the code: ... name length and trimming (C-4), ..."
- plan, Decisions 4: "... at most 64 characters, no control characters (reuse the `text()` rules with a new
  `LIMITS.assignee = 64`, same as requester). Open points taken: trim and 64, matching existing text fields; report
  these in the build report."
- Its doubt: none material.
