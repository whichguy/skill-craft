# Fixed-port probe record

`executed_probe.py` preserves the probe wrapper and `executed-command.txt` preserves its heredoc command form. These files are for reproducibility and inspection only. They were saved after the probe; neither file was executed or rerun while preparing this record. No port was touched during this documentation step.

The wrapper ran the same Battleship shell check recipe and fixed port used by the first Battleship product check in `test/shiploop_e2e/cases.json`. The observed result was exit code 0. The check succeeds after `curl -fsS` writes a response to `page.html` and `grep -qi battleship page.html` matches; it then deletes `page.html`. The response body was not retained.

The temporary sibling handler in the wrapper responds with HTML containing `<title>Battleship</title> stale sibling app`; the candidate handler responds only with `candidate`. The probe started the sibling on port 39171 before launching the candidate against that same port. Because the two handlers are disjoint and the check passed, the sibling-response explanation is strongly supported, but the exact response body/source was not captured and remains an inference.

The candidate launch redirected both stdout and stderr to `/dev/null`. No bind error text was captured. `EADDRINUSE` is therefore inferred from the sibling occupying the shared port when the candidate attempted to listen, not observed in stderr. The original receipt's `candidate_server_still_running: false` was a hardcoded value, not a process-state measurement; the corrected receipt sets this field to `null` and marks it unobserved.

`result-original.json` preserves the original receipt. `result.json` keeps the observed exit code and adds the evidence limits above. This probe used temporary local Node servers only and did not alter repository sources, call a model, deploy, or install anything.
