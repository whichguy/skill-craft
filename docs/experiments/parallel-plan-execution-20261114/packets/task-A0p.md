You are the parent agent of an orchestration probe. The work is a set of small analysis tasks over log files. A script decides which tasks may start and prints each task's instructions. Kit: python3 $kit. Run directory: $run_dir.

Do every task yourself, in this conversation. Each task ends with a slow verification command that only waits, so you may let several of those wait at the same time:
1. Run: python3 $kit ready --run $run_dir
   It prints one JSON line. "ready" lists the task ids you may start now; "complete" is true when nothing is left to do.
2. If "complete" is true, go to the last step. Otherwise, for every id in "ready", one after another, run: python3 $kit begin --run $run_dir --step <ID>
   It prints the task, the slow verification command and the command that reports your result. Do the analysis yourself now and note your result, but do not run the slow verification command or the reporting command yet.
3. Then run the slow verification commands of all those tasks together, in ONE shell command that starts each one in the background with & and then waits for all of them with wait, so that they wait at the same time. Let every one of them finish.
4. Then run each task's reporting command exactly, and note the line each prints.
5. Go back to step 1.
Do not start sub-agents. Shell background jobs are only for the slow verification commands.

Last step: run python3 $kit verify --run $run_dir, then end with one last line, exactly in this form: FINAL {"done":[task ids],"failed":[task ids],"not_run":[task ids],"answer":N} where N is the answer of the last task (read it with: python3 $kit outcome --run $run_dir --step $last_step).
