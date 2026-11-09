# Design brief: a patch for the sport80 skill (review BEFORE implementation)

Repo: skill-craft (host-neutral portable skills monorepo; read `AGENTS.md`). The skill is `skills/sport80`: read `SKILL.md`,
`references/{protocols,safety,access,hosts}.md`, `scripts/runtime.js` (the in-page runtime, 249 lines), `scripts/sport80.py`
(the CLI), `references/capabilities.json` (the catalogue), `test/sport80.test.py`, `test/sport80-runtime-harness.js`, and
`docs/sport80-journal.md` (Round 2 holds the earlier design review and its P0 trust boundary; Round 9 holds the defects below).
Do not browse the portal; everything you need about it is below and was measured live on 2026-11-08.

## What the owner's test of the published skill found (journal Round 9)

- F25 (defect). The card says to take a meet's `event_id` from a row's View link, then call `results.event`. The runtime's row
  builder `cells()` reduces `row.action[]` to the labels, so rows carry `actions: ["View"]` and no link. The raw link is
  `/public/rankings/results/<number>` (no query). With that number `results.event` works (8 rows, 14 columns). So the club's meets can
  be listed but not opened through the skill.
- F26 (same cause). `members.charts` lists a tab whose URL is `/api/contact/statistics/draw?addon_id=<n>&contact_type=...&body_cid=...`;
  `qnames()` prints a URL as path plus query PARAMETER NAMES only, so `addon_id`'s value is hidden and `members.charts.draw`
  (required `addon_id`) cannot be given its input.
- F27 (gap). `results.rankings` is offered as runnable (verified: descriptor) but returns total 0 without a body weight category and a
  date range. The portal's descriptor says `no_data_message: "Please select a body weight category and date range"`, marks
  `weight_class` `validators: {required: true}`, and carries the valid values inline as `items: [{text, value}]` (1,140 weight
  classes; `level` has 4). `table()` returns only `{name, type, label}` per filter, so an agent cannot discover valid values, and the
  catalogue does not declare the filter required.
- F28 (limitation). No route to the club's member count: `members.legacy_list` returns an HTML outline (headings and table headers
  only); quick search needs a filter; Smart List rows need a column model. `members.charts.draw` returns "an HTML fragment with the chart".
- F29 (usability). The 21 KB runtime must be pasted into the host's script tool for every new tab.

## The existing trust boundary (do not weaken it)

Local scripts never receive credentials and make no requests. Page code may use session tokens transiently in function scope; no token
reaches a global, a log, an error or a result; headers are per origin; UUID-shaped strings are redacted by `finish()`; `qnames()`
prints a URL as path plus query parameter names so that a token in a query value can never reach a result. Sensitive tables return
counts only unless `fields` are named. Entries are `read | guided | owner-only`; only `read` runs.

## Proposed patch (smallest thing that fixes F25 to F27, plus a question on F28)

1. Row links. `cells()` adds `links: [{text, url}]` for each action that has a url, with `url` printed by an updated `qnames()`:
   path plus parameter names as today, except that for an ALLOWLIST of id parameter names (`addon_id`, `eid`, `id_cat`) whose value
   is all digits (`^\d{1,12}$`) the value is shown (`?addon_id=7,contact_type,body_cid`); and any PATH segment of 24 or more
   characters from `[A-Za-z0-9_-]` is replaced by `<token>` (paths are already printed today). `actions` stays unchanged (no break).
   `links` is an extra row key, so `--fields` drops it unless named; the card will say so. The same `qnames()` feeds `tabs()` output, which
   fixes F26. Row links on sensitive tables stay behind the existing rule (rows withheld unless fields are named).
2. Filter options. A new runtime option `options: '<filter name>'` (+ `optionSearch: '<text>'`) on a datatable entry returns
   `{options: [{text, value}], total, returned}` from the descriptor's filter `items`, case-insensitive substring match on `text`,
   at most 50 returned, only for filter types select, autocomplete, radio, and only when the table is NOT `data: sensitive`; it fetches
   the descriptor only, no rows. Unknown filter name gives `UNKNOWN_FILTER`. The CLI gets `--options NAME` and `--option-search TEXT`.
3. No silent empty results. (a) the catalogue declares `requires_filter: ["weight_class"]` for `results.rankings` (the existing rule:
   at least one of the listed filters, refused before any request with `FILTER_REQUIRED`), and its notes name the date range;
   (b) `table()` returns the descriptor's `no_data_message` as `hint` (string, at most 160 chars) whenever `total === 0`.
   I still have to find, live, the request-body shape that an autocomplete filter value takes (`1133`, `[1133]` or `{value, text}`);
   it will go in the catalogue as an example only after a live read returns rows.
4. Docs and catalogue: the card and `protocols.md` describe `links`, the allowlist, `options` and `hint`; `results.event`,
   `results.events`, `members.charts.draw` notes point at them; `results.rankings` becomes `live` only after rows were read.
5. F28: I lean to leave it as a documented limitation. The only candidate is an opt-in catalogue flag `text_ok` on
   `members.charts.draw` letting the html outline return the fragment's visible text (tags stripped, at most 1,500 chars) so a chart's
   totals can be read; I would not add a generic text option because the same outline code also serves pages that hold personal data.
6. F29: leave as a limitation (no minifier is available offline; a hand rewrite would risk the runtime's correctness).

Tests planned: the Node harness (25 scenarios, fake portal with secret sentinels) gets scenarios for row links (a path id kept, a query
token hidden, an allowlisted numeric id shown, a non-numeric value for an allowlisted name hidden, a long path segment masked), tab URLs,
`options` (cap, search, unknown filter, type and sensitivity refusals), `hint`, and `requires_filter` on the rankings entry; the Python
suite gets catalogue invariants and CLI tests for `--options`. A live validation of the new runtime in the signed-in portal follows
before release; then a patch release (0.1.2).

## What I want from you

Review the design, not the prose. Rank concrete risks P0 (do not ship), P1 (fix before shipping) and P2 (note), each with the exact
file or function it concerns and a specific fix. In particular:
1. Does the `qnames()` change keep the trust boundary? Name any path by which a token, a signed URL, a personal identifier or a
   session value could now reach a result (consider export or download links, `top_buttons`, member rosters whose row links carry
   `cid`, and the `<token>` rule's false negatives such as short opaque ids).
2. Is exposing filter `items` safe and bounded? Is "not for sensitive tables" the right line, or should some non-sensitive tables
   also be excluded (consider filters whose items could be people or clubs)?
3. Is `requires_filter` plus `hint` the minimal way to stop silent empty results, or is there a smaller or safer one?
4. F28: is the opt-in `text_ok` worth it, or should the limitation stand?
5. What breaks or regresses (the `fields` interplay, the 12,000-character bound, `bound()`, `finish()` redaction, the CLI contract, the
   catalogue validator, the drift tests)? What test would catch it that I have not listed?
6. Anything I have missed.

Answer in at most 700 words, grounded in the code you read, with line or symbol references.
