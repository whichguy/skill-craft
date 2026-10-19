<!-- partial: loop-result (version 2). These are loops.RESULT_LINE, REPORT_FIELDS and LOOP_RULE, with the refusal routes
of loops.check_loop_packet made explicit. Each loop refusal names its own command: the start command when no run
matches this action's contract, or the receipt's next_argv while it is active. The stop and outcome pairs are the ones
check_loop_packet accepts. -->
Result: a complete Receipt reports done, a stopped one {{stop_outcomes}}; keep the Receipt in evidence_refs and run the Callback. If the Callback refuses for the loop, run the command the refusal names, then the Callback again.
Done-report fields: classification trivial|non-trivial|unresolved, exit_assessment satisfied|unsatisfied|unknown, continuation_assessment allowed|blocked|cancelled, plus evidence and handoff (nonblank text).
Call an exit condition satisfied only when a command or file shows it after your last edit.
