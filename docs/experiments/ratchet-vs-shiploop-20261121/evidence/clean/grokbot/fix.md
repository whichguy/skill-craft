# Fix pass

Each shortfall in look.md was reproduced first, in the page with Playwright (headless Chromium at 1440 and 390 pixels) or through the HTTP API, then rechecked the same way after the change. `npm test` passed before the pass (10 of 10) and after it (23 of 23). Browser-only rules live in `public/rules.js` so the suite can test them as a module. Keyboard focus can only be shown in a browser, so its check is in the product's browser check `node test/browser.cjs` (UI-1), which `npm test` does not run.

## Shortfalls

- high, a duplicate save overwrites a saved item: fixed. A save that is not an edit is refused with an alert naming **Edit <name>**, and the saved item is kept. Test: TC-10 a new save under an existing name keeps the saved entry until the person chooses Edit.
- high, reopening a conversation loses the draft and reading position: fixed. Drafts and reading positions are kept per person in browser storage and restored on reload; **Switch person** clears them. Test: TC-11 unsent drafts and reading positions are kept per person across a reload (module rule and the served `/rules.js`).
- high, a starter example overwrites an unsent message: fixed. The example asks before replacing a draft. Test: TC-12 a starter example asks before replacing an unsent message (module rule).
- high, a follow-up makes an earlier failed reply unrecoverable: fixed. Any failed message keeps its alert and **Retry**, and the retried reply is placed after that message. Test: TC-13 an earlier failed reply stays retryable after later messages.
- high, over-limit input silently drops the tail: fixed. The silent `maxlength` is gone. A field over its limit shows how much to remove and blocks its form until shortened. Test: TC-14 text over a field limit is reported instead of cut short (module rule and the page's limits).
- high, steering can add work to the wrong task: fixed. With more than one running task the app asks which gets the step (**Add to <task>** or **Don’t add**), and a note under the reply says where it went. Test: TC-15 a step added while several tasks run goes only to the task the person chooses.
- high, a task stays Running after its worker stopped: fixed. When progress cannot be saved, the task turns Interrupted once saving works again, keeps its checkpoint, offers **Retry task**, and the log names the task and the error. Test: TC-16 a task whose progress cannot be saved becomes Interrupted, logged and retryable.
- high, a large total is rounded before approval: fixed. Amounts beyond 9007199254740991 are refused with an explanation before **Confirm changes** is offered. Test: TC-17 an amount that cannot be kept exactly is refused before approval is offered.
- medium, capitalized fields and decimal creates: partly fixed. A change to a field spelled differently is now refused with a **Change result** that lists the fields that can change. Test: TC-18 a change to a field spelled differently names the fields that can change. Not changed: the reply to `What is the STATUS of ...` and the echo for a decimal create come from the required stand-in's parsing, which must not be changed or worked around. README documents lowercase field names and whole-number creates.
- medium, a rejected step's outcome disappears: fixed. The outcome is stored with the bot's reply and stays in the conversation. Test: TC-19 whether an added step went anywhere stays in the conversation.
- medium, the return summary has no time boundary and its links leave the task offscreen: fixed. **Since you were away** separates work that finished while away (since this browser last closed or hid the page) from work that finished during this visit, and a task link scrolls to and focuses the task. Tests: TC-20 the return summary separates work finished while away from work finished before or after (module rule), and UI-1 (the summary link focuses the task).
- medium, a remembered entry cannot be corrected at its saved length: fixed. Memory text may be as long as a message (12,000), the most a remembered fact can be. Test: TC-21 a remembered fact can be corrected at its saved length.
- medium, conversations are indistinguishable in navigation: fixed. When titles repeat, each button also shows the latest message the person sent there. Test: TC-22 conversations that open the same way are told apart by their latest message.
- low, keyboard focus falls to the page body: fixed. Opening a conversation from the list moves focus to **Message**, and cancelling a task moves focus to its card. Test: UI-1 browser workspace in `test/browser.cjs` (needs Chrome; `npm test` has no browser).
- medium, ordinary questions and completed research give no usable answer: not changed. Every reply must come from the required stand-in, which echoes unknown questions and returns only step acknowledgments for research. Writing answers in the app would replace the provider. README says so.

## Choices documented in README.md

Each was checked against the running product before it was written down.

- Bot names can repeat. Messages show the bot's current name, so a rename relabels earlier messages.
- Conversation titles are the first message, whitespace collapsed, cut to 56 characters. Repeated titles also show the latest message. New bots and conversations come first.
- Starter examples fill the composer for review and ask before replacing a draft.
- Saved instructions and tasks are shared across a person's bots. Each bot uses one instruction, and editing or deleting it affects every bot using it. Duplicate names are refused.
- Field limits, and that nothing is cut off.
- Drafts and reading positions are kept in this browser per person, and **Switch person** clears them. Failed replies keep **Retry** under their message.
- Memory matches facts without regard to capitals. Forgetting leaves the transcript intact.
- Editable fields and their types. Field names must be lowercase. Creation takes whole numbers. The largest exact amount.
- Pending creations reserve their order ID, and rejecting one frees it.
- Confirmation compares reviewed values, so a change followed by a change back still lets an earlier proposal apply.
- How steering picks a task. Interruption after a storage error. What **Since you were away** counts as away, including a browser that has not opened the app before.
- The stand-in's echo replies and step-only research results.
- Token precedence: a valid `PROVIDER_TOKEN` comes first, and an invalid one falls back to the saved token. A token saved through Setup is stored as plain text in the owner-only `workspace.json`.
