# Loop block sizes, before and after (2026-10-16)

Method: `python3 test/shiploop_e2e/packets.py --offline node-fix-bug` logic (`offline_packets`, inline), run on two checkouts
whose paths have the same length: an archive of the base commit 398466a3 and the working tree after the change, both with the
offline walk writing the loop contract as `emit` does (so neither ends with "The loop contract is missing"). Characters.
"Loop block" runs from the `Until Loop (no iteration limit` heading to the closing rule. "Printed" is what `emit` prints: the
whole packet up to 16,000 characters, else the head.

| packet | loop block before | after | packet before | after | printed before | after |
|---|---|---|---|---|---|---|
| 01-step-plan | 2682 | 3278 (+596) | 25369 | 25978 (+609) | 19479 | 20022 (+543) |
| 03-test-spec | 1914 | 2530 (+616) | 14133 | 14752 (+619) | 14133 | 14752 (+619) |
| 05-validate-existing | 2091 | 2699 (+608) | 14601 | 15211 (+610) | 14601 | 15211 (+610) |
| 06-implement | 193 | 154 (-39) | 18509 | 18474 (-35) | 14821 | 14729 (-92) |
| 08-test | 2635 | 3235 (+600) | 20145 | 20751 (+606) | 14730 | 15278 (+548) |
| 09-document | 1876 | 2492 (+616) | 13354 | 13972 (+618) | 13354 | 13972 (+618) |
| 10-verify | 2174 | 2782 (+608) | 20349 | 20962 (+613) | 15309 | 15864 (+555) |
| 11-carry-forward | 2046 | 2658 (+612) | 22559 | 23181 (+622) | 15905 | 16228 (+323) |

- Seven stages print an argument: the blocks grow from 15,418 to 19,674 characters (+4,256, +28%), +596 to +616 each.
  `06-implement` has no argument in this walk (the synthetic step plan has no steps, so it prints "Unavailable: ...");
  with one step the implement block is 2,146 -> 2,669 (+523, same method on a one-step state).
- What the growth is: the literal start command, whose two paths repeat the argument's Contract and Receipt lines
  (about 450 characters), the RUN line, the two marker lines, the host line and the result line (about 650), less the
  `How to invoke ... card ...` line (about 290 with the card path), the `Argument:` label, the four-space indent of
  each argument line and the old closing sentence (about 300).
- The inline step-plan head is the limit that binds: 19,503 before at the repo's own measure (the tool then included the
  72-character "contract is missing" line), 19,974 after, under the 20,000 the host cuts at
  (`PrintedHeadTests.HOST_CUT`). Two offsets pay for it: the offline walk now writes the contract (-72, a fidelity fix: a
  real packet never has that line) and the head's pointer sentence is shorter (-53, same obligations). The heading lost
  "; the loop script counts the iterations" (-39), which the block figures above already include.
