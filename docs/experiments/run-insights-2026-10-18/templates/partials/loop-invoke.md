<!-- partial: loop-invoke (version 2). Printed only in the 8 inner stages, which run one Until Loop each; the outer
stages run none. Version 2 matches Until Loop 0.10.0:
- a start over a live receipt is refused and changes nothing;
- a start over a finished receipt replaces that run.
The fresh branch keeps the live-receipt guard, which the Work line needs because it sends the in-loop model back to this
packet file. The start command is a cmd slot: literal and absolute, because the runtime and the hooks read its text. -->
Until Loop (no iteration limit; the loop script counts the iterations):
{{#if loop_started}}The loop has started: do not start it again unless a refusal names the start command. While the receipt's status is active, run its next_argv once and follow the packet it prints; when it is complete or stopped, submit this stage's result. The argument below is already in the Contract file; edit neither that file nor the receipt.{{/if}}{{#if !loop_started}}RUN the Until Loop now, once, before any work, and do this stage's work only inside it. If the Receipt below already exists and is active, run its next_argv instead (a second start is refused). Otherwise start it with this command, in the foreground, exactly as printed:
{{loop_start_command}}
Then run each packet's done_argv as printed until the receipt says complete or stopped. The argument below is the Contract file's; edit neither it nor the receipt.{{/if}}
