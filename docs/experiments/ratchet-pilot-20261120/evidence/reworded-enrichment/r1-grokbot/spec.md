## Use cases

### U-1: The operator starts the local app to make it available on this computer
Flow: With Node.js 22 or later, run `node server.js` and open `GET /` on `PORT`, or port `3000` when it is unset. Use `DATA_DIR`, or `./data` when it is unset, to reopen the same saved work after a restart. No npm dependencies are needed.
Source: request

### U-2: Maya enters as herself to get to her own workspace
Flow: The first screen offers `Continue as Maya`, `Continue as Theo` and `Continue as Ana` without a password prompt. Maya continues as Maya, sees her own workspace and remains Maya on reload. She uses `Switch person` to return to the first screen. Theo can continue from there into his own workspace.
Source: request

### U-3: The person setting up the app supplies a provider token to enable replies
Flow: With no saved token, find `Setup`, enter a credential in `Provider token` and choose `Save token`. A refused token gives an alert and allows another attempt. A token accepted by the stand-in enables replies and is kept secret. A valid `PROVIDER_TOKEN` already supplies the credential.
Source: request

### U-4: Maya organizes her work by bot and conversation to resume a discussion
Flow: Maya starts with `Assistant` in `Bots`. She uses `New bot`, enters a name in `Bot name` and chooses `Save bot name` to open the new bot. She uses `Rename bot` with the same form to change its name. She starts discussions with `New conversation` and uses the buttons in `Bots` and `Conversations` to return to the right transcript.
Source: request

### U-5: Maya chats with a bot to get an answer in context
Flow: In `Message`, Maya writes a message, uses Shift+Enter for a new line and sends with Enter or `Send`. `Conversation` shows her message and the provider reply as `Message from Maya` and `Message from <bot name>`. She can ask `what did I ask first` in the same discussion to refer to the earlier message. A message with `[slow]` shows a pending status. A message with `[fail once]` gives an alert and `Retry` obtains the reply to the original message.
Source: request

### U-6: Maya maintains saved instructions to reuse them with a bot
Flow: In `Saved instructions`, Maya supplies `Instruction name` and `Instruction text` and chooses `Save instruction`. `Use <name>` makes the instruction active for that bot's next reply, visible with `who are you`. `Edit <name>` reloads both fields so she can save revised text under the same name. `Delete <name>` removes the saved entry.
Source: request

### U-7: Maya maintains saved tasks to reuse a request in chat
Flow: In `Saved tasks`, Maya supplies `Task name` and `Task request` and chooses `Save task`. `Run <name>` sends that request in the open conversation. `Edit <name>` reloads both fields so she can save a revised request under the same name. `Delete <name>` removes the saved entry.
Source: request

### U-8: Maya inspects and corrects a bot's memory to keep it accurate
Flow: Maya asks the bot to `remember that I prefer tea` and sees the fact in `Memory`. She uses `Edit memory`, `Memory text` and `Save memory` to correct it. She can remove a fact with `Forget` or a chat request starting with `forget`. She uses `what do you remember` to see the current facts. Another bot or another person has a separate memory.
Source: request

### U-9: Maya asks about synthetic records to get an answer she is allowed to see
Flow: Starting with the supplied records, Maya asks `how many orders can you see` and gets a count of `3`. She asks `what is the status of ORD-1001` and sees `open`. Asking about `ORD-1003` receives the provider's cannot-see reply. Theo can ask about that order because he is a reader.
Source: existing: records/README.md, records/records.json, provider/README.md

### U-10: Maya reviews a proposed update to decide whether to apply it
Flow: On the starting records, Maya asks `update ORD-1001` and the bot asks which field to change and to what value. She answers `the status to closed` and sees `ORD-1001 status: open → closed` in `Proposed changes`. `Confirm changes` applies that proposal. `Reject changes` leaves the order alone. `Change result` says what happened, including if a reload or repeat leaves the proposal already resolved.
Source: request

