# ShipLoop efficiency plan: compact evidence copy (2026-10-17)

**Consumer.** The workers and reviewers of the ShipLoop efficiency plan (units U2 to U35), and the owner. Each unit's exit items
and the plan cite inputs by their scratchpad name (`SP/...`, under `/private/tmp/claude-501/...`, which macOS purges after
days). This directory is the committed copy; read it instead of the scratchpad. **When.** At the start of a unit that cites an
`SP/` path, and when a journal row or a reviewer needs the number behind a claim.

**Size.** 2.4 MB on disk (the unit's bound is 3 MB). Large streams are gzip or tar.gz files (`gunzip -c`, `tar -xzf`); the
rest is plain text.

**Redactions.** The owner's Developer Edition org username and org id are replaced by `<org-username>` and `<org-id>` in
`pk-live/` (they are identifiers of a personal account and the repository is public). Nothing else was changed.

## Where each `SP/` input is

| Scratchpad name | Here | What it is |
|---|---|---|
| `SP/eff2/aggregate-plan-final.md` | `plan/aggregate-plan-final.md` | the plan, revision 6 (the work order) |
| `SP/final-plan.md` | `plan/rev4-final-plan.md` | revision 4, the long form of every "rev 4 Step n.n" |
| `SP/eff2/COMMON.md`, `IMPL.md`, `ADDENDUM-cut.md` | `plan/` | owner rules, the unit worker brief, the host-cut addendum (Grok shows the first and last ~10,000 characters of an output above 20,000) |
| `SP/eff2/findings-*.json`, `decisions-*.json`, `redteam-*.json` | `findings/` | the six artifact reviews (69 findings), the three decision files, the two red-team files |
| `SP/artrev/*.md` | `artrev/` | the recorded Claude Sonnet 5.5 inline run of node-fix-bug (ShipLoop 1.3.0): per stage the packet, the model's calls, the result |
| `SP/v9/node-fix-bug` | `v9-node-fix-bug/` | the same run's compact export: `events.jsonl.gz` (the host stream), `metrics.json`, `slice-result.json`, `sessions.jsonl`, `timeline.jsonl`, `transcript.md`, `prompt.txt`, `invocation.json`, `run.tar.gz` (the run directory: state, results, tests, loops, improve, packets), `packet-archive.tar.gz` (every packet printed). Left out: the product tree and the plugin build, which the run directory and the packets reproduce |
| `SP/pk/live` | `pk-live/` | the packet files of the live Salesforce chess run, one per stage (redacted as above) |
| `SP/eff2/final-verify/fv_heads.py`, `main83.json`, `main163.json`, `merged83.json`, `merged163.json` | `final-verify/` | the head-length script and its numbers on main and on the merged tree at 83 and 163 characters (raw lengths, scratch clone paths) |
| render texts behind the head tables | `final-verify/render-texts-int-83-163.tar.gz` | the printed and whole texts of every offline packet on the reconciled INT tree, both routes, at 83 (`o83`) and 163 (`o163`) |
| unit U1's own numbers | `u1/` | `heads-reference-install-83-163.json` (head and whole length per stage and route, normalised to the reference install of `test/shiploop_head_budget.py`), `fv-int-83.json` and `fv-int-163.json` (the `fv_heads.py` form on the INT tree: the root path is 72 characters), `measure_heads.py`, `unreconciled-summary.txt` (the four red suites before the reconciliation), `failfirst-*.txt` |

## Not here

- `SP/sfchess/live2` (the Salesforce chess run 2, 169 MB) is copied unchanged to `/Users/dadleet/src-archive/2026-10-17/shiploop-live2-run2/`.
- Branch bundles (INT, the three feature branches, the docs branch): `/Users/dadleet/src-archive/2026-10-17/shiploop-eff-int-c5f79b.bundle`.

## The head table (what its numbers mean)

`test/shiploop_e2e/head_table.json` holds the length of every producer stage's printed head and whole text on the offline
node-fix-bug case, at a reference install: run directory 83 characters, skill root 63, CLI path 96 (a plugin-cache install).
`test/shiploop_head_budget.py` builds the packets in a temp directory of the right length and rewrites the rest by arithmetic, so
the value does not move with the machine. The raw numbers of `fv_heads.py` differ from the table by the CLI path (the offline walk prints
the bare word `shiploop`: +264 on the inline step-plan head) and by the root path of the checkout that rendered them.
