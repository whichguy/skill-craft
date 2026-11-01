# Clean install of the published skill-craft 2.27.2 (2026-11-01)

**Question.** Can someone who installs ShipLoop from the `skill-craft@whichguy` marketplace on a plain machine run it?
This is the live half of `docs/shiploop-portability-audit-journal.md`'s open item 4 ("no live-model first run from a
machine with nothing installed"). Consumer: that journal's Round 5, and the owner's decision on what is still unproven.

**Under test.** The release `e13af240100c066489e83c028d97339845402b55` (skill-craft 2.27.2, ShipLoop 1.26.2) as published
on `origin/main`; nothing from a working checkout.

## What was run

| # | Check | How | Model |
|---|-------|-----|-------|
| 1 | Native install into a fresh Claude config, then probes on the installed tree | `probes.sh` (re-runnable; output `probes.out`) | none |
| 2 | One live `hello` session, Claude host | `python3 test/shiploop_e2e/run.py --case hello --host claude --source marketplace` | `deepseek-v4.1-flash:1017-cloud` through Ollama |
| 3 | One live `hello` session, Codex host | `python3 test/shiploop_e2e/run.py --case hello --host codex --source marketplace` | `gpt-6.1-terra`, effort `xhigh` |

## Results

1. **Passed.** `claude plugin install skill-craft@whichguy` into a disposable `CLAUDE_CONFIG_DIR` gave one plugin, 2.27.2.
   The installed tree has no difference from `git archive origin/main plugins/skill-craft`; all eight entry scripts are
   mode 755; `FLOOR = (3, 9)` and the card's "needs `python3` 3.9 or newer and `git` on PATH" are present. On stock macOS
   Python 3.9.6 in a clean environment (`env -i`): `shiploop --help` exits 0 and `workspace start` exits 0 with a 15,772-byte
   packet. With `python3` absent from PATH, all five hook entries exit 0 with no output. In a Python 3.7.3 container
   (`node:14`) the installed tree's hooks exit 0 silently and `shiploop --help` exits 2 with one line,
   "ShipLoop needs Python 3.9 or newer; this python3 is 3.7.3."
2. **Blocked, not a ShipLoop result.** The host registered `/skill-craft:shiploop` and loaded the harness's export of the
   published tree (`plugins/skill-craft` from `origin/main`, passed with `--plugin-dir`; this is not a native marketplace
   install), then the first model call returned `429: you (dadleet) have reached your monthly usage limit`. One turn, no
   ShipLoop state written; process FAIL, shiploop FAIL, committed FAIL, checks FAIL, all downstream of the 429. The same
   Ollama limit was met on 2026-10-29. Evidence: `claude-hello-429-result.json`.
3. **Passed, every verdict.** The Codex preflight and the run installed the plugin by `codex marketplace add` and install into
   a fresh profile and got skill-craft 2.27.2 / ShipLoop 1.26.2 (`plugin sha256 b665a3fac1d7`). Verdicts: invoked
   `$skill-craft:shiploop`, plugin, process (rc 0, 929.2 s, 202 turns), shiploop `done`, committed (HEAD with 6 files, 15
   commits, 0 uncommitted), and both request checks (`hello.py` prints exactly `Hello, world!`; `python3 -m unittest -q`).
   ShipLoop command failures 0, asked a person 0, Improve children 8, packet copies 33 prints each with its kept copy, one
   keepalive decision (allow). Evidence: `codex-hello-result.json`, `codex-hello-invocation.json`.

## Evidence boundary

- Row 3 is the only live-model evidence, one host and one tiny case; it is not a baseline (the harness found 13 earlier
  `hello` rows, none with codex / gpt-6.1-terra / xhigh).
- Which interpreter the Codex session ran is inferred, not measured. The harness's own `python3` is 3.15.1
  (`codex-hello-invocation.json`); 61 of the model's ShipLoop or Improve script calls used a bare `python3`, and 16 used
  `/Applications/Xcode.app/Contents/Developer/usr/bin/python3` (Python 3.9.6) taken from the packets' printed command lines. The
  session's PATH was not recorded, so it is not proven that the whole session ran on 3.9.6.
- Row 2's plugin came from `--plugin-dir`, so only rows 1 and 3 exercise a native marketplace install.
- The host is macOS arm64 with the Command Line Tools; a Mac without them, Windows, WSL and Python 3.8 stayed untested.
- Machine load during rows 2 and 3 was 60 to 111 on 18 CPUs, because other sessions were running; row 3's 929 s is not a speed
  figure.

## Side observation

`workspace start` printed "ShipLoop progress observer unavailable; use view --start to retry." in 3 of 13 fresh starts at a
load average near 60 (0 of 6 on Python 3.9.6, 2 of 6 on Python 3.15.1, 1 of 1 in the first 3.9.6 probe). The cause is the
1.0 s startup deadline in `shiploop_progress.start`; it is a stderr notice and does not stop the run. The owner decides
whether to touch that limit.
