# PushPress skill journal

How the `pushpress` skill became a skill in this repository: where it came from, what was kept, removed and changed, how it
was packaged, reviewed and checked, and what is still unknown. Edited in place; a statement that no longer holds is marked
`superseded` with its date and reason, never deleted.

**Finding status:** `firm` (observed or measured, repeatable) · `interim` (observed once, or cause unconfirmed) ·
`exploratory` (hypothesis) · `superseded`.

**Privacy rule for this work:** the PushPress admin and its API expose member data, including minors'. Nothing in the skill,
this journal or the evidence may contain a member's name, email, phone, birthday or address, a record ID, a key, a machine path,
or a fact that identifies one gym. This journal names what was removed by category, never by value, and names the source by
commit hash and path, not by repository.

## Request and consumers

On 2026-11-08 the owner asked whether a PushPress skill had been put in the skill-craft marketplace. It had not. A project skill
for one gym had been built and surveyed read-only the same day, and the request was a generic copy of it. The marketplace is this
repository: a skill ships as `skills/<leaf>/` inside the one `skill-craft` plugin with a pending note, as `sport80` did.

Consumers: any gym that runs PushPress Core and works with an agent that has a browser tool, installed as `skill-craft:pushpress`.
The gym the source skill was written for keeps its own private overlay (`references/<tenant>.md`) and its own project skill; neither is
here. Maintainers: a change to a route, label or claim needs a re-check against the live page first (the skill's drift procedure).

## Round 0 - repository state (2026-11-08)

- Base: `origin/main` at `d4ff1a47ce89aec5ee546d1601c401850561c58f` (skill-craft 2.35.7, `sport80` 0.1.1): 24 skills, 59 core
  suites and 199 in all, no pending notes. Branch `pushpress` was cut from it in a separate worktree; the main checkout was not touched.
- Precedent read in full: `c1c1cf5b638e5c1bafe06820163a40951baf794b` (the `sport80` feature commit and its decisions),
  `1cd0dd92b9d2ae985e7722dfba8172b2b3166ba2` (a card edit that also edited the pending note),
  `f7b66f577ea5f656dd21971ddf42cfa364463e18` (a test that asserted the pending note, fixed after the release consumed it),
  `1db0d579ea7065c2012e5a87a1012e6b1dcbe588` (the record of the publication: checks run, measurements, the owner's rules) and
  `dcc15966ed399cf154468ca282201f0a3e433f24` (the release).
- **Placement history (`firm`).** The work started as a standalone plugin on the `lennox-s40` pattern, because the first read of this
  repository (at `7b40757183e025f212b720db483e5f73c2b5f247`) showed only workflow skills and external pins. `sport80` then shipped inside the
  bundle: a browser-driven vendor portal, minors' data, write gates, verified only through Claude in Chrome, with a host section that says
  so. That removed the objection that a Claude-in-Chrome-verified skill cannot live here. The standalone draft remains an unpublished local
  drafting repository (head `ce024be517ed79bd51c3a1be64179a5245cad0d8`); it is not a destination.
- **Authorship (`firm`).** The first two commits were first made under an author identity that this repository's earlier commits do not use. Before the third
  was made they were re-authored with the repository's usual identity: `d33177a13c863a89525e12be85571d7498b6d49d` is now `4c7b5fc521ce14c9ab930de0c7a9b551c923d74f` and `41dd64fe95ff4da2d2142c6b8884f6c74dbba6aa` is now `a30c8634000d2623efc9ef1a316dd21a3aad1dc6`. Only the author, the
  committer and the second message's mention of the first commit changed; every tree is identical, so every measurement taken before the change applies to the
  new hashes. Every hash below is the new one.

## Round 1 - source and baseline (2026-11-08)

- **Source:** a project skill, commit `c20f862420c47cc7fa8d9671357baa1abbe20632` ("Add a pushpress skill: verified admin-UI map, sign-in flow,
  safety rules"), under `.claude/skills/pushpress/` in the source project. It was built and checked read-only against one live PushPress Core
  tenant (the *Core Pro Monthly* tier) on 2026-11-08. Its own build journal stays in the source project.
- **Baseline for every diff:** `git archive c20f862 .claude/skills/pushpress`, **not** the source working tree, which held another session's
  uncommitted edits (G3).
- **Drafting repository:** the source was made tenant-neutral there first, in 5 commits, with a scripted port (74 replacements, then 23 more after
  a review, each asserting its match count), a regex scan, a 51-entry external denylist of the source tenant's names and figures (kept outside any
  repository), and an independent read-only review.
- **F1 (`firm`): scans find shapes, not sentences.** In the drafting repository the regex scan and the denylist both passed before the review, which
  still found a policy name and count, a live UTC offset (it identifies a time zone) and several "showed no data" style sentences about one gym:
  3 blockers, 7 should-fix, 6 nits, all real and fixed. The lint in `test/pushpress.test.py` is narrow for that reason; a person or a fresh agent
  must read the diff of any change to this skill.
- **F2 (`firm`): two defects in the source were found by that review and are stricter here.** `Add Plan` and `Add Credit` were MONEY in the profile
  reference but WRITE-DATA in the router, so the weaker rule won; and the webhook list was "safe to call anytime" although the same file says its
  response includes each webhook's signing secret.

## Round 2 - what was kept, removed and changed

**Kept:** the door router (API, admin UI or public tenant pages), the working rules, the sign-in procedure, the seven action classes,
`scripts/pp-extract.js`, and the references `app-map`, `people-and-plans`, `schedule-and-checkins`, `money-and-reports`, `settings-and-admin`,
`browser-technique`, `api-and-mcp-tools` and `drift-and-open-questions`, with the `[observed]`, `[documented]` and `[not exercised]` tags unchanged.

**Left behind in the source project:** its tenant overlay (identity, configuration snapshot, public-page funnel, known issues, ties to the
project's other systems, a privacy-policy follow-up). It is the pattern for what a project supplies as `references/<tenant>.md`.

**Removed, by category (no values):**

| Category | Where it was |
|---|---|
| Tenant identity: host, company name, company ID, time zone and location | the card, `app-map`, `settings-and-admin`, `api-and-mcp-tools`, the extractor |
| Business configuration: plan categories, plan names and prices, discount names and counts, class and location names, document names, product and pre-order counts, people counts, payment mix, API-key count, the fee line that said "this gym's tier" | `people-and-plans`, `schedule-and-checkins`, `money-and-reports`, `settings-and-admin`, `api-and-mcp-tools` |
| Tenant anomalies and empty states stated as facts: a run of zero check-ins, unused appointments, no events | `schedule-and-checkins`, `drift-and-open-questions` |
| Financial figures: revenue and KPI readings, a forecast comparison, an invoice page count | `money-and-reports`, the overlay (not shipped) |
| Coupling to the source project: its issue register and the section codes cited from it, its budget and bookkeeping systems, its change-validation gate, its project instructions and credential-setup script, other platforms in its website funnel, its help-center evidence file and its build journal | every reference, the card |
| A population assumption: the age range of one gym's clients | the card, `people-and-plans`, `browser-technique` |

**Changed in meaning, not only removed (each is a decision; none was measured):**

- **D1. The description is anchored on the name PushPress.** The source said "even if they never say the name", which was safe inside one gym's
  project and would trigger on unrelated "plans or pricing" talk in a public skill. Trigger quality is **not** measured.
- **D2. "Know the tenant first".** The skill states that, apart from the one tier named under Honest limits, it carries no tenant facts (it first said none: F7), says to get the host and company name from the user or the
  project's notes, and describes the overlay: it wins over the maps for its own tenant, the live page wins over both, and it never loosens a rule.
- **D3. Safety classes made consistent and stricter.** `Add Plan` and `Add Credit` are MONEY (F2); `Add Document` is OUTBOUND as a precaution (G3);
  the strictest class applies when a control fits several; the webhook reads return signing secrets, so they are called only when asked and only
  URLs and event types are reported; the API file's labels map onto the card's seven classes and both delete tools are also DESTRUCTIVE (F4).
- **D4. The quantity "known bug" is `[not exercised]`.** The source called it a bug on the strength of its own issue register; it was never re-tested,
  so it reads "reported once, not re-tested" and keeps the advice to check a plan's quantity before editing.
- **D5. "Reading zeros".** One tenant's run of zero check-ins became a generic caution: a zero count means nothing was *recorded*; cross-check with the
  API's check-in count before concluding anything about attendance.
- **D6. API "Setup" paragraph.** The SDK's MCP server, its start command, that it declares no scopes so every tool is mounted, every write tool by name,
  and the two webhook reads. Drawn from the source project's notes, so it is `[documented]`, not re-run.
- **D7. The extractor.** The company-switcher label became `__pp.company('<company name>')`, stored in session storage so it survives a full page
  load; auto-detecting the button was rejected because it cannot be verified without the live DOM. After Round 4 it also masks contact details, record
  ids and "Select <name>" labels in everything it records, and says in its header what it does not protect. Its header comment and one runtime message
  no longer name a host's tool.
- **D8. Sign-in wording independent of one user's setup.** The grant is "the host's approved credential flow", a vault item bound to the tenant host
  is a conditional, there is a manual path when the host has no approved fill, and no password manager is named.
- **D9. A password's length is not recorded.** The source probed `value.length`; a length in a transcript is information about the password, so the
  skill asks only whether the field is empty, and takes no screenshot or page-text read while a password is revealed.

## Round 3 - packaging for skill-craft

- **Host neutrality is packaging, as `sport80` showed (`firm`).** The card speaks in capabilities (a browser tab, real pointer clicks, a page-script tool,
  the host's credential flow). `references/hosts.md` holds the prerequisites, the tested matrix (Claude in Chrome tested; everything else not), the one
  verified recipe tool by tool, and a fallback for any other tool. `references/browser-technique.md` keeps its Claude in Chrome tool names and says so in
  its first paragraph. `test/pushpress.test.py` fails if the card names a host tool identifier.
- **No CLI.** `sport80` has a Python CLI because it constructs requests worth pinning. This skill's only script is injected page JavaScript, so its
  hermetic suite is the card and reference contract, link and anchor resolution, a narrow lint with a seeded-leak proof, and a stub-DOM harness for the
  extractor with twelve deliberate breaks it must catch (eleven at first; F9 added the twelfth). Nothing asserts the pending note, because `scripts/release.py` consumes it (`f7b66f57`).
- **D10. Leaf `pushpress`.** It keeps the source skill's name. The plugin namespaces it `skill-craft:pushpress`, so a marketplace install cannot shadow
  a project skill of the same name; `./install.sh --skill pushpress` links it as plain `pushpress`, so a project that already has its own skill by that
  name should use the plugin.
- **D11. Not shipped:** the three eval cases (they are `claude plugin eval` cases keyed to a standalone plugin layout and stay in the unpublished draft,
  unrun), the drafting repository's `check.py` (its denylist must stay outside any repository), and any tenant overlay.

## Round 4 - independent review of the candidate (2026-11-08)

A fresh read-only agent read all 17 files of the first candidate commit (`4c7b5fc521ce14c9ab930de0c7a9b551c923d74f`) against the bar (AGENTS.md,
ARCHITECTURE.md, the shipped `sport80` card and hosts.md), with none of my conclusions. It found no tenant fact, no personal data and no machine path,
and reported 10 should-fix items and 8 nits. I checked each against the files; all were real; all were fixed in
`a30c8634000d2623efc9ef1a316dd21a3aad1dc6`.

- **F3 (`firm`): the extractor masked only buttons and ID links.** A link's visible text was printed for any link without an id in its path, so a
  `mailto:` or `tel:` link printed the address or number; tabs, column headers, labels, inputs, toggles and headings recorded raw text (a row checkbox
  labelled "Select <name>" reached the output); `sidebar()` printed raw paths; and, found while reading the fix, the recorded page path held a person's
  record id on a profile page. All are masked now and pinned by five new harness cases and six new mutations. The first draft of the phone mask turned the
  ISO date 2026-10-01 into `<phone>`; the final pattern needs a 3-3-4 digit group, a plus sign with 8 to 15 digits, or 10 to 15 bare digits, and the
  harness pins that a dated heading survives. Rejected: dropping every label with 3 or more digits as buttons do (it loses counts in tab labels), and
  applying the Open, Edit and View label mask to tabs and toggles (the "Open invoices" tab and the "Open gym access" toggle would become "Open <item>").
- **F4 (`firm`): the API file did not speak the card's classes.** Its labels (READ-PII, WRITE-OUTBOUND, WRITE-CONFIG) did not match the seven, both delete
  tools lacked DESTRUCTIVE, and its confirm list omitted a write tool and read as if it gated the webhook reads too. Fixed (D3, D6).
- **F5 (`firm`): several statements claimed more than the evidence.** Dating ("everything checked on 2026-11-08") did not fit the API file or two
  "reported" statements that carried no tag; the built-in browser row contradicted the prerequisites; one line named the owner's password manager; an
  App Store list could not be told apart from the apps a gym has installed; and "confirmed live" on an empty webhook list told a reader the surveyed gym
  had none. Fixed, and the legend now says what *reported* means.
- **F6 (`firm`): a password's length must not reach a transcript** (D9).
- **Lesson (`firm`).** Two independent reads, a scan and a denylist each found different things. The first review, of the drafting repository, passed the
  extractor's masks as read-only and clean; this one, briefed to attack the masks and the tests as well as the prose, found four gaps in them. Brief a reviewer
  to attack the privacy code, not only to read the text, and have the harness pin every gap found.

## Round 5 - a read of the rewritten sentences against the source (2026-11-08)

Done after Round 4, because its lesson said a person must read the diff. I read the 14 shipped text files as ordinary text, then diffed every reference and the
card against `git archive c20f862` of the source skill, starting with the sentences the first generalization **rewrote** rather than removed. A removed fact is
easy to see in a diff; a fact restated as something general is not.

- **F7 (`firm`): three tenant-derived statements had passed a scan, a 51-entry denylist and two independent reviews.** None holds a name or a number a scan could
  match, which is why they passed. By category: a sentence about one gym's pricing practice, restated as a capability of the product (nothing observed it as a
  capability); two example values taken from one gym's list; and, in a settings-table row, the surveyed gym's own subscription tier with the tier above it. All
  three are removed, the last from the row only: the tier is still named wherever the verification scope is stated, because the scope has to say what the checks
  ran on. So the card's "carries no tenant facts" became "apart from the one tier named under Honest limits", and the pending note says the same.
- **F8 (`firm`): several lines claimed more than was checked.** "Everything in it was checked" included the extractor's masks, which no live page has seen; "three
  fresh agents checked the skill" described the source project's version, not this generalized copy; and the extractor header said it masks link text for "any URL
  with an ID segment" while the code masks 10 or more lower-case hex characters and the person routes. Each now says what was done (G1). Two smaller leftovers went
  too: the API file called the skill "this plugin", and the card's router used a label (`READ-PII`) that only the API file defines.
- **F9 (`firm`): one more extractor edge.** Side-panel text was skipped on `/user/` pages only, while ids and link text were masked on `/people/<id>` routes too. The
  skip uses the same predicate now; the harness pins it and a twelfth deliberate break proves it. Widening the id pattern to UUIDs and numbers was rejected: those
  shapes cannot be verified without the live DOM, and masking any segment that holds a digit would blank the date-ranged report links. The limit is documented in
  the header instead.
- **Lesson (`firm`).** Round 4's lesson stands, stronger: scans find shapes, reviewers find some sentences, and a read of the *rewritten* sentences against the source
  found the rest. Do that diff read for any change to this skill and for any port, and write what it finds into the commit and this journal by category, never by
  value. All of it is fixed in `f12acb0dbb795b5e24e0794e1966e0a4e8ed4a76`.

## Round 6 - checks (2026-11-08)

Run on the final candidate head `f12acb0dbb795b5e24e0794e1966e0a4e8ed4a76` (tree `2f685e6ed827e8a99688423bfd2bc72a835870b1`), base `d4ff1a47`, with each exit code captured from the command itself and no pipe between a
command and its status. Raw results: `docs/evidence/pushpress-candidate-20261108/summary.json`. The commit that adds this journal and that file changes only docs, so the
tested tree is its parent's; `python3 test/pushpress.test.py` was run again on the commit that adds them, because that suite lints them.

| Check | Result |
|---|---|
| `python3 test/pushpress.test.py` | exit 0: 14 tests OK (twelve deliberate extractor breaks, each asserted to apply once and to fail the harness) |
| `node test/pushpress-extractor-harness.js` | exit 0: PASS, 14 checks |
| `node --check` on the extractor | exit 0 |
| `node test/skill-frontmatter.test.js` | exit 0: PASS, 25 skills |
| `python3 test/test-groups.test.py` | exit 0: 61 tests (core suites 60, all suites 200) |
| `python3 test/installed-skill-invocation.test.py` | exit 0: 12 tests |
| `python3 scripts/check-release-boundary.py --base origin/main` | exit 0, OK, over the three commits |
| `python3 scripts/release.py --dry-run` | exit 0: pushpress 0.1.0 to 0.1.0 (1 note); skill-craft 2.35.7 to 2.35.8 |
| `python3 scripts/build-packages.py OUT`, then `python3 scripts/check-marketplace-packages.py --root OUT` | exit 0 and 0: 1 of 1; the packaged skill is identical to `skills/pushpress` |
| `bash test/run-all.sh --group quick --changed-from origin/main --jobs 8` | exit 0, PASS: 41 suites in 467.8 s wall (slowest: shiploop-navigator-contract 467.8 s, shiploop-actual-improve-cli 420.8 s, shiploop-lint 339.0 s), on the final head; 41 rather than the earlier 18 because the changed set is computed against the local `origin/main`, which another session had moved meanwhile, so it also pulled in that session's shiploop and sport80 suites; all 18 earlier suites are among them |
| privacy: the 51-entry external denylist, then shapes (emails, record ids, phones, keys, paths, personal markers), over the 19 files this branch adds or changes (the 17 changed files, then the journal and the evidence once written) | 0 hits in 5,154 lines read; one control proved the denylist grep matches a file and a second that the shape greps fire on a seeded line; the one shape match was the lint's own regex literal |

Earlier scoped quick tiers on the same trees, before the commits were re-authored: 208.1 s for 18 suites on the first commit's tree and 433.1 s for 18 on the second's
(tree `a3b5915f678e9836940f33d032cf0462d35b5bc5`); the second ran while other sessions were using the machine, which is why it took twice as long.

**Release rehearsal (the check `sport80` missed: F20 of `1db0d579ea7065c2012e5a87a1012e6b1dcbe588`).** In a disposable detached worktree, never on the branch, the real
`scripts/release.py` cut `release: skill-craft 2.35.8, pushpress 0.1.0` (`fafbc0d89e9adde0b7e4135e1f319b954ec5b509`, in the scratch worktree only, reachable from no branch) with the trailer `Skill-Craft-Release: skill-craft 2.35.8, pushpress 0.1.0` (the real one joins name and version with an at sign, which this suite's email lint rejects), and consumed the
pending note. Then the four checks that the `sport80` publication handed to `release-push.py`, with the same argv: `bash scripts/sync-plugin-views.sh --check`,
`python3 scripts/check-marketplace-packages.py`, `python3 scripts/check-release-boundary.py --base d4ff1a47` and `python3 test/test-groups.test.py`, all exit 0; then the changed suites
on the released tree (the pushpress suite, the harness, the frontmatter test and the installed-skill test), all exit 0; the packaged copy equals the source. Nothing in this
skill's suite asserts the pending note, which the cut deletes.

**Trial on the moved main (G7).** A second disposable detached worktree at the local `origin/main` (`60ba1b70f929294549ceb9d45bf62f33667e3ea7`), the candidate merged in without squash: exit 0, 0
conflicts. `release.py --dry-run` there printed `pushpress 0.1.0 -> 0.1.0 (1 note)` and `skill-craft 2.35.8 -> 2.35.9`. The real cut there gave `release: skill-craft 2.35.9, pushpress 0.1.0` (`4fb4ab5143d3e3aa126d16cec872cb99eab13c46`, scratch only); the four release checks, the pushpress suite, the harness and the
frontmatter test passed on it, and the packaged copy equals the source. The only pending note in that merged tree was this skill's (`initial.md`): the other session's had been consumed by its own release. This is a rehearsal of what a publish would meet now, not the release.

**Not run:** the real release on the branch; `scripts/release-push.py`; any push, tag or merge; CI; the aggregate or full core group; any check against a live tenant.

## Still unknown

- **G1 (`firm`).** The generalized skill has not been run against a live tenant after generalization. Its facts are one read-only survey of one tenant on
  2026-11-08, and the extractor's new masks are covered by a stub DOM only.
- **G2 (`firm`).** No write flow was exercised (no save, create, charge, send, delete, merge or download); the sign-in procedure was observed in one session
  and not re-tested; three fresh-agent checks ran with the source project's version of the skill only, never against a no-skill baseline. The three eval cases have not been run; they stay in
  the unpublished drafting repository.
- **G3 (`interim`).** The source working tree held another session's uncommitted edits to two references: they say the *Document Ready to Sign* email is
  addressed to the member, so attaching a document emails the person, which contradicts the committed "alerts to staff" wording. They were not ported
  (uncommitted, one tenant, and they carry tenant counts and an address). The precaution (`Add Document` is OUTBOUND; two sentences hedged) is here.
  Re-check this skill against them once committed.
- **G4 (`firm`).** Other hosts are untested; other PushPress tiers may differ; Grow, Train and the Staff and Members apps were never surveyed.
- **G5 (`exploratory`).** Trigger quality of the re-anchored description is untested.
- **G6 (`firm`).** Not checked by either reviewer: the Kisi and HybridAF access-integration note, PushPress's published fees against live sources, and the
  SDK figures (44 tools, "8 of 49 methods").
- **G7 (`firm`).** `origin/main` kept moving while this branch was prepared: four commits by other sessions since the base (`d4ff1a47ce89aec5ee546d1601c401850561c58f`), one of
  them a release (skill-craft 2.35.8 with shiploop 1.33.6), all in files this branch does not touch. So a release needs main merged into the branch again just before the cut, as it
  did for sport80; the version this release carries moves with main (2.35.8 on the base, 2.35.9 on the main of the Round 6 trial); and a cut ships whatever is pending on main as
  well. Round 6 records a trial of exactly that in a scratch worktree; it is not the release.
- **G8 (`firm`).** The three eval cases and the drafting repository's scanner exist only in the unpublished drafting repository. Deleting that repository loses them; nothing
  in this branch depends on it.
