# ShipLoop efficiency, tranche 1, worker PK: journal

Branch `feat/shiploop-eff-packets-6afcbc` (base `feat/packet-essentials-first-255e57`, 398466a3). Unreleased, unpushed.
Scope: PK1 owner rule and master-index pointer under every packet's first line; PK2 a new-file spec diff prints as a pointer;
PK3 prose paths print as symbols. Evidence behind all three: the packet compaction study (changes A, D) and the live
Salesforce chess run (65.5% of packet bytes were lines already sent in an earlier packet; absolute paths were 14% of packet
bytes and 22% of the model's output tokens; the model never opened the run's context-index.md, 0 reads across five
compactions, although every packet named it mid-packet).

Method for every step: render the 48 offline packets of the `node-fix-bug` step case before and after (inline and ask-agent,
the whole render and the printed head) with `docs/experiments/shiploop-eff-packets-20261016/dump_packets.py`, list every
removed or changed line with `packet_diff.py`, and measure real characters with `packet_sizes.py`. Each removed line must be
a same-packet duplicate or a symbol substitution; anything else is a defect.

## PK1: owner rule and master-index pointer (status: firm, unit-tested; live effect unmeasured)

Question: will a model that lost its context open the run's index if the pointer is the packet's second line instead of a
mid-packet sentence? Unanswered until a live run; the unit tests pin the placement, not the behaviour.

Change: `shiploop_prompts.OWNER_RULE` and `index_pointer(path)` (one definition each) print directly under the header line
of every producer packet (whole render and printed head) and of the Improve packet; the old mid-packet "Run context
index" line is gone and the pass-log rule keeps its own line. `context-index.md` opens with a map of about 3 KB (current
stage and packet file, next and recovery commands, one row per run file or folder, the three knowledge files, the skill's
guides); the run's record follows. `emit` writes the index when a run lacks it, so the pointer always names a file.

Measured (`pk1-diff-and-sizes.txt`): producer packets +171 characters (two lines +344, the old line -173), Improve packets
+344, across the 48 packets +12,643 of 590,842 (+2.1%). Removed lines: only the old mid-packet index line (21 packets),
replaced by the pointer and the pass-log line. One side effect: the printed head of `carry-forward` (inline) crossed the
16,000-character print limit by the added 344 characters, so the existing fallback moved its quoted hand-offs to the full
packet (that fixture's hand-off is "none open"); borderline heads do this.

Pins moved with the lines (deliberately): the callback is now the third line after the header, not the first
(rehydration, delegation, improve-schedule, navigator-contract, planning-handoff); the packet-anatomy classifier knows both
lines and the split pass-log line. Improve ceiling (3,000) and producer ceiling (33,000) were not exceeded: no bound raised.
