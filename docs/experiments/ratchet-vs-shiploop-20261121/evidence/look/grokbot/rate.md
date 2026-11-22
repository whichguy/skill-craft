# Would the customer care?

`/Users/dadleet/e2e-runs/d20261122-360a9f/deep/grokbot/request.md` is a request a customer gave a software builder. Below are things a reviewer says the delivered product
gets wrong. For each, taking the reviewer's description as true, say whether the customer, an operator or the next
maintainer would care:

- `must`: it loses data, misleads a user, breaks something that worked, or is a plain defect anyone would report.
- `should`: a careful builder would not have left it; a real but smaller cost.
- `no`: a reasonable builder could ignore it; fixing it is taste, speculation or over-engineering for this request.

Answer with one JSON object and nothing else: `{"ratings": [{"n": 1, "rating": "must|should|no", "why": "one sentence"}]}`

## The reported shortfalls

- **1**: Keyboard cancellation can stop the wrong task.
- **5**: Valid bot names can push chat controls outside a narrow window.
- **6**: A cancellation click can disappear while a chat action is in flight.
- **7**: The open page continues to report live progress when the server is down.
- **8**: Reloading loses the reading position and unsent text.
- **10**: An incomplete clarification loses the pending record request.
- **11**: Active instructions cannot be cleared from an existing bot.
- **12**: Approval previews can make field boundaries ambiguous.
- **13**: A total above the safe integer range can be silently rounded on update.
- **14**: The composer silently drops the tail of overlong input.
- **15**: Setup gives no reason when the environment token is rejected.

## The reviewer's full text, for the detail of each

# Product look

Reproduced in headless Chromium with a real `node server.js` process and disposable data. For a fresh reproduction, run `PORT=61848 DATA_DIR=../tmp/look-repro STANDIN_SLOW_MS=2500 STANDIN_STEP_MS=650 node server.js` from the repository, using a free port and an empty data directory. Open the corresponding loopback URL, continue as Maya unless specified, and save a valid offline token. The eight `npm test` cases passed.

## Shortfalls

