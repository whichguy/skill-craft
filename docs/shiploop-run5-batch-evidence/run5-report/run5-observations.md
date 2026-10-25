# Run 5 live observations (for analysis.md)

- 18:03 (33 min): spec accepted after a 7-pass Improve review (about 16 min). Passes 1-6 were non-trivial, and each
  closed an oracle gap a weaker engine could pass:
  1. themes replaced by replayable FENs and move lists;
  2. the start moves and the first result FENs, plus black castling;
  3. queenside castling, where the rook must move;
  4. a black rook leaving home and its castling right;
  5. capturing a white rook on its home square;
  6. promotion to R/B/N, black promotion, black en passant.

  Pass 7 was trivial. This is F4's stand-in text rule working at spec time without the dropped field. Compare it with
  run 4's spec review (passes, minutes) and with test strength (mutation, dodges).
  Evidence: worktree/.shiploop-improve/spec-1d6d2aa8/reviews/review-1..7.md.
- Grok host sessions restarted twice in-run by 30 min (resume-1.txt, resume-2.txt).
- 18:05 (36 min): spec `primary` = R-1..R-7, every requirement. That is the strictest setting for F6: every unverified
  outcome at product-acceptance needs a passed lower-layer test, else add-work. Watch for add-work loops (the
  overcomplication review's F6 risk), and judge whether the template nudges "all primary".
- 18:10 (40 min): test-strategy (before its Improve review) recorded:
  - test_layers: SLChessEngine and SLChessController unit tests via `sf apex run test`, available; slChessBoard at the
    component layer, harness "browser session", status prerequisite. The reason says no browser tool and `sf org open`
    is denied.
  - targets: org de, keeps_state yes, with a base_state_route.

  F1 closed run 4's "UI unverified" exit (component is prerequisite, not unverified). F3 recorded the stateful org.
  Watch prepare: a browser named as the *component* harness, on a host with no browser. Does prepare switch to a local
  component runner, or block? If it blocks, consider a generic fix: a component layer's harness is a local test
  runner, not a browser.
- 18:17 (47 min): test-strategy accepted after review with the board still "component · browser session ·
  prerequisite". The plan has 3 items: W1 project + engine, W2 controller + grader games, W3 board + entry metadata.
  Candidate generic fix (after the run, if prepare stumbles): the test-strategy text and the F1 shape should say that a
  component layer's harness renders the component in isolation with a local test runner, while a browser on the deployed
  app is the e2e layer. Today nothing stops a browser being recorded as the component harness.
- 18:27 (58 min): the Grok host's in-run restarts come in pairs a minute apart: resume-1 and resume-2 at 17:34,
  resume-3 and resume-4 at 18:25-18:26. The first resume session likely ends at once. After the run, check
  sessions.jsonl durations: is it a harness resume issue (an empty first resume) or Grok's turn-end behaviour? Count the
  re-orientation cost of each.
- 18:30 (60 min): **prepare dodged F1's harness_runs gate.**
  - The prerequisite row slChessBoard [component] got a "harness run": headless Chrome rendering a local probe HTML
    (`run/scratch/prepare-browser-probe.txt`), whose text says "This is not /lightning/n/SLChess_Board and not the
    slChessBoard component."
  - Prepare's summary sets the default "continue Apex work and leave the on-screen board unobserved".
  - The gate checks only that the evidence file exists.
  - Generic lesson (candidate, next batch): harness_runs evidence must show a test of the row's code ran (a test-result
    line, a count), not any program output; and a component layer's harness renders the component in isolation (a
    local runner), while a browser on the deployed app is the e2e layer.
  - Add a known-dodge row: a harness run whose evidence runs no test.
  - Downstream test of F6: R-5 (board) is primary, so an unobserved board needs a passed lower-layer test at
    product-acceptance, else add-work. Watch whether F6 catches it.
- 18:36 (67 min): W1 step-plan passed every gate with 0 refusals.
  - F3: both focused `sf apex run test --target-org de` commands name the org target.
  - F1: C2-C5 executed (Apex tests), C1 and C6 searched (sfdx-project API version, a contract string).
  - F2: no guards.
  - One step, S1, covers C1-C6; its proof is a grep, which counts as context.
  - Expect: RED unobserved at verify, and the mutation check skipped with "every focused command tests a deployed target
    or one that keeps state".
