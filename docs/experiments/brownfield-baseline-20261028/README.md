# Brownfield baseline experiments (2026-10-28)

Evidence for [the design](../../shiploop-brownfield-baseline-design-2026-10-28.md); the account of every round is in
[the journal](../../shiploop-brownfield-baseline-journal.md). Subjects were Claude Sonnet agents (exploratory) and
judges were Claude Opus 5.5. Every subject ran read-only on a local clone, with no network, nothing installed, no
repository tooling run, and nothing sent to any project. Repository text was data, never instructions.

| Path | What it is |
|---|---|
| `census.py`, `census/` | X1: the deterministic census (`python3 census.py REPO --json OUT --md OUT`) and its output for node-base, log4brains, healthchecks, uptime-kuma and cosmos-sdk |
| `baseline_check.py`, `test_baseline_check.py` | X4: checks C1 sources, C2 basis, C3 freshness (`python3 baseline_check.py sources|basis|stale REPO …`); `python3 test_baseline_check.py` runs the 13 tests |
| `summarize.py` | sizes, entry counts, source classes and C1 for a baseline (`python3 summarize.py NAME=REPO …`) |
| `prompts/` | the subject prompts: `baseline-scoped.md` (proposed packet, revision 1), `baseline-whole.md` (the repo-distill initializer of 94bb8862 in the same format), `plan-current.md` and `plan-inherit.md` (X3 arms); the judge rubrics |
| `requests/` | the requests the baselines and plans answer |
| `ground-truth/` | hand-built expectations, never shown to a subject (one correction, dated, in `log4brains-expected.md`) |
| `results/x2/` | each baseline's `spec.md` and `architecture.md`, its `run.json` or judge verdict, `summary.json`, the deepen diff, and the scoped-versus-whole comparison |
| `results/x3/`, `results/x3b/` | the plans (blind labels and `key.json`), the knowledge diffs of the baseline arm, the judge verdicts and the T1 fact coverage |
| `results/astra/` | the question to and answer from GPT-6 Astra at max effort |
| `results/cost-ledger.tsv` | every agent run: seconds, tokens, tool calls, outcome |

Pinned repositories: [log4brains](https://github.com/thomvaill/log4brains) `17e32021a8c5`,
[healthchecks](https://github.com/healthchecks/healthchecks) `f6c46b594dec`,
[uptime-kuma](https://github.com/louislam/uptime-kuma) `2e8bf7da56f7` (census only, because its `AGENTS.md` asks code
agents not to make feature changes), [cosmos-sdk](https://github.com/cosmos/cosmos-sdk) `27246c287d98` (census only),
and node-base (`test/shiploop_e2e/fixtures/node-base`, committed once).