### U-11: Maya reviews a proposed order creation to add a record she can read
Flow: On the starting records, Maya asks `create an order for Acme Tools totalling 125` and reviews a new `order` with customer `Acme Tools`, total `125` and status `open`. On confirmation with no intervening creation, it becomes `ORD-1005` and Maya is its sole reader. Confirming the same proposal twice yields one order.
Source: existing: records/README.md, records/records.json, provider/README.md

### U-12: Maya starts and steers longer work to get results after leaving the app
Flow: Maya sends `long task: supplier options [long]` and sees `Task: supplier options` in `Tasks`, with `Task status` reading `Running`. While it runs, she can send `add step: compare lead times` in its conversation. She can close the browser and return to the finished steps and current status. `Since you were away` reports relevant outcomes and work still running.
Source: request

### U-13: Maya cancels longer work to stop the remaining steps
Flow: Maya selects `Cancel task` on a `Running` task. She sees a truthful account of the cancellation, including finished work and what could still be stopped when the cancellation took effect.
Source: request

### U-14: Maya recovers interrupted work to finish without losing the discussion
Flow: Maya sends `research: supplier options [fail step 2]`. After the first step succeeds and the second fails, she sees `Failed` and uses `Retry task` to continue. If the server stops mid-task, she can return after restart, see what happened and use `Retry task` on a task shown as `Interrupted`. The transcript remains available.
Source: request

### U-15: Maya uses the chat comfortably by keyboard or in a narrow window
Flow: At a viewport width of `1440` pixels, Maya finds the applicable named controls on the main screen. In a narrow window she can read the transcript and write a message while secondary areas may be folded away. She navigates to the controls and operates them by keyboard.
Source: request

## Clauses

### C-1: The application runs with Node.js using `node server.js`
Observable: Running `node server.js` from the application folder under Node.js 22 starts the local service.
Source: request

### C-2: Starting the application requires no npm dependencies
Observable: A checkout with Node.js available and no installed npm packages serves the working application without an install step.
Source: request

### C-3: The service listens on the port set by `PORT`
Observable: With `PORT` set to an available port, the application is reachable on that port. When `PORT` is unset, the default is `3000`.
Source: request

### C-4: `GET /` serves the chat application
Observable: A browser opening `/` on the running service reaches the application.
Source: request

### C-5: All durable state kept by the application belongs under `DATA_DIR`
Observable: Starting with a custom `DATA_DIR` confines application-created durable data to that folder. With `DATA_DIR` unset, the folder is `./data`.
Source: request

### C-6: People can return to saved work after a server restart
Observable: Stop and start the service with the same data folder. On returning as the same person, the person can find their saved bots, conversations and messages, saved instructions, saved tasks, bot memory, and recorded proposal and task outcomes.
Source: implied: the request says what the application keeps survives a restart

### C-7: A fresh data folder starts with the supplied synthetic records
Observable: Starting with an empty data folder gives Maya, Theo and Ana the records and access shown in `records/records.json` irrespective of confirmed changes in another data folder.
Source: existing: records/README.md

### C-8: Using the application leaves the starting fixtures intact
Observable: `records/people.json` and `records/records.json` still match the supplied files after the app is used, including after a confirmed change.
Source: existing: records/README.md

### C-9: The initial screen offers one `Continue as <name>` button for each person in `records/people.json`
Observable: A browser with no current person sees buttons named `Continue as Maya`, `Continue as Theo` and `Continue as Ana`.
Source: request

### C-10: A person can enter by selecting their own continue button without a password
Observable: Activating `Continue as Maya` makes Maya the current person without a password prompt.
Source: request

### C-11: `Switch person` returns the person to the chooser
Observable: After continuing as a person, activate the button named `Switch person` to see the `Continue as <name>` buttons again.
Source: request

### C-12: Reloading preserves the selected person
Observable: After continuing as Theo, reload the page and continue in Theo's workspace without choosing Theo again.
Source: request

