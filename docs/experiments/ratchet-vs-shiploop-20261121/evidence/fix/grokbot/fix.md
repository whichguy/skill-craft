# Fix pass

Before: `npm test` passed 8 of 8. After: 21 of 21. Every shortfall was first reproduced in headless Chromium against a real `node server.js` with disposable data. Each new test was run against the original product files and failed there.

The suite has no browser. For page-only fixes, the rule that carries the fix now lives in `public/rules.js`, which the page loads before `app.js` and the suite requires directly (TC-15 to TC-19). TC-20 and TC-21 check the served stylesheet and page. The page behaviour itself was checked again in Chromium after each fix.

## Shortfalls

- **high · Keyboard cancellation can stop the wrong task.** Fixed: task, proposal and memory buttons carry a key, and a refresh returns focus to the control with the same key, never to another task's. Test: `TC-15 returns keyboard focus to the same task control when the task list reorders`.
- **high · A capitalized field can write the wrong field.** Fixed: a change naming a field that differs only in capitals from the record's field is refused, nothing is written, and the Change result names the right field. Test: `TC-9 refuses a field whose capitals differ from the record field and leaves the record alone`. The read reply "ORD-1001 has no STATUS." comes from the stand-in and is unchanged; it is documented.
- **high · Saving a reused name silently overwrites a saved entry.** Fixed: saving a name that is already saved without choosing Edit is refused with an alert, and the entry is kept. Test: `TC-11 keeps a saved entry when a blank form reuses its name`.
- **high · A temporary storage failure leaves abandoned work looking active.** Fixed: a reply or task that cannot save its progress shows as failed with Retry or Retry task at once, and that state is saved on the next request after storage accepts writes again. Test: `TC-12 marks work stopped by a storage failure as recoverable and saves that once storage returns`.
- **medium · Valid bot names can push chat controls outside a narrow window.** Fixed: the chat column can no longer grow wider than its space, and a long bot name is cut with an ellipsis. Send and the tools toggle stay in view at 390, 1100 and 1440 pixels. Test: `TC-20 keeps the chat column within a narrow window whatever the bot name`.
- **medium · A cancellation click can disappear while a chat action is in flight.** Not changed. It reproduces only when the action's response is held on purpose. A local action round trip measured about 6 ms. The card keeps showing Running and Cancel task, and a second press cancels, so a fix would be speculative hardening. Documented in README.
- **medium · The open page reports live progress while the server is down.** Fixed: an alert says that what is shown is the last known state, and it clears when the server answers again. Test: `TC-18 labels a lost connection as the last known state until the server answers again`.
- **medium · Reloading loses the reading position and unsent text.** Fixed: each person's draft and reading position in each conversation are kept for the browser tab and restored after a reload. Test: `TC-19 restores each conversation draft and reading position after a reload`.
- **medium · Common opening questions make saved conversations indistinguishable.** Fixed: an empty conversation is listed as Untitled conversation, a repeated name gets a number such as "(2)", and the tooltip shows your latest message. Only the creation button is now named New conversation. Test: `TC-17 gives conversations with the same opening message distinct names`.
- **medium · An incomplete clarification loses the pending record request.** Not changed. Every reply comes from the stand-in, which the request says to use as it is; the app would have to write replies of its own to re-ask. Sending `Update ORD-1001` again recovers. The phrasing it needs is documented in README.
- **medium · Active instructions cannot be cleared from an existing bot.** Fixed: a Clear instructions button under the active instructions returns the open bot to having none and keeps its conversations. Test: `TC-13 clears the open bot instructions and keeps its conversations`.
- **medium · Approval previews can make field boundaries ambiguous.** Fixed: a value containing `·`, `→` or a quotation mark is shown in quotation marks. Test: `TC-16 shows proposed values with unambiguous boundaries`.
- **medium · A total above the safe integer range can be silently rounded.** Fixed: a number larger than 9007199254740991 is refused before any proposal, and the record is left alone. Test: `TC-10 refuses a number that cannot be stored exactly instead of proposing a rounded one`.
- **medium · The composer silently drops the tail of overlong input.** Fixed: the Message box no longer cuts pasted text. Sending more than 12,000 characters shows the server's alert, sends nothing and keeps the text. Test: `TC-21 refuses an overlong message with a reason instead of cutting it short`.
- **low · Setup gives no reason when the environment token is rejected.** Fixed: Setup shows an alert that the provider refused the `PROVIDER_TOKEN` token, without showing it. Test: `TC-14 tells setup that the environment token was refused without showing it`.

## Choices documented in README

Each was checked against the running product:
- how conversations are named (first message, 56 characters, newest first), the Untitled and numbered names, and the tooltip;
- a new bot's one empty conversation;
- drafts and reading positions kept per tab across reloads;
- dark mode shared by everyone using the browser;
- the 80 and 12,000 character limits, trimming and the 64 KB request limit;
- saved instructions and tasks being per person and shared across that person's bots, Use copying text, and Clear instructions;
- refusal of a reused name;
- memory deduplication and whole-fact forgetting, whose reply confirms either way;
- exact field names, and the capitalized read reply;
- the phrasing that follow-ups to `Update` need;
- quoting in previews and the largest number allowed;
- immutable id, type and readers, and the conflict check on confirm;
- one token serving every person, and the refused environment token;
- several tasks per conversation, and which one Add step extends;
- what Since you were away compares with;
- clicks ignored while an action is in flight (not changed);
- the lost-connection alert, and what happens when the data folder cannot be written.
