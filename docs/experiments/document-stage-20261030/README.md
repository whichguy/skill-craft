# Document-stage review evidence (2026-10-30)

Journal: [../../shiploop-document-stage-journal.md](../../shiploop-document-stage-journal.md). Proposal:
[../../shiploop-document-stage-proposal-2026-10-30.md](../../shiploop-document-stage-proposal-2026-10-30.md).

| Path | What it holds |
|---|---|
| `harness/build.py` | builds the three post-implement scenarios from `test/shiploop_e2e/fixtures/node-base` |
| `harness/render.py` | makes one arm: copies a scenario and writes its packet (A from the skill's source, B from `variant_b.json`) |
| `harness/grade.py` | deterministic checks per arm |
| `harness/judge_pack.py` | blind X/Y judge inputs and the key |
| `harness/stale_mentions.py`, `harness/stale_history.py` | the drift hint and its precision run over a repository's history |
| `packets/` | the S1 packet for each arm, arm paths replaced by `<arm>` |
| `arms/<scenario>-<arm>-r1/` | each arm's diff against the base, result and notes |
| `grades-r1.json`, `judge/`, `judge-key-r1.json` | grades, judge inputs, verdicts and the X/Y key |
| `research/` | the external research survey and the live-run audit (with the correction in the journal, L7) |
| `pilot-scope-defect.md` | the L3 excerpt from the 2026-10-29 pilot run |

Rerun (no model for the first three lines; subjects and judge as in the journal):

```sh
python3 -I harness/build.py <out>
python3 -I harness/render.py <out> <arms> s1-basket A 1     # and B, and s2-rename, s3-health
python3 -I harness/stale_history.py <repository> 30
python3 -I harness/grade.py <arms>/*-r1
```
