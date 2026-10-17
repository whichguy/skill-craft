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

## PK2: a new file's spec diff prints as a pointer (status: firm on the fixture; live effect unmeasured)

Question: how much of the hand-off block repeats a file the same packet quotes whole, and can the repeat go without losing
an obligation? Live run: the plan packet's diff block was 22.1 KB, 20.7 KB of it the spec it had quoted above; test-strategy
16.5 KB likewise; test-spec and implement printed 11.4 KB of followed R-<n>/AD-<n> entries that are inside the quoted files.

Change: `navigator._spec_diff_lines` splits the diff at its `diff --git` lines; a chunk that adds a whole new file
(`new file mode`, one `@@ -0,0 +1,N @@` hunk of `+` lines, N lines exactly) whose text equals the file quoted in the same
packet's reads block becomes `HOME/<file>: new since the baseline ... (<bytes> bytes; sections: ...)`. Sections are level 1
and 2 headings outside code fences, at most 12. `_followed_lines` lists a followed ID when its entry text is a substring of the
quoted file. The "uncut diff" heading became "nothing cut that is not printed in this packet". Any mismatch keeps the text:
a modified file, an untracked file (no diff), a BOM (the quote drops it, the diff keeps it), a stage that does not quote the
file (`document` quotes architecture only: spec.md's diff stays; `carry-forward` quotes nothing: both stay).

Measured (`pk2-handoff-block-sizes.txt`, long-knowledge fixture, characters of the block): plan 54,450 -> 28,734; test-strategy
48,287 -> 26,044; test-spec 37,840 -> 28,532; implement 16,011 -> 15,297; document 42,053 -> 37,898; verify 42,157 -> 38,002;
product-acceptance 51,105 -> 28,862; carry-forward 26,332 -> 26,364 (+32, the longer heading); ten stages 362,660 -> 273,444
(-89,216, -24.6%). The offline packets have no knowledge files, so their bytes are unchanged (0 of 603,485).

Obligation check (`check_handoff_dedupe.py`, `pk2-obligation-check.txt`): every line the change removed is either diff
scaffolding or a `+` line of a file the packet quotes whole with its text in that quote, or a line of a followed entry that
is in a quoted file; no unexplained line in any of the ten stages.

Not done: nothing listed in the brief was skipped. The ID list for followed entries was done because it can be exact (substring
of the quoted file's text, which is where the entry was cut from).