### C-13: Workspace data is scoped to the current person
Observable: Create a distinct bot, discussion, saved instruction, saved task, memory fact, proposal and task as Maya. While using the app as Theo, those private items are unavailable in views and responses, including operations addressed to a previously open item. Switching back to Maya makes her own items available again.
Source: request

### C-14: Work started as one person stays with that person if selection changes
Observable: Send a slow reply request or start a background task as Maya, then switch to Theo. The result and any resulting memory, proposal or task activity belong to Maya's original workspace.
Source: implied: U-2 shares the current person with pending replies and background work in U-5 and U-12

### C-15: Guided setup is available when no provider token is saved
Observable: A person entering an unconfigured app finds a region named `Setup` that explains the credential needed to enable chat. The region contains a textbox named `Provider token` and a button named `Save token`.
Source: request

### C-16: Saving a credential accepted by the stand-in enables replies
Observable: Enter `sk-local-` followed by twelve ASCII letters or digits and activate `Save token`. The app accepts it and can obtain a provider reply. Additional ASCII letters or digits after the minimum are accepted too.
Source: existing: provider/README.md, provider/standin.js

### C-17: A refused credential leaves setup recoverable
Observable: With no valid credential, submit a missing or invalid token, such as `sk-local-` followed by eleven digits. An alert indicates the refusal. A subsequent valid token can be submitted through `Provider token` and `Save token`.
Source: request

### C-18: A valid credential saved through setup remains usable after restart
Observable: Save a valid token without `PROVIDER_TOKEN`, then restart with the same data folder. The app can obtain a provider reply without saving the token again.
Source: implied: the request calls the setup token saved and requires kept data to survive restart

### C-19: A valid `PROVIDER_TOKEN` supplies a saved credential
Observable: Start with an empty data folder and a valid `PROVIDER_TOKEN`. After choosing a person, chat can obtain a provider reply without using `Save token`.
Source: request
Open: Credential precedence and recovery when both the environment and saved data supply credentials, including when an environment value is invalid, are for the requester to settle.

### C-20: The saved provider token is secret from every person using the app
Observable: After saving a token or supplying it in `PROVIDER_TOKEN`, the credential is absent from pages and application responses, including setup feedback and provider error feedback.
Source: request

### C-21: Each assistant reply comes from the supplied offline stand-in
Observable: With a valid token, chat works without access to an outside service. Supported prompts return the stand-in's reply text from `output.text`. Unmatched input yields its `You said: "<text>". (<bot name> has N message(s) from you in this conversation.)` reply.
Source: existing: provider/README.md

### C-22: The delivered application uses the stand-in as supplied
Observable: `provider/standin.js` remains identical to the supplied file and is the provider used for replies. Delivery contains no app-authored copy or replacement for it.
Source: existing: provider/README.md

### C-23: Each first-time person starts with one bot named `Assistant`
Observable: Enter as a person who has never used the app. Their bot list contains exactly one bot, named `Assistant`, which is open.
Source: request

### C-24: The `Bots` navigation lets the person open any of their bots
Observable: The navigation named `Bots` has a button named with each of the person's bot names. Activating one opens that bot's workspace.
Source: request

### C-25: `Bots` marks the open bot as current
Observable: After switching between two bots, the open bot's button is exposed as current in `Bots`.
Source: request

### C-26: The new-bot form creates a named bot
Observable: Activate `New bot`, enter a name in `Bot name`, and activate `Save bot name`. `Bots` gains a button with the saved name.
Source: request
Open: How to handle missing names or name collisions among a person's bots is for the requester to settle.

### C-27: Saving a new bot opens it
Observable: After the new-bot form saves a bot, the new bot is the current bot without a further selection.
Source: request

### C-28: The rename form changes the open bot's name
Observable: Activate `Rename bot`, enter a new name in `Bot name`, and activate `Save bot name`. The button for that same bot now has the new name, and its conversations and memory are still associated with it.
Source: request

