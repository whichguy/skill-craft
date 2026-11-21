# Grokbot-local: blind vs with-build test-writing sessions (activity, execution side, tolerance, own reports)

Sources. RUN = /Users/dadleet/e2e-runs/ratchet-parallel-20261121-6f54fb.
- blind: RUN/gb-blind (session record `sessions/01-tests-1-1/events.jsonl`, 79 events; work folder `work/`).
- with-build: RUN/gb-beside (`sessions/01-tests-1-1/events.jsonl`, 83 events; `work/` holds server.js, lib/, public/, test/ of the finished product and `ratchet/build-1.md`).
- `ratchet/spec.md` and `ratchet/plan.md` are byte-identical in both work folders (diff). `ratchet/acceptance.json` differs only in the command form (blind: `node acceptance/suite.cjs U-1`; with-build: `node --test --test-name-pattern='^U-1 ' acceptance/suite.cjs`). Both map 115 items (C-1 to C-100 and U-1 to U-15).
- The two stage prompts differ as the brief says: blind adds "the product is not in this folder", the adapter rule, "Take each name, and each answer at an open point, from ratchet/plan.md", the `Assumed` section, "run every command against the starting project; new behaviour must fail there". With-build instead says "Run every command against the product as it stands" and points at the Discoveries in `ratchet/build-*.md`.
- Models: both Codex, gpt-6.2-sol high (run.json). Sessions: blind 1308.6 s, with-build 1296.9 s.
- Counting scripts (read-only, nothing run but them): `gb-session-activity-count.py` (adapted from the morning's `blind-session-activity-count.py`), `dump.py` and `full.py` (print every command with its output), `tails.py`, `names-blind.py`, `names-beside.py`, `names-beside2.py`, `literals.py`, `split-lines.py`; their text outputs `count-gb-blind.txt`, `count-gb-beside.txt`, `blind-dump.txt`, `beside-dump.txt`, all beside this file. Every statement below was checked against the command text or the file named. I ran none of the products or the suites.

## Part 1: what each session ran

| session | seconds | shell cmds | own acceptance-test runs | of those showing a failing test | first acceptance run | product's own tests (`npm test` / `node --test`) run by the session itself | distinct product source files read | output tokens |
|---|---|---|---|---|---|---|---|---|
| blind (gb-blind) | 1308.6 | 35 | 4: #20 (two single items, `node acceptance/suite.cjs C-81` then `C-33`), #22 (all 115 mapped commands, 8 at a time), #27 (`C-100` alone), #35 (all 115, final) | 4 of 4 (by design: 90 items must fail on the starting project: #20 C-33, #22 and #35 "expectedFailures":90, #27 C-100) | #20 of 35 (full run first at #22) | 0 directly. `npm test` ran only inside item C-100 on a temporary copy of the starting project (#27, #22, #35): it reported zero tests | 0 product files (no product existed). Starting files read: README.md, package.json, provider/README.md, provider/standin.js, records/README.md, records/people.json, records/records.json (#1, #7) | 60,959 (reasoning 16,021) |
| with-build (gb-beside) | 1296.9 | 37 | 12: #12 (C-33 only), #20 (all C-), #21 (all U-), #24, #26, #27, #29, #31 (subsets re-run after edits), #32 (all 115), #34 (all 115), #35 (C-83, U-3), #37 (C-3). A 13th, #33, ran a probe script built on the harness, not the tests | 6 of 12: #20 (9 items failed), #21 (U-1, U-6, U-8), #24, #26, #27, #29 (the last two with C-13, C-48, C-53, C-99, U-6 failing); the last four runs (#32, #34, #35, #37) and #31 are all green | #12 of 37 (single item, passed); first failing run #20 | 0 directly. `npm test` ran only inside item C-100 (`acceptance/runtime.cjs` line 298) | 5 product files: server.js (#9), public/app.js (#9, #11, #23, #28), public/index.html (#9, #18), test/rules.test.js and test/service.test.js (#13). Not read: lib/*.js (only listed in #1). Also read: ratchet/build-1.md (#3, the build report with 16 Discoveries) | 59,531 (reasoning 15,656) |

Gate results in `run.json` for context: with-build `after-given-build` pass, `cycle-1-first` pass, `final` pass. Blind `cycle-1-first` and `final`: pass false with 25 items passing and 91 failing (90 items plus one gate-level entry `check: npm test`, which fails on the starting project's zero tests). The 25 passing items are the existing-behaviour ones that the shipped provider and fixtures can answer (23 clauses + U-9, U-11), exactly the list the session printed in #22.

Notes on the table
- "Acceptance run" = a command that executes `node acceptance/suite.cjs ...`, `node --test ... acceptance/suite.cjs`, a runner over `ratchet/acceptance.json`, or `$TMPDIR/ratchet-run-checks.cjs`. Not counted: `node -c` syntax checks, heredoc file writes, probes (listed below). Rule: `gb-session-activity-count.py`, `kind()`.
- "Showing a failing test" uses the regex `not ok|✖|# fail N|FAIL|"expectedFailures":N|Failures: ...` on the command output.
- Blind probes of its own machinery (not the suite): #10 (compiles `acceptance/webkit.swift` with swiftc), #11, #12 (WebKit driver on a `data:` page), #21, #24 (adapter on a `data:` page: #21 died with SIGSEGV, #24 exit 1), #29, #30 (adapter on a tiny HTTP page, below), #23, #28 (V8 coverage flush after SIGTERM from a `node -e` child). With-build probe: #33 (`$TMPDIR/ratchet-discovery.cjs`, one discovery about a held save).

### What did the blind session run its tests AGAINST?

Against the starting project only: provider/standin.js, records/*.json, package.json, README.md and the two ratchet files (command #4 `rg --files`: nine files, no server.js, no lib, no public). The suite has a switch for it: `delivered()` (adapter.cjs line 158) is false when `server.js` is absent, and then each item runs its `baseline` branch instead of its browser scenario (suite.cjs line 1829 to 1833: "`${id} is absent in the starting checkout. No chat service has been delivered`" is the failure for the 90 new-behaviour items; the 25 existing ones run `selected.baseline()` against the shipped provider, for example C-81 prints "Starting checkout: checks the shipped provider or fixtures", #20). So no browser, no service start, no page scenario of the suite ever ran against anything. Its one real execution against the starting folder is item C-100's baseline, `baselineRuleTests` (adapter.cjs 358): copy the starting folder (`deliveryCopy`, minus .git, data, acceptance, ratchet, node_modules) into `$TMPDIR/chat-tests-coverage-*` and run `npm test` there (zero tests, exit 0, so C-100 fails as designed, #27).

Did it write or generate a stand-in? Not a product stand-in, but yes, small throwaway fixtures to prove its own driver:
1. #11 and #12: pages given as data URLs, `'data:text/html,<textarea></textarea><button>Next</button>'` (42 bytes of HTML), driving the compiled WebKit driver with open/eval/key (Shift+Enter, Tab, Option+Tab).
2. #21 and #24: `'data:text/html,' + encodeURIComponent('<section aria-labelledby="h"><h1 id="h">Example</h1><label>Message<textarea></textarea></label><button onclick="this.textContent = \'Clicked\'">Send</button><span role="status" aria-label="Task status">Running</span></section>')` (238 and 169 bytes), run through the real adapter (`sandbox(t)`, `s.browser({url})`, `page.fill/key/click/wait/close/reopen`).
3. #29 and #30: an inline `http.createServer` fixture in a `node <<'EOF'` heredoc (no file written): `fixture.listen(0,'127.0.0.1')`, serves one HTML page of about 430 bytes (a labelled section with a textarea, a Send button, a status span, an article "Message from Example") with `Set-Cookie: session=probe; Path=/; HttpOnly` and a `/probe` route that echoes the cookie; used to check the driver's `size`, `fill`, `key`, `messages`, request arming/abort, replay and close/reopen with the cookie kept. #29 failed ("Cannot read properties of undefined (reading 'payload')", the page had no article named for the speaker the test read), #30 passed after editing the fixture page.
4. #23 and #28: `spawn(process.execPath, ['-e', 'console.log("ready");setInterval(()=>{},1000)'], {env:{NODE_V8_COVERAGE: dir}})` to check that SIGTERM flushes V8 coverage (#23 printed `[]`; #28, with `--require ./acceptance/adapter.cjs`, printed one coverage file; the adapter's `RATCHET_ACCEPTANCE_COVERAGE` SIGTERM handler at adapter.cjs lines 16-21 is the result).
Size: each of the first three fixtures is one inline string of 42 to 430 bytes; the fourth a one-line child process. Left in the work folder: none. `git status` after #34/#35 lists only `acceptance/*`, `ratchet/acceptance.json`, `ratchet/tests-1.md`; `RUN/gb-blind/tmp` holds only Node's compile cache (the swiftc probe binary was unlinked in #34 with `unlink(missing_ok=True)`). Left inside the suite: none of these fixtures (grep of `createServer`, `fake`, `stub`, `mock` in acceptance/*: only `net.createServer()` in `portAvailable`, adapter.cjs line 105, to find a free port).

The suite itself holds the following test-side stand-ins or mechanisms that did not run against a product: a page-side patch of `window.fetch` that records, holds, drops or aborts the page's own requests (adapter.cjs `browserTools`, lines 456-482), a `MutationObserver` sampler (`watch`), a delivery copy per service start (`deliveryCopy`, line 188) and a V8-coverage rule-module probe (`ruleTests`, line 309). Unlike battleship, none of them answers on behalf of the product (nothing forges a product reply).

## Part 2: the execution side of each suite

### Line counts

| suite | file | lines | what it holds |
|---|---|---|---|
| blind | adapter.cjs | 692 | processes and ports (1-112), fixtures and provider helpers (113-164), env, delivery copy, service start/stop/restart, WebKit launch (165-328), V8 coverage and `npm test` (329-365), in-page instrumentation `browserTools` (366-533), `Page` driver client with the product's labels as methods `enter`, `switch`, `selectBot`, `newBot`, `send`, `save`, `token`, ... (534-687) |
| blind | webkit.swift | 128 | Swift WKWebView line driver (open, eval, key, size, close, return) |
| blind | suite.cjs | 1905 | the 115 items: 1,271 lines inside `clause(...)`/`useCase(...)` blocks, 634 lines of helpers (propose, startTask, state, openDiscussion, label constants) and the runner |
| blind | total | 2,725 | |
| with-build | harness.cjs | 520 | Chrome DevTools client and `Page`, service launch/restart/stop, scratch dirs, source copy, token |
| with-build | flows.cjs | 226 | page-driving helpers with the product's labels (`enter`, `bot`, `library`, `proposed`, `task`, ...) |
| with-build | runtime.cjs | 324 | C-1 to C-6, C-15 to C-22, C-100 (startup, port, data dir, credential, `npm test` coverage) |
| with-build | workspace.cjs | 427 | C-9 to C-14, C-23 to C-31, C-45 to C-60 |
| with-build | records.cjs | 317 | C-43 to C-77 (provider clarification, grounding, proposals) |
| with-build | tasks.cjs | 351 | C-78 to C-93 |
| with-build | interface.cjs | 317 | C-32 to C-42, C-94 to C-99 |
| with-build | scenarios.cjs | 347 | U-1 to U-15 |
| with-build | observe-listen.cjs / provider-observation.cjs / coverage-on-stop.cjs / suite.cjs | 14 / 17 / 4 / 23 | `--require` preloads (listen request capture, provider call log, SIGTERM exit) and the item registry |
| with-build | total | 2,887 | |

Execution side against expectation side.
- Blind: start, configure, drive or instrument = adapter.cjs 692 + webkit.swift 128 = 820 lines (30%). Expectations and scenarios = suite.cjs 1,905 (70%), of which 1,271 in item blocks and 634 scenario helpers. The product's labels live in two places: adapter.cjs `Page` methods (about 60 lines) and the suite's constants (suite.cjs lines 17-50, about 35 lines); the adapter is not only start-up.
- With-build: harness.cjs 520 + preloads 35 = 555 lines (19%) start, configure, drive or instrument. flows.cjs 226 (8%) is the page-object layer with labels. The seven item files plus registry = 2,106 lines (73%), of which 1,604 inside `check(`/`workspace(` blocks.

### Does anything outside the adapter start or configure the product?

Blind: no. Grep of `spawn`, `process.env`, `server.js`, `PORT`, `DATA_DIR`, `PROVIDER_TOKEN`, `STANDIN_`, `/api`, `fetch(`, `request(` in suite.cjs: PORT, DATA_DIR, PROVIDER_TOKEN and `node server.js` appear only in item description strings (lines 190, 197, 208, 410); `server.request()` (lines 195, 203, 434) is an adapter method. The suite configures through the adapter's settings object only (`{token, slow, step, defaultData, defaultPort, copy, coverage, offline}`, 31 uses). The env names sit in adapter.cjs `settingNames` (line 165) and `environment()` (167-186).
With-build: partly outside its harness. runtime.cjs line 298 spawns `npm test` itself (`h.child('npm', ['test'], {cwd: h.root, env})`); runtime.cjs 282 and 309-310, tasks.cjs 9 and 204/223/304 pass `nodeArgs: ['--require', ...]` and `env: {NODE_V8_COVERAGE, NODE_PATH: ''}` into `app.launch`; scenarios.cjs 36 and 45 pass `cwd` and `NODE_PATH`; runtime.cjs names `PROVIDER_TOKEN`/`DATA_DIR`/`PORT` in item titles only.

### Product-facing names, blind suite

"plan" = ratchet/plan.md, "spec" = ratchet/spec.md, "neither" = an assumption or run-time discovery.

| name | where used | in |
|---|---|---|
| `node server.js`, cwd = a copy of the checkout root | adapter.cjs 14, 243 | spec (U-1, C-1) and plan |
| env `PORT`, `DATA_DIR`, `PROVIDER_TOKEN`; defaults port 3000, `./data` | adapter.cjs 165-186; suite C-3, C-5, C-19 | spec and plan |
| env `STANDIN_SLOW_MS`, `STANDIN_STEP_MS` | adapter.cjs 165, 183-184 | spec (once each) and provider/README.md (starting file); not plan |
| `GET /` as the only named route; no JSON route, field or status named anywhere (grep `/api` empty) | adapter.cjs 249 (`url`), suite C-4 | spec ("open GET /"); the rest is discovered at run time from the page's own requests |
| host `127.0.0.1` | adapter.cjs 249 (`'http://127.0.0.1:' + port + '/'`) | neither |
| response header `text/html` | suite.cjs 205 (`document.contentType`) | neither (the with-build suite asserts the same, runtime.cjs 78) |
| 46 fixed UI labels, roles and names (`Continue as <name>`, `Switch person`, `Message`, `Send`, `Bots`, `Conversations`, `Conversation`, `New bot`, `Rename bot`, `Bot name`, `Save bot name`, `New conversation`, `Setup`, `Provider token`, `Save token`, `Saved instructions`, `Instruction name/text`, `Save instruction`, `Use/Edit/Delete <name>`, `Saved tasks`, `Task name/request`, `Save task`, `Run <name>`, `Memory`, `Edit memory`, `Memory text`, `Save memory`, `Forget`, `Proposed changes`, `Confirm changes`, `Reject changes`, `Change result`, `Tasks`, `Task: <title>`, `Task status`, `Cancel task`, `Retry task`, `Retry`, `Since you were away`, `Message from <name>`) | suite.cjs 17-50, adapter.cjs 534-687 | all in spec (names-blind.py: spec=True for each); about a third also in plan |
| statuses `Running`, `Completed`, `Failed`, `Cancelled`, `Interrupted`; step lines `Done: ...` | suite.cjs `state`, `doneLines` | spec |
| accessibility semantics: `aria-current` read as the "current" flag | adapter.cjs `measure` | plan (Nuances) |
| element-to-role mapping (`section`+name = region, `nav`, `article`, `output` = status, `li`, `summary` = button) and `title` as a name fallback for 7 roles | adapter.cjs `kind()`/`name()` 366-390 | neither (hedge; plan says only "semantic labeled regions and navs, named articles, native buttons and labeled form controls") |
| the page sends its commands with `window.fetch`, as `application/json` bodies | adapter.cjs 456 (patch), 680 (replay) | neither (listed under Assumed; plan names "same-origin JSON endpoints", `POST` commands, "fetch" only in prose about stale reads) |
| version key names in a command body: `/^(?:expected)?(?:selection)?(?:version\|revision)$/i` | adapter.cjs 680 | neither (plan: "expected selection version" as a concept, no key name) |
| article internals: speaker label, `time`, `header`, "You" are children to ignore when reading a message's text | adapter.cjs `messageText` | neither |
| `provider/standin.js` and its `respond` function (V8 coverage of a served reply) | adapter.cjs 297-308 | plan ("Import check, respond, and runStep"), spec C-22 |
| `test/`, `npm test`, `node:test`; the reporter line `ok N`/`pass N` | adapter.cjs 345-356 | `test/`, `npm test`, `node:test` in spec and plan; the reporter format regex is neither |
| a rule module is any file outside provider/, records/, acceptance/, test/ and server.js with functions run by both the app and `npm test` | adapter.cjs 309-325 | plan ("server-side modules", "rule code imported by the app"); no file name |
| provider reply texts (`You said: ...`, `I can see N order record(s).`, `I remember: ...`) | suite.cjs 34-47 | provider/README.md and spec (starting file / spec) |
| wording regex families: setup guidance (line 380), pending status (584, 1663), stale/unapplied (972), applied/rejected (1126-1127), steering refusal (175, 1229), stop detail (1310, 1844), failure info (1317), summary words (1409-1411) | suite.cjs | neither (hedges; the status words above are in spec) |
| numbers: narrow 540 px, tiny text 10 px, viewport height 900, pixel slacks 1 and 2, expected article counts 4 | suite.cjs 1419, 1522, 1495-1497, 1525; adapter.cjs `size(width, height = 900)` | neither (spec/plan fix only 1440) |
| `Option+Tab` to traverse every control in WebKit | adapter.cjs 598 | n/a (host mechanic) |
| test-side only: `RATCHET_ACCEPTANCE_COVERAGE`, `NODE_V8_COVERAGE`, proxy variables, `NODE_OPTIONS` cleared | adapter.cjs | n/a |

Names in neither spec nor plan (blind): 6 discrete names or behaviours (host 127.0.0.1; `text/html`; `window.fetch` as the transport; the version-field key regex; article-internals reading; the test-reporter output format), plus the element-to-role/`title` mapping, 4 numeric constants (540, 10, 900 and the 1 and 2 pixel slacks count as one family) and 8 wording-regex families.

### Product-facing names, with-build suite (shorter)

| name | in | note |
|---|---|---|
| `server.js`, `PORT`, `DATA_DIR`, `PROVIDER_TOKEN`, `STANDIN_*`, 3000, `./data`, `GET /`, `text/html`, the UI labels, statuses, `Done:` lines, `provider/standin.js` `respond` and `runStep`, `test/`, `npm test` | spec and plan (STANDIN_* spec and starting README) | same list as blind, with the same labels (flows.cjs, workspace.cjs, ...) |
| 127.0.0.1 | neither | the build binds `server.listen(port, '127.0.0.1')` (server.js 98); blind guessed the same |
| no `/api/...` route, JSON field, DOM id, class or data attribute anywhere | | grep of acceptance/*.cjs for `querySelector`, `getElementById`, `data-`, `className`, `/api/`, `'#`: nothing except one `input[type=password]` count (workspace.cjs 56, generic). The tests find everything through Chrome's accessibility tree (`Accessibility.getFullAXTree`) by role and name |
| `window.fetch` | neither | harness.cjs 398-404 (`repeat`) replays a captured request through `fetch(` in the page, but captures through the DevTools `Fetch` and `Network` domains, so XHR would also be seen |

Names that could only have come from the built product, checked by taking every string, regex and double-quoted or template literal in acceptance/*.cjs and removing those present in spec, plan, provider files or READMEs (`names-beside.py`, `names-beside2.py`): 891 single-quoted strings, 7 distinct words found only in the build.  Of the 7, 2 are product-derived, 5 generic (`border` from the regex `\border\b`, `content-type`, `hidden`, `queryselectorall`, `sort` as test data):
1. `preparing` in the pending-status regex `/(?:reply|answer|respond|thinking|preparing|working|waiting|pending|on its way)/i` (interface.cjs 80). The built page says `botName + ' is preparing a reply…'` (public/app.js 255, read in #9/#11/#23); neither spec nor plan has the word. One entry in a list of nine alternatives.
2. The printed listening address, `/https?:\/\/(?:127\.0\.0\.1|localhost):(\d+)/` to learn an ephemeral port (harness.cjs 458-461). The build prints `Local chat is ready at http://127.0.0.1:<port>` (server.js 106) and its build-1.md Discovery says "Start with PORT=0 and open the printed address". The branch runs only when `launch({port: 0})`, which no item passes (grep for `port: 0` finds nothing): dead code.
Count: 2 product-derived names, no DOM id, class, data attribute or route.
Behaviours that look tied to the build's own behaviour though they are not names: `assert.equal(buttons.length, 2)` for the Assistant's conversation list (workspace.cjs 185, 202), `cards.length === 2` after one exchange (interface.cjs 184), the tuned step delays (`step: 535, 560, 565, 665, 700, 780, 880` in tasks.cjs, runtime.cjs) and the 70 to 75 ms network-quiet wait before any input (harness.cjs `readyForInput`). I did not test these against another build.

So the hypothesis "a test written beside the build ties itself to the build's own names" is not supported for this app: both suites use the same spec-given accessible labels, the with-build suite has 2 weak product-derived entries, and the one place the blind suite had to guess a name (`window.fetch`, the version key, article internals) the with-build suite avoids by reading the page through the browser's own protocol instead. The ties show up elsewhere: the with-build suite hooks the provider (`provider-observation.cjs` patches `standin.respond` and `standin.runStep`, taken from the plan's "Import check, respond, and runStep directly from the stand-in") and the listen call (`observe-listen.cjs`), which a blind suite could not assume to work.

## Part 3: tolerance and thresholds

Reading rule. A row is a place where the blind suite accepts more than one answer or shape, or fixes a number the spec leaves open, with the with-build suite at the same point. Classes: equal; blind looser (blind accepts more or tests less); blind stricter (blind accepts less or tests more); mixed (neither is a superset). Wording lists are "mixed" unless the alternatives are the same. Line numbers are of the files as left in the work folders.

| # | blind: file, test, line | blind accepts or fixes | with-build at the same point (quote) | class |
|---|---|---|---|---|
| 1 | suite.cjs C-95, C-96 (`narrowWidth`, 1419; `page.size(narrowWidth)`, 1486, 1503) | narrow = 540 CSS px (height 900) | interface.cjs C-95, C-96, 180 and 195: `await page.resize(640, 850);` | blind stricter (narrower window; plan says "Avoid a particular narrow breakpoint") |
| 2 | suite.cjs C-97, 1522 | tiny text floor: `row.fontSize >= 10 && row.box.height > row.fontSize` | interface.cjs C-97, 232: `(!parseFloat(style.fontSize) \|\| !parseFloat(style.opacity)) return false` (only non-zero) | blind stricter |
| 3 | suite.cjs C-95, 1495-1497 | page overflow `scrollWidth <= width + 2`; message `left >= -2 && right <= width + 2` | interface.cjs C-95, 188: `bounds.left >= -1 && bounds.right <= bounds.viewportWidth + 1`; 189: `scrollWidth <= this.clientWidth + 2` | blind looser (by 1 px) |
| 4 | suite.cjs C-97, 1525 and C-98, 1536-1537 | turns may overlap by 1 px; composer must not overlap the last turn beyond 1 px | interface.cjs C-97 217 `bounds.top >= previousBottom - 1`; C-98 248 `box.top >= conversation.bottom - 12` | blind stricter (1 px against 12 px at C-98) |
| 5 | suite.cjs C-98, 1538-1539 | Send grouped if vertical gap `<= max(editor height, send height)` (same row at any distance passes) | interface.cjs C-98, 251: `(sharedRow && near < box.width / 2) \|\| Math.abs(send.top - box.bottom) <= box.height` | mixed |
| 6 | suite.cjs C-36, 584; U-5 (C-41 band) 1663 | pending status text matches `/reply\|respond\|thinking\|wait\|working\|writing\|generat\|answer/i` | interface.cjs C-36, 80: `/(?:reply\|answer\|respond\|thinking\|preparing\|working\|waiting\|pending\|on its way)/i` | mixed |
| 7 | suite.cjs C-15, 380 | setup explains: any of provider, credential, token, key within 100 characters of chat, reply, enable, connect, enter, paste, need, required, setup, local (either order) | runtime.cjs C-15, 177-178: `/\b(token\|credential)\b/i` and `/\b(repl(?:y\|ies)\|chat\|enable\|connect\|start)\b/i` | mixed |
| 8 | suite.cjs C-69, 972 (`unresolved`) | stale change explained by `stale\|changed\|unapplied\|could not\|not appl\|no longer\|again\|conflict\|unavailable` in the result region (or chat) | records.cjs 6 `noEffect`: `rejected\|declined\|cancelled\|unchanged\|unapplied\|stale\|not applied\|did not\|no changes\|could not\|cannot\|couldn't\|expired\|review again\|out of date\|...`, plus `/reviewed[^\n]*waiting/` | mixed |
| 9 | suite.cjs C-77 (1128-1145), 1769-1788; 1126-1127 (`appliedText`, `rejectedText`) | applied: `applied\|confirmed\|saved\|created\|updated\|changed\|closed\|succeeded\|success`; rejected: `rejected\|cancelled\|canceled\|declined\|no (record )?chang\|not appl\|unchanged` | records.cjs 7 `applied`: `applied\|updated\|created\|committed\|confirmed\|succeeded\|saved\|changed`; 6 `noEffect` | mixed |
| 10 | suite.cjs C-84, `refusedSteer` 173-176 and 1229 | steering "not added" in prose, about 10 phrasings | tasks.cjs 8 `notAdded`: `not added\|no (eligible\|active\|running )?(task\|work)\|could not add\|couldn't add\|cannot add\|can't add\|wasn't added\|did not add\|not running\|nothing to add\|no longer running\|already (completed\|finished\|ended)` | mixed |
| 11 | suite.cjs C-83, 1213-1220 | one task only; says nothing about two live tasks (the Open point) | tasks.cjs C-83, 119-135: with two running tasks `appended.length` may be 1 (once, at the end) "else `assert.match(selectionFeedback, /which\|choose\|select\|specify\|multiple\|several\|more than one/i)`" | blind looser (omits the open case) |
| 12 | suite.cjs C-86, 1295-1306 (`stopPartway`, `raceLastStep`) | cancellation seen through the page only: `assert.ok(after.length <= before.length + 1, 'Only a step already in flight might report a result')` | tasks.cjs C-86, 190-198: reads a provider call log through `--require provider-observation.cjs`: `assert.ok(atCancellation.length > 0 && atCancellation.length < 8 ...); await h.pause(850); assert.deepEqual(await taskRuns(service, title), atCancellation)` (no step starts after cancellation) | blind looser (cannot see a step that starts but is not shown) |
| 13 | suite.cjs C-87, 1306-1311 | cancel detail `/skip\|stopp\|remaining\|prevent\|did not (run\|start)\|not start\|did(n't\| not) finish\|in.flight/i`; earlier steps kept | tasks.cjs C-87, 218-221: `assert.match(detail, stopped)`, `assert.match(detail, /\b(?:step\|work\|progress\|remaining\|finished\|result)\b/i)`, and when a step was in flight `assert.match(detail, /\b(?:in.flight\|started\|in.progress\|unknown\|discarded\|unrecorded\|step\s+\d+)\b/i)` | blind looser |
| 14 | suite.cjs C-3, 199 + adapter.cjs 232-239 | default port observed by really binding 3000; if 3000 stays busy for 8 s the check falls back to an OS port and passes (`t.diagnostic('Port 3000 stayed occupied ...')`) | runtime.cjs C-3, 71: `assert.match(running.output, /Acceptance TCP listen request: 3000\b/)` (a `--require` hook on `net.Server.listen`, never binds 3000) | mixed (blind stricter when 3000 is free, vacuous when busy) |
| 15 | suite.cjs C-19 (410-413), U-3 | valid `PROVIDER_TOKEN` on a fresh folder only; no invalid-override case | scenarios.cjs U-3, 87-91: `const withBadOverride = await app.restart({ credential: 'invalid-environment-value' }).catch(() => null);` accepts a refusal to start or a start, asserts only that the saved token is not in the HTML | blind looser (omits) |
| 16 | suite.cjs C-29, 512-529 | any number of conversation buttons for a bot; opens each by clicking and reading the transcript (`openDiscussion`, 82-98, handles duplicate names by index) | workspace.cjs C-29, 185, 202: `assert.equal(buttons.length, 2);` | blind looser |
| 17 | suite.cjs C-49, 741 | after Delete, `Use`, `Edit` and `Delete` for that name are all absent and another entry stays | workspace.cjs C-49, 318-323: only `f.disappear(page, 'button', 'Use Temporary voice', box)` | blind stricter |
| 18 | adapter.cjs 492 (`click(query, index) { matches(query)[index]?.click(); }`), every `page.click` without `{keyboard: true}`; `fill` sets the value and dispatches `input`/`change` | a synthetic DOM `click()` works on a covered or off-screen control | harness.cjs 273-283 `clickNode`: scrolls to the node, then `Input.dispatchMouseEvent` mousePressed/mouseReleased at its centre; `fill` uses `DOM.focus`, select-all, `Input.insertText` | blind looser (not tested: pointer reachability) |
| 19 | adapter.cjs 366-400 (`name()`, `kind()`) | its own accessible-name and role computation: `aria-labelledby`, `aria-label`, `<label>`, input value, `alt`, `title` for 7 roles, else text; `section`+name = region | harness.cjs `find`: Chrome's own accessibility tree | mixed (can differ either way; I did not run either) |
| 20 | adapter.cjs 456-482, used by `capture`, `arm`, `replay`, `traffic`, `watch`; about 20 items depend on it (C-12, C-65 to C-77, U-9 to U-11, ...; counted by regex, not exact) | the page's commands must go through `window.fetch` for the capture to see them (else "The public HTTP command was issued" fails) | harness.cjs `Fetch.requestPaused`, `Network.requestWillBeSent` (types Fetch and XHR) | blind stricter |
| 21 | adapter.cjs 680 (`replay(command, currentCommand)`) | replays a captured command from another session after swapping any version or revision key to the current one, so the replay is rejected for ownership, not for version | harness.cjs `repeat` (398-404): replays verbatim with only the content-type header; records.cjs C-70 `other.repeat(stolen)` | blind stricter (a verbatim replay could be refused for a stale version and still pass) |
| 22 | suite.cjs 601-621 (`recoverReply`, used by C-39 at 622) | after SIGKILL restart: a reply already there, an enabled Retry, or status text `/resum\|retry\|reply\|thinking\|working\|recover/i` | interface.cjs 105-128: Retry, a reply, or status/alert text `/interrupted\|pending\|reply\|respond\|answer\|retry\|recover/i`; one Maya turn and one reply at the end | mixed |
| 23 | suite.cjs `interruptTask` 1330-1340, C-89, C-90, C-91 | status after restart in `['Interrupted','Running','Completed']`; Retry only if Interrupted | tasks.cjs 239-257 `f.phase(page, title, ['Interrupted', 'Running', 'Completed'])`, `if (status === 'Interrupted') ...` | equal |
| 24 | suite.cjs `summarySeveralPeople` 1409-1411 (C-93) | summary words `complete\|finished\|done`, `running\|in progress\|ongoing`, `fail\|interrupt\|attention\|retry` | tasks.cjs 8 `attention` `/\b(fail(ed\|ure)?\|interrupted\|needs? attention\|try again\|retry)\b/i`; 335-343 `/\b(?:complete(?:d)?\|finished\|done)\b/`, `/\b(?:running\|in progress\|active\|working)\b/` | mixed |
| 25 | suite.cjs C-65, 921-930 | ID promised in the creation preview is optional: `if (promised) {...}` | records.cjs C-65, 83-95: `if (promised) {...}` | equal |
| 26 | suite.cjs C-48, 726-734 (Use again after edit); C-45, C-50 (library reload only) | the edit takes effect after another `Use` | workspace.cjs C-48, 309-316: `await page.click('Use Stable name', library)` before the reply is checked | equal |
| 27 | suite.cjs C-99 / keyboardWorkflow 1545 | focus visible if `focusVisible \|\| outline > 0 \|\| boxShadow !== 'none'` | interface.cjs C-99: `(outlineStyle !== 'none' && outlineWidth > 0) \|\| boxShadow !== 'none' \|\| this.matches(':focus-visible')` | equal |
| 28 | suite.cjs C-100, adapter.cjs 309-325; C-4 205 | at least one common function range app and `npm test`; `text/html` | runtime.cjs 292-318 same V8 coverage rule; 78 `/text\/html/i` | equal |

Count: 28 places. Equal 5 (23, 25, 26, 27, 28). Blind looser 7 (3, 11, 12, 13, 15, 16, 18). Blind stricter 6 (1, 2, 4, 17, 20, 21). Mixed 10 (5, 6, 7, 8, 9, 10, 14, 19, 22, 24).

Reading across rows. At the Open points of the specification the two suites are nearly the same (rows 15, 22 to 26): both treat the answer as free. The blind suite is looser mostly by omission (it never exercises the two-task steering case, the bad environment override or the conversation count) and by running synthetic clicks; it is stricter in four invented numbers (540 px, 10 px, a 1 px overlap and a vertical-gap rule) and in two assumptions about the page (commands via `window.fetch`, ownership replay by version-key swap).

Five most consequential differences, in order
1. C-86 (suite.cjs 1295-1306 against tasks.cjs 183-199, row 12): the with-build suite sees every provider call through a `--require` hook that patches `standin.runStep` and asserts no new step starts after cancellation; the blind suite can only see which "Done:" lines the page shows, so a build that starts a step after cancel and never shows it passes blind.
2. Window width and text size (rows 1, 2; suite.cjs 1419, 1522 against interface.cjs 180, 232): the blind suite fixes 540 px and 10 px as acceptance numbers although the plan says to avoid a particular narrow breakpoint; the with-build suite uses 640 px and only requires a non-zero font size. A build that folds panels at 560 px, or sets a 9 px timestamp inside an article, fails blind and passes with-build.
3. Command transport (row 20; adapter.cjs 456 against harness.cjs Fetch/Network domains): every `decision()`, `capture()` and `replay()` in the blind suite needs the page to use `fetch`. About 20 items (C-12, C-65 to C-77, U-9 to U-11) would fail for an environment reason if the build sent commands with XHR or a form post. With-build is transport-neutral.
4. Pointer realism (row 18; adapter.cjs 492 against harness.cjs 273-283): blind clicks call `element.click()`, so a control covered by another panel, clipped or off-screen still works; with-build uses a real mouse event at the node's centre. This affects every item that clicks, and U-15/C-96/C-98 most.
5. C-3 default port (row 14; adapter.cjs 232-239 and suite.cjs 199 against runtime.cjs 71): blind starts the product without PORT and expects it to answer on 3000, and if 3000 is busy it quietly runs the check on an OS port instead (the item still passes); with-build captures the `listen` argument and asserts it is 3000 without binding 3000.

## Part 4: the sessions' own reports

### Blind: ratchet/tests-1.md

`## On the starting project`
```
- No existing clauses failed.
- No other clauses passed.
- All 115 commands printed their item ID. The 23 existing clauses and two existing use cases passed the portions observable through the shipped provider and fixtures. The 90 remaining items failed. C-100 ran the baseline's `npm test` and observed zero tests. The other 89 could not observe their requested application behavior because the baseline has no chat service.
- For existing clauses with application obligations, such as C-7, C-70 and C-76, the passing baseline check covers only the shipped fixture or provider contract. The corresponding HTTP and browser tests run when the service is delivered.
```
Check: matches the run (#22 and #35: 25 passed, 90 expected failures, 0 mismatches). Nothing here is about the product; every one of the 89 failures says "no chat service", not anything about its clause.

`## Assumed`, each line labelled
```
- The supplied computer's macOS WebKit and `swiftc` are available for real-browser checks. The local Node executable was v26.12.1. The baseline checks used that executable.
- A 540 CSS pixel viewport represents a narrow window for the responsive checks. The typography check uses 10 CSS pixels as a floor for visibly tiny transcript text.
- The browser's same-origin command transport uses `fetch` with JSON for addressed mutations. The adapter learns URLs, methods, and payloads from the actual UI. Where a replay needs the destination selection version, it substitutes version or revision fields recognized in the observed command.
- Closing and recreating a browser page with its session retained is the return event used for the task summary. The checks avoid specifying when activity becomes seen.
- The default-port check starts with `PORT` unset after the OS confirms port 3000 is free. If another process holds it throughout the bounded wait, the command reports the default observation as unavailable and exercises an OS-assigned port.
- The C-22 delivery check observes the supplied provider's bytes and execution during a served reply. A dormant provider copy that is neither executed nor served is outside that observation.
```
1. WebKit, swiftc, Node version: execution (host tooling of the test machine).
2. 540 px and 10 px: design gap (a number a responsive test needs; the spec leaves C-95 and C-97 `Open:` and the plan says to avoid a breakpoint, so neither supplied one).
3. `fetch` transport and the version/revision key names: design gap (the plan names `POST` commands that "carry an expected selection version" but no transport or key); how it learns URLs from the page is execution.
4. Page close and reopen as the "away" event: execution (how a test simulates leaving; C-93's `Open:` is untouched).
5. Default-port check with a bounded wait and an OS-port fallback: execution (how to observe 3000 safely).
6. C-22 observation of the served provider: execution (how to see the provider run), though it also fixes a reading of C-22's wording.

`## Discoveries` (blind)
```
- A test command must run at least one rule test to establish C-100. | Observable: Inspect the Node test report and execution of files under `test/`. | Why: The starting checkout's `npm test` exits successfully and reports zero tests.
- Provider reply text is displayed subject to the credential secrecy requirement. | Observable: Put the exact configured test credential in a prompt that normally echoes and inspect the returned pages and responses for it. | Why: The stand-in's ordinary fallback echoes input, so an unconditional exact-text comparison would contradict C-20 in that case.
- A steering acknowledgement from the provider is distinct from the outcome of appending a step. | Observable: Inspect the feedback and task progress after sending a steering request with no eligible task or with a task that finishes during the reply. | Why: The offline provider returns affirmative steering text without observing the worker's state.
```
Labels: 1 execution (how to run C-100 against an empty starting project; the spec's C-100 wording would let an empty `npm test` pass); 2 design gap (spec C-18/C-20 versus the stand-in's echo: two clauses conflict for echo-like input); 3 design gap (the plan's Nuances already say "Provider `steer` replies are affirmative even when no work can accept the addition", the spec does not say the page must show the real outcome).

### With-build: ratchet/tests-1.md (the stage asks for `## Failing now` and `## Discoveries`; no `## Assumed`, no `## On the starting project`)

```
## Failing now

none

## Discoveries

- An otherwise enabled action attempted while another save is awaiting acknowledgement should indicate whether it was accepted, deferred or blocked. | Observable: Delay the Save instruction response, then open New bot, enter a name and activate Save bot name before releasing the response. | Why: Save bot name remained enabled, but the click sent no request, showed no feedback and created no bot.
```
Check: `Failing now: none` matches #32 and #34 (all 115 PASS). The one Discovery is about the build (a control that stays enabled but does nothing while another save is pending), found by the held-response probe #33; label: design gap in the spec (no clause says what a blocked action must show), not a test assumption. The with-build report states no assumption at all, so nothing in it says which choices (640 px, the tuned step delays, `buttons.length === 2`) the session took.

## What I could not determine
- Whether the blind suite passes on the finished product: I did not run anything. Rows 1, 2, 18, 19, 20 and 21 and the claim "about 20 items depend on `window.fetch`" are readings of the code (the count is a regex over block text plus helpers, not exact). I did not check whether the built page sends commands with `fetch` (the with-build session read public/app.js for `fetch(` in #9 but I did not open it).
- Where the with-build session got `preparing` and the printed-address regex: the text is in public/app.js and server.js, which it read, and in build-1.md, but a model can guess a common word; I label them "product-derived" on that evidence only.
- Line numbers were taken with grep on the files as left in the work folders; a few quoted ranges (rows 12, 13, 22) are the start of the cited function, not exact first and last lines.
- Mixed rows (6 to 10, 24) compare regex alternatives by eye; a different count under another reading of "superset" is possible.
- Whether the 2 weak product-derived entries and the build-dependent behaviours (count of 2 buttons, tuned delays) could not equally be explained by the spec: I did not test either suite against a second build.
- The blind session's 91st failing gate entry is `check: npm test`; I did not open the gate script to see what it checks beyond the name.
