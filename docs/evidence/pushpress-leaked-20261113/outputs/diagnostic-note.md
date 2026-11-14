# Post-hoc diagnostic (not in the frozen design)

Run after round a's stage 1 failed its gain line (C5a 12 of 12 and C4 12 of 12 on the held-out leak prompts), to explain HP11, the one prompt C4 missed in Round 12 (0 of 2). It cannot pass or fail a
frozen line and does not change round a's decision (no change). Files: `diagnostic-C4-DL1.json`, `diagnostic-C5a-DL1.json`, `diagnostic-C4-DL2-4.json` (18 runs, 0.594 USD); the C5a runs of DL2 to DL4
and the first two of DL1 are the dev stage's (`dev/dev-C5a-pos.json`), and C4's first two runs of HP11 are Round 12's (`../../pushpress-description-20261113/outputs/heldout-C4-pos.json`).

| prompt | what it is | C4 fired | C5a fired |
|---|---|---|---|
| DL1 (= HP11) | key pushed to a public repository; "rotate it first, or clean up the history first?" | 2 of 8 (Round 12 0 of 2; here 2 of 6) | 8 of 8 (dev 2 of 2; here 6 of 6) |
| DL2 | screenshot of the API-keys page posted in a Slack channel | 2 of 2 | 2 of 2 (dev) |
| DL3 | webhook signing secret committed to a public repository | 2 of 2 | 2 of 2 (dev) |
| DL4 | key visible in deploy logs that contractors can read; "is that bad?" | 0 of 2 | 2 of 2 (dev) |

Reading: the difference sits on two short prompts in which PushPress is only the name of the key (DL1, DL4), and DL1 was chosen because C4 had missed it. DL2 and DL3 loaded in both arms. The first author
agent's prompts carried the gym's own context and loaded in both arms, which is why round a's set could not separate them. This is a hypothesis, not a result: it comes from four prompts, two of them written
by me before I saw any of these runs and one of them the observed miss; round b (`../round-b/`) tests it on new prompts.