### C-29: The `Conversations` navigation lets the person reopen conversations of the open bot
Observable: After saving discussions with two bots, open one bot. `Conversations` lists that bot's discussions as buttons. Selecting a discussion restores its transcript.
Source: request
Open: Conversation button naming and whether reopening the app automatically selects a last-viewed discussion are for the requester to settle.

### C-30: `Conversations` marks the open discussion as current
Observable: Select either of two discussions of a bot and find that discussion's button exposed as current in `Conversations`.
Source: request

### C-31: `New conversation` opens a fresh discussion for the current bot
Observable: Activate `New conversation` while a discussion has messages. The composition area is ready for a fresh discussion with the same bot. The prior discussion remains available.
Source: request

### C-32: The `Conversation` region shows the transcript of the open discussion
Observable: In the region named `Conversation`, each message is an article named `Message from <name>` using the speaker's person or bot name. The visible order of messages follows the discussion.
Source: request

### C-33: `Send` submits the text in `Message` to the open conversation
Observable: Enter ordinary text in the textbox named `Message` and activate the button named `Send`. The person's turn appears in that conversation and is submitted for a provider reply.
Source: request

### C-34: Enter sends the composed message
Observable: Press Enter with a message in the focused `Message` textbox. It is submitted just as with `Send`.
Source: request

### C-35: Shift+Enter inserts a new line in `Message`
Observable: With `Message` focused, press Shift+Enter. A new line appears in the draft without submitting it.
Source: request

### C-36: An outstanding reply is indicated by a status
Observable: After sending a prompt containing `[slow]`, a status announces that a reply is on its way during the provider delay. The stand-in uses `STANDIN_SLOW_MS`, defaulting to `1500` milliseconds.
Source: request

### C-37: A reply failure is indicated by an alert
Observable: The first attempt at a message containing `[fail once]` produces an alert. The original user message remains visible in the discussion.
Source: request

### C-38: `Retry` attempts the failed reply to the original message
Observable: After a first-attempt `[fail once]` error, activate `Retry`. The stand-in succeeds on the next attempt, and the transcript contains one copy of the user's turn.
Source: request

### C-39: An interrupted reply leaves its submitted turn recoverable
Observable: After a submitted turn is shown and before its slow reply returns, interrupt the service. On return the discussion still has the submitted turn, identifies the unresolved reply, and offers a path to obtain the reply without duplicating the turn. If recovery has already finished, the discussion shows the resulting reply once.
Source: implied: the request calls for recovery from interruption without losing the conversation
Open: Whether to resume an interrupted reply or wait for `Retry` is for the requester to settle.

### C-40: A reply belongs to the conversation that originated the request
Observable: Send a `[slow]` prompt and open a different conversation or bot before it completes. Returning to the originating conversation shows the reply there. The other conversation gains no message from that action.
Source: implied: U-4 and U-5 share reply delivery with conversation and bot selection

### C-41: Follow-ups use the earlier turns of the same conversation
Observable: Send a distinct first message, close and reopen that conversation, then ask `what did I ask first`. The reply identifies that first turn. In a fresh conversation this prompt instead gets `This is the first thing you've asked.`
Source: existing: provider/README.md, provider/standin.js

### C-42: The provider answers as the open bot with its current instructions
Observable: Ask `who are you` after selecting or renaming a bot. The reply says `I am <bot name>.` It reports that bot's active instructions or `I have no special instructions.` when it has none.
Source: existing: provider/README.md, provider/standin.js

### C-43: An underspecified change request can elicit a clarifying reply
Observable: As Maya, send `update ORD-1001`. The reply asks `Which field of ORD-1001 should I change, and to what value?`
Source: existing: provider/README.md, provider/standin.js

### C-44: The next answer to a clarifying reply uses the record already discussed
Observable: Immediately after that clarifying reply, send `the status to closed` in the same conversation. The stand-in proposes setting `ORD-1001`'s status to `closed` without requiring Maya to restate the ID.
Source: existing: provider/README.md

