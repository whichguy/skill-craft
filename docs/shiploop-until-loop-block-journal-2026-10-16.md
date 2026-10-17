# ShipLoop Until Loop block: say "RUN this skill", with the command and the result (journal)

Living journal for the change that rewrote the Until Loop block of every inner-stage packet
(`skills/shiploop/scripts/shiploop_loops.py`, `invoke_lines`). Branch `feat/shiploop-eff-loop-6afcbc`, on
`feat/packet-essentials-first-255e57` (base 398466a3; the head change 11f5a5b9). Edit this file rather than deleting a claim;
mark a superseded claim with the date and the reason.

## Question (2026-10-16)

The owner: the packets "don't actually clearly say, explicitly, the physical layout of the /until-loop argument", they talk
in generalities and never say "RUN this skill" and give it the explicit result of what to do: "the /until-loop skill with the
explicit command vs. generalizing". What does a model that lost all context have to read, and where, to start the loop and
to finish the stage?

## Evidence that the old block was the problem

- Old block (base): `INVOKE /until-loop NOW with the argument below, verbatim`, an `Argument:` label, the argument's lines
  indented by four spaces among prose, then `How to invoke: on Claude Code, the Skill tool ...; elsewhere, the card
  <ADAPTER.md>, section "Start from a parent-written contract"`. Nothing marked where the argument began or ended; no literal
  command appeared for any host but through the card. `docs/experiments/shiploop-loop-block-20261016/block-before.txt`.
- The worker brief (from the live-run diagnosis of the Salesforce chess run, Grok): the model read ADAPTER.md (24 KB) 6 times,
  147 KB, and improve/SKILL.md 7 times, 203 KB, to learn the start command and the done report. Not re-measured here.
- The card says: start with `python3 <script> start --receipt <Receipt> < <Contract>`; the file wins over the argument text;
  an `active` receipt means run its `next_argv`, never start a second run.

## Experiments and results

1. Runtime shapes (scratch contract, `start` run twice; status firm). `start` prints an active packet with `next_argv`,
   `done_argv` (`done --state <file> --action=<token>`, the JSON report on stdin) and `report_schema` (classification,
   exit_assessment, continuation_assessment, evidence, handoff). A second `start` for the same `--receipt` is NOT refused: it
   writes a new run over the receipt. So "never start a second run" is only a rule, and a literal start command in the packet
   must not sit under a RUN line once the receipt exists. Decision: a packet read after the start leads with the resume line
   (`RESUME_LINE`) instead of the RUN line.
2. Budget (status firm). The inline step-plan head is printed as a head and the host cuts at about 20,000 characters; the
   base measured 19,503 (`PrintedHeadTests.HOST_CUT`), so 497 characters of headroom, and the loop block is the head's last
   element, so a cut removes the block. The first explicit block cost +1,063 there. Trims, each keeping its obligation: the
   report-format sentence became "run its done_argv as printed" (the packet's `report_schema` carries the fields), the start
   command uses `python3` like every other command the packet prints (it was `sys.executable`; the runtime's own
   `next_argv`/`done_argv` keep the interpreter that ran `start`), the heading dropped "; the loop script counts the
   iterations" (the Repeat line says "no iteration limit"), the head's pointer sentence lost 53 characters, and the offline
   walk now writes the loop contract as `emit` does (it printed "The loop contract is missing" in every offline packet, 72
   characters a real packet never has). Result: 19,974, headroom 26. Thin by construction: any other change to this head must
   pay for itself.
3. Sizes (`docs/experiments/shiploop-loop-block-20261016/sizes.md`). Seven stages: block 15,418 -> 19,674 characters (+28%),
   +596 to +616 each; one-step implement 2,146 -> 2,669. The command (about 450 characters, two paths that repeat the argument's
   Contract and Receipt lines) is most of it.

## Findings

- (firm) The old `Start from a parent-written contract` command lived only in the card; the new block prints it, with the
  real absolute script, receipt and contract paths. Test: the printed command equals `start_command(...)` and, run in a
  shell from another directory, makes the receipt `active` with the contract's work.
- (firm) A resumed packet must not invite a second start (Experiment 1). Test: only the first line differs between a fresh
  and a started packet.
- (firm) The E2E readers need no change beyond the classifier comment: the loop block is one `until-loop` section ending
  at the closing rule; the start command is not model glue (`metrics.glue_reasons`) and the runtime's `next` call is still
  the `improve-next` kind.
- (interim, unproven) That the new wording makes a cleared model start the loop without opening a card. The next live run
  should count reads of `ADAPTER.md` and `improve/SKILL.md` during loop start (expected 0), start-command errors, second
  starts, and guessed report fields.
- (interim) The result line's restart clause ("if that refuses for the loop, run the start command again") carries the old
  closing sentence over; refusals that concern the loop print their own start command, so the clause is a pointer, not the
  only source.

## Commits and related work

Base 398466a3 (head reads to its closing line) and 11f5a5b9 (the head leads with duties; the 20,000 test). The change's own
commit is the one that adds this file.
