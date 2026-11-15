You are the parent agent of an orchestration probe. The work is a set of independent feature requests for one software project, a help-desk ticket service. A script decides which request may start and prints each request's full instructions. Kit: python3 $kit. Run directory: $run_dir.

Do every request yourself, in this conversation, one at a time:
1. Run: python3 $kit ready --run $run_dir
   It prints one JSON line. "ready" lists the request ids you may start now; "complete" is true when nothing is left to do.
2. If "complete" is true, go to the last step. Otherwise take the first id listed in "ready" and run: python3 $kit begin --run $run_dir --step <ID>
   It prints the request and ends with the command that reports your result. Do the request yourself, in the workspace it names, then run that reporting command exactly and note the line it prints.
3. Go back to step 1.
Do not start sub-agents or background jobs.

Last step: run python3 $kit verify --run $run_dir, then end with one last line, exactly in this form: FINAL {"done":[request ids],"failed":[request ids],"not_run":[request ids],"answer":N} where N is the answer of the last request (read it with: python3 $kit outcome --run $run_dir --step $last_step).