### C-45: `Save instruction` stores a reusable named instruction
Observable: In `Saved instructions`, fill the textboxes `Instruction name` and `Instruction text`, then activate `Save instruction`. The saved entry can be selected by its name later.
Source: request
Open: Whether the saved instruction library is shared among one person's bots or kept per bot is for the requester to settle.

### C-46: `Use <name>` applies the saved instruction to the open bot starting with its next reply
Observable: Activate `Use <name>` in `Saved instructions` and then ask that bot `who are you`. The reply reflects the chosen text. Other bots keep their own active instructions.
Source: request

### C-47: `Edit <name>` loads a saved instruction into the instruction form
Observable: Activate `Edit <name>` on an instruction. Its name is in `Instruction name` and its text is in `Instruction text`.
Source: request

### C-48: Saving edits under the existing instruction name updates that entry
Observable: Edit an instruction, change its text and choose `Save instruction` with its name unchanged. The entry can be used with the revised text.
Source: request
Open: Whether a bot that is already using the instruction picks up edits immediately or on another `Use <name>` is for the requester to settle.

### C-49: `Delete <name>` removes the saved instruction from the library
Observable: Activate `Delete <name>` on a saved instruction. That entry is no longer available to select in `Saved instructions`.
Source: request
Open: What happens to instructions already active on a bot when the saved entry is deleted is for the requester to settle.

### C-50: `Save task` stores a reusable named request
Observable: In `Saved tasks`, fill the textboxes `Task name` and `Task request`, then activate `Save task`. The saved request can be selected by its name later.
Source: request
Open: Whether the saved task library is shared among one person's bots or kept per bot is for the requester to settle.

### C-51: `Run <name>` sends the saved request to the open conversation
Observable: Activate `Run <name>` in `Saved tasks`. The saved `Task request` appears as the person's turn in the open conversation and follows the normal reply flow.
Source: request

### C-52: `Edit <name>` loads a saved task into the task form
Observable: Activate `Edit <name>` on a saved task. The saved values appear in `Task name` and `Task request`.
Source: request

### C-53: Saving edits under the existing task name updates that entry
Observable: Edit a saved task, change its request and choose `Save task` with its name unchanged. A later `Run <name>` sends the revised request.
Source: request

### C-54: `Delete <name>` removes the saved task from the library
Observable: Activate `Delete <name>` on a saved task. That entry is no longer available to run in `Saved tasks`.
Source: request

### C-55: `Memory` shows the facts currently held by the open bot about the current person
Observable: The region named `Memory` shows each current fact as a list item. With no facts, the list contains no facts. Choosing a different bot shows its memory instead, and asking `what do you remember` gives the provider's reply from the corresponding facts.
Source: request

### C-56: A provider `remember` result adds its facts to the originating bot's memory for that person
Observable: Send `remember that I prefer tea` and see `I prefer tea` in that bot's `Memory`. It can be recalled in another conversation of that bot. A different bot has not gained the fact.
Source: existing: provider/README.md

### C-57: An `Edit memory` button opens the selected fact for editing
Observable: On a memory list item, activate `Edit memory` and find its current fact in the textbox named `Memory text`.
Source: request

### C-58: `Save memory` replaces the selected fact with the correction
Observable: Change `Memory text` and activate `Save memory`. The list item and a later `what do you remember` reflect the corrected fact.
Source: request

### C-59: `Forget` removes the selected fact from the open bot's memory for that person
Observable: Activate `Forget` on a memory list item. The item disappears and the bot's later `what do you remember` reply omits that fact.
Source: request