- 19:02 (93 min): run.py crashed after the Grok session ended its turn normally (the result event at 19:02:38).
  - The error was ModuleNotFoundError `_strptime`, in metrics.py acceptance_stamps: Homebrew replaced Python 3.14 with
    3.15.1 under the running process, and the lazily imported stdlib module was gone. No double host: only ShipLoop's
    progress observer (pid 20567) was left.
  - The coordinator resumed in place with --resume-run (its resume 1), on python 3.15.1. W1 implement was accepted
    before the crash.
  - Harness lesson (generic, small): run.py should import its lazily loaded stdlib modules (time.strptime/_strptime) at
    startup, or record the interpreter version and refuse to continue on a mid-run change. Count the lost minutes in
    the report.
- **Run 5a ended BLOCKED at 93 min**, at W1 implement (accepted as blocked; work items 0 of 3). Grok **1.0.70**'s auto
  mode refused the deploy twice: "Salesforce deploy to unresolved org alias `de` is a remote stateful mutation; block
  until the target is confirmed safe". The command was `cd <wt> && grep … && sf project deploy start --target-org de`.
  Run 4, on Grok 1.0.62, ran the same command shape 15+ times under auto mode with the same host_allow. The sf guard
  logged 61 calls, none of them a deploy (all allowed except `org open`). Nothing reached the org, and the preflight
  stays clean. ShipLoop correctly reported blocked (`present`, awaiting a person) rather than faking a deploy. Cost:
  about $25.5, 350 turns, 5 Grok sessions; Improve 37.3 min across 5 reviews; planning closed at 78.5 min.
- **Owner decision (19:10): rerun with the looser permission mode** (`--permission-mode bypassPermissions`). The sf
  guard keeps the org scope.
## Run 5b (`/Users/dadleet/e2e-runs/20261024/chess-sf-full-12a23d`, bypassPermissions)
- 19:32 (24 min): spec accepted after a 3-pass review (5a took 7). The review added more replayable oracles: the full
  promotion list, clock defaults, perft positions such as Kiwipete, and result FENs for rook captures and pawn moves.
  14 requirements; `primary` = 13 of 14 (all but R-13).
