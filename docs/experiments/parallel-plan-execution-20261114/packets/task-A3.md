You are the parent agent of an orchestration probe. The work is a set of small analysis tasks over log files. A script decides which tasks may start and prints each task's instructions; fresh sub-agents do the tasks; you launch them and collect their one-line results. You never need to read the log files or do a task yourself. Kit: python3 $kit. Run directory: $run_dir. At most $capacity sub-agents may be active at the same time.

Repeat this loop:
1. Run: python3 $kit ready --run $run_dir --claim --capacity $capacity
   It prints one JSON line. "ready" lists the task ids it has just claimed for you to start now; "deferred" lists tasks that are ready but did not fit the capacity (they are offered again on a later call); "claimed" lists tasks claimed earlier whose sub-agent has not begun them yet; "running", "done", "failed", "blocked" and "waiting" list the others; "complete" is true when nothing is left to do.
2. If "complete" is true, leave the loop.
3. Otherwise start one fresh sub-agent for every id in "ready", all together in the same turn before you wait for any of them, using your built-in facility for starting an agent with its own context. A sub-agent starts with no memory of this conversation, so give it the whole instruction: "Run exactly `python3 $kit begin --run $run_dir --step <ID>` and do what it prints. It ends with a command that reports your result: run that command exactly, then reply with the one line it prints." If you could not start a sub-agent for a claimed id, run `python3 $kit release --run $run_dir --step <ID>` so the task is offered again.
4. When any sub-agent returns, go back to step 1 without waiting for the others. If "ready" is empty and "complete" is false, tasks are claimed, running or deferred: wait for a sub-agent to return, then go back to step 1.
Do not do the tasks yourself and do not use shell background jobs.

After the loop run: python3 $kit verify --run $run_dir
End with one last line, exactly in this form: FINAL {"done":[task ids],"failed":[task ids],"not_run":[task ids],"answer":N} where the ids come from the last "ready" line ("done", "failed", and "blocked" plus "waiting" plus "deferred" for not_run) and N is the answer of the last task (read it with: python3 $kit outcome --run $run_dir --step $last_step).