### C-60: A provider `forget` result removes the indicated fact from the originating bot's memory for that person
Observable: With `I prefer tea` saved, send `forget that I prefer tea`. The fact is removed from `Memory` and the bot's later recall omits it. If no facts remain, `what do you remember` returns `I don't remember anything about you yet.`
Source: existing: provider/README.md, provider/standin.js

### C-61: Record counts are limited to the current person's readable records of the requested type
Observable: With the original records, `how many orders can you see` gives Maya `3`, Theo `2` and Ana `1`. `how many accounts can you see` gives each `2`.
Source: existing: records/README.md, records/records.json, provider/README.md

### C-62: A lookup of a readable record reflects its current working values
Observable: With the original records, Maya's `what is the status of ORD-1001` returns `open`. After confirmation of a status change to `closed`, a new lookup returns `closed`; Theo can see this shared record's updated value too. A lookup of a missing field on a readable record gives the provider's no-such-field reply.
Source: existing: records/README.md, provider/README.md, provider/standin.js

### C-63: A record outside a person's readable set is unavailable to that person's assistant
Observable: Maya asking for a value on `ORD-1003` receives `I can't see a record called ORD-1003.`, the same kind of response as for an unknown ID. The lookup discloses no field values of the restricted record.
Source: existing: records/README.md, provider/README.md

### C-64: A person cannot obtain an actionable update for a record they cannot read
Observable: Maya sends `set the status of ORD-1003 to closed` or `update ORD-1003`. The answer says it cannot see that record. No confirmable change to that record becomes available. An unknown record is also unavailable for update.
Source: existing: records/README.md, provider/README.md, provider/standin.js

### C-65: `Proposed changes` previews the exact requested record change before approval
Observable: Maya sends `set the status of ORD-1001 to closed` on the starting data. The region named `Proposed changes` identifies the record `ORD-1001`, the field `status`, the previous value `open` and the proposed value `closed`, as in `ORD-1001 status: open → closed`. A proposed new order shows the proposed `type`, `customer`, `total` and `status` values.
Source: request
Open: For creation, whether a not-yet-assigned order ID is reserved for preview or reported as assigned at confirmation is for the requester to settle. An ID explicitly promised in a preview is part of what the person is asked to approve.

### C-66: A proposal has an explicit `Confirm changes` control
Observable: An actionable `Proposed changes` region exposes a button named `Confirm changes` for the proposal shown.
Source: request

### C-67: A proposal has an explicit `Reject changes` control
Observable: An actionable `Proposed changes` region exposes a button named `Reject changes` for the proposal shown.
Source: request

### C-68: A proposal leaves working records untouched until explicitly confirmed
Observable: Request a creation or update. While the proposal is unconfirmed, a fresh lookup or count still returns the working data from before the proposal, even after reload. Sending a follow-up or activating a different proposal does not itself approve this one.
Source: request
Open: Retention, expiry and coexistence of pending proposals across turns or reloads are for the requester to settle.

### C-69: Confirmation applies the exact change the person approved when it can still be applied
Observable: With `ORD-1001` still `open`, confirm the displayed change to `closed`. A fresh lookup reports `closed`. If intervening work makes the displayed change inaccurate, the user sees that outcome before any different change can be applied.
Source: request
Open: The handling of stale proposals, including whether the person must ask again or can review a refreshed proposal, is for the requester to settle.

### C-70: Record changes remain subject to the acting person's record permissions
Observable: A proposal generated for Maya cannot be confirmed by Theo acting as Theo. An attempted update of `readers` to a plain name cannot turn a reader list into text or give a previously unauthorized person access. The resulting working data still has the record identity, type and reader information required by the records contract.
Source: existing: records/README.md
Open: Which schema-valid fields beyond the documented examples are permitted for editing is for the requester to settle within the records access rules.

### C-71: Rejection resolves the proposal without a record effect
Observable: Activate `Reject changes` on an update or creation. An ensuing lookup or count shows no effect from that proposal, and repeating a stale confirmation of the rejected proposal cannot apply it.
Source: request

### C-72: Cancelling a proposed change has no record effect
Observable: If a proposed change is abandoned or cancelled, it does not create or update a record. `Reject changes` provides that outcome without requiring a separate cancel control.
Source: request