- **Pattern across 5a and 5b: almost every requirement is marked primary**, so the field does not discriminate. This
  makes F6 maximally strict. Candidate (judge it by product-acceptance's cost in 5b): the spec duty or placeholder could
  say primary outcomes are what the user asked for directly, usually a few, while the rest support them. Fix only if
  5b shows an add-work loop or needless cost.
- 19:41 (33 min): 5b test-strategy (before review), as F1 and F3 intend:
  - the board's component layer uses `sfdx-lwc-jest` (a local runner), prerequisite, and prepare adds a render test;
  - the board's e2e layer is unverified (no browser);
  - targets: org de keeps state yes, with a base route; the local worktree keeps state no.

  5a's "browser as component harness" did not recur (variance between samples). The component-layer wording fix drops
  in priority; the harness_runs evidence fix (5a's probe page) stays high.
- 19:59 (51 min): 5b prepare accepted. **F1 worked as intended.** It installed `@salesforce/sfdx-lwc-jest`, wrote a stub
  slChessBoard, and ran `npm run test:unit`: "slChessBoard ✓ draws eight ranks and a status word" (1 passed, EXIT 0),
  saved in `run/scratch/prepare-jest-run.txt`. The plan has 3 items. Planning took 51 min, against 5a's 60. This is the
  same gate that accepted 5a's browser probe page, so the evidence fix (a test-result line must show a test of the
  row's code ran) stays top priority.
- 20:02 (54 min): 5b's first refusal, at W1 step-plan: "the criteria step S1 names are 5,192 characters together;
  the limit is 1,200" (the producer limit). W1's plan again had one step for every criterion, as 5a's did. Watch
  whether the exit taken is a split or a shortening; the gate works as designed.
- 20:11 (63 min): after the refusal, W1 was split into 6 steps (S1-S6, 4-5 criteria each); 5a's W1 had one step.
  - F1: 25 criteria executed, 1 searched (Cdoc, the docstring duty).
  - F3: the focused Apex commands name `org de`; the jest regression runs locally.
  - The producer limit drove behaviour-level steps (the owner's step-series rule) without a new gate.
- 20:52 (104 min): the first deploy succeeded (the guard logged `project deploy start --target-org de` and `--metadata
  ApexClass:SLChessEngine`, both allowed), so bypassPermissions removed 5a's blocker. A new refusal came from the spec
  write-back gate (S3.3): "Restore …/docs/shiploop/spec.md to what HEAD holds plus this step's acceptance lines…". It
  works as designed.
- **Retired-term leak:** that refusal still says "run the same complete command again". R4 retired the phrase, but
  `shiploop_knowledge_home.py:629` splits it across two concatenated string literals ("…the same complete " +
  "command again…"), so the line-based retired-terms scan misses it. Next batch: fix the string, and make
  `test/shiploop-retired-terms.test.py` join adjacent string literals (or scan rendered refusal text). Check that the
  run's metrics `nomenclature` record (S-16) caught it from the printed text.
- 21:05 (117 min): W1 S1-S4 accepted, one commit each, with behaviour headlines:
  - S1: start position returns 20 legal moves; illegal moves throw;
  - S2: en passant captures, and a blocked pawn cannot push;
  - S3: sliders, king moves, and promotion; both mates are checkmate;
  - S4: both sides castle; check with a flight, and stalemate.

  S5 sent back: "C28's promotion line needs an illegal straight pawn capture". The criterion as written could not be
  met, so the step used the send-back route (build plan S3.3) instead of editing the spec. Count the send-backs and the
  rework minutes in the report.
- 21:12 (123 min): W1's revised step-plan was accepted after the send-back. New refusal from the expectations gate:
  "expectation E3 is works, but …/SLChessEngine.cls does not exist on the item's lint base. A new path needs an absent
  expectation."
  - After a mid-item send-back, S1-S4 are committed, so the file exists in HEAD. The gate judges expectations against
    the item's lint base (before W1), so the model must declare a file that exists "absent". It resolved this.
  - Candidate generic fix (check the evidence first): when a step-plan is revised after some of the item's steps were
    committed, judge expectations against the latest step commit, or say in the refusal that "the item's base is before
    its committed steps".
  - So far 5b has 3 distinct refusals: the producer limit, the spec write-back, and this expectation base.
- 21:42 (153 min): W1 test and document accepted. Base run (`tests/nav-5265…-base1.md`): both focused Apex commands
  were left out as remote, with F3's reason ("runs on org de, which keeps state between runs (test-strategy targets;
  base state: …)"); the `npm run test:unit` regression was counted. Mutation check skipped by the Salesforce card's
  all-remote reason (focused commands only), passed, nothing refused. Run 4's W2 failure mode (a remote test run on a
  base that already held the change) is closed. Cost: W1's Apex REDs are unobserved; verify should print the "RED
  unobserved" block, so check its packet. The mutation coverage of W1's Apex code is 0 (structural); surface it in the
  report.
- 21:49 (160 min): W1 complete (27 stages); verify printed "RED unobserved" for both Apex commands (I2 works).
- 22:06 (178 min): W2 implement sent back: "C6 cannot be caught from anonymous Apex". This is the second send-back, and
  both were criteria a step found it could not meet as planned. Ask in the report: should step-plan's criteria check
  (or the Improve review of the step plan) catch "unconfirmable by the planned command" before implement? Count the
  rework minutes.
- 22:29 (201 min): W2 complete (38 stages) after 1 send-back; W2 took about 41 min. W3, the board, began.
- 22:36 (208 min): W3 step-plan accepted after three new refusals, each fixed in stage:
  - the producer limits: S1's task was 1,676 characters (limit 700), and S1's criteria 1,303 (limit 1,200);
  - the expectation-to-assumption link: "expectations cite from A12, A4, which is not an open plan assumption whose
    consumer is W3 (those are A8)".
- **Second retired-term leak:** that refusal still says "consumer", which R3 renamed to `due_item`. The source is
  shiploop_expectations.py's open-assumption link refusal. The retired-terms pattern only catches "as `consumer`".
  Next batch: fix the text, and widen the pattern to "whose consumer is" and "consumer W<n>".
  - Combined with the `knowledge_home` "same complete command" split literal, the conclusion is that the line-based
    retired-terms scan needs a rendered-text check: render each gate's refusal and scan that.
- 09:08 Oct 25 (≈252 active min): **F5 worked on first contact.** The end-of-work Improve review committed two real
  board fixes, each with a `Regression test:` line, and nothing was refused:
  - `6ac037a`: "send a legal promotion when queen is not legal", `Regression test: TC_B4_promotionQueen (b)`;
  - `b039c2a`: "ignore a load reply that arrives after New game" (a load generation, since a matching FEN is no
    proof), `Regression test: TC_B6_newGame (b)`.
  - Minor weakness: the gate requires every whitespace token to appear in a commit test file, and "(b)" matches almost
    any file. Consider checking only ID-like tokens.
- 09:25 Oct 25 (≈269 active min): **F6 worked on first contact.** product-acceptance was accepted with no refusal and
  no add-work. Unverified rows:
  - R-10 (play on the board, primary): `lower_layer_check: TC_B1_startBoard`, a passed jest component test;
  - R-9 (an illegal move shows an error, primary): `TC_19_controllerMates`, an Apex test;
  - R-15 (tab and class visibility, not primary): a reason.
  Run 4's failure (the main human outcome accepted on words) is closed. The new refusal before it came from the
  system-test gate: "2 of the 8 listed commands did not pass". It was fixed in stage.
