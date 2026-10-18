<!-- partial: loop-result. shiploop_loops RESULT_LINE + REPORT_FIELDS + LOOP_RULE, shortened (one route back: the
receipt's next_argv; the start command is printed above only while no receipt exists). -->
Result: when the Receipt says complete (stopped: report it), keep it in evidence_refs and run the Callback. If the Callback refuses for the loop, run the receipt's next_argv once, then the Callback again. Done-report fields: classification trivial|non-trivial|unresolved, exit_assessment satisfied|unsatisfied|unknown, continuation_assessment allowed|blocked|cancelled, plus evidence and handoff (nonblank text).
Call an exit condition satisfied only when a command or file shows it after your last edit.
