<!-- partial: loop-invoke. shiploop_loops BLOCK_HEADING, INVOKE_LINE / RESUME_LINE and FOLLOW_LINE, verbatim; the
start command is a cmd slot (literal and absolute: the runtime and the hooks read its text). -->
Until Loop (no iteration limit; the loop script counts the iterations):
{{#if loop_started}}The loop already started: do not start it again (a second start resets it). While the receipt's status is active, run its next_argv once and follow the packet it prints; when complete or stopped, submit this stage's result. Its argument is already in the Contract file; do not edit that file or the receipt:{{/if}}{{#if !loop_started}}RUN the Until Loop now, once, before any work, and do this stage's work only inside it. Start it with this command, in the foreground, exactly as printed:
{{loop_start_command}}
Then follow each packet it prints (run its done_argv as printed) until the receipt says complete or stopped. Its argument is already in the Contract file; do not edit that file or the receipt:{{/if}}
