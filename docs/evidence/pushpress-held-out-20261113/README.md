# P8: the held-out rerun on the published and the fixed card (journal Round 11)

Two versions of the `pushpress` card, run on eight held-out cases, two trials each. Nothing here touches a PushPress tenant: the cases are single-turn
prompts in a sandbox with the tools Skill, Read, Glob and Grep, and two of them replay a tool result from a history file.

## Layout

- `frozen/` holds the design, frozen by hash before any model ran: `gen_cases_p8.py` (the generator), `cases/` (what the model saw and what the graders check),
  `answer-key.json` and `answer-key.md` (each criterion with its source, and the pass lines fixed before any run), `score_p8.py` (the scorer),
  `regex-selftest-p8.js` (a self-test of the regex graders), and `frozen-manifest.txt` with `frozen-hashes.json` (a SHA-256 for each of the 57 files, and one over the
  manifest lines). The files were first written directly in this folder and moved under `frozen/` unchanged when the repository lint flagged the made-up session ids
  of the generator (a UUID shape) because the lint reads only files directly in an evidence folder; the manifest paths are relative to `frozen/`, so its text and its
  overall hash did not change. Check it: `cd frozen && shasum -a 256 -c frozen-manifest.txt` (57 lines, all OK).
- `outputs/` holds the outputs (not `results/`, which the repository's `.gitignore` excludes). `published.json` and `fixed.json` are the `claude plugin eval --json` results of the two arms with machine paths replaced by
  placeholders (the scorer reads no path); `p8-summary.json` and `p8-scorer-output.txt` are the scorer's output, which is byte-identical whether it reads these copies or
  the original files; `answers-p8.md` is every run's verdicts and graded final message.

## How the runs were made

Each arm is a temporary plugin `pushpress-quiz` 0.0.1 that holds one card and the eight cases (file by file identical to the git trees checked: the published card is
`skills/pushpress/` at `ffbc1cb852ccde469743c5d312d95603fd27d56a`, which equals the release `03f68d93a44500aca958db74440c1483e9038e11`; the fixed card is that directory
at `0b50cb39abdcd4207e46c57f9f1e7e359e226c9c`). Run from a scratch directory outside every repository:

    claude plugin eval <plugin dir> --ablation none --model sonnet --judge-model sonnet -j 4 --max-cost-usd 2.0 --no-publish --trust-plugin --json <result file>

CLI 2.1.323, model `sonnet`, default effort, judge `sonnet` with three votes on each judge criterion, two runs per case. A probe case came first (one replayed MCP-style
tool result, two trials) and was removed from the plugin before the runs.

Re-score without a model: `python3 -B -I frozen/score_p8.py frozen/answer-key.json outputs/p8-summary.json outputs/published.json outputs/fixed.json`.

## What was not kept

- Whole transcripts. The eval CLI deletes each run's sandbox unless it is given `--keep-temp`, which these runs did not use, so `answers-p8.md` holds the final message
  that each judge saw and not the tool calls in between. For the two history-replay cases (w1 and i1), in each card, the CLI left a session file in the case folder; it
  holds the whole system prompt and tool list of the session, so it is not committed. It showed that the skill listing was in the context of all eight of their trials
  and that the model answered from the replayed tool result without calling the skill.
- The judges' reasons. The result keeps each judge's vote, not its rationale.