### C-73: Each confirmed proposal has at most one record effect
Observable: Activate `Confirm changes` more than once on the same creation proposal, or reload during confirmation and repeat the action. The proposal creates at most one order. Repeating confirmation of an already applied update cannot write it again over a subsequent change.
Source: request

### C-74: A confirmed creation gives the creator sole readability of the new record
Observable: Maya confirms a new order. Subsequent record queries by Maya can see it. Theo and Ana cannot see it.
Source: existing: records/README.md

### C-75: A new order receives the next free `ORD-` number
Observable: Starting with the original records, the first confirmed addition receives `ORD-1005`. A second confirmed addition with those orders still present receives `ORD-1006`. Successful overlapping creations cannot receive the same ID.
Source: existing: records/README.md, records/records.json

### C-76: Confirmed record effects survive a server restart
Observable: Apply a change, restart with the same data folder and query as an authorized reader. The confirmed value or created order is present.
Source: existing: records/README.md

### C-77: `Change result` reports the actual proposal outcome
Observable: After a confirmation, rejection, or attempted confirmation that could not apply, a region named `Change result` distinguishes what took effect from what did not. After an awkward reload, the person can tell whether the effect was applied, is still unresolved, or cannot be completed. The app does not claim success where the effect is unknown or absent.
Source: request

### C-78: A provider long-task result starts background work for its originating conversation
Observable: Send `long task: supplier options` or `research: supplier options` and see the task begin in the originating context. Sending `[long]` in the title requests the stand-in's eight-step variant instead of its normal three-step task.
Source: existing: provider/README.md

### C-79: `Tasks` exposes each long task by its title
Observable: After asking for `long task: supplier options [long]`, the region named `Tasks` includes an article named `Task: supplier options`.
Source: request

### C-80: Each long task exposes its current state through `Task status`
Observable: The status named `Task status` in the task article reads `Running` while work continues, `Completed` after all steps succeed, `Failed` after a stopping failure, `Cancelled` after cancellation takes effect, or `Interrupted` if execution stops before completion without a failure or cancellation and has yet to resume.
Source: request

### C-81: Completed task steps become visible as progress
Observable: Let a provider task advance. Results from `runStep` appear in the task article in the order of the requested steps, such as `Done: Collect what is known about supplier options`. The stand-in controls the step delay through `STANDIN_STEP_MS`, with a default of `500` milliseconds.
Source: existing: provider/README.md

### C-82: A running task can progress with no app page open
Observable: Start a task, close the app in the browser while leaving the Node service running, and return after the steps can finish. Progress is visible, including `Completed` if all steps finished successfully while away.
Source: request

### C-83: A steering follow-up appends a step to work running in the originating conversation
Observable: While a task runs in a discussion, send `add step: compare lead times` in that discussion. The task includes the added step after the steps it already had.
Source: existing: provider/README.md
Open: If multiple tasks can run in one conversation, how a follow-up selects one of them is for the requester to settle.

### C-84: A steering request without an eligible running task has an honest outcome
Observable: Send `add step: compare lead times` when the discussion has no task, when its tasks are only `Completed`, `Failed`, `Cancelled` or `Interrupted`, or when the only running task belongs to another discussion. The app makes clear that the step was not added. The same holds if the eligible task ends before the addition can take effect.
Source: implied: U-12 requires steering ongoing work and an honest account of what happened

### C-85: A running task offers `Cancel task`
Observable: A task article whose state is `Running` exposes the button `Cancel task`.
Source: request

### C-86: Cancellation stops the task's remaining work when it takes effect
Observable: Cancel a running task before its last step has started. After cancellation takes effect, no further pending steps start for that task. If work completed before cancellation could take effect, the task reports completion.
Source: request
Open: Whether a step already in flight finishes, is interrupted, or has its result discarded is for the requester to settle within what the stand-in permits.