- **high · Keyboard cancellation can stop the wrong task.** In one conversation, send `Research: keyboard A [long]` and `Research: keyboard B [long]`. With both running, focus **Cancel task** on the lower card, which was B in the observed run. Wait for a progress refresh and press Space. Focus jumped to A’s **Cancel task** and Space cancelled A while B continued. Progress updates need to preserve focus on the same task so keyboard activation stops the intended work.
- **high · A capitalized field in a record request can write the wrong field.** On fresh records, send `WHAT IS THE STATUS OF ord-1001`. The app replies `ORD-1001 has no STATUS.` even though the provider guide says capitals do not matter. Send `set the STATUS of ORD-1001 to closed` and confirm the `ORD-1001 STATUS: ∅ → closed` preview. The app reports success, but a read of lowercase `status` still returns `open` and a read of uppercase `STATUS` now returns `closed`. Both spellings need to address the existing status field.
- **high · Saving a reused name silently overwrites a saved entry.** Save an instruction named `Review rules` with text `First version`. In the cleared form, type the same name with `Third without edit` and click **Save instruction** without first clicking **Edit Review rules**. There is one entry and **Edit Review rules** loads the replacement text. The same steps with a saved task named `Check size` replaced its original request. The app needs to preserve the original or explicitly ask before replacing it when the user has opened a blank form.
- **high · A temporary storage failure leaves abandoned work looking active.** Start `Research: unwritable data [long]` and send `who are you [slow]`. When the task is Running and the chat says the assistant is replying, rename the disposable data directory and create a regular file at its old path. Keep it there for four seconds, then remove the file and restore the directory, leaving the server running. The terminal logged `Background task progress could not be saved.` and `Reply progress could not be saved.` After storage was restored the task still said Running and the chat still said `Assistant is replying…`, with neither retry control visible. Restarting finally exposed the interruption and recovery controls. Work that has stopped needs to be marked recoverable once storage is available again, with an accurate status in the meantime.
- **medium · Valid bot names can push chat controls outside a narrow window.** At desktop width, create a bot named with 80 consecutive `N` characters. Resize to 390 × 700. The chat content spans 871 pixels in Chromium. **Send** starts at x=753 and **Toggle workspace tools** at x=827, beyond the clipped edge. A valid name needs to fit without moving the composer or workspace controls out of reach.
- **medium · A cancellation click can disappear while a chat action is in flight.** Start a long task. In Playwright, intercept `POST /api/action` for the next `send`, let the request reach the server, and hold the response. Send `ping outstanding request` and click **Cancel task** while the response is held. Release the response. The chat reply arrives, but the task is still Running, and the click produced no feedback. The cancellation needs to be accepted or the control needs to indicate when it is unavailable.
- **medium · The open page continues to report live progress when the server is down.** Start `Research: interruption audit [long]`, then send `Who are you [slow]`. When the task is Running and the reply is pending, stop the server by PID. After four seconds the page still says `Assistant is replying…` and Running, with no connection alert. Restarting shows the correct interruption and retry controls. While disconnected, the page needs to label these as last-known states and visibly indicate reconnection.
- **medium · Reloading loses the reading position and unsent text.** Fill a conversation with seven long messages, scroll up to an earlier turn, type `Draft survives?` without sending, and reload. Chromium returned to the bottom (scroll offset changed from 300 to 2471) and the composer was empty. Returning to the same conversation needs to preserve the reading position and the in-progress draft.
- **medium · Common opening questions make saved conversations indistinguishable.** Create two conversations in the same bot, each starting with `How many orders can you see?`, and give each a different second message. Both buttons have that exact label and the same tooltip. There is no visible way to distinguish the discussions without opening them. Empty conversations also share the accessible name **New conversation** with the creation button. Returning to the right discussion needs a way to distinguish entries when their generated names coincide.
- **medium · An incomplete clarification loses the pending record request.** Send `Update ORD-1001`. The assistant asks which field and value. Answer `status`. The assistant echoes `You said: "status".` instead of asking for the missing value. Follow with `the status to closed` and it echoes again without a proposal. The app needs to keep the outstanding question recoverable and help the user provide the missing value. The ordinary-language `Could you close order ORD-1001 for me?` also produces an echo without pointing to the supported update phrasing.
- **medium · Active instructions cannot be cleared from an existing bot.** Save `Review rules` with `Second via edit`, click **Use Review rules**, then delete the saved entry. `who are you` still reports those instructions. The only remaining controls save another nonblank entry and apply it, so the user cannot return this bot to having no special instructions. The active instructions need a way to be removed while keeping the bot and its conversations.
- **medium · Approval previews can make field boundaries ambiguous.** Send `create an order for Order lead · status: closed · total: 999 totalling 27`. The preview displays `customer: Order lead · status: closed · total: 999 · status: open · total: 27` inline. The actual customer value includes the first status and total labels. Likewise, `set the customer of ORD-1001 to Acme → North` displays `Acme Tools → Acme → North`. The preview needs to delimit values so the user can identify exactly which fields and values will be written.
- **medium · A total above the safe integer range can be silently rounded on update.** Send `set the total of ORD-1001 to 9007199254740993`. The preview offers `9007199254740992` without flagging the difference. Confirm and then ask `what is the total of ORD-1001`. The reply and stored record both contain `9007199254740992`. The create flow accepts `9007199254740991` and rejects `9007199254740992`. Updates need to preserve the requested number exactly or clearly refuse it before offering confirmation.
- **medium · The composer silently drops the tail of overlong input.** With **Message** focused, insert 12,000 `a` characters followed by `Do not send this until Friday` in one operation. Chromium retains 12,000 characters without an alert. Press Enter and the shortened message is sent without the suffix. The user needs visible notice that the text did not fit before sending it.
- **low · Setup gives no reason when the environment token is rejected.** Start with an empty data directory and `PROVIDER_TOKEN=sk-local-tooShort` and continue as Maya. The ordinary Setup form appears with no alert. A valid token entered there works. Setup needs to say that the environment token was refused, without displaying it, so the operator can tell why the expected configuration did not take effect.

## Choices the customer was not told

- The initial conversation title comes from the first sent message, with whitespace collapsed and the result cut to 56 characters. The list puts the most recently created conversation first.
- A new bot starts with one empty conversation.
- Saved instructions and saved tasks are per-person libraries available across that person’s bots. Applying an instruction copies its current text onto the selected bot, and an edited library entry takes effect on that bot when applied again.
- Bot names and saved-entry names are limited to 80 characters. The composer, saved-entry bodies and memory edits are limited to 12,000 characters. Names and text are trimmed on submission, and JSON action requests have a 65,536-byte limit.
- Conversationally remembered facts are deduplicated case-insensitively, and conversational forgetting matches the full fact case-insensitively.
- An approval compares the proposed field’s original value with its current value. New-order approvals also check that the proposed ID is still available. A conflict ends that proposal and asks for a fresh one.
- Existing record identity, type and reader fields are immutable through the chat.
- Both a saved setup token and an accepted environment token configure the whole installation. An accepted environment token takes precedence when both are present.
- Several long tasks can run in one conversation. An `Add step` follow-up targets the latest-created task still running in that conversation and appends the new step after its current plan.
- The return summary uses the browser’s last-seen time for each person to show newly completed or cancelled tasks, alongside currently running, failed and interrupted tasks.
- Dark mode is a browser preference shared by profiles using that browser.
- Draft text follows its conversation when switching threads in the same open tab.
