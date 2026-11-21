# Closing look

I read the request, specification, plan, build and test reports, and the app, provider and records READMEs. This checkout had no fix or referee reports. I used the existing acceptance helpers to run the Node server on available ports with disposable data, exercise its HTTP actions and open the app in Chrome at 1440 and 390 pixels. I used the existing fault probe for storage failures.

I tried invalid and valid setup tokens, record counts for all three people, a hidden record, a clarified update and rejection, order creation and replayed confirmation, protected fields, an overflowing total and signed zero. I checked 120 and 121 characters for names, 24,000 and 24,001 for messages, reusable text and direct memory edits, and a blank submission. I also tried reply retry, keyboard sending, task steering and cancellation, task completion after closing the page, and a restart with saved setup, memory and a confirmed order. The exact caps and hostname choices are implementation details. Existing clauses already cover the unrepresentable-value and secret-preview cases.

## Added clauses

- **C-263** — product keeps to it: no. Two instances opened the same directory on different ports. The first confirmed ORD-1005, then an instruction save through the second erased the order and the recorded decision. The order was still absent after restart.
- **C-264** — product keeps to it: no. After restoring an older backup and restarting at the same URL, the open page continued to show a stale transcript and a connection warning. A direct request returned the restored workspace, which the browser displayed after a reload.
- **C-265** — product keeps to it: no. In desktop Chrome, reopening the original discussion or reloading took a transcript scrolled to an older passage to the newest turn.
- **C-266** — product keeps to it: yes. Stale instruction and task saves each reported a conflict and preserved both the newer saved value and the unsaved text in the original editor.
- **C-267** — product keeps to it: yes. With directory sync failing after replacement, the browser showed Applied and a durability warning. Repeating the decision returned Applied and the reviewed field retained its committed value.
- **C-268** — product keeps to it: yes. With result writes failing before replacement, the reply and task appeared interrupted while the server ran. After clearing the fault, retry finished the original user turn once and resumed the task at its first unfinished step.