### C-87: Cancellation preserves an account of work already finished
Observable: Cancel after at least one step is shown as finished. The task retains that finished work and makes clear what was stopped, including the outcome of any step already in flight.
Source: request

### C-88: A stopping step failure is visible as a recoverable failure
Observable: Send `research: supplier options [fail step 2]`. The first step is recorded as finished, and the second step's first attempt fails. The task shows `Failed` with information about the failure. Later steps are not reported as done while the failed step is outstanding.
Source: existing: provider/README.md, provider/standin.js

### C-89: Restart recovery distinguishes an interrupted task from work that is executing
Observable: Stop the Node service during a task and restart with the same data folder. Already reported finished steps remain available. A task whose execution has ceased appears as `Interrupted` unless it has recovered into a truthful live or terminal state. No step is shown as finished solely because it had started before the stop.
Source: implied: U-14 requires recovery from interruption and an honest account of work
Open: Whether interrupted work resumes automatically on startup or waits for `Retry task` is for the requester to settle.

### C-90: A failed or interrupted task offers `Retry task`
Observable: A task article whose state is `Failed` or `Interrupted` exposes the button `Retry task` for that task. A still-running or already finished task is not a failure or interruption requiring retry.
Source: request

### C-91: Retrying a task continues from recorded progress
Observable: Activate `Retry task` after `[fail step 2]`. The previously finished first step remains recorded once, the retry succeeds at the second step, and the remaining steps can complete. Retrying an interrupted task similarly preserves its recorded finished steps and continues the unfinished work in the same task.
Source: implied: U-14 requires recovering the work, and the stand-in's step retry succeeds on later attempts

### C-92: A task's recovery stays in the originating discussion
Observable: On returning after a failure or interruption, reopen the conversation that requested the task. Its earlier turns remain available and recovery can be followed for the original task.
Source: request

### C-93: `Since you were away` reports the person's task activity upon return
Observable: Return after leaving while tasks were running. In the region named `Since you were away`, completed work is identifiable, tasks still executing are indicated as running, and unresolved failed or interrupted work is called out for attention where present. Activity of other people is absent.
Source: request
Open: What counts as being away and when the app considers an update seen are for the requester to settle.

### C-94: The main screen exposes all applicable named interface elements at 1440 pixels wide
Observable: At a browser viewport width of `1440` pixels, the applicable regions, navigations and controls in the request can be found on the main screen without opening a menu. State-specific forms and controls are available in the states in which they are used.
Source: request

### C-95: Narrow windows keep conversation reading available
Observable: Narrow the window with a conversation open. The transcript is still readable in the main chat view while secondary areas may be folded away.
Source: request
Open: The minimum supported viewport width and which secondary areas fold away are for the requester to settle.

### C-96: Narrow windows keep message composition available
Observable: In the narrow chat view, `Message` and `Send` stay in view so the person can write and submit a turn while reading the conversation.
Source: request

### C-97: The chat's visual presentation supports comfortable reading
Observable: In a discussion with multiple turns and multiline text, the transcript is the visual focus. Readable type, spacing and clear message boundaries let the person follow the speakers and read their replies without crowding or clipping.
Source: request
Open: The visual treatment, including typography and layout details beyond readable, conversation-centered use, is left to the builder by the request.

### C-98: The message composer is visually clear
Observable: On the chat view, the person can distinguish where they write the next turn from the transcript and locate the send action alongside composition.
Source: request

### C-99: Everyday actions are operable by keyboard
Observable: Using the keyboard alone, a person can reach and operate the applicable named controls for entry, setup, bot and conversation selection, composing, saved items, memory, proposals and task recovery. Focus is apparent while moving among controls.
Source: request

### C-100: `npm test` runs `node:test` tests under `test/` for the rules used by the app
Observable: Run `npm test` in the delivered project. It runs the tests under `test/` using Node's test runner, exercises rule modules used by the running application, and exits successfully when those checks pass.
Source: request
