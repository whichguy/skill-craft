# Three deliveries of one request: which is the better feature?

Three builders each delivered the same customer request (below). Each delivery was audited by running it: every
stated requirement, a list of conditions the request leaves unsaid, its tests, its specification and its documents.
Items the audits disagreed on were run again on all three by another person, and every defect an auditor reported
was tried on all three. You have the audits (with those re-runs applied) and the defect table. The deliveries are
labelled X, Y and Z; the labels and their order carry no meaning. You do not have the products and should not guess
at them beyond the audits.

Judge as the person who will run this feature and keep it working: what does each delivery give that the others do
not, and does it matter? Size is not quality: a longer specification, more tests or more code count only through
what the audits show they bought, and count against a delivery where the audits show they cost (requirements the
customer did not ask for, tests that pin one builder's choices, code a maintainer must carry). Count each
consequence once, however many audit lines mention it.

For each pair (X-Y, X-Z, Z-Y):

- `better`: `<letter>-much`, `<letter>-some` (naming the better delivery) or `same`.
- `advantages`: each real advantage of either side, with the audit line or defect id behind it (`ref`) and whom it
  matters to: `requester`, `operator`, `maintainer` or `no one`.
- `lesser_lacks`: what the lesser delivery would need to match the better one, as a list of concrete changes.
- `one_task_closes`: `yes` if one short follow-up task (about an hour of the same builder's work) would close that
  list, else `no`. `yes` when `better` is `same`.
- `why`: three sentences at most.

Answer with one JSON object and nothing else:

```json
{"pairs": [{"pair": "X-Y", "better": "same", "advantages": [{"of": "X", "what": "...", "ref": "U-4", "matters_to": "operator"}], "lesser_lacks": ["..."], "one_task_closes": "yes", "why": "..."}]}
```

## The request

Build and deliver a finished, working chat application that feels like seamless, elegant Grok-style chat, running on this computer. I want to open it, ask for help in ordinary language, and get useful answers that make my work easier.

It is a Node.js app with no npm dependencies. `node server.js` serves it on the port in the PORT environment variable (default 3000), GET / is the app, and everything it keeps lives under the folder named by the DATA_DIR environment variable (default `./data`), so it survives a restart. The assistant's replies come from the stand-in in `provider/` (read `provider/README.md`): use it as it is for every reply and do not change it. The records the assistant may work with are the synthetic ones in `records/` (read `records/README.md`), which also says which person may read which.

I want the conversation to be the center of the experience: polished typography, comfortable reading, clear composition, and replies that explain what matters without overwhelming me. When I ask a follow-up, the bot should understand the conversation, ask a useful clarifying question when needed, and help me reach an answer or finish a task.

I want to name my bots and keep multiple saved conversations, returning to the right bot and discussion without losing my place. I should be able to save reusable instructions and tasks, use them again, and change them when my needs change. I want to inspect what a bot remembers about me, correct mistakes, and ask it to forget something. My information should stay separate from another user's, and each bot's memory should stay separate from my other bots.

Within the synthetic records, I want to ask real questions, receive accurate answers grounded in records I am allowed to read, and follow up naturally. When I ask to create or update something, I want to see the exact proposed changes before deciding. Nothing should be written until I explicitly confirm that proposal. Rejecting or cancelling it should leave the records alone. Repeating an action or reloading at an awkward moment should not accidentally apply it twice, and I should understand what actually happened.

For longer tasks, I want useful work to continue while the app is closed. When I return, I want an honest account of what finished, what is still happening, and anything that needs my attention. I want to steer ongoing work with a follow-up or cancel it, with a clear explanation of what can still be stopped and what has already happened. If something fails or is interrupted, help me recover without guessing or losing the conversation.

Help me get started through guided, recoverable setup that explains what I need without exposing secrets. Make everyday use comfortable on a desktop, in a narrow window, and with the keyboard. Deliver the complete working experience so I can use it confidently.

How people get in. There are no passwords. The first screen offers a button named Continue as <name> for each person in `records/people.json`; after that a button named Switch person brings that screen back. What I see, and what my bots remember, belongs to the person I continued as, and reloading the page keeps me as that person.

How it looks is yours to design. So that a screen reader, and anyone checking the app, can find things, use the accessible names below. At a desktop width (1440 pixels) everything named here is on the main screen without my having to open a menu; in a narrow window you may fold parts away, as long as reading the conversation and writing a message stay in view.

- Setup. When no provider token has been saved, a region named Setup explains what is needed, with a textbox named Provider token and a button named Save token. A token the provider refuses shows an alert and lets me try again. A token in the PROVIDER_TOKEN environment variable counts as saved. Once saved, the token is never shown again, in any page or any response.
- Bots. A navigation named Bots lists my bots as buttons named with each bot's name, with the open one marked as current. A button named New bot, a textbox named Bot name and a button named Save bot name create a bot and open it; a button named Rename bot uses the same textbox and button for the open bot. A person who has never used the app starts with one bot named Assistant.
- Conversations. A navigation named Conversations lists the open bot's conversations as buttons, with the open one marked as current. A button named New conversation starts one.
- The conversation. A region named Conversation holds the messages as articles named Message from <name>, with my name or the bot's name. A textbox named Message and a button named Send write to it; Enter sends and Shift+Enter makes a new line. While a reply is on its way, a status says so. If a reply fails, an alert says so and a button named Retry tries again without sending my message a second time.
- Saved instructions. A region named Saved instructions has textboxes named Instruction name and Instruction text and a button named Save instruction. Each saved one has buttons named Use <name>, Edit <name> and Delete <name>. Using one makes it the open bot's instructions from the next reply on. Edit <name> puts it back into those two textboxes, to change and save again under the same name.
- Saved tasks. A region named Saved tasks has textboxes named Task name and Task request and a button named Save task. Each saved one has buttons named Run <name>, Edit <name> and Delete <name>. Running one sends its request in the open conversation. Edit <name> puts it back into those two textboxes, to change and save again under the same name.
- Memory. A region named Memory lists what the open bot remembers about me as list items, each with buttons named Edit memory and Forget. Editing uses a textbox named Memory text and a button named Save memory.
- Changes. A proposal appears in a region named Proposed changes that states each change exactly (for example `ORD-1001 status: open → closed`), with buttons named Confirm changes and Reject changes. Afterwards a region named Change result says what happened.
- Long tasks. A region named Tasks shows each long task as an article named Task: <title>. It holds a status named Task status that reads Running, Completed, Failed, Cancelled or Interrupted, the steps that have finished, a button named Cancel task while it runs, and a button named Retry task after a failure or an interruption. When I come back after being away, a region named Since you were away tells me what finished, what is still running and what needs my attention.

Cover the rules the app follows in modules it uses, with node:test tests under test/ that `npm test` runs.

## The inventory


## Stated requirements

- **S-1**: The app is a finished, working chat application running on this computer: I can open it, ask for help in ordinary language and get a useful reply.
- **S-2**: It is a Node.js app with no npm dependencies.
- **S-3**: `node server.js` serves the app on the port in the PORT environment variable, and on port 3000 when PORT is unset.
- **S-4**: GET / is the app.
- **S-5**: Everything the app keeps lives under the folder named by the DATA_DIR environment variable (default `./data`).
- **S-6**: What the app keeps survives a restart: bots, conversations, messages, memory, saved instructions, saved tasks, a token saved with Save token, confirmed record changes and long-task results.
- **S-7**: Every assistant reply comes from the stand-in in `provider/`, used as it is (not edited, copied or replaced).
- **S-8**: Every reply text shown is the stand-in's `output.text`, and the app acts on the stand-in's other fields: remember, forget, clarify, proposal, task and steer.
- **S-9**: The stand-in's commands match regardless of capitals, and the first rule that fits the person's last message is the one used.
- **S-10**: The records the assistant may work with are the synthetic ones in `records/`; a person may read, and ask to change, only the records whose readers include that person's id.
- **S-11**: From the starting records, Maya (maya) can use ORD-1001, ORD-1002, ORD-1004, ACC-2001 and ACC-2003; Theo (theo) can use ORD-1001, ORD-1003, ACC-2001 and ACC-2002; Ana (ana) can use ORD-1004, ACC-2001 and ACC-2003.
- **S-12**: `records/people.json` and `records/records.json` are the starting state and stay as they are; the app keeps its own working copy of the records under its data folder, so a confirmed change survives a restart.
- **S-13**: Starting with an empty data folder gives the starting records again.
- **S-14**: A record a person creates is theirs: its `readers` is that person alone, and a new order's `id` is the next free `ORD-` number.
- **S-15**: The conversation is the center of the experience, with polished typography, comfortable reading and clear composition.
- **S-16**: Replies are presented so that they explain what matters without overwhelming me.
- **S-17**: A follow-up is understood from the open conversation: the stand-in receives that conversation's messages, oldest first, ending with the new person message, and no other conversation's messages.
- **S-18**: A reply is given only the open bot's memory of this person, this conversation's history and the records this person may read.
- **S-19**: `what did I ask first` replies `You first asked: "<first person message>".` when this conversation already contains an earlier person message, and `This is the first thing you've asked.` when it does not.
- **S-20**: Any other person message replies `You said: "<text>". (<bot name> has N message(s) from you in this conversation.)`, where <text> is the message with `[fail once]` and `[slow]` removed and the ends trimmed, and N counts the person messages in this conversation including this one.
- **S-21**: The bot asks a useful clarifying question when needed, and my next message is taken as the answer to it (sent with the conversation so far), helping me reach an answer or finish a task.
- **S-22**: I can name my bots.
- **S-23**: I can keep multiple saved conversations for a bot and return to the right bot and discussion, with that discussion's messages still there, without losing my place.
- **S-24**: I can save reusable instructions, use them again and change them.
- **S-25**: I can save reusable tasks, use them again and change them.
- **S-26**: I can inspect what a bot remembers about me.
- **S-27**: I can correct a mistake in what a bot remembers about me.
- **S-28**: Asking a bot to remember something adds it to what that bot remembers about me: `remember that <fact>` replies `I'll remember that <fact>.` and adds that fact.
- **S-29**: Asking a bot to forget something removes it: `forget <fact>` and `forget that <fact>` reply `I've forgotten "<fact>".` and remove that fact from what this bot remembers about me.
- **S-30**: `what do you remember` replies `I remember: <facts joined by "; ">.` when this bot has facts for me, and `I don't remember anything about you yet.` when it has none.
- **S-31**: My information stays separate from another user's: my bots, conversations, messages, memory, saved instructions, saved tasks and long tasks are not shown to or used for another person.
- **S-32**: Each bot's memory stays separate from my other bots.
- **S-33**: What a bot remembers about me is the same in all of that bot's conversations.
- **S-34**: Questions about the records get accurate answers grounded only in records I am allowed to read, and I can follow up naturally.
- **S-35**: `how many orders can you see` replies `I can see N order record(s).` and `how many accounts can you see` replies `I can see N account record(s).`, with N counted only from records that person may read.
- **S-36**: `what is the <field> of <ID>` replies `The <field> of <record id> is <value>.` for a readable record with that field, `<record id> has no <field>.` when it lacks the field, and `I can't see a record called <ID>.` when the person cannot see it; typed ids match without regard to capitals.
- **S-37**: When I ask to create or update something, I see the exact proposed changes before deciding.
- **S-38**: `set the <field> of <ID> to <value>` on a readable record replies `I propose one change: <record id> <field>: <from> → <to>. Confirm to apply it.` and writes nothing; on a record the person cannot see it replies `I can't see a record called <ID>.` and writes nothing.
- **S-39**: `update <ID>` on a readable record replies `Which field of <record id> should I change, and to what value?` and writes nothing; `the <field> to <value>` right after that question produces the same proposal as `set the <field> of <ID> to <value>`.
- **S-40**: `create an order for <customer> totalling <number>` replies `I propose creating one order: customer <customer>, total <number>, status open. Confirm to apply it.` and writes nothing.
- **S-41**: Nothing is written until I explicitly confirm the proposal with Confirm changes.
- **S-42**: After a field change is confirmed, a later question from that person returns the new value, and the record's other fields stay as they were.
- **S-43**: Confirming a create stores one order with that customer, that total and status open; the creator can then read it and another person cannot.
- **S-44**: Rejecting or cancelling a proposal leaves the records alone: a later question still returns the old value, and a rejected create stores nothing.
- **S-45**: Repeating an action, such as a confirm, or reloading at an awkward moment does not apply it twice.
- **S-46**: I am told, and can understand, what actually happened to a proposal.
- **S-47**: `long task: <title>` or `research: <title>` replies `I'll work on "<subject>" in the background and tell you when it is done.` and runs that task's steps in the background, one `runStep` at a time, in order (the subject is the title with bracket markers removed).
- **S-48**: A task title without `[long]` has three steps (`Collect what is known about <subject>`, `Compare the options for <subject>`, `Write the summary of <subject>`); a title containing `[long]` adds `Check part 1 of <subject>` through `Check part 5 of <subject>` before the summary, eight steps in all.
- **S-49**: Each step takes STANDIN_STEP_MS milliseconds (500 unless set), and a completed step's stand-in result is `Done: <step text>`.
- **S-50**: Longer tasks continue doing useful work while the app is closed.
- **S-51**: When I return, I get an honest account of what finished, what is still happening and anything that needs my attention.
- **S-52**: I can steer ongoing work with a follow-up: `add step: <text>` replies `I'll add "<text>" to the task that is running.` and adds that step at the end of my running task in this conversation.
- **S-53**: The conversation stays usable while a task runs: I can send a follow-up and get its reply while Task status reads Running.
- **S-54**: I can cancel ongoing work, with a clear explanation of what can still be stopped and what has already happened.
- **S-55**: If something fails or is interrupted, the app helps me recover without guessing (a step is not shown as finished unless it finished) or losing the conversation.
- **S-56**: A task title containing `[fail step 2]` fails its second step on the first attempt: Task status reads Failed, the steps that had already finished stay recorded, and the conversation remains.
- **S-57**: Setup is guided and recoverable and explains what I need without exposing secrets.
- **S-58**: Everyday use is comfortable on a desktop, in a narrow window and with the keyboard: the named textboxes and buttons can be reached and used from the keyboard.
- **S-59**: There are no passwords: the first screen offers a button named Continue as <name> for each person in `records/people.json` (Continue as Maya, Continue as Theo, Continue as Ana).
- **S-60**: After continuing, a button named Switch person brings the first screen back.
- **S-61**: What I see, and what my bots remember, belongs to the person I continued as, including after Switch person and continuing back as the first person.
- **S-62**: Reloading the page keeps me as the person I continued as.
- **S-63**: At a desktop width of 1440 pixels everything named in the request is on the main screen without opening a menu, including Setup, Proposed changes, Change result and Since you were away when they apply.
- **S-64**: In a narrow window parts may be folded away, but reading the conversation and writing a message stay in view.
- **S-65**: When no provider token has been saved, a region named Setup explains what is needed without exposing a token, with a textbox named Provider token and a button named Save token.
- **S-66**: The provider accepts a token that is the text `sk-local-` followed by at least twelve letters or digits, and refuses a missing or other token.
- **S-67**: A token the provider refuses shows an alert and lets me try again from Setup.
- **S-68**: Saving an accepted token dismisses Setup, and later replies use it.
- **S-69**: A token in the PROVIDER_TOKEN environment variable counts as saved: Setup is not shown, the token is not shown, and replies work.
- **S-70**: Once saved, the token is never shown again, in any page or any response, including after a restart.
- **S-71**: A navigation named Bots lists my bots as buttons named with each bot's name, with the open one marked as current.
- **S-72**: A button named New bot, a textbox named Bot name and a button named Save bot name create a bot and open it, and my existing bots remain.
- **S-73**: A button named Rename bot uses the Bot name textbox and Save bot name button to rename the open bot, which is then listed under the new name.
- **S-74**: A person who has never used the app starts with one bot named Assistant.
- **S-75**: A navigation named Conversations lists the open bot's conversations as buttons, with the open one marked as current.
- **S-76**: A button named New conversation starts a conversation.
- **S-77**: A region named Conversation holds the messages as articles named Message from <name>, with my name or the bot's name, each showing that message.
- **S-78**: A textbox named Message and a button named Send write my message into the open conversation.
- **S-79**: Enter in the Message textbox sends the message.
- **S-80**: Shift+Enter in the Message textbox makes a new line and does not send.
- **S-81**: While a reply is on its way, a status says so; a message containing `[slow]` waits STANDIN_SLOW_MS milliseconds (1500 unless set) before the reply, and the status shows during that wait.
- **S-82**: If a reply fails, an alert says so.
- **S-83**: A button named Retry tries the failed reply again without adding my message a second time; a message containing `[fail once]` fails on its first attempt and succeeds on Retry.
- **S-84**: A region named Saved instructions has textboxes named Instruction name and Instruction text and a button named Save instruction; saving adds that named instruction.
- **S-85**: Each saved instruction has buttons named Use <name>, Edit <name> and Delete <name>.
- **S-86**: Use <name> makes that saved text the open bot's instructions from the next reply on, including in that bot's other conversations, and does not change another bot's instructions.
- **S-87**: With no instructions, `who are you` replies `I am <bot name>. I have no special instructions.`; after instructions are set, it replies `I am <bot name>. My instructions: <instructions>`.
- **S-88**: Edit <name> on an instruction puts it back into the Instruction name and Instruction text textboxes, to change and save again under the same name.
- **S-89**: Delete <name> on an instruction removes that saved instruction.
- **S-90**: A region named Saved tasks has textboxes named Task name and Task request and a button named Save task; saving adds that named task.
- **S-91**: Each saved task has buttons named Run <name>, Edit <name> and Delete <name>.
- **S-92**: Run <name> sends that task's request in the open conversation as a message from me, and the bot's reply appears there.
- **S-93**: Edit <name> on a task puts it back into the Task name and Task request textboxes, to change and save again under the same name.
- **S-94**: Delete <name> on a task removes that saved task.
- **S-95**: A region named Memory lists what the open bot remembers about me as list items, each showing that fact.
- **S-96**: Each memory list item has buttons named Edit memory and Forget.
- **S-97**: Forget removes that item from what the open bot remembers about me.
- **S-98**: Editing a memory uses a textbox named Memory text and a button named Save memory, and Save memory updates that item to the saved text.
- **S-99**: A proposal appears in a region named Proposed changes that states each change exactly (for example `ORD-1001 status: open → closed`), with buttons named Confirm changes and Reject changes.
- **S-100**: After a proposal is decided, a region named Change result says what happened.
- **S-101**: A region named Tasks shows each long task as an article named Task: <title>, using the stand-in's task title.
- **S-102**: Each task article holds a status named Task status that reads Running, Completed, Failed, Cancelled or Interrupted.
- **S-103**: Each task article shows the steps that have finished.
- **S-104**: Each task article has a button named Cancel task while it runs.
- **S-105**: When every step has finished successfully, Task status reads Completed.
- **S-106**: Each task article has a button named Retry task after a failure or an interruption.
- **S-107**: When I come back after being away, a region named Since you were away tells me what finished, what is still running and what needs my attention.
- **S-108**: The rules the app follows are in modules it uses, covered by node:test tests under test/ that `npm test` runs.

## Conditions the request leaves unsaid

- **U-1**: Whether the current person is held per browser, per tab, or as one person for the whole server when two clients are open at once.
  - Probe: Save a valid provider token. In browser A, Continue as Maya and send `hello from Maya`. In a second browser or private window, Continue as Theo and send `hello from Theo`. Reload each. Read which person each browser shows, which messages each conversation holds, and what a further send from browser A does after Theo has continued in browser B. Repeat with two tabs of the same browser.
  - Outcomes that would be acceptable: Each browser keeps its own person; or all tabs in one browser share one person while a private window can be another; or the server has one current person and the latest Continue as changes it for every client. In every case personal data stays with the person a client is acting as.
- **U-2**: Whether the person's identity is checked by the server on every request, or only chosen in the page.
  - Probe: As Maya, note the id of a conversation, a memory item and a pending proposal from the page's network requests. Switch person to Ana. Replay the requests for Maya's conversation and memory, and a confirm of Maya's proposal, from Ana's session. Read the responses and ask Maya's question about the record afterwards.
  - Outcomes that would be acceptable: Refused (for example 403 or 404) or empty; any answer that never returns or changes another person's data.
- **U-3**: What else is on the first screen besides the Continue as buttons, whether a token must be saved before a person can continue, and who a reload belongs to while the Continue as screen is up.
  - Probe: With no token saved and an empty data folder, open GET /. Note whether Setup and the chat controls are present before Continue as. Save `sk-local-abcdefghijkl`, then see whether the Continue as buttons are still required. Continue as Maya, click Switch person, and reload. See which screen returns and whether a message can be sent before choosing again.
  - Outcomes that would be acceptable: The first screen is only the person buttons (plus Setup when no token is saved), or the main controls are visible but inert until a person continues. Saving a token and choosing a person may happen in either order. After Switch person, a reload may stay on the chooser or return to the person who last continued. Data already stored for a person stays that person's.
- **U-5**: Which token is used when both PROVIDER_TOKEN and a saved token exist, and whether a token from the environment is copied into the data folder.
  - Probe: Run with PROVIDER_TOKEN=`sk-local-abcdefghijkl` and confirm Setup is absent and a reply works. Save a different accepted token through Setup if the screen allows it and send `who are you`. Restart once with the variable still set and once with it unset; each time open GET / and send a message.
  - Outcomes that would be acceptable: Either source may win, if stated. The environment token may be used only while set, or kept in the data folder. A token is never shown in a page or response.
- **U-6**: What happens when the token in use is refused: an invalid PROVIDER_TOKEN at start, or a saved token that stops being accepted during use.
  - Probe: Start with PROVIDER_TOKEN=`not-a-token` and open GET /. Then start with PROVIDER_TOKEN=`sk-local-short`, Continue as Maya and send `hello`. Read the alert, whether Setup is offered, and whether a new accepted token can be saved and the message retried.
  - Outcomes that would be acceptable: An invalid environment token is treated as unsaved and Setup is shown, or the refusal alert appears with a route back to Setup; any route that lets the person recover without exposing the token.
- **U-7**: Whether the token is stored in plain text under DATA_DIR and whether it leaks into logs or error messages.
  - Probe: Save a token. Search the server output, every API response and the files under DATA_DIR for the token text. Trigger a provider error (for example with `hello [fail once]`) and read the alert and the server output.
  - Outcomes that would be acceptable: Stored on disk is fine if never sent to the browser or logged; plain or obscured storage, if stated.
- **U-8**: Whether Assistant, a bot made with New bot, or a conversation made with New conversation starts open and empty, and what a brand-new bot contains.
  - Probe: With an empty data folder, Continue as Ana and read the Conversations navigation, the Conversation region, and whether Send works before New conversation. Ask `who are you` and `what do you remember`. Click New bot, save the name Clerk, and look at Clerk's conversations, Memory and `who are you`. Click New conversation and see which conversation is marked current.
  - Outcomes that would be acceptable: A new person or bot already has one empty open conversation; or Send creates the first conversation; or New conversation is required first. A new bot has no memories and no instructions, or a generic welcome that is not another bot's. New conversation may become the open one or leave the previous one open.
- **U-9**: How empty, blank, unusually long or duplicate bot names are handled, and whether bots that share a name can be told apart.
  - Probe: Click New bot, leave Bot name empty and click Save bot name. Then create a second bot named Assistant, give each Assistant a different discussion, switch away, and inspect the Bots navigation visually and by accessible name. Try a 300-character name.
  - Outcomes that would be acceptable: Blank names refused with a message; duplicates refused, or allowed with each bot distinguishable before selecting it; long names refused, accepted intact or shortened only for display.
- **U-11**: How conversation buttons are named and ordered, so that conversations, including empty ones and ones with similar openings, can be told apart before opening them.
  - Probe: In one bot click New conversation twice and read the accessible names in the Conversations navigation. Then start two conversations whose first messages share a long opening and end in different customer names. Return to Conversations and read the button names and order, visually and by accessible name.
  - Outcomes that would be acceptable: Named by first message, time, a title or a generated label, in any order, as long as each entry can be identified before selecting it and the open one is marked current.
- **U-13**: Which bot and conversation are open after reloading, after Switch person and back, after a new visit and after a server restart, and whether an unsent draft and the scroll position survive.
  - Probe: As Maya open bot Second, its second conversation, scroll up, and type an unsent message. Reload. Switch person to Theo and back to Maya. Close the browser and open the app again. Restart the server and reload. Each time read the open bot, open conversation, the Message box and the scroll position.
  - Outcomes that would be acceptable: The last-open bot and conversation restored per person, or a stated default conversation when none is restored; the draft and scroll position kept or not, as long as the place is.
- **U-14**: Whether saved instructions and saved tasks belong to the person (shared by all their bots) or to one bot.
  - Probe: As Maya, on Assistant, save instruction Tone = `Be brief` and task Ping = `hello`. Create and open a bot named Other and look at Saved instructions and Saved tasks. If listed, Use Tone and Run Ping, switch back to Assistant and ask `who are you`. Then Switch person, Continue as Theo and look again.
  - Outcomes that would be acceptable: One library per person shown for every bot, with Use and Run affecting only the open bot and conversation; or a separate library per bot. Never visible to another person.
- **U-15**: What Save instruction or Save task does when the name already exists and Edit was not used, or when the name or text is empty.
  - Probe: Save instruction A = `x`; save instruction A = `y` without pressing Edit; count the Use A buttons and check with `who are you` after Use A which text applies. Try to save with an empty name and with empty text. Repeat for Save task.
  - Outcomes that would be acceptable: Overwrite with a notice, refuse with a message, or ask; empty fields refused. Not two entries with one name.
- **U-16**: What happens when Edit <name> is used and the Instruction name or Task name is changed before saving.
  - Probe: Save instruction Tone = `Be brief`. Click Edit Tone, change Instruction name to Style, and save. Read the Saved instructions buttons. Repeat for a saved task.
  - Outcomes that would be acceptable: Saving keeps the original name, renames the same item, or creates a second item, as long as Use, Edit, Delete and Run point at the items the person can see.
- **U-17**: What happens to a bot's instructions when the saved instruction it uses is later edited or deleted.
  - Probe: Save instruction Tone = `Be formal`, click Use Tone, send `who are you`. Edit Tone to `Be casual`, save, and send `who are you` without using Use. Then Delete Tone and send `who are you` again.
  - Outcomes that would be acceptable: The bot follows the saved instruction (an edit updates, a delete clears), or keeps the copy taken at Use until another Use; either, if what the bot now uses is visible or explained.
- **U-20**: What happens if I send again, switch conversation, reload, switch person, or lose the acknowledgement while a reply is still on its way.
  - Probe: Send `hello [slow]` and press Enter again at once. Send another `[slow]` message and switch to a different conversation, then back. Send one and reload during the wait. As Maya send `set the status of ORD-1001 to closed [slow]` and Switch person to Theo before it returns, then back to Maya. Send `long task: alpha [slow]`, close the page before it acknowledges, reopen, and try sending the same text again.
  - Outcomes that would be acceptable: Send disabled while pending, or messages queued in order. The person's message is stored once and its reply lands in its own conversation for its own person, kept after reload; Theo sees nothing of Maya's reply or proposal. A received turn is shown as received and is not started twice by recovery, while a deliberate new send still can be.
- **U-21**: What Retry does after a reload or a server restart, what happens to a failed message if I send a new one instead, and whether a reply interrupted by stopping the server is retried automatically.
  - Probe: Send `hello [fail once]`; at the alert, reload, then click Retry. Repeat with a server restart before Retry. Separately, at the alert send `next` instead of Retry and read the messages. Send `hello [slow]` and stop the server during the wait, start it and reopen.
  - Outcomes that would be acceptable: Retry still offered and succeeds, or the failed message is marked failed with a way to resend; the person can tell that the message was received and that its reply failed; a new message is accepted or the person is told to retry first; an interrupted reply is retried automatically or waits for Retry. Never duplicated, never lost.
- **U-22**: Whether `[fail once]` and `[slow]` remain in the stored person message.
  - Probe: Send `hello [fail once]`, Retry it, then send `what did I ask first`. Compare the quotation with the Message article.
  - Outcomes that would be acceptable: The stored message may keep or drop the markers, as long as the first attempt still fails and Retry can succeed.
- **U-23**: Whether a memory forget that matches nothing, or a repeated remember, is reported honestly and kept tidy.
  - Probe: Send `remember that likes tea` twice and open Memory. Send `forget tea` and `forget coffee`, read the replies and the Memory list. Then send `forget that likes tea`.
  - Outcomes that would be acceptable: Duplicates merged or shown; a non-matching forget flagged, or matched loosely and shown; the Memory list is the truth; an exact forget removes the fact.
- **U-25**: Whether Memory text starts filled with the fact being edited.
  - Probe: Send `remember that likes tea`. Click Edit memory and read Memory text before typing. Save a one-word change and read the Memory list.
  - Outcomes that would be acceptable: Memory text starts with the current fact, or empty, as long as Save memory updates the item being edited.
- **U-26**: Whether management actions (Save instruction, Use, Edit, Delete, Save task, Rename, Save memory, Forget) add messages to the conversation.
  - Probe: Click Save instruction, Use, Delete, Save task, Rename bot, Save memory and Forget in turn, and after each see whether a new Message article appeared; then send `what did I ask first`.
  - Outcomes that would be acceptable: Management actions other than Run add no message, or add a note; Run, Send and memory phrases typed into Message do write to the conversation.
- **U-27**: Whether Memory and task progress update while the page stays open.
  - Probe: Send `remember that likes tea` and, without reloading, read Memory. Start `long task: alpha` and, without reloading, watch Task status and the finished steps until they stop changing.
  - Outcomes that would be acceptable: They update on their own while the page is open, or on reload, if stated.
- **U-29**: Whether a proposal that changes `readers`, `id`, `type` or `owner` is offered and applied.
  - Probe: As Maya send `set the readers of ORD-1001 to ana` and confirm; send `set the id of ORD-1004 to ORD-9999` and confirm; check which records Maya, Theo and Ana can read.
  - Outcomes that would be acceptable: Refused with an explanation, or allowed only with a clear warning; never silently changing who may read a record or breaking a record.
- **U-30**: Whether a proposed value is validated (a word into a number field, a field the record does not have, an unknown status, a decimal amount), and whether the person is told how to correct it.
  - Probe: As Maya send `set the total of ORD-1001 to banana`, `set the colour of ORD-1001 to red` and `create an order for Acme totalling 42.50`; confirm whatever is offered; ask `what is the total of ORD-1001`. Then send a corrected request in the same conversation.
  - Outcomes that would be acceptable: Refuse or warn before confirm, saying what to correct, with the corrected request working in the same conversation; or apply exactly what was shown. Either if the proposal states the exact change.
- **U-31**: How long an undecided proposal lasts (reload, restart, switching conversation, later messages), whether an older proposal can be confirmed after a newer one, which gestures confirm or cancel it, and what the controls show after a decision.
  - Probe: As Maya send `set the status of ORD-1001 to closed`. Press Enter in Message, reload, restart the server and reload; read whether the status changed and the proposal remains. Switch to another conversation and back. Send a second set command before deciding the first; Reject one, then try Confirm changes on each, and click Confirm again after a decision. Read Change result and ask `what is the status of ORD-1001`.
  - Outcomes that would be acceptable: Kept and decidable, or expired or dropped with a clear message; only Confirm changes confirms, or Enter too; afterwards the buttons disappear, are disabled, or a later click writes nothing. Never applied without a confirm and never twice.
- **U-32**: How a proposed create is worded before confirm, including whether its order id is previewed.
  - Probe: As Maya send `create an order for Northwind totalling 40` and read Proposed changes. Before confirming, ask `how many orders can you see`. Confirm and compare any previewed id with the stored one.
  - Outcomes that would be acceptable: The stand-in's sentence, or customer, total and status open listed, with or without a preview id; a previewed id is the one stored or marked provisional. Nothing stored before Confirm changes.
- **U-33**: What Confirm does when the record no longer has the proposed `from` value (another reader changed it, or an earlier proposal on the same field was confirmed).
  - Probe: As Maya send `set the status of ORD-1001 to closed` and do not confirm. In another browser as Theo, or in another of Maya's conversations, send `set the status of ORD-1001 to shipped` and confirm. Back in the first, click Confirm changes; read Change result and ask `what is the status of ORD-1001`.
  - Outcomes that would be acceptable: Refused as stale with a new proposal offered, or applied with Change result stating the actual from-value; not a silent overwrite reported as 'open → closed'. The same confirm never writes twice.
- **U-34**: How the next free ORD- number is chosen when two create proposals are pending at once or two people create orders, and what 'next free' means.
  - Probe: As Maya send `create an order for North totalling 10` and, without confirming, as Ana send `create an order for South totalling 20`; confirm both. Ask `what is the customer of ORD-1005` and `ORD-1006` as each person.
  - Outcomes that would be acceptable: Assigned at confirm time or reserved at proposal; one more than the highest number or the lowest unused; distinct ids either way.
- **U-35**: Whether the Change result stays visible after reload and how confirmed changes are recorded in the conversation.
  - Probe: Confirm a proposal and reload at once; click Confirm again if still offered; look for the Change result and the conversation's record of it.
  - Outcomes that would be acceptable: Result kept in the conversation or in the region; any persistent, honest account.
- **U-36**: Whether a confirmed change to a record another person may also read is visible to that other person.
  - Probe: As Maya send `set the status of ORD-1001 to closed`, Confirm changes, ask `what is the status of ORD-1001`. Switch person, Continue as Theo, ask the same. Restart the server and ask Theo again.
  - Outcomes that would be acceptable: One working copy, so Theo sees closed, or a copy per person, so Theo sees open. The starting files stay unchanged and a person still cannot read a record that does not list them.
- **U-37**: Which long tasks the Tasks region shows: the open conversation's, the open bot's, or all of the person's.
  - Probe: As Maya start `long task: report [long]` in conversation 1; open conversation 2 and another bot; look at Tasks; Switch person to Theo and look again.
  - Outcomes that would be acceptable: All of the person's tasks, or the conversation's or bot's with a way to reach the others; never another person's.
- **U-38**: What happens when a second long task is started while one is running.
  - Probe: In one conversation send `long task: alpha [long]` and, before it completes, `long task: beta`. Read the reply and the Tasks region until both end.
  - Outcomes that would be acceptable: Refused, queued, or run alongside the first, as long as Tasks shows what is happening.
- **U-39**: What `add step:` does when no task is running in the conversation, or when several are (including several with the same title), and whether the feedback identifies which task received the step.
  - Probe: In a conversation with no running task send `add step: double-check` and read the reply and Tasks. Then start two long tasks with the same title in one conversation and send `add step: extra`; read both task articles and the feedback, visually and by accessible name.
  - Outcomes that would be acceptable: With none running, say there is nothing to add to, or start a one-step task; with several, add to the latest or ask which, and the feedback identifies the task that got the step. Never claim an addition that did not happen.
- **U-40**: Whether a finished, failed or cancelled task leaves a message in its conversation.
  - Probe: Start `long task: notes` and wait for Completed; read the Conversation region; reload; then ask a follow-up.
  - Outcomes that would be acceptable: A bot message with the result, or the result only in the task article; either if findable after reload.
- **U-41**: What happens to a running task when the server stops and starts again (mark it Interrupted, resume it, or both), and how a step whose completion was not recorded is treated.
  - Probe: Start `long task: audit [long]`. Close the browser for longer than eight step intervals, reopen and read Task status. Start another; after two steps finish, stop the server mid-step; start it again; reload and read Task status, the finished steps, Since you were away, whether Retry task is present and whether it continues on its own.
  - Outcomes that would be acceptable: Interrupted with Retry task, or resumed automatically from the next unfinished step; finished steps kept, and a step that did not finish not shown as finished or silently counted.
- **U-42**: Whether Retry task resumes at the failed step or starts the task over.
  - Probe: Start `long task: plan [fail step 2]`; wait for Failed; click Retry task; read the step list until Completed and count the entries for step 1.
  - Outcomes that would be acceptable: Resume at the failed step, or rerun all with the list kept clear, as long as the failed step can succeed on a later attempt.
- **U-43**: What Cancel task does to a step already in progress, whether it asks first, and how the account separates 'already happened' from 'stopped'.
  - Probe: Run with STANDIN_STEP_MS=3000 and start `long task: big [long]`; click Cancel task mid-step; read Task status, finished steps and the explanation; wait a few seconds and read again.
  - Outcomes that would be acceptable: The in-flight step finishes and is listed and then the task stops, or it is discarded and said so; cancel may stop at once or ask first; status ends Cancelled and stays so.
- **U-44**: What counts as 'being away' for the Since you were away region, which events it reports, and when reported items stop appearing.
  - Probe: As Maya start `long task: crates [fail step 2]` and `long task: alpha`, close the tab, wait until both end, reopen; read Since you were away; reload again. Reload right after a send with nothing running, and while a proposal waits. Switch person to Ana and check it shows only Ana's work.
  - Outcomes that would be acceptable: Since the person's last visit, or only when something changed; dismissed on reading or after a reload; needing attention may include failed or interrupted tasks and waiting proposals. Consistent with Task status, only the person's own, never inventing work.
- **U-45**: Which parts fold away in a narrow window, how a folded part is reached again, and which narrow widths are supported.
  - Probe: Narrow the window step by step to 375 pixels. At each width read whether Bots, Conversations, Saved instructions, Saved tasks, Memory and Tasks can be reached and by which control, and that the conversation and Message stay in view. Widen to 1440 pixels and see them on the main screen.
  - Outcomes that would be acceptable: A disclosure or menu opens folded regions, or scrolling reaches them, or they return only when wide; any stated set of widths. At 1440 pixels they are on the main screen without a menu.
- **U-46**: What the app does when DATA_DIR is missing, unwritable, or holds damaged or unexpected data at start.
  - Probe: Start with DATA_DIR pointing to a folder that does not exist, then to one that cannot be written. Then put invalid JSON, or valid JSON of an unexpected shape, in one of the app's data files and start again. Each time read the process output and the page, and check the data files and `records/` files afterwards.
  - Outcomes that would be acceptable: A missing folder created and served; otherwise refuse to start, or start and report the problem, with an actionable recovery step; damaged data kept for recovery, not overwritten or silently replaced by seeded records.
- **U-49**: Whether the capitalization of field names in record requests keeps their meaning.
  - Probe: As Maya send `what is the STATUS of ORD-1001` and `what is the status of ORD-1001`; then `set the Status of ORD-1001 to closed` and `set the status of ORD-1001 to closed`, rejecting each. Compare replies and previews; repeat as Ana on ORD-1001.
  - Outcomes that would be acceptable: The same value and the same exact preview for each capitalization, with reader rules still applied; or a clear message that the field was not recognized. Never a different field or a new field silently.
- **U-50**: Whether a lookup or change keeps the record identifier the person typed (for example ORD-1001A while ORD-1001 exists).
  - Probe: As Maya send `what is the status of ORD-1001A` and `set the status of ORD-1001A to closed`; then `what is the status of ORD-1001`.
  - Outcomes that would be acceptable: The reply says ORD-1001A cannot be used or found and how to correct it; ORD-1001 itself still answers. Never ORD-1001's status presented as ORD-1001A's.
- **U-54**: What happens when storage writes fail while the app is open: whether the outcome of the save (or of a reply) is reported truthfully and recoverable.
  - Probe: With the app open, make DATA_DIR read-only. Save an instruction, send a message and confirm a proposal. Read what the page says. Restore write access, restart with the same folder, and see what was saved.
  - Outcomes that would be acceptable: A clear storage error with a recovery step, nothing reported as saved that was not; after recovery earlier work is present and the person can tell whether the attempted save happened; no reply left pending forever.
- **U-57**: Whether one unexpected failure in background work takes down the whole app.
  - Probe: Start a long task that fails (`long task: crates [fail step 2]`) and, separately, provoke a storage error during a task step (make DATA_DIR read-only mid-task); then try to read conversations, send a message and use other tasks.
  - Outcomes that would be acceptable: The failure is reported on the affected item and the rest stays usable; or the app enters a clearly reported read-only or unavailable mode with a recovery step.
- **U-58**: Where keyboard focus lands after an action such as Confirm changes, Reject changes or Send, especially when several proposals are on screen.
  - Probe: Produce two proposals in view. Using only the keyboard, Reject one and read which control has focus; press Enter and see what happens. Repeat after Send and after Save memory.
  - Outcomes that would be acceptable: Focus moves to a sensible nearby control or the result, never onto another proposal's Confirm changes.
- **U-60**: Whether unexpected server errors are shown honestly to the person and recorded for the operator.
  - Probe: Provoke an unexpected error (for example a malformed request body to a message or confirm endpoint, or a damaged data file during use); read the page's message and the server output.
  - Outcomes that would be acceptable: The page says the action failed and what to try; the server output records the error without exposing the token.

## The defect table (each defect with what each delivery did when it was tried)

- **D-1** (medium) Keyboard Confirm/Reject moves focus onto the next proposal's same-named button, so a second Enter decides another proposal. Expected: Focus moves to the Change result or the composer, never onto another proposal's decision button; the second proposal stays pending. — X: present; Y: absent; Z: absent
- **D-2** (medium) A capitalised field name in a change request creates a second field instead of changing the existing one. Expected: Same field and same preview regardless of capitals, or a message that Status is not a field of ORD-1001. — X: present; Y: absent; Z: absent
- **D-3** (medium) Conversations cannot be told apart before opening: empty ones and ones with the same opening share a name. Expected: Each conversation identifiable before selecting it (distinct label, time or number). — X: present; Y: absent; Z: present
- **D-4** (medium) A forget that matches no remembered fact is reported as done. Expected: The person is told nothing matched (as for add step with no task), or a loose match is applied and shown; the reply should not claim a forget that did not happen. — X: present; Y: present; Z: present
- **D-5** (medium) After a storage write failure a pending reply stays pending and blocks the conversation until restart. Expected: The reply is marked failed (or retried) once it cannot be saved, with a storage error the person can act on; never left pending. — X: present; Y: absent; Z: absent
- **D-6** (low) A storage failure during a long task leaves the task showing Running with no progress until restart. Expected: The task is reported as Failed or Interrupted with Retry task once progress cannot be saved. — X: present; Y: absent; Z: absent
- **D-7** (medium) After a refused rename the instruction form stays silently bound to the edited entry, so the next new instruction replaces it. Expected: Either the edit is visibly in progress and can be cancelled, or a new name after a failed edit saves a new entry; no saved entry silently lost. — X: present; Y: absent; Z: absent
- **D-8** (low) Duplicate bot names are accepted but cannot be told apart. Expected: Duplicates refused, or each bot distinguishable before selecting it. — X: present; Y: absent; Z: present
- **D-9** (low) Saving an instruction or task under an existing name silently overwrites it. Expected: Overwrite with a notice, refuse, or ask. — X: present; Y: absent; Z: absent
- **D-10** (low) Damaged or unreadable data folder crashes the server at start with a raw stack trace. Expected: Refuse to start with a plain message naming the file and a recovery step, keeping the damaged file. — X: present; Y: absent; Z: absent
- **D-11** (low) A question about ORD-1001A is answered with ORD-1001's value. Expected: A reply that ORD-1001A cannot be found, with how to correct it. — X: present; Y: absent; Z: present
- **D-12** (low) Unexpected server errors and request-time storage failures are not recorded in the server output. Expected: The operator's output records the error (without the token). — X: present; Y: present; Z: present
- **D-13** (low) Step feedback does not identify which of two same-titled tasks received it. Expected: Feedback that identifies the task that got the step. — X: present; Y: absent; Z: present
- **D-14** (low) Since you were away shows nothing when returning in a browser without the app's stored baseline. Expected: On return the person is told what finished (beta) and what needs attention (crates Failed), regardless of browser, or at least the failed task flagged. — X: absent; Y: present; Z: present

## Audit of delivery X

```json
{
 "code": "X",
 "shares": 3,
 "stated": [
  {
   "id": "S-1",
   "built": "yes",
   "observed": true,
   "evidence": "Playwright headless at 1440x900 against PORT=4731 DATA_DIR=run-data/a: Continue as Maya, saved token in Setup, typed \"Can you help me plan my week?\" and clicked Send; an article \"Message from Assistant\" appeared with the stand-in reply \"You said: \\\"Can you help me plan my week?\\\". (Assistant has 1 message(s) from you in this conversation.)\". Record questions, memory, proposals and tasks all answered in the same page.",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-2",
   "built": "yes",
   "observed": true,
   "evidence": "package.json identical to the base (no dependencies); no node_modules folder; grep of require() in server.js, lib/*.js, test/*.js finds only node: built-ins, ./lib, ../provider/standin and ../records/*.json; the app started and ran with plain node.",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-3",
   "built": "yes",
   "observed": true,
   "evidence": "With PORT and DATA_DIR unset, `node server.js` printed \"Stillpoint is ready at http://localhost:3000\" and curl http://127.0.0.1:3000/ returned 200; with PORT=4731, 4732, 4733 it served on those ports (curl /api/state returned the people list).",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-4",
   "built": "yes",
   "observed": true,
   "evidence": "curl -i http://127.0.0.1:3000/ returned 200 text/html with the app page (<!doctype html>, Stillpoint); in the browser GET / showed the Continue as buttons and then the workspace.",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-5",
   "built": "yes",
   "observed": true,
   "evidence": "Default run (no DATA_DIR) created ./data/workspace.json in the working directory (ls data: workspace.json, mode 600). Runs with DATA_DIR=run-data/a, run-data/b, run-data/c each wrote only run-data/<x>/workspace.json; find of files changed in the work copy outside run-data found nothing changed (lib files identical to the original by diff); records/ and provider/ unchanged by diff. Only client conveniences (theme, last-seen time for Since you were away) live in browser localStorage.",
   "spec": "stated",
   "proved": "passes",
   "proved_by": "server.js createServer default changed from `dataDir = process.env.DATA_DIR || './data'` to `dataDir = './data'`; probe: PORT=4734 DATA_DIR=run-data/s5 node server.js served but run-data/s5 was never created and ./data/workspace.json was written instead; npm test still 8 pass 0 fail. Edit undone (diff against the original clean) and the suite back to 8 pass."
  },
  {
   "id": "S-6",
   "built": "yes",
   "observed": true,
   "evidence": "On server A (token saved via Save token, no PROVIDER_TOKEN) I snapshotted Maya's state (2 bots Assistant/Ledger, 5 conversations with message counts, memory \"works in Porto\", instruction Tone=Be very brief in use, saved task Count, proposals rejected/applied, tasks report Completed 8, crates Failed 1, big Cancelled 4), killed the process by pid, restarted with the same DATA_DIR and no PROVIDER_TOKEN: the snapshot was byte-identical, configured=true (token kept), and \"what is the status of ORD-1001\" -> \"The status of ORD-1001 is closed.\" and \"what is the customer of ORD-1005\" -> \"The customer of ORD-1005 is Doubleclick.\" (confirmed changes kept).",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-7",
   "built": "yes",
   "observed": true,
   "evidence": "lib/workspace.js requires ../provider/standin and calls respond/runStep; provider/ is identical to base/provider by diff after all runs; reply texts and task step texts observed match the stand-in rules exactly (e.g. \"Done: Collect what is known about crates\").",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-8",
   "built": "yes",
   "observed": true,
   "evidence": "Observed each field acted on: remember (\"remember that likes tea\" -> fact listed in Memory), forget (\"forget prefers email\" -> memory []), clarify (\"update ORD-1004\" then \"the status to closed\" -> proposal ORD-1004 status: open -> closed), proposal (Proposed changes region with exact change), task (\"long task: crates [long]\" ran 8 steps), steer (\"add step: double-check totals\" appended and ran as step 9). Shown reply texts equal the stand-in output.text in every probe.",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-9",
   "built": "yes",
   "observed": true,
   "evidence": "\"WHAT IS THE STATUS OF ord-1001\" was handled by the lookup rule (stand-in reply \"ORD-1001 has no STATUS.\" since the field name is used as typed); \"What Do You Remember\" -> \"I remember: what do you remember.\"; \"FORGET THAT what do you remember\" -> \"I've forgotten \\\"what do you remember\\\".\"; \"remember that what do you remember\" used the remember rule (first rule) -> \"I'll remember that what do you remember.\" The app passes the message unchanged to the stand-in.",
   "spec": "absent",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-10",
   "built": "yes",
   "observed": true,
   "evidence": "Per person \"what is the type of <ID>\" for all 7 records: each person got a value only for records listing them and \"I can't see a record called <ID>.\" otherwise. Changes: as Ana \"set the status of ORD-1002 to closed\" -> \"I can't see a record called ORD-1002.\" with 0 proposals, and \"update ORD-1003\" -> \"I can't see a record called ORD-1003.\"; Maya still read ORD-1002 status shipped.",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-11",
   "built": "yes",
   "observed": true,
   "evidence": "HTTP client (cookie per person) against PORT=4732 DATA_DIR=run-data/b PROVIDER_TOKEN=sk-local-abcdefghijkl: Maya readable ORD-1001, ORD-1002, ORD-1004, ACC-2001, ACC-2003 (3 orders, 2 accounts); Theo ORD-1001, ORD-1003, ACC-2001, ACC-2002 (2 orders, 2 accounts); Ana ORD-1004, ACC-2001, ACC-2003 (1 order, 2 accounts); all others \"I can't see a record called <ID>.\"",
   "spec": "absent",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-12",
   "built": "yes",
   "observed": true,
   "evidence": "records/people.json and records/records.json unchanged by diff against base after confirmed edits and creates; the working copy is the \"records\" array inside DATA_DIR/workspace.json; ORD-1001 closed and ORD-1005 created survived a restart (see S-6).",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-13",
   "built": "yes",
   "observed": true,
   "evidence": "Server C on a new empty DATA_DIR=run-data/c while server A's copy had ORD-1001 closed: Maya \"what is the status of ORD-1001\" -> \"The status of ORD-1001 is open.\", \"how many orders can you see\" -> \"I can see 3 order record(s).\", \"what is the total of ORD-1004\" -> \"The total of ORD-1004 is 45.\"",
   "spec": "absent",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-14",
   "built": "yes",
   "observed": true,
   "evidence": "Maya \"create an order for Northwind totalling 40\" -> proposal create {id ORD-1005, readers [\"maya\"]}, confirmed -> \"Created ORD-1005.\"; Ana then created \"Ana Co\" -> ORD-1006 readers [\"ana\"]; Ana reads ORD-1006, Maya gets \"I can't see a record called ORD-1006.\"; Theo and Ana cannot see ORD-1005.",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-15",
   "built": "yes",
   "observed": true,
   "evidence": "Screenshots at 1440x900: centred 760px conversation column between a sidebar and a tools panel; message text 16.4px, line-height 27.5px, dark green-grey on a warm pale canvas, author header with avatar per message, clear separators, composer pinned at the bottom with a hint line.",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-16",
   "built": "yes",
   "observed": true,
   "evidence": "Replies appear as plain paragraphs under the bot name; proposals as a bordered card listing each change with two buttons; results as a short Change result card; task progress kept in the Tasks panel rather than the transcript (screenshots s44.png, s51.png).",
   "spec": "absent",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-17",
   "built": "yes",
   "observed": true,
   "evidence": "In conversation 2 of the same bot \"what did I ask first\" -> \"This is the first thing you've asked.\"; \"apples\" -> \"(Assistant has 2 message(s) from you in this conversation.)\"; then \"You first asked: \\\"what did I ask first\\\".\"; back in conversation 1 \"what did I ask first\" quoted conversation 1's first message and \"bananas\" counted 40 messages of conversation 1 only. Code passes conversation.messages in stored order ending with the new person message.",
   "spec": "absent",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-18",
   "built": "yes",
   "observed": true,
   "evidence": "Memory: bot Second answered \"I don't remember anything about you yet.\" while Assistant remembered \"prefers email\"; Theo's bot remembered nothing of Maya's. Records: counts per person matched only readable records (S-11). History: counts and first-question replies were per conversation (S-17).",
   "spec": "absent",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-19",
   "built": "yes",
   "observed": true,
   "evidence": "Fresh conversation \"what did I ask first\" -> \"This is the first thing you've asked.\"; after earlier messages -> \"You first asked: \\\"what did I ask first\\\".\" (the conversation's first person message); in the UI after \"Can you help...\" the same rule quoted the first message.",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-20",
   "built": "yes",
   "observed": true,
   "evidence": "\"  hello there [slow]  \" -> \"You said: \\\"hello there\\\". (Assistant has 2 message(s) from you in this conversation.)\"; next \"Thanks a lot\" -> \"... has 4 message(s) ...\"; in bot Ledger \"second conversation note\" -> \"(Ledger has 1 message(s) ...)\".",
   "spec": "absent",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-21",
   "built": "yes",
   "observed": true,
   "evidence": "UI: Enter on \"update ORD-1001\" -> \"Which field of ORD-1001 should I change, and to what value?\"; Enter on \"the status to closed\" -> \"I propose one change: ORD-1001 status: open → closed. Confirm to apply it.\" with Proposed changes \"ORD-1001 status: open → closed\".",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-22",
   "built": "yes",
   "observed": true,
   "evidence": "UI: New bot, Bot name \"Clerk\", Save bot name -> Bots navigation [Assistant (aria-current false), Clerk (true)]; Rename bot, \"Ledger\", Save bot name -> [Assistant, Ledger (current)]; \"who are you\" -> \"I am Ledger. I have no special instructions.\"",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-23",
   "built": "yes",
   "observed": true,
   "evidence": "UI: Ledger had conversations \"second conversation note\" and \"who are you\"; switching to Assistant and back to Ledger reopened the last-open conversation with its 2 messages; selecting \"who are you\" showed its own 2 messages; after reload Ledger and \"who are you\" were still marked current with the same messages; Assistant's conversation kept 14 articles.",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-24",
   "built": "yes",
   "observed": true,
   "evidence": "UI Saved instructions: saved Tone=\"Be brief\" -> buttons Use Tone, Edit Tone, Delete Tone; \"who are you\" before Use -> \"I have no special instructions.\"; after Use Tone -> \"My instructions: Be brief\"; Edit Tone filled the boxes with \"Tone\"/\"Be brief\"; changed to \"Be very brief\" and saved -> still one Tone; Use Tone -> \"My instructions: Be very brief\".",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-25",
   "built": "yes",
   "observed": true,
   "evidence": "UI Saved tasks: saved Count=\"how many orders can you see\" -> Run Count, Edit Count, Delete Count; Run Count added Maya's message and reply \"I can see 3 order record(s).\"; Edit Count filled the boxes; changed to \"how many accounts can you see\", saved (still one Count); Run Count -> \"I can see 2 account record(s).\"",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-26",
   "built": "yes",
   "observed": true,
   "evidence": "UI: after \"remember that likes tea\" and \"remember that works in Lisbon\", the Memory region listed two list items \"likes tea\" and \"works in Lisbon\", each with Edit memory and Forget.",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-27",
   "built": "yes",
   "observed": true,
   "evidence": "UI: Edit memory on \"works in Lisbon\" filled Memory text with it; changed to \"works in Porto\", Save memory -> list \"likes tea\", \"works in Porto\"; \"what do you remember\" -> \"I remember: likes tea; works in Porto.\"",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-28",
   "built": "yes",
   "observed": true,
   "evidence": "\"remember that likes tea\" -> \"I'll remember that likes tea.\" and the fact appeared in Memory; \"remember that prefers email\" -> \"I'll remember that prefers email.\" and was listed by \"what do you remember\".",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-29",
   "built": "yes",
   "observed": true,
   "evidence": "\"forget prefers email\" -> \"I've forgotten \\\"prefers email\\\".\" and the bot's memory became []; \"remember that likes jazz\" then \"forget that likes jazz\" -> \"I've forgotten \\\"likes jazz\\\".\" and memory [].",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-30",
   "built": "yes",
   "observed": true,
   "evidence": "With facts: \"I remember: likes tea; works in Porto.\"; after all forgotten: \"I don't remember anything about you yet.\"",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-31",
   "built": "yes",
   "observed": true,
   "evidence": "UI: after Maya built bots, conversations, memory, instructions, saved tasks and long tasks, Switch person -> Continue as Theo showed Bots [Assistant], Conversations [New conversation], no messages, \"Assistant has no saved memories.\", no saved instructions or tasks, \"No background tasks yet.\", Since you were away caught up; \"what do you remember\" -> \"I don't remember anything about you yet.\"; \"who are you\" -> no special instructions. API: Theo's /api/state contained none of Maya's text; replaying Maya's botId/conversationId/memory id from Theo's cookie for selectConversation, send and forgetMemory each returned {\"error\":\"That item is unavailable in this workspace.\"} and Maya's memory was untouched.",
   "spec": "stated",
   "proved": "fails",
   "proved_by": "lib/workspace.js view(): `workspace: state.users[identity.id]` changed to `workspace: Object.values(state.users)[0]` (every person shown the first person's workspace); npm test: TC-2 failed (actual 'Studio guide', expected 'Assistant' for Theo's bot), TC-5 and TC-6 failed too. Edit undone, diff clean, suite back to 8 pass 0 fail."
  },
  {
   "id": "S-32",
   "built": "yes",
   "observed": true,
   "evidence": "Bot Second: \"what do you remember\" -> \"I don't remember anything about you yet.\" while Assistant remembered \"prefers email\"; \"remember that only in Second\" in Second; back on Assistant -> \"I remember: prefers email.\" only.",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-33",
   "built": "yes",
   "observed": true,
   "evidence": "\"remember that prefers email\" in conversation 1; in conversation 2 and in a new conversation 3 of the same bot \"what do you remember\" -> \"I remember: prefers email.\"",
   "spec": "stated",
   "proved": "passes",
   "proved_by": "lib/workspace.js: remembered facts tagged with the conversationId and the provider given only facts of the current conversation (memory filter in reply()); probe: remember in one conversation, New conversation, \"what do you remember\" -> \"I don't remember anything about you yet.\"; npm test still 8 pass 0 fail. Edit undone, diff clean, suite back to 8 pass."
  },
  {
   "id": "S-34",
   "built": "yes",
   "observed": true,
   "evidence": "Maya: \"what is the customer of ord-1004\" -> \"The customer of ORD-1004 is Dune Supply.\"; follow-ups \"what is the total of ORD-1001\" -> 125, status questions answered with the current working value; Ana asking about ORD-1001 -> \"I can't see a record called ORD-1001.\"; values match records.json.",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-35",
   "built": "yes",
   "observed": true,
   "evidence": "Maya \"I can see 3 order record(s).\" / \"I can see 2 account record(s).\"; Theo 2 / 2; Ana 1 / 2; after Maya's confirmed create Maya 4 orders, others unchanged.",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-36",
   "built": "yes",
   "observed": true,
   "evidence": "\"what is the customer of ord-1004\" -> \"The customer of ORD-1004 is Dune Supply.\" (lower-case id matched); \"what is the tier of ORD-1004\" -> \"ORD-1004 has no tier.\"; Ana \"what is the status of ORD-1001\" -> \"I can't see a record called ORD-1001.\"",
   "spec": "absent",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-37",
   "built": "yes",
   "observed": true,
   "evidence": "UI: \"set the status of ORD-1001 to closed\" showed region Proposed changes \"ORD-1001 status: open → closed\" with Confirm changes and Reject changes before anything was written; create showed \"Create ORD-1005 · type: order · customer: Doubleclick · status: open · total: 9 · readers: [\\\"maya\\\"]\".",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-38",
   "built": "yes",
   "observed": true,
   "evidence": "\"set the total of ORD-1004 to 60\" -> \"I propose one change: ORD-1004 total: 45 → 60. Confirm to apply it.\" with a pending proposal; \"what is the total of ORD-1004\" still 45; Ana \"set the status of ORD-1002 to closed\" -> \"I can't see a record called ORD-1002.\", no proposal, ORD-1002 still shipped.",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-39",
   "built": "yes",
   "observed": true,
   "evidence": "\"update ORD-1004\" -> \"Which field of ORD-1004 should I change, and to what value?\"; \"the status to closed\" -> \"I propose one change: ORD-1004 status: open → closed. Confirm to apply it.\" (same change object as set); status still open afterwards.",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-40",
   "built": "yes",
   "observed": true,
   "evidence": "\"create an order for Northwind totalling 40\" -> \"I propose creating one order: customer Northwind, total 40, status open. Confirm to apply it.\"; \"how many orders can you see\" before confirm -> 3.",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-41",
   "built": "yes",
   "observed": true,
   "evidence": "Before Confirm changes: ORD-1001/ORD-1004 statuses and totals unchanged, order count unchanged, ORD-1005 unreadable; after clicking Confirm changes the new values were read back. Rejected proposals wrote nothing.",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-42",
   "built": "yes",
   "observed": true,
   "evidence": "UI: confirm \"ORD-1001 status: open → closed\" -> Change result \"Confirmed. The proposed changes were applied.\"; \"what is the status of ORD-1001\" -> closed; customer -> Acme Tools; total -> 125 (unchanged).",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-43",
   "built": "yes",
   "observed": true,
   "evidence": "Confirm of Northwind create -> result \"Created ORD-1005.\"; Maya: customer Northwind, total 40, status open, 4 orders; Theo and Ana: \"I can't see a record called ORD-1005.\"",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-44",
   "built": "yes",
   "observed": true,
   "evidence": "UI: Reject changes on ORD-1001 status -> Change result \"Rejected. No records were changed.\"; \"what is the status of ORD-1001\" -> open. API: rejected \"create an order for Southwind totalling 20\" -> status rejected, 4 orders still, ORD-1006 unreadable; a later confirm of the rejected proposal returned 200 but status stayed rejected and the count stayed 4.",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-45",
   "built": "yes",
   "observed": true,
   "evidence": "UI: Enter pressed twice on the create message -> one person message and one reply; Confirm changes double-clicked and the page reloaded at once -> one Change result \"Created ORD-1005.\", 4 orders, ORD-1005 Doubleclick. API: confirm repeated on an applied create -> 200, still 4 orders; send repeated with the same requestId -> one message and one reply.",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-46",
   "built": "yes",
   "observed": true,
   "evidence": "Change result texts observed: \"Rejected. No records were changed.\", \"Confirmed. The proposed changes were applied.\", \"Created ORD-1005.\"; they replace the proposal buttons in the bot's message and stay after reload.",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-47",
   "built": "yes",
   "observed": true,
   "evidence": "\"long task: crates [long]\" -> \"I'll work on \\\"crates\\\" in the background and tell you when it is done.\"; \"Research: Ledger tidy-up\" -> same form; steps finished one at a time in order at about 0.53 s intervals (541, 1069, 1545 ... 4124 ms) with texts in step order; task title \"crates\" (marker removed).",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-48",
   "built": "yes",
   "observed": true,
   "evidence": "\"Research: Ledger tidy-up\" -> 3 steps Collect/Compare/Write the summary of Ledger tidy-up; \"crates [long]\" -> 8 steps with Check part 1..5 of crates before Write the summary of crates.",
   "spec": "absent",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-49",
   "built": "yes",
   "observed": true,
   "evidence": "Default STANDIN_STEP_MS: steps finished at ~0.5 s intervals (541..4124 ms for 8); server C with STANDIN_STEP_MS=200: 234, 437, 645 ms; each finished entry \"Done: <step text>\".",
   "spec": "absent",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-50",
   "built": "yes",
   "observed": true,
   "evidence": "UI: started \"long task: report [long]\" and \"long task: crates [fail step 2]\", closed the page for 6 s, opened a new page in the same browser context: Task: report Completed with all 8 steps, Task: crates Failed after step 1 with Retry task. Work runs in the server process (README: keep the Node process running).",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-51",
   "built": "yes",
   "observed": true,
   "evidence": "On return, region Since you were away listed \"report — Completed · Assistant · <conversation>\" and \"crates — Failed · Assistant · <conversation>\"; another return during \"slowpoke [long]\" listed \"slowpoke — Running\" and \"crates — Failed\". It shows each task's status; failed and interrupted tasks stay listed until retried; pending proposals are not mentioned.",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-52",
   "built": "yes",
   "observed": true,
   "evidence": "During \"long task: audit [long]\": \"add step: double-check totals\" -> \"I'll add \\\"double-check totals\\\" to the task that is running.\" with notice \"Added to audit.\"; steps became 9 and the task completed with \"Done: double-check totals\" last. With no running task the stand-in reply came back but the notice said \"There was no running task in this conversation. No step was added.\"",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-53",
   "built": "yes",
   "observed": true,
   "evidence": "UI: while Task: big showed Task status Running, \"what is the status of ORD-1004\" got \"The status of ORD-1004 is open.\" and Task status still read Running; API: \"how many orders can you see\" answered while the audit task was Running.",
   "spec": "absent",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-54",
   "built": "yes",
   "observed": true,
   "evidence": "UI: Cancel task on Task: big mid-run -> Task status Cancelled, 4 finished steps listed, \"Cancelled. 4 finished steps were kept. Unfinished steps will produce no saved results.\", Cancel task button gone; 2 s later unchanged (no further steps). API: cancel after 2 steps -> Cancelled, 2 kept, unchanged 2.5 s later.",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-55",
   "built": "yes",
   "observed": true,
   "evidence": "Started `research: restart test [long]` as Ana and sent `slow one [slow]` (STANDIN_SLOW_MS=8000) in a second conversation, then killed the server by pid mid-work (workspace.json showed the task Running with 6 finished steps and the reply pending) and restarted it. The page showed Task: restart test with Task status Interrupted, exactly the 6 `Done: ...` steps that had finished, the note \"The server stopped. Retry starts with the first unfinished step.\" and a Retry task button; the slow conversation kept my message, an alert read \"The server restarted before the reply finished. Retry to continue this conversation.\" with a Retry button. Retry gave one bot reply (my message not duplicated); Retry task went Running at \"6 of 8 steps finished.\" and then Completed with 8 steps. The task's conversation still held both messages.",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-56",
   "built": "yes",
   "observed": true,
   "evidence": "Sent `research: alpha [fail step 2]`: after 2.5 s Task: alpha showed Task status Failed, finished steps [\"Done: Collect what is known about alpha\"], note \"Step 2 failed. Retry resumes here and keeps completed steps.\", a Retry task button; the conversation still held all four messages and no alert was raised. Retry task -> Completed with the same first step plus steps 2 and 3.",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-57",
   "built": "yes",
   "observed": true,
   "evidence": "Fresh data folder, Continue as Maya: region Setup reads \"Connect the local provider. Enter your provider token to start chatting. The local provider accepts sk-local- followed by at least 12 letters or digits. The token is stored on this computer.\" with a masked (type=password, role=textbox) Provider token box; Message is read-only with placeholder \"Connect the provider to start chatting…\" and Send disabled. `bad-token` and `sk-local-short` each gave the alert \"The provider refused that token. Check the format and try again.\", the box was cleared and focused, Setup stayed; `sk-local-abcdefghijkl` then dismissed Setup. The token never appeared in page HTML or any of 130 response bodies.",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-58",
   "built": "yes",
   "observed": true,
   "evidence": "At 1440 px, 80 Tab presses from the page start cycled through every named control in order: New bot, the bot buttons, Rename bot, Bot name, Save bot name, New conversation, the conversation buttons, Switch person, Conversation, Confirm changes, Reject changes, Message, Send, Instruction name, Instruction text, Save instruction, Task name, Task request, Save task, Edit memory, Forget, Cancel task, Retry task. Keyboard only: Tab to Instruction name, type `KB`, Tab, type `Answer briefly.`, Tab, Enter saved it (Use KB/Edit KB/Delete KB appeared); Tab to Use KB + Enter applied it; Tab to Message, type `who are you`, Enter -> \"I am Assistant. My instructions: Answer briefly.\"; Tab to New bot + Enter focused Bot name, typing `Keyboarder` + Enter created and opened it. At 390 and 700 px the Toggle workspace tools button opened the tools and Escape closed them.",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-59",
   "built": "yes",
   "observed": true,
   "evidence": "GET / with an empty data folder showed buttons Continue as Maya, Continue as Theo, Continue as Ana and no password input (count of visible input[type=password] = 0).",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-60",
   "built": "yes",
   "observed": true,
   "evidence": "After continuing as Maya, clicking Switch person hid the workspace and showed the three Continue as buttons again.",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-61",
   "built": "yes",
   "observed": true,
   "evidence": "Maya had bots Assistant and Scout, memory \"I like green tea\", 24 messages and the instruction Pirate. Switch person -> Continue as Theo: bots [\"Assistant*\"], one empty New conversation, Memory \"Assistant has no saved memories.\", no saved instructions; `what do you remember` -> \"I don't remember anything about you yet.\" Switch person -> Continue as Maya again: bots [\"Assistant*\",\"Scout\"], memory [\"I like green tea\"], the same 24 messages.",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-62",
   "built": "yes",
   "observed": true,
   "evidence": "page.reload() as Maya kept profile Maya with bots [\"Assistant*\",\"Scout\"]; after switching to Theo, reload kept Theo. A new page in the same browser context after the server restarted also opened as Ana.",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-63",
   "built": "yes",
   "observed": true,
   "evidence": "At 1440x900 as Maya with a decided and a pending proposal, a memory and a running task, every named control and region was visible and inside the viewport without opening anything: Bots, Conversations, New bot, Rename bot, Bot name, Save bot name, New conversation, Conversation, Message, Send, Switch person, Saved instructions (+ its 2 textboxes and button), Saved tasks (+ its 2 textboxes and button), Memory, Edit memory, Forget, Tasks, Since you were away, Proposed changes, Change result. On a server with no token, Setup, Provider token and Save token were visible at x=409..949, y=115..360.",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-64",
   "built": "yes",
   "observed": true,
   "evidence": "At 390x800 and 700x800 the side panels fold away (Bots, Saved instructions etc. not displayed), while region Conversation and textbox Message and Send stay visible in view (Message box at y=700, width 288 at 390 px); sending `narrow hello 390` by Enter got the bot reply. The Toggle navigation / Toggle workspace tools buttons open the folded parts with the conversation and Message still visible.",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-65",
   "built": "yes",
   "observed": true,
   "evidence": "With no token saved, after Continue as Maya the region Setup was visible with one textbox Provider token and one button Save token; its text explains the sk-local- format and shows no token.",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-66",
   "built": "yes",
   "observed": true,
   "evidence": "POST /api/action setup with no token, \"\", \"sk-local-abc!defghijklm\", \"sk-local-abcdefghijk\" (11 chars) and \"SK-LOCAL-abcdefghijkl\" each returned 400 \"The provider refused that token. Check the format and try again.\"; in the page `bad-token` and `sk-local-short` were refused and `sk-local-abcdefghijkl` accepted (Setup dismissed, replies work).",
   "spec": "absent",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-67",
   "built": "yes",
   "observed": true,
   "evidence": "Entering `bad-token` and pressing Save token showed an alert \"The provider refused that token. Check the format and try again.\", Setup stayed visible, the Provider token box was emptied and focused; a second refused token gave the same alert, and a valid one then worked.",
   "spec": "stated",
   "proved": "passes",
   "proved_by": "Removed role=\"alert\" from <p id=\"setup-error\"> in public/index.html; a refused token then produced no alert in the page (Playwright: alerts []), yet `npm test` still passed 8 of 8. Restored the file (cmp identical to the original) and the suite is back to 8 pass."
  },
  {
   "id": "S-68",
   "built": "yes",
   "observed": true,
   "evidence": "After saving `sk-local-abcdefghijkl`, Setup was hidden, no alert showed, and `who are you` sent with Send got \"I am Assistant. I have no special instructions.\"; after a server restart the token was still in effect (no Setup, replies worked).",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-69",
   "built": "yes",
   "observed": true,
   "evidence": "Started a second server with PROVIDER_TOKEN=sk-local-envtoken12345 and an empty DATA_DIR: Continue as Maya showed no Setup region, `who are you` replied \"I am Assistant. I have no special instructions.\", the token was not in page HTML or any of the 9 response bodies, and data2/workspace.json held \"token\":\"\".",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-70",
   "built": "yes",
   "observed": true,
   "evidence": "After saving the token, page HTML and all 130 response bodies of the session contained no `sk-local-abcdefghijkl`; after two server restarts the page HTML and 29 response bodies of a new page again did not contain it.",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-71",
   "built": "yes",
   "observed": true,
   "evidence": "navigation Bots listed buttons [\"Assistant*\"] then [\"Assistant\",\"Helper*\"] (* = aria-current=\"true\" on the open bot); selecting Assistant moved the mark: [\"Assistant*\",\"Scout\"].",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-72",
   "built": "yes",
   "observed": true,
   "evidence": "New bot, Bot name `Helper`, Save bot name -> Bots [\"Assistant\",\"Helper*\"], header shows Helper, empty conversation open; Assistant kept its conversations.",
   "spec": "stated",
   "proved": "fails",
   "proved_by": "Deleted the line `target.activeBot = created.id;` in the newBot case of lib/workspace.js; the page then left Assistant open after Save bot name (Bots [\"Assistant*\",\"Helper\"]) and `npm test` failed TC-4 (7 pass, 1 fail). Restored (cmp identical), suite back to 8 pass."
  },
  {
   "id": "S-73",
   "built": "yes",
   "observed": true,
   "evidence": "Rename bot filled Bot name with \"Helper\"; changing it to `Scout` and Save bot name -> Bots [\"Assistant\",\"Scout*\"]; `who are you` -> \"I am Scout. I have no special instructions.\"",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-74",
   "built": "yes",
   "observed": true,
   "evidence": "A fresh person (Maya on an empty data folder; Theo and Ana later) had Bots [\"Assistant\"] only.",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-75",
   "built": "yes",
   "observed": true,
   "evidence": "navigation Conversations for Scout listed [\"who are you*\"]; after New conversation and a send [\"second thread hello*\",\"who are you\"]; clicking \"who are you\" moved the current mark and showed its two messages.",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-76",
   "built": "yes",
   "observed": true,
   "evidence": "New conversation added \"New conversation*\" at the top of the Conversations list and opened it with 0 messages.",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-77",
   "built": "yes",
   "observed": true,
   "evidence": "region Conversation held articles \"Message from Maya | who are you\" and \"Message from Assistant | I am Assistant. I have no special instructions.\"; after rename the bot's articles read \"Message from Scout\".",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-78",
   "built": "yes",
   "observed": true,
   "evidence": "Typing `who are you` into textbox Message and clicking Send added \"Message from Maya | who are you\" and the bot reply to the open conversation.",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-79",
   "built": "yes",
   "observed": true,
   "evidence": "Enter in Message with `hello by enter` sent it (bot replied \"You said: \\\"hello by enter\\\". (Assistant has 2 message(s)...)\") and cleared the box.",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-80",
   "built": "yes",
   "observed": true,
   "evidence": "`line one`, Shift+Enter, `line two` left the box value \"line one\\nline two\" with no new article; Enter then sent one message \"line one\\nline two\".",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-81",
   "built": "yes",
   "observed": true,
   "evidence": "`ping [slow]` (default 1500 ms): a status \"Assistant is replying…\" in Conversation at 0.4 s and 1.2 s; gone at 2.4 s with the reply shown. With STANDIN_SLOW_MS=8000 the same status showed during the wait.",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-82",
   "built": "yes",
   "observed": true,
   "evidence": "`ask me [fail once]`: an alert \"The reply failed. Retry to resume without sending your message again.\" and a Retry button; my message shown once.",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-83",
   "built": "yes",
   "observed": true,
   "evidence": "Clicking Retry after `ask me [fail once]` added exactly one bot reply (\"You said: \\\"ask me\\\". (Assistant has 5 message(s) from you...)\"); the conversation gained 2 articles in total (my message once), and the alert cleared.",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-84",
   "built": "yes",
   "observed": true,
   "evidence": "region Saved instructions has textboxes Instruction name, Instruction text and button Save instruction; saving Pirate / \"Talk like a pirate.\" listed Pirate.",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-85",
   "built": "yes",
   "observed": true,
   "evidence": "The saved instruction had buttons Use Pirate, Edit Pirate, Delete Pirate.",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-86",
   "built": "yes",
   "observed": true,
   "evidence": "Use Pirate on Assistant, then `who are you` -> \"I am Assistant. My instructions: Talk like a pirate.\"; in a New conversation of Assistant the same; in bot Scout `who are you` -> \"I am Scout. I have no special instructions.\"",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-87",
   "built": "yes",
   "observed": true,
   "evidence": "With no instructions: \"I am Assistant. I have no special instructions.\" / \"I am Scout. I have no special instructions.\"; after Use Pirate: \"I am Assistant. My instructions: Talk like a pirate.\"",
   "spec": "absent",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-88",
   "built": "yes",
   "observed": true,
   "evidence": "Edit Pirate filled Instruction name \"Pirate\" and Instruction text \"Talk like a pirate.\"; changing the text to \"Talk like a calm pirate.\" and Save instruction kept one Pirate entry (buttons Use/Edit/Delete Pirate only); Use Pirate then `who are you` -> \"I am Assistant. My instructions: Talk like a calm pirate.\"",
   "spec": "stated",
   "proved": "passes",
   "proved_by": "Deleted `field.value = item.text;` in the Edit button handler of public/app.js; Edit Pirate then left Instruction text empty (Playwright: \"Pirate\" \"\"), yet `npm test` passed 8 of 8. Restored (cmp identical), suite 8 pass. For comparison a server-side break (`if (item) Object.assign(...)` -> `if (false) ...` in replaceEntry, lib/workspace.js) failed TC-3; restored, 8 pass."
  },
  {
   "id": "S-89",
   "built": "yes",
   "observed": true,
   "evidence": "Delete Pirate removed the entry: the region's buttons were then only Save instruction.",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-90",
   "built": "yes",
   "observed": true,
   "evidence": "region Saved tasks has textboxes Task name, Task request and button Save task; saving Count / \"How many orders can you see?\" listed Count.",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-91",
   "built": "yes",
   "observed": true,
   "evidence": "The saved task had buttons Run Count, Edit Count, Delete Count.",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-92",
   "built": "yes",
   "observed": true,
   "evidence": "Run Count added \"Message from Maya | How many orders can you see?\" and \"Message from Assistant | I can see 3 order record(s).\" to the open conversation.",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-93",
   "built": "yes",
   "observed": true,
   "evidence": "Edit Count filled Task name \"Count\" and Task request \"How many orders can you see?\"; changing the request to \"How many accounts can you see?\" and Save task kept one Count; Run Count then sent it and got \"I can see 2 account record(s).\"",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-94",
   "built": "yes",
   "observed": true,
   "evidence": "Delete Count removed it: only Save task remained in the region.",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-95",
   "built": "yes",
   "observed": true,
   "evidence": "After `remember that I like tea` and `remember that my desk is B4`, region Memory listed two list items \"I like tea\" and \"my desk is B4\"; bot Scout's Memory read \"Scout has no saved memories.\"",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-96",
   "built": "yes",
   "observed": true,
   "evidence": "Each memory list item held buttons [\"Edit memory\",\"Forget\"].",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-97",
   "built": "yes",
   "observed": true,
   "evidence": "Forget on \"my desk is B4\" left [\"I like green tea\"]; `what do you remember` -> \"I remember: I like green tea.\"",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-98",
   "built": "yes",
   "observed": true,
   "evidence": "Edit memory on \"I like tea\" showed textbox Memory text filled \"I like tea\"; changing to \"I like green tea\" and Save memory updated the item; `what do you remember` -> \"I remember: I like green tea; my desk is B4.\"",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-99",
   "built": "yes",
   "observed": true,
   "evidence": "`set the status of ORD-1001 to closed` as Maya showed region Proposed changes \"ORD-1001 status: open → closed\" with buttons Confirm changes and Reject changes; `create an order for Zed totalling 50` showed \"Create ORD-1005 · type: order · customer: Zed · status: open · total: 50 · readers: [\\\"maya\\\"]\".",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-100",
   "built": "yes",
   "observed": true,
   "evidence": "Confirm changes -> region Change result \"Confirmed. The proposed changes were applied.\" and `what is the status of ORD-1001` -> \"closed\"; Reject changes on the Zed order -> Change result \"Rejected. No records were changed.\" and Maya still saw 3 orders.",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-101",
   "built": "yes",
   "observed": true,
   "evidence": "`research: weekly planning [long]` showed in region Tasks an article named \"Task: weekly planning\" (the stand-in's title without the marker).",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-102",
   "built": "yes",
   "observed": true,
   "evidence": "The article held a status named Task status; it read Running, then Completed; other tasks read Failed (alpha), Cancelled (beta) and Interrupted (after a restart).",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-103",
   "built": "yes",
   "observed": true,
   "evidence": "At 1.3 s the article listed [\"Done: Collect what is known about weekly planning\",\"Done: Compare the options for weekly planning\"] and \"2 of 8 steps finished.\"; at completion all 8 \"Done: ...\" steps.",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-104",
   "built": "yes",
   "observed": true,
   "evidence": "A Cancel task button showed while running; on beta it set Task status Cancelled with 3 finished steps kept (\"Cancelled. 3 finished steps were kept. Unfinished steps will produce no saved results.\") and no further steps 1.5 s later; Completed and Cancelled tasks have no Cancel task button.",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-105",
   "built": "yes",
   "observed": true,
   "evidence": "After about 5.8 s Task: weekly planning read Completed with 8 steps and \"All 8 steps finished.\"",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-106",
   "built": "yes",
   "observed": true,
   "evidence": "Retry task showed on the Failed alpha task and on the Interrupted restart test task (not on Running/Completed/Cancelled); each retry resumed at the first unfinished step and completed.",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-107",
   "built": "yes",
   "observed": true,
   "evidence": "As Ana: started `research: omega [long]`, closed the page, reopened 6 s later in the same browser: Since you were away read \"omega — Completed · Assistant · research: omega [long]\". As Theo: with one task Failed and one [long] task running, closed and reopened 0.8 s later: \"one — Failed …; two — Running …\"; reopened again after both ended: \"two — Completed …; one — Failed …\". After a restart: \"sigma — Failed …; restart test — Interrupted …\". Tasks that finished while a page was open are not repeated on the next return (it compares with the last time a page was seen, kept in localStorage).",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-108",
   "built": "yes",
   "observed": true,
   "evidence": "`npm test` (node --test) ran test/app.test.js: 8 node:test tests, 8 pass, 0 fail, about 6.6 s; it requires server.js, which uses lib/workspace.js, lib/records.js and lib/store.js and the unmodified provider.",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  }
 ],
 "unstated": [
  {
   "id": "U-1",
   "behaviour": "The person is held per browser by an HttpOnly signed cookie (still_session). Two browser contexts keep their own person; tabs of one browser share it, and a Switch person in one tab changes the other tab on its next 700 ms poll.",
   "handling": "sound",
   "observed": true,
   "evidence": "Playwright (pw2.js): context A Continue as Maya + 'hello from Maya', context B Continue as Theo + 'hello from Theo'; after reload A shows Maya with only Maya's two messages, B shows Theo with only Theo's; a further send from A lands in Maya's conversation, B unchanged. Second tab of A showed Maya; Switch person -> Continue as Ana in tab 2; tab 1 (no reload) then showed Ana with Ana's empty conversation, and a send from tab 1 went to Ana.",
   "spec": "decided-unmarked",
   "told": "no",
   "told_where": ""
  },
  {
   "id": "U-2",
   "behaviour": "Every action is resolved inside the cookie's own person's workspace; ids from another person's workspace return 404 and change nothing. Cookies are HMAC-signed; forged or swapped cookies are treated as no person.",
   "handling": "sound",
   "observed": true,
   "evidence": "p8.js: as Maya noted bot/conversation/proposal/memory ids, switchPerson, continue as Ana; selectConversation, decideProposal confirm, editMemory, forgetMemory and send with Maya's ids all -> 404 'That item is unavailable in this workspace.'; Ana's /api/state does not contain Maya's memory text. Forged cookie maya.000..., theo.<maya signature>, bare 'maya' -> /api/state returns only {people}. Back as Maya: proposal still pending, memory intact, 'what is the status of ORD-1002' -> shipped (unchanged).",
   "spec": "decided-unmarked",
   "told": "no",
   "told_where": ""
  },
  {
   "id": "U-3",
   "behaviour": "First screen shows only the three Continue as buttons (no Setup, no chat controls). Setup appears only after choosing a person, with Message read-only and Send disabled until a token is saved; the token is server-wide. After Switch person and reload the chooser returns and nothing can be sent.",
   "handling": "acceptable",
   "observed": true,
   "evidence": "pw1.js on an empty data folder: visible controls on GET / = ['Continue as Maya','Continue as Theo','Continue as Ana']; Setup region not visible; Message not visible. After Continue as Maya: Setup visible, message readOnly=true, send disabled=true. Saving sk-local-abcdefghijkl hides Setup. Switch person + reload: Continue as Maya visible, Message not visible. API: send without a person -> 401 'Choose a person to continue.'; setup without a person -> 401. Token must come after choosing a person (fixed order).",
   "spec": "silent",
   "told": "no",
   "told_where": ""
  },
  {
   "id": "U-5",
   "behaviour": "A valid PROVIDER_TOKEN wins over a saved token and is used only while set; it is not copied into the data folder. While a valid env token is set, Setup is hidden and a setup request is silently ignored (200, nothing stored).",
   "handling": "acceptable",
   "observed": true,
   "evidence": "p7.js: PROVIDER_TOKEN=sk-local-abcdefghijkl -> continue configured=true, 'who are you' replied; POST setup sk-local-zzzzzzzzzzzz -> 200, workspace.json token stays ''. Restart without the variable -> configured=false (Setup back). No response contained either token.",
   "spec": "silent",
   "told": "no",
   "told_where": ""
  },
  {
   "id": "U-6",
   "behaviour": "An invalid environment token is treated as unsaved: Setup is shown and a valid token can be saved through it, after which replies work. Provider unauthorized errors during use cannot arise with this stand-in (format check only) and would show the generic reply-failed alert.",
   "handling": "sound",
   "observed": true,
   "evidence": "p7.js: PROVIDER_TOKEN=not-a-token -> configured=false; setup sk-local-yyyyyyyyyyyy -> configured=true; 'who are you' -> 'I am Assistant...'. PROVIDER_TOKEN=sk-local-short -> configured=false; send -> 400 'Save a provider token in Setup before sending.'. Bad token typed in Setup (pw1.js) -> alert 'The provider refused that token. Check the format and try again.' and the field remains usable.",
   "spec": "silent",
   "told": "no",
   "told_where": ""
  },
  {
   "id": "U-7",
   "behaviour": "Saved token is stored in plain text in DATA_DIR/workspace.json (file mode 0600, folder 0700). It is never in any API response, page or server output; token-shaped text typed in messages is replaced by '[provider token hidden]'. Provider errors show a generic alert without the token.",
   "handling": "acceptable",
   "observed": true,
   "evidence": "p1.js/p7.js/p7b.js: after setup, grep finds the token only in d1/workspace.json (-rw-------); full token strings absent from /api/state, action responses, /, /app.js; server log only 'Stillpoint is ready...'. 'hello [fail once]' -> alert 'The reply failed. Retry to resume without sending your message again.'. Message 'my key is sk-local-abcdefghijkl ok' stored as 'my key is [provider token hidden] ok'. README says only 'The app keeps the token server-side' (plain storage not stated).",
   "spec": "decided-unmarked",
   "told": "no",
   "told_where": ""
  },
  {
   "id": "U-8",
   "behaviour": "A new person starts with bot Assistant holding one empty open conversation titled 'New conversation'; Send works at once. New bot opens a bot with one empty conversation, no memory, no instructions. New conversation becomes the open one.",
   "handling": "sound",
   "observed": true,
   "evidence": "pw1.js as Ana on empty data: Bots ['Assistant [current]'], Conversations ['New conversation [current]'], Conversation region shows empty-state prompts; 'who are you' -> 'I am Assistant. I have no special instructions.'; 'what do you remember' -> 'I don't remember anything about you yet.'. New bot 'Clerk': Bots ['Assistant','Clerk [current]'], Conversations ['New conversation [current]'], Memory 'Clerk has no saved memories.', 'who are you' -> 'I am Clerk. I have no special instructions.'. New conversation -> ['New conversation [current]','who are you'].",
   "spec": "silent",
   "told": "no",
   "told_where": ""
  },
  {
   "id": "U-9",
   "behaviour": "Empty name blocked by the browser (required); blank (spaces) refused with an alert. Duplicate names are allowed and the two bots show identically (same text, same accessible name, no other cue). The Bot name field has maxlength=80 so a 300-character paste is silently cut to 80 and stored cut; the API refuses over 80.",
   "handling": "poor",
   "observed": true,
   "evidence": "pw3.js as Theo: empty -> validationMessage 'Please fill out this field.', no bot; '   ' -> alert 'Bot name must contain between 1 and 80 characters.'. Second bot named Assistant -> Bots nav ['Assistant','Assistant [current]'], visual text 'Assistant\\nAssistant'. 300 L's typed -> field value length 80, bot saved with an 80-char name; API newBot with 300 chars -> 400 same message.",
   "spec": "silent",
   "told": "no",
   "told_where": "",
   "rerun": true
  },
  {
   "id": "U-11",
   "behaviour": "Conversation buttons are named by the first 56 characters of the first message (empty ones 'New conversation'), newest first, open one aria-current. Two empty conversations share the name 'New conversation' (also the name of the New conversation button), and conversations whose first messages share 56 characters get identical names, visually and by accessible name.",
   "handling": "poor",
   "observed": true,
   "evidence": "pw3.js: two New conversation clicks -> ['New conversation [current]','New conversation','hello from Theo']; two conversations starting 'Please summarise the open orders for customer Acme Tools and list anything unusual about customer Zeta/Omega' -> ['Please summarise the open orders for customer Acme Tools [current]','Please summarise the open orders for customer Acme Tools', ...]; title attribute holds the same cut text. pw2.js: getByRole('button',{name:'New conversation'}) matched 2 elements (the + control and the empty conversation).",
   "spec": "silent",
   "told": "no",
   "told_where": "",
   "rerun": true
  },
  {
   "id": "U-13",
   "behaviour": "Open bot and conversation are stored per person on the server and restored after reload, Switch person and back, a new browser visit and a server restart. The unsent draft is dropped on reload and scroll jumps to the bottom.",
   "handling": "sound",
   "observed": true,
   "evidence": "pw6.js as Maya: open bot Second, its second conversation, scrollTop=100, draft typed. After reload: bot Second, same conversation, draft '', scroll at bottom (2271/2271). After Switch to Theo and back: same bot and conversation. New context with saved cookie: same. After server stop/start: same bot/conversation, person Maya.",
   "spec": "decided-unmarked",
   "told": "no",
   "told_where": ""
  },
  {
   "id": "U-14",
   "behaviour": "Saved instructions and saved tasks are one library per person, shown for every bot; Use changes only the open bot, Run sends in the open conversation. Another person never sees them.",
   "handling": "sound",
   "observed": true,
   "evidence": "pw3.js as Theo on Assistant: saved Tone='Be brief' and Ping='hello'; on new bot Other both listed; Use Tone -> notice 'Applied “Tone” to Other.'; Run Ping -> 'Theo: hello' in Other's conversation; Other 'who are you' -> 'My instructions: Be brief'; first Assistant 'who are you' -> 'I have no special instructions.'. workspace.json: maya instructions [] shortcuts [], ana [] [], theo ['A'] ['Pong','T1'].",
   "spec": "silent",
   "told": "yes",
   "told_where": "README.md: \"Each profile has its own bots, chats, saved entries, and task activity.\""
  },
  {
   "id": "U-15",
   "behaviour": "Saving an existing name without Edit silently overwrites that entry's text (one entry, no notice). Empty fields are blocked by the browser; blank (spaces) refused with an alert. Same for tasks.",
   "handling": "poor",
   "observed": true,
   "evidence": "pw3.js: Save instruction A='x' then A='y' -> buttons Use A/Edit A/Delete A once, no alert; Use A then 'who are you' -> 'My instructions: y'. Empty name -> 'Please fill out this field.'; '   ' -> alert 'Instruction name must contain between 1 and 80 characters.'. Task T1='one' then T1='two' -> one Run T1; blank task name -> 'Task name must contain between 1 and 80 characters.'.",
   "spec": "silent",
   "told": "no",
   "told_where": "",
   "rerun": true
  },
  {
   "id": "U-16",
   "behaviour": "Edit then a changed name renames the same item (instruction and task). Renaming onto an existing name is refused with 'That name is already in use.' but the form stays silently bound to the edited item (see defects).",
   "handling": "acceptable",
   "observed": true,
   "evidence": "pw3.js: Edit Tone fills ['Tone','Be brief']; change name to Style, Save -> buttons Use/Edit/Delete Style, no Tone; Edit Ping -> Pong, Save task -> Run/Edit/Delete Pong. Edit Style -> name A (existing) -> alert 'That name is already in use.', list unchanged.",
   "spec": "silent",
   "told": "no",
   "told_where": ""
  },
  {
   "id": "U-17",
   "behaviour": "Use copies the instruction text into the bot; later Edit or Delete of the saved instruction does not change the bot. The Saved instructions region shows 'Active on <bot>: <text>' so what the bot uses stays visible.",
   "handling": "acceptable",
   "observed": true,
   "evidence": "pw3.js: Formal='Be formal', Use Formal, 'who are you' -> 'My instructions: Be formal'; Edit Formal to 'Be casual' -> 'who are you' still 'Be formal', region shows 'Active on Assistant: Be formal'; Delete Formal -> still 'Be formal' and region still shows it.",
   "spec": "decided-unmarked",
   "told": "no",
   "told_where": ""
  },
  {
   "id": "U-20",
   "behaviour": "Send is disabled and a status 'Assistant is replying…' shows while a reply is pending; a second Enter is ignored and typed text stays in the box. The server refuses a second send in that conversation (409) and ignores a repeated request id. Replies land in their own conversation and person, survive reload and switching; a page closed before the acknowledgement keeps the received message and its pending reply; a deliberate resend creates a new message.",
   "handling": "sound",
   "observed": true,
   "evidence": "pw4.js (STANDIN_SLOW_MS=2500): 'hello [slow]' Enter Enter -> one person message and one reply; status 'Assistant is replying…'; send disabled; text typed during wait remained in box. Switched conversation during 'second [slow]' and back -> reply present. Reload during 'third [slow]' -> status still shown then reply. Maya 'set the status of ORD-1001 to closed [slow]' + Switch to Theo: Theo's view has no Maya message/proposal (0 Proposed changes); back as Maya the proposal is there. p4.js: same requestId sent twice -> 1 message; send during pending -> 409 'Finish or retry the last reply first.'. pw8.js: page closed 150 ms after sending 'long task: alpha [slow]'; reopened page shows the message and 'Clerk is replying…'; one alpha task; sending the same text again creates a second message.",
   "spec": "silent",
   "told": "no",
   "told_where": ""
  },
  {
   "id": "U-21",
   "behaviour": "After a failed reply an alert and Retry remain after reload and after a server restart, and Retry succeeds without a second person message. Sending a new message instead is refused (button disabled; API 409 'Finish or retry the last reply first.') with the alert still visible. A reply interrupted by stopping the server becomes failed with 'The server restarted before the reply finished. Retry to continue this conversation.' and waits for Retry.",
   "handling": "sound",
   "observed": true,
   "evidence": "pw4.js: 'hello [fail once]' -> alert 'The reply failed. Retry to resume without sending your message again.', only Maya's message; reload -> Retry present; typing 'next' + Enter -> send disabled, alert remains, 'next' stays in box; Retry -> reply added, one person message. p9.js: failed reply + server restart -> Retry -> complete; 'slow one [slow]' + restart -> failed with restart message, Retry -> 'You said: \"slow one\"'.",
   "spec": "decided-unmarked",
   "told": "no",
   "told_where": ""
  },
  {
   "id": "U-22",
   "behaviour": "The stored person message keeps the markers; the first attempt fails and Retry succeeds; 'what did I ask first' quotes the message with the marker.",
   "handling": "acceptable",
   "observed": true,
   "evidence": "p4.js: 'hello [fail once]' failed; retry -> bot 'You said: \"hello\"...'; 'what did I ask first' -> 'You first asked: \"hello [fail once]\".'; the Message article shows 'hello [fail once]'.",
   "spec": "silent",
   "told": "no",
   "told_where": ""
  },
  {
   "id": "U-23",
   "behaviour": "Repeated remember (any capitals) is merged into one fact. A forget that matches no fact exactly removes nothing but the reply still says \"I've forgotten ...\" with no notice from the app; Memory list stays the truth. An exact forget removes the fact.",
   "handling": "poor",
   "observed": true,
   "evidence": "p4.js: 'remember that likes tea' x2 and 'Remember that Likes Tea' -> memory ['likes tea']; 'forget tea' -> reply 'I've forgotten \"tea\".', memory still ['likes tea']; 'forget coffee' -> 'I've forgotten \"coffee\".', memory ['likes tea']; 'forget that likes tea' -> memory [].",
   "spec": "silent",
   "told": "no",
   "told_where": ""
  },
  {
   "id": "U-25",
   "behaviour": "Edit memory opens Memory text filled with the current fact; Save memory updates that item.",
   "handling": "sound",
   "observed": true,
   "evidence": "pw3.js: after 'remember that likes tea', Edit memory -> Memory text value 'likes tea'; changed to 'likes coffee', Save memory -> Memory list item 'likes coffee'.",
   "spec": "silent",
   "told": "no",
   "told_where": ""
  },
  {
   "id": "U-26",
   "behaviour": "Save instruction, Use, Delete, Save task, Rename bot, Save memory and Forget add no messages to the conversation; Run and typed memory phrases do.",
   "handling": "sound",
   "observed": true,
   "evidence": "pw3.js: article count unchanged after Save instruction (0), Save task (0), Use (0, a transient notice instead), Delete (0), Save memory + Rename bot + Forget (0); Run Ping added 'Theo: hello' and a reply; 'what did I ask first' -> first typed message.",
   "spec": "silent",
   "told": "no",
   "told_where": ""
  },
  {
   "id": "U-27",
   "behaviour": "Memory and task progress update on their own while the page stays open (700 ms polling).",
   "handling": "sound",
   "observed": true,
   "evidence": "pw3.js: after 'remember that likes tea', Memory list showed 'likes tea' without reload. pw7.js: snapshots of Task: alpha without reload went 'Running … 1 of 3 steps finished' -> 'Completed … All 3 steps finished.'.",
   "spec": "silent",
   "told": "no",
   "told_where": ""
  },
  {
   "id": "U-29",
   "behaviour": "Proposals to change readers, id or type are refused: the bot's reply text still says 'I propose one change ... Confirm to apply it.' but the app shows a Change result 'Record identity and access fields cannot be changed.' with no Confirm. owner is not protected: it can be set (as a new field on an order or changed on an account) with an ordinary preview; readers are untouched.",
   "handling": "acceptable",
   "observed": true,
   "evidence": "p2.js as Maya: 'set the readers of ORD-1001 to ana', 'set the id of ORD-1004 to ORD-9999', 'set the type of ORD-1001 to account' -> proposal status conflict, result 'Record identity and access fields cannot be changed.', changes []. 'set the owner of ORD-1001 to theo' -> pending 'owner: nothing → theo' (rejected). Records afterwards: readers unchanged (ORD-1001 maya,theo; ORD-1004 maya,ana).",
   "spec": "decided-unmarked",
   "told": "no",
   "told_where": ""
  },
  {
   "id": "U-30",
   "behaviour": "No value validation: a word into a number field, an unknown status and a field the record does not have are offered with an exact preview and applied as shown (e.g. 'total: 125 → banana', 'colour: ∅ → red'). A decimal create is not understood by the stand-in (no proposal). A corrected request in the same conversation works.",
   "handling": "acceptable",
   "observed": true,
   "evidence": "p2.js: 'set the total of ORD-1001 to banana' -> 'ORD-1001 total: 125 → banana', confirmed -> 'The total of ORD-1001 is banana.'; 'set the colour of ORD-1001 to red' -> 'colour: nothing → red', confirmed; 'set the status of ORD-1001 to banana' -> pending preview; 'create an order for Acme totalling 42.50' -> 'You said: ...' no proposal; 'set the total of ORD-1002 to 99.5' -> preview 80 → 99.5 (p12.js).",
   "spec": "silent",
   "told": "no",
   "told_where": ""
  },
  {
   "id": "U-31",
   "behaviour": "An undecided proposal stays pending across Enter in Message, reload, server restart and switching conversation. Several can be pending; confirming an older one after a newer changed the same field is refused as conflict. Only Confirm changes confirms; after a decision the buttons are replaced by a Change result and a later confirm writes nothing.",
   "handling": "sound",
   "observed": true,
   "evidence": "p3.js: Maya 'set the status of ORD-1001 to closed' -> pending; server restarted -> still pending, status still open; new conversation and back -> pending. Second proposal (open→shipped) rejected; first confirmed -> applied; confirm of the rejected one -> stays rejected; confirm first again -> no second write. Two pending (→open, →shipped): confirm newer applied, older -> conflict 'The records changed after this preview. No changes were applied. Ask for a fresh proposal.'. pw4.js: Enter on empty Message with proposal pending -> proposal remains.",
   "spec": "decided-unmarked",
   "told": "no",
   "told_where": ""
  },
  {
   "id": "U-32",
   "behaviour": "Proposed create lists 'Create ORD-1005 · type: order · customer: Northwind · status: open · total: 40 · readers: [\"maya\"]' with the previewed id; nothing is stored before Confirm; the stored id equals the preview, or the confirm is refused as conflict if the id was taken meanwhile.",
   "handling": "sound",
   "observed": true,
   "evidence": "p3.js: 'create an order for Northwind totalling 40' -> preview id ORD-1005; 'how many orders can you see' before confirm -> 3; confirm -> 'Created ORD-1005.'; count -> 4; 'what is the customer of ORD-1005' -> Northwind.",
   "spec": "decided-unmarked",
   "told": "no",
   "told_where": ""
  },
  {
   "id": "U-33",
   "behaviour": "Confirm re-checks the current value; if it changed (another person's confirm or an earlier proposal), the proposal becomes conflict with 'The records changed after this preview. No changes were applied. Ask for a fresh proposal.' No new proposal is offered automatically.",
   "handling": "acceptable",
   "observed": true,
   "evidence": "p3.js: Maya proposes ORD-1001 → closed (pending); Theo proposes → cancelled and confirms (applied); Maya confirms -> conflict with that message; both then read 'The status of ORD-1001 is cancelled.'.",
   "spec": "decided-unmarked",
   "told": "no",
   "told_where": ""
  },
  {
   "id": "U-34",
   "behaviour": "Next free number is one more than the highest ORD- number, previewed at proposal time and not reserved. Two pending creates preview the same id; the first confirm gets it and the second is refused as conflict (must ask again). Ids stay distinct.",
   "handling": "acceptable",
   "observed": true,
   "evidence": "p3.js: Maya 'create an order for North totalling 10' preview ORD-1006; Ana 'create an order for South totalling 20' preview ORD-1006; Maya confirm -> 'Created ORD-1006.'; Ana confirm -> conflict. Maya sees ORD-1005/1006 customers; Ana and Theo 'I can't see a record called ORD-1005/1006/1007.'.",
   "spec": "decided-unmarked",
   "told": "no",
   "told_where": ""
  },
  {
   "id": "U-35",
   "behaviour": "The decision is stored with the proposal in the conversation; after a reload a Change result region stays under the bot message that proposed it, with no Confirm offered again.",
   "handling": "sound",
   "observed": true,
   "evidence": "pw5.js as Ana: Confirm changes then immediate reload -> 0 Proposed changes, Change result 'Confirmed. The proposed changes were applied.' under 'I propose one change: ORD-1004 status: closed → open...'; 0 Confirm buttons; status reads open.",
   "spec": "decided-unmarked",
   "told": "no",
   "told_where": ""
  },
  {
   "id": "U-36",
   "behaviour": "One shared working copy: Theo sees Maya's confirmed change, also after a restart. records/ files unchanged; non-readers still cannot read.",
   "handling": "sound",
   "observed": true,
   "evidence": "p11.js/p13.js: Maya confirms ORD-1001 → closed; Maya and Theo both 'The status of ORD-1001 is closed.'; after a real server restart Theo still closed; Theo 'what is the status of ORD-1002' -> 'I can't see a record called ORD-1002.'. diff -r base/records work/records -> identical.",
   "spec": "silent",
   "told": "no",
   "told_where": ""
  },
  {
   "id": "U-37",
   "behaviour": "Tasks lists all of the person's tasks across bots and conversations, newest update first, each from another conversation labelled '<bot> · <conversation title>'; never another person's.",
   "handling": "sound",
   "observed": true,
   "evidence": "pw7.js as Theo: tasks report/beta/alpha listed from conversation 2 and from another bot with context 'Assistant One · long task: alpha'; after Switch to Ana, Tasks region empty, Since you were away 'You’re caught up on background work.'.",
   "spec": "silent",
   "told": "yes",
   "told_where": "README.md: \"Tasks shows background work across your conversations.\""
  },
  {
   "id": "U-38",
   "behaviour": "A second long task runs alongside the first; both shown in Tasks with their own status and step counts.",
   "handling": "sound",
   "observed": true,
   "evidence": "p5.js/pw7.js: 'long task: alpha [long]' then 'long task: beta' -> both Running (8 and 3 steps), both Completed later; UI showed 'Task: report … 3 of 8' and 'Task: beta … 1 of 3' at once.",
   "spec": "silent",
   "told": "no",
   "told_where": ""
  },
  {
   "id": "U-39",
   "behaviour": "With no running task the bot text says it will add the step but the app adds a notice 'There was no running task in this conversation. No step was added.'. With several running, the step goes to the latest started; the notice 'Added to <title>.' names only the title, so two tasks with the same title are not told apart (the receiving article shows one more step).",
   "handling": "poor",
   "observed": true,
   "evidence": "p5.js: 'add step: double-check' -> notice 'There was no running task in this conversation. No step was added.', Tasks empty. Two 'long task: dup [long]' + 'add step: extra' -> notice 'Added to dup.'; steps [8, 9]; pw7.js articles both named 'Task: dup', one '… of 8', other '… of 9 steps finished'.",
   "spec": "decided-unmarked",
   "told": "no",
   "told_where": "",
   "rerun": true
  },
  {
   "id": "U-40",
   "behaviour": "A finished, failed or cancelled task leaves no message in its conversation (the bot only said it would 'tell you when it is done'); the result is in the task article and Since you were away, findable after reload.",
   "handling": "acceptable",
   "observed": true,
   "evidence": "pw7.js: after both dup tasks Completed, last conversation messages are the start/steer replies only; after reload the two task articles remain; follow-up 'did the dup task finish?' -> generic 'You said: ...'.",
   "spec": "silent",
   "told": "no",
   "told_where": ""
  },
  {
   "id": "U-41",
   "behaviour": "Tasks keep running while the browser is closed. On a server restart a running task is marked Interrupted with its finished steps kept and the unfinished step not counted; it does not resume on its own; Retry task continues from the first unfinished step. Since you were away lists it.",
   "handling": "sound",
   "observed": true,
   "evidence": "pw7.js: context closed 5 s (>8 x 400 ms) while 'audit [long]' ran; reopened -> Task: audit Completed with 8 steps. p5.js (STANDIN_STEP_MS=1000): stopped after 2 steps -> restart: Interrupted, 2 finished, detail 'The server stopped. Retry starts with the first unfinished step.'; 1.5 s later still Interrupted; Retry task -> Completed with 8 distinct steps, attempts [1,1,2,1,...]. pw8.js UI: article shows Interrupted, both steps, Retry task; Since you were away 'audit Interrupted · Clerk · long task: audit [long]'.",
   "spec": "decided-unmarked",
   "told": "yes",
   "told_where": "README.md: \"If the process stops, the next launch marks unfinished work as interrupted.\""
  },
  {
   "id": "U-42",
   "behaviour": "Retry task resumes at the failed step and keeps the earlier steps; step 1 appears once.",
   "handling": "sound",
   "observed": true,
   "evidence": "p5.js: 'long task: plan [fail step 2]' -> Failed, 1 finished, 'Step 2 failed. Retry resumes here and keeps completed steps.'; Retry task -> Completed with 3 steps, 'Done: Collect what is known about plan' once, attempts [1,2,1].",
   "spec": "decided-unmarked",
   "told": "yes",
   "told_where": "README.md: \"Retry resumes from the last saved step.\""
  },
  {
   "id": "U-43",
   "behaviour": "Cancel task acts at once without asking; the in-flight step's output is discarded; status Cancelled with 'Cancelled. 1 finished step was kept. Unfinished steps will produce no saved results.' and stays so.",
   "handling": "sound",
   "observed": true,
   "evidence": "p5.js with STANDIN_STEP_MS=3000: 'long task: big [long]', cancel 4.5 s in (step 2 in flight) -> Cancelled, finished 1, that detail; 4 s later unchanged (no step 2 added).",
   "spec": "decided-unmarked",
   "told": "yes",
   "told_where": "README.md: \"Cancelling preserves completed steps and discards pending output.\""
  },
  {
   "id": "U-44",
   "behaviour": "Since you were away is per browser and person (last-seen time in localStorage): it lists tasks Completed or Cancelled since the last visit, plus every Running, Failed or Interrupted task; completions drop off after the next reload; waiting proposals are not mentioned. Shows only the person's own tasks.",
   "handling": "acceptable",
   "observed": true,
   "evidence": "pw7.js as Theo: started 'crates [fail step 2]' and 'audit [long]', closed context, waited 5 s, reopened -> 'audit Completed · …', 'crates Failed · …'; reload -> only 'crates Failed'; with a pending proposal and reload -> still only crates; with nothing running -> 'You’re caught up on background work.'; as Ana -> caught up, no Theo items.",
   "spec": "decided-unmarked",
   "told": "no",
   "told_where": ""
  },
  {
   "id": "U-45",
   "behaviour": "At 1440 px all regions are on the main screen. Below that (1024, 800, 600, 375 px tested) Bots/Conversations fold behind 'Toggle navigation' and the tools (Saved instructions, Saved tasks, Memory, Since you were away, Tasks) behind 'Toggle workspace tools' as overlay panels; Escape closes them; the conversation and Message stay in view; no horizontal scroll.",
   "handling": "sound",
   "observed": true,
   "evidence": "pw8.js: width 1440 all shown, toggles hidden; 1024/800/600/375 Bots, Conversations, tools hidden, Conversation and Message shown, toggles shown, no horizontal scroll; at 375 Toggle navigation shows Bots and Conversations (focus to New bot), Toggle workspace tools shows instruction form, Memory, Since you were away and Tasks with Message still visible (screenshot narrow-tools.png).",
   "spec": "decided-unmarked",
   "told": "yes",
   "told_where": "README.md: \"On a narrow screen, use the header buttons to open navigation or workspace tools. Escape closes the open panel.\""
  },
  {
   "id": "U-46",
   "behaviour": "Missing DATA_DIR is created. Unwritable folder, invalid JSON or JSON of an unexpected shape in workspace.json make the process exit at start with a raw Node stack trace and no recovery advice; the damaged file is left as it was and records/ untouched.",
   "handling": "poor",
   "observed": true,
   "evidence": "DATA_DIR=./_audit/missing/deeper -> created, workspace.json written, served. DATA_DIR inside a chmod 500 folder -> 'Error: EACCES: permission denied, mkdir' stack, exit 1; DATA_DIR=chmod 500 folder -> EACCES open '.workspace-next.json' stack. '{not json' -> 'SyntaxError: Expected property name ...' stack from store.js, file unchanged. '{\"hello\":1}' -> 'TypeError: Cannot convert undefined or null to object' at visitConversations, process exits, file unchanged.",
   "spec": "silent",
   "told": "no",
   "told_where": "",
   "rerun": true
  },
  {
   "id": "U-49",
   "behaviour": "Field names are passed through as typed. 'what is the STATUS of ORD-1001' -> 'ORD-1001 has no STATUS.'; 'set the Status of ORD-1001 to closed' previews 'Status: ∅ → closed' and confirming creates a second field Status beside status, so the record then answers differently by capitalization. Reader rules still apply (Ana cannot see ORD-1001).",
   "handling": "poor",
   "observed": true,
   "evidence": "p2.js/p12.js as Maya: 'what is the STATUS of ORD-1001' -> 'ORD-1001 has no STATUS.' vs 'The status of ORD-1001 is open.'; 'set the Status of ORD-1001 to closed' preview from null; confirming 'set the Status of ORD-1001 to open' -> record {status:'closed', Status:'open'}; 'what is the Status of ORD-1001' -> open while status -> closed (also after restart, p13.js). Ana: 'I can't see a record called ORD-1001.'.",
   "spec": "silent",
   "told": "no",
   "told_where": "",
   "rerun": true
  },
  {
   "id": "U-50",
   "behaviour": "The typed identifier is not kept: 'what is the status of ORD-1001A' is answered 'The status of ORD-1001 is open.' (the stand-in matches the prefix and the app passes it through); 'set the status of ORD-1001A to closed' gets the fallback 'You said: ...' and no proposal. ORD-1001 still answers.",
   "handling": "poor",
   "observed": true,
   "evidence": "p2.js as Maya: 'what is the status of ORD-1001A' -> 'The status of ORD-1001 is open.'; 'set the status of ORD-1001A to closed' -> 'You said: \"set the status of ORD-1001A to closed\". ...', no proposal; 'what is the status of ORD-1001' -> open.",
   "spec": "silent",
   "told": "no",
   "told_where": "",
   "rerun": true
  },
  {
   "id": "U-54",
   "behaviour": "With DATA_DIR read-only, actions fail with HTTP 500 'The workspace could not save this action. Please try again.' and nothing is reported as saved. But a reply that was already pending stays pending forever: the conversation shows '... is replying' and refuses new messages (409) with no Retry, even after write access returns, until the server is restarted (then it becomes failed with Retry). Earlier work survives.",
   "handling": "poor",
   "observed": true,
   "evidence": "p6.js (STANDIN_SLOW_MS=2000): sent 'hello [slow]', chmod 500 DATA_DIR; Save instruction -> 500 that message; confirm proposal -> 500; after 2.6 s and 5.6 s reply still {status:'pending'}; send -> 409 'Finish or retry the last reply first.'; chmod 700 -> Save instruction 200 but reply still pending. Server output: 'Reply progress could not be saved.'. After restart: instruction Tone present, proposal still pending, reply failed with 'The server restarted before the reply finished...'.",
   "spec": "silent",
   "told": "no",
   "told_where": "",
   "rerun": true
  },
  {
   "id": "U-57",
   "behaviour": "A provider failure in a task is reported on that task (Failed + Retry task) and the rest stays usable. A storage error during a task step leaves that task shown as Running with no progress, forever, until restart (then Interrupted); the server only logs 'Background task progress could not be saved.'. Other reads and actions keep working once storage is writable.",
   "handling": "poor",
   "observed": true,
   "evidence": "p5.js: 'crates/plan [fail step 2]' -> Failed with 'Step 2 failed. Retry resumes here...', other conversations usable. p6.js: 'long task: crates [long]' then DATA_DIR chmod 500 -> task ['Running',0] at once and 3 s later; /api/state 200; after restoring write access still Running 0; log 'Background task progress could not be saved.'; after restart Interrupted, 0 steps.",
   "spec": "silent",
   "told": "no",
   "told_where": "",
   "rerun": true
  },
  {
   "id": "U-58",
   "behaviour": "After Send and Retry focus returns to Message; after Save memory to the first Edit memory button. After a keyboard Confirm changes or Reject changes, focus moves to the same-named button of the next proposal on screen, so a second Enter confirms or rejects another proposal.",
   "handling": "poor",
   "observed": true,
   "evidence": "pw4.js/pw5.js: two proposals (ORD-1004 status open→closed, ACC-2003 tier bronze→gold); focus Confirm changes of the first, Enter -> focus on Confirm changes inside the ACC-2003 proposal; Enter again -> both Change results 'Confirmed...', 'what is the tier of ACC-2003' -> gold. Same with Reject: second Enter rejected the other proposal. After Send/Retry -> TEXTAREA message; after Save memory -> BUTTON Edit memory.",
   "spec": "silent",
   "told": "no",
   "told_where": "",
   "rerun": true
  },
  {
   "id": "U-60",
   "behaviour": "Malformed requests get clear 4xx messages (400 not valid JSON, 415 send JSON, 404 unavailable). Unexpected errors return 500 'The workspace could not save this action. Please try again.' whatever the cause, and the server output records nothing about them (no error, no stack). No token in either.",
   "handling": "poor",
   "observed": true,
   "evidence": "p10.js: '{bad' and '[1,2]' -> 400 'The request was not valid JSON.'; text/plain -> 415; text 123 -> 400 'Message must contain between 1 and 12000 characters.'; unknown action -> 404. p6.js read-only DATA_DIR: Save instruction / confirm / New conversation -> 500 'could not save'; server log had only 'Stillpoint is ready...', 'Background task progress could not be saved.', 'Reply progress could not be saved.' (nothing for the three 500s).",
   "spec": "silent",
   "told": "no",
   "told_where": "",
   "rerun": true
  }
 ],
 "extras": [
  {
   "what": "Dark mode toggle (Toggle dark mode button, remembered in localStorage)",
   "where": "public/app.js setTheme, header",
   "worth": "value",
   "why": "Comfortable reading option; does not interfere with required controls."
  },
  {
   "what": "Empty-state example prompts (Count my orders, Review memory, Start a research task)",
   "where": "public/index.html #examples",
   "worth": "value",
   "why": "Guided start for a new person; fills the Message box without sending."
  },
  {
   "what": "Loopback-only binding, Host header check, Origin check and a strict Content-Security-Policy",
   "where": "server.js",
   "worth": "value",
   "why": "Blocks cross-site actions and DNS-rebinding against a passwordless local app; the app is only reachable at localhost/127.0.0.1 as asked ('on this computer')."
  },
  {
   "what": "Any token-shaped text (sk-local- + 12 chars) in messages, memory and step output replaced by '[provider token hidden]'",
   "where": "lib/workspace.js clean()",
   "worth": "neutral",
   "why": "Prevents echoing a pasted token, but silently alters what the person typed."
  },
  {
   "what": "'Active on <bot>: <instruction>' line in Saved instructions",
   "where": "public/app.js renderTools",
   "worth": "value",
   "why": "Shows which instruction text the open bot uses, since Use copies the text."
  },
  {
   "what": "Skip to message link and Escape closing folded panels",
   "where": "public/index.html, public/app.js",
   "worth": "value",
   "why": "Keyboard comfort."
  }
 ],
 "spec_notes": "docs/[tool]/spec.md (R-1..R-5, 39 lines) states requirements tied to request lines and decides several things the request leaves open in ordinary requirement lines without marking them as the builder's choice: browser-specific sessions (U-1), Use copies an instruction to the bot (U-17), readers/type/identity immutable (U-29), a mismatched value or claimed next id produces a conflict rather than reserving ids (U-32/U-33/U-34), add step goes to the latest running task (U-39), restart turns tasks into Interrupted with no automatic resume (U-41), Since you were away covers new completions, running work and issues (U-44), and narrow widths fold workspace controls (U-45). None is marked open for the customer. It pins fixture facts (Maya sees three orders, cannot read ORD-1003, ORD-1005 next) that hold only for the starting records. It is silent on name validation and duplicates, conversation naming, value validation, field-name capitals, unknown identifiers, damaged data and storage failures. No contradiction of the request found; owner is not listed as protected although the request is silent on it.",
 "tests_notes": "One file, test/app.test.js, with 8 broad scenario tests that each cover many behaviours (TC-2: bot creation, rename, fail/retry, conversation switching, cross-person 404, restart and switch person; TC-7: steer, step failure, retry, cancel, restart of tasks and replies). They drive the programmatic createServer({dataDir, token}) and the private /api/action protocol (action names such as decideProposal, retryReply, cancelTask) and assert the internal state shape (workspace.bots, activeBot, conversations[].proposals[].status 'conflict', reply.status, task.finished), so another correct build would fail them. TC-7 relies on fixed delays (delay(800), delay(180)) with STANDIN_STEP_MS=140, so it is timing-dependent. TC-8 checks the raw HTML for aria-label=\"...\" and >label</label> strings rather than accessible names in a browser. Nothing exercises the browser UI (focus, folding, Since you were away, polling), storage failures, damaged data or name/field validation.",
 "maintainer": "lib/workspace.js is one closure where every action, reply and task step rewrites the whole single workspace.json through store.transact, and correctness of retries, cancel and restart depends on runId/attempt/status checks interleaved with async provider calls; error paths that cannot write simply log and leave replies or tasks in their in-memory pending/Running state. On the client, public/app.js re-renders by fingerprint and restores focus to any button with the same accessible name, which is what sends keyboard focus to another proposal's Confirm changes; changing labels or list rendering there needs care."
}
```

## Audit of delivery Y

```json
{
 "code": "Y",
 "shares": 3,
 "stated": [
  {
   "id": "S-1",
   "built": "yes",
   "observed": true,
   "evidence": "Browser (Playwright, headless chromium) at 1440x900: PORT=49592 DATA_DIR=audit/d1 node server.js; Continue as Maya, saved token, typed \"Can you help me plan my week?\" + Send -> article \"Message from Assistant\" with the stand-in reply; \"How many orders can you see?\" -> \"I can see 3 order record(s).\"",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-2",
   "built": "yes",
   "observed": true,
   "evidence": "package.json has no dependencies/devDependencies, no node_modules; every require in server.js and lib/ is node:* or a local file; server started with plain node server.js",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-3",
   "built": "yes",
   "observed": true,
   "evidence": "PORT=49592/53042/54762 node server.js -> \"Local chat is ready at http://127.0.0.1:<PORT>\" and served there; with PORT and DATA_DIR unset (port 3000 free): log \"ready at http://127.0.0.1:3000\", curl http://127.0.0.1:3000/ -> 200 text/html",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-4",
   "built": "yes",
   "observed": true,
   "evidence": "curl -i http://127.0.0.1:49592/ -> 200 text/html, <title>Local Chat</title>; page shows Continue as Maya/Theo/Ana",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-5",
   "built": "yes",
   "observed": true,
   "evidence": "DATA_DIR=audit/d1 -> d1/state.json and d1/provider-token only; nothing written elsewhere in the work folder; with DATA_DIR unset started from the work folder -> ./data/state.json created (removed afterwards)",
   "spec": "stated",
   "proved": "fails",
   "proved_by": "server.js createServer: `options.dataDir ?? process.env.DATA_DIR ?? './data'` -> `options.dataDir ?? './data'` (DATA_DIR ignored); npm test 18 pass 1 fail: \"CLI preserves unsupported and nested damaged snapshots and dangling entries\" (it spawns server.js with DATA_DIR pointing at a damaged snapshot and expects a refusal). Restored; npm test back to 19/19 pass."
  },
  {
   "id": "S-6",
   "built": "yes",
   "observed": true,
   "evidence": "HTTP API (/api/person, /api/actions/*, /api/view) script p1-p6.cjs: as Ana on DATA_DIR=d2: bots [Assistant, Week Planner], 2 conversations, 19 turns, memory [\"restart fact\"], instruction Brief, bot instructions, saved task Count, tasks [stop me: Cancelled 2 steps, away test: Completed 8], token saved via Save token, ORD-1004 status shipped (confirmed). kill <pid>, restart same DATA_DIR with no PROVIDER_TOKEN: identical view, ready=true, \"what is the status of ORD-1004\" -> shipped, created ORD-1005 still counted",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-7",
   "built": "yes",
   "observed": true,
   "evidence": "diff -r provider base/provider -> identical; lib/chat.js requires ../provider/standin respond, lib/tasks.js requires runStep; replies observed are exactly the stand-in rule texts (e.g. You said: ... (Assistant has 1 message(s) ...))",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-8",
   "built": "yes",
   "observed": true,
   "evidence": "HTTP API (/api/person, /api/actions/*, /api/view) script p1-p6.cjs: reply text equals stand-in output.text in every probe; remember -> fact added to bot.memory; forget -> removed; clarify (\"update ORD-1002\" then \"the status to shipped\") -> proposal; proposal -> stored in conversation.proposals, nothing written; task -> Tasks entry with steps run; steer -> \"add step: check the totals\" appended to running task",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-9",
   "built": "yes",
   "observed": true,
   "evidence": "HTTP API (/api/person, /api/actions/*, /api/view) script p1-p6.cjs: \"REMEMBER THAT I like tea\" -> \"I'll remember that I like tea.\"; \"WHAT DID I ASK FIRST\" -> \"You first asked: ...\"; \"What Do You Remember\" -> list; \"remember that forget me not\" -> remembered (first rule wins, not forget)",
   "spec": "absent",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-10",
   "built": "yes",
   "observed": true,
   "evidence": "HTTP API (/api/person, /api/actions/*, /api/view) script p1-p6.cjs: Maya \"what is the status of ORD-1003\" and \"set the status of ORD-1003 to closed\" -> \"I can't see a record called ORD-1003.\" with no proposal; Maya \"update ACC-2002\" -> can't see, proposals 0; Theo reads ORD-1003",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-11",
   "built": "yes",
   "observed": true,
   "evidence": "HTTP API (/api/person, /api/actions/*, /api/view) script p1-p6.cjs: fresh DATA_DIR=d3, \"what is the type of <id>\" for all 7 ids per person: maya ORD-1001,ORD-1002,ORD-1004,ACC-2001,ACC-2003; theo ORD-1001,ORD-1003,ACC-2001,ACC-2002; ana ORD-1004,ACC-2001,ACC-2003; counts maya 3/2, theo 2/2, ana 1/2",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-12",
   "built": "yes",
   "observed": true,
   "evidence": "after confirming ORD-1001 closed and creating ORD-1005 on d1: diff -r records base/records -> identical; working copy in d1/state.json records shows ORD-1001 closed and ORD-1005; survives restart (S-6)",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-13",
   "built": "yes",
   "observed": true,
   "evidence": "HTTP API (/api/person, /api/actions/*, /api/view) script p1-p6.cjs: fresh DATA_DIR=d3 (while d1 has ORD-1001 closed): \"what is the status of ORD-1001\" -> \"The status of ORD-1001 is open.\"; readable sets match records.json",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-14",
   "built": "yes",
   "observed": true,
   "evidence": "HTTP API (/api/person, /api/actions/*, /api/view) script p1-p6.cjs: Maya confirms \"create an order for Acme Tools totalling 250\" -> \"Changes confirmed. Created ORD-1005.\"; state.json record {id ORD-1005, readers [\"maya\"]}; Theo and Ana -> \"I can't see a record called ORD-1005.\"",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-15",
   "built": "yes",
   "observed": true,
   "evidence": "Browser (Playwright, headless chromium) at 1440x900: screenshot shot-desktop.png: centred conversation column, person messages in tinted bubbles right, bot replies left with author labels, system-ui 15px / 23px line height, composer docked at the bottom, side rails for bots and tools",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-16",
   "built": "yes",
   "observed": true,
   "evidence": "Browser (Playwright, headless chromium) at 1440x900: each reply is shown as plain readable text under the bot name, one block per turn; notices (e.g. no step added) appear as a separate small status line under the reply",
   "spec": "absent",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-17",
   "built": "yes",
   "observed": true,
   "evidence": "HTTP API (/api/person, /api/actions/*, /api/view) script p1-p6.cjs: new conversation: \"what did I ask first\" -> \"This is the first thing you've asked.\"; in Week Planner conversation 2 \"second conversation about travel\" -> \"(Week Planner has 1 message(s) ...)\" while conversation 1 had 2; a reply after a failed turn counts it; other conversations' messages never counted or quoted",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-18",
   "built": "yes",
   "observed": true,
   "evidence": "HTTP API (/api/person, /api/actions/*, /api/view) script p1-p6.cjs: Helper bot \"what do you remember\" -> nothing while Maya's Assistant remembers \"my desk is by the window\"; counts per person reflect only readable records; history per conversation (S-17)",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-19",
   "built": "yes",
   "observed": true,
   "evidence": "HTTP API (/api/person, /api/actions/*, /api/view) script p1-p6.cjs: fresh conversation \"what did I ask first\" -> \"This is the first thing you've asked.\"; after \"  hello there [slow]  \", \"WHAT DID I ASK FIRST\" -> \"You first asked: \\\"what did I ask first\\\".\"",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-20",
   "built": "yes",
   "observed": true,
   "evidence": "HTTP API (/api/person, /api/actions/*, /api/view) script p1-p6.cjs: \"  hello there [slow]  \" -> \"You said: \\\"hello there\\\". (Assistant has 2 message(s) from you in this conversation.)\"; \"Hello [fail once]\" + Retry -> \"You said: \\\"Hello\\\". (Assistant has 4 message(s) ...)\"",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-21",
   "built": "yes",
   "observed": true,
   "evidence": "Browser (Playwright, headless chromium) at 1440x900: \"update ORD-1004\" -> \"Which field of ORD-1004 should I change, and to what value?\"; next \"the status to shipped\" -> \"I propose one change: ORD-1004 status: open → shipped. Confirm to apply it.\" with a Proposed changes region",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-22",
   "built": "yes",
   "observed": true,
   "evidence": "Browser (Playwright, headless chromium) at 1440x900: New bot, Bot name \"Planner\", Save bot name -> Bots nav lists Assistant, Planner [aria-current]; Rename bot -> \"Week Planner\"; \"who are you\" -> \"I am Week Planner. I have no special instructions.\"",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-23",
   "built": "yes",
   "observed": true,
   "evidence": "Browser (Playwright, headless chromium) at 1440x900: Week Planner has 2 conversations; switched to Assistant (its own history), back to Week Planner (opens last conversation with its 2 messages), opened conversation 1, reload -> same bot and conversation current with its 4 messages",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-24",
   "built": "yes",
   "observed": true,
   "evidence": "Browser (Playwright, headless chromium) at 1440x900: Save instruction Brief/\"Answer briefly.\" -> Use Brief, Edit Brief, Delete Brief; Use Brief then \"who are you\" -> \"My instructions: Answer briefly.\"; Edit Brief refilled both textboxes, saved \"Answer in bullet points.\" under the same name; active text changes after Use Brief again -> \"My instructions: Answer in bullet points.\" (README says Use again activates an edit)",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-25",
   "built": "yes",
   "observed": true,
   "evidence": "Browser (Playwright, headless chromium) at 1440x900: Save task Count/\"how many orders can you see\" -> Run Count, Edit Count, Delete Count; Run Count -> my message + \"I can see 1 order record(s).\"; Edit Count refilled the fields, changed to accounts, Run Count -> \"I can see 2 account record(s).\"",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-26",
   "built": "yes",
   "observed": true,
   "evidence": "Browser (Playwright, headless chromium) at 1440x900: \"remember that I prefer mornings\" -> Memory list item \"I prefer mornings\" with Edit memory and Forget",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-27",
   "built": "yes",
   "observed": true,
   "evidence": "Browser (Playwright, headless chromium) at 1440x900: Edit memory, Memory text \"I prefer evenings\", Save memory -> item updated; \"what do you remember\" -> \"I remember: I prefer evenings.\"; Forget -> 0 items and \"I don't remember anything about you yet.\"",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-28",
   "built": "yes",
   "observed": true,
   "evidence": "HTTP API (/api/person, /api/actions/*, /api/view) script p1-p6.cjs: \"remember that my desk is by the window\" -> \"I'll remember that my desk is by the window.\" and bot.memory gains it",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-29",
   "built": "yes",
   "observed": true,
   "evidence": "HTTP API (/api/person, /api/actions/*, /api/view) script p1-p6.cjs: \"forget that I like tea\" -> \"I've forgotten \\\"I like tea\\\".\" and removed; \"forget forget me not\" -> \"I've forgotten \\\"forget me not\\\".\" and removed",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-30",
   "built": "yes",
   "observed": true,
   "evidence": "HTTP API (/api/person, /api/actions/*, /api/view) script p1-p6.cjs: with facts -> \"I remember: I like tea; forget me not.\"; with none -> \"I don't remember anything about you yet.\"",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-31",
   "built": "yes",
   "observed": true,
   "evidence": "HTTP API (/api/person, /api/actions/*, /api/view) script p1-p6.cjs: DATA_DIR=d2: Ana has 2 bots, memory, instruction, saved task, 2 tasks; Maya sees only Assistant, no memory/instructions/saved tasks/tasks; Maya POST rename-bot and send with Ana's botId -> 404 \"This item is unavailable in the current workspace.\"; Ana's session switching to Theo shows Theo's data, back to Ana restores hers",
   "spec": "stated",
   "proved": "fails",
   "proved_by": "lib/chat.js view(): `savedWorkspaces[person.id]` -> `savedWorkspaces[Object.keys(savedWorkspaces)[0]]` (every person shown the first workspace); npm test 15 pass 4 fail, incl. \"failed and cancelled tasks keep committed steps and ignore obsolete controls\" and \"setup, record scoping, saved workspace and transparent provider echo\". Restored; 19/19 pass."
  },
  {
   "id": "S-32",
   "built": "yes",
   "observed": true,
   "evidence": "HTTP API (/api/person, /api/actions/*, /api/view) script p1-p6.cjs: Maya: Assistant remembers \"my desk is by the window\"; new bot Helper \"what do you remember\" -> \"I don't remember anything about you yet.\"",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-33",
   "built": "yes",
   "observed": true,
   "evidence": "HTTP API (/api/person, /api/actions/*, /api/view) script p1-p6.cjs: \"remember that my desk is by the window\" in one conversation; New conversation in same bot, \"what do you remember\" -> \"I remember: my desk is by the window.\"",
   "spec": "stated",
   "proved": "fails",
   "proved_by": "lib/chat.js reply(): memory passed to respond filtered to facts whose text appears in this conversation's turns; npm test 18 pass 1 fail: \"setup, record scoping, saved workspace and transparent provider echo\". Restored; 19/19 pass."
  },
  {
   "id": "S-34",
   "built": "yes",
   "observed": true,
   "evidence": "HTTP API (/api/person, /api/actions/*, /api/view) script p1-p6.cjs: Maya: status of ORD-1001 open, ord-1002 shipped, name of acc-2001 Acme Tools; after confirm, follow-up reads return the new value",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-35",
   "built": "yes",
   "observed": true,
   "evidence": "HTTP API (/api/person, /api/actions/*, /api/view) script p1-p6.cjs: Maya \"how many orders can you see\" -> \"I can see 3 order record(s).\", accounts -> 2; Theo 2/2; Ana 1/2",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-36",
   "built": "yes",
   "observed": true,
   "evidence": "HTTP API (/api/person, /api/actions/*, /api/view) script p1-p6.cjs: \"what is the status of ord-1002\" -> \"The status of ORD-1002 is shipped.\"; \"what is the tier of ORD-1001\" -> \"ORD-1001 has no tier.\"; \"what is the status of ORD-1003\" as Maya -> \"I can't see a record called ORD-1003.\"; acc-2001 lowercase matched",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-37",
   "built": "yes",
   "observed": true,
   "evidence": "Browser (Playwright, headless chromium) at 1440x900: \"set the status of ORD-1004 to closed\" -> region Proposed changes \"ORD-1004 status: open → closed\" with Confirm changes / Reject changes; create shows \"Create order, Customer: Nova, Total: 12, Status: open, Access: Ana only, Order ID: assigned on confirmation\"",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-38",
   "built": "yes",
   "observed": true,
   "evidence": "HTTP API (/api/person, /api/actions/*, /api/view) script p1-p6.cjs: \"set the status of ORD-1001 to closed\" -> \"I propose one change: ORD-1001 status: open → closed. Confirm to apply it.\"; then status still open; ORD-1003 -> can't see, no proposal",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-39",
   "built": "yes",
   "observed": true,
   "evidence": "HTTP API (/api/person, /api/actions/*, /api/view) script p1-p6.cjs: \"update ORD-1002\" -> \"Which field of ORD-1002 should I change, and to what value?\" (no write); \"the status to shipped\" -> \"I propose one change: ORD-1002 status: shipped → shipped. Confirm to apply it.\" same as set form; \"update ORD-1003\" -> can't see",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-40",
   "built": "yes",
   "observed": true,
   "evidence": "HTTP API (/api/person, /api/actions/*, /api/view) script p1-p6.cjs: \"create an order for Acme Tools totalling 250\" -> \"I propose creating one order: customer Acme Tools, total 250, status open. Confirm to apply it.\"; orders count still 3 before confirm",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-41",
   "built": "yes",
   "observed": true,
   "evidence": "HTTP API (/api/person, /api/actions/*, /api/view) script p1-p6.cjs: after the proposal and before Confirm changes, \"what is the status of ORD-1001\" -> open; records in state.json unchanged; create counted only after confirm",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-42",
   "built": "yes",
   "observed": true,
   "evidence": "HTTP API (/api/person, /api/actions/*, /api/view) script p1-p6.cjs: confirm ORD-1001 status -> \"Changes confirmed and applied.\"; status closed, customer Acme Tools, total 125 unchanged",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-43",
   "built": "yes",
   "observed": true,
   "evidence": "HTTP API (/api/person, /api/actions/*, /api/view) script p1-p6.cjs: confirm create -> \"Changes confirmed. Created ORD-1005.\"; Maya: customer Acme Tools, total 250, status open, orders 4; Theo and Ana can't see ORD-1005",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-44",
   "built": "yes",
   "observed": true,
   "evidence": "HTTP API (/api/person, /api/actions/*, /api/view) script p1-p6.cjs: reject ORD-1002 proposal -> \"Changes rejected. The records were left as they were.\"; confirm afterwards stays rejected; rejected total 999 -> total still 80; rejected create Zeta -> orders still 4, ORD-1006 can't see; UI reject on ORD-1004 -> status still open",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-45",
   "built": "yes",
   "observed": true,
   "evidence": "HTTP API (/api/person, /api/actions/*, /api/view) script p1-p6.cjs: confirm the same proposal twice -> same result, one change; create confirmed twice -> same \"Created ORD-1005\", one record; same send submission id posted twice -> same turnId receipt, one turn",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-46",
   "built": "yes",
   "observed": true,
   "evidence": "Browser (Playwright, headless chromium) at 1440x900: after Reject changes a region Change result: \"Changes rejected. The records were left as they were.\"; after Confirm: \"Changes confirmed and applied.\" / \"Changes confirmed. Created ORD-1005.\"",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-47",
   "built": "yes",
   "observed": true,
   "evidence": "HTTP API (/api/person, /api/actions/*, /api/view) script p1-p6.cjs: \"research: market [x] sizing\" -> \"I'll work on \\\"market  sizing\\\" in the background and tell you when it is done.\"; results arrive one at a time in order at ~584, 1104, 1624 ms",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-48",
   "built": "yes",
   "observed": true,
   "evidence": "HTTP API (/api/person, /api/actions/*, /api/view) script p1-p6.cjs: 3 steps: Collect what is known about / Compare the options for / Write the summary of; \"Long task: weekly review [long]\" -> 8 steps with Check part 1..5 before the summary",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-49",
   "built": "yes",
   "observed": true,
   "evidence": "HTTP API (/api/person, /api/actions/*, /api/view) script p1-p6.cjs: default ~520 ms per step; server with STANDIN_STEP_MS=150 -> steps at 195, 366, 529 ms; each result \"Done: <step text>\"",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-50",
   "built": "yes",
   "observed": true,
   "evidence": "Browser (Playwright, headless chromium) at 1440x900: \"long task: away test [long]\" Running, page closed, 6 s later reopened in the same browser context -> Task status Completed with all 8 steps",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-51",
   "built": "yes",
   "observed": true,
   "evidence": "Browser (Playwright, headless chromium) at 1440x900: after reopening: region Since you were away \"Task #2 · away test — Completed\"; second probe: \"Task #1 · flaky — Failed — needs attention | Task #4 · big job — Running\"",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-52",
   "built": "yes",
   "observed": true,
   "evidence": "HTTP API (/api/person, /api/actions/*, /api/view) script p1-p6.cjs: during [long] task \"add step: check the totals\" -> \"I'll add \\\"check the totals\\\" to the task that is running.\"; task count 9; last result \"Done: check the totals\"; with no running task -> reply plus notice \"No step was added. No task is running in this conversation.\"",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-53",
   "built": "yes",
   "observed": true,
   "evidence": "HTTP API (/api/person, /api/actions/*, /api/view) script p1-p6.cjs: while weekly review task Running, \"how many orders can you see\" -> \"I can see 2 order record(s).\" with Task status still Running; in the browser a [slow] message showed \"Assistant is preparing a reply…\" and replied while big job ran",
   "spec": "absent",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-54",
   "built": "yes",
   "observed": true,
   "evidence": "Browser (Playwright, headless chromium) at 1440x900: Cancel task on running \"stop me\" -> Task status Cancelled, \"Remaining work was stopped. Any in-flight step result was discarded. Completed steps are shown below.\" with the 2 finished steps; no further steps 1.5 s later",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-55",
   "built": "yes",
   "observed": true,
   "evidence": "Playwright headless chromium against node server.js (fresh DATA_DIR in work folder): sent `long task: plan [fail step 2]`: Task status Failed, steps list shows only 'Done: Collect what is known about plan', note 'Step 2 failed. Retry to continue from that step.', Retry task present; Retry task -> Running '1 of 3 steps finished' -> Completed with the three steps once each. Separately `long task: audit [long]`, stopped the server (SIGTERM by pid) with 2 of 8 steps done, restarted on the same DATA_DIR: Task status Interrupted, the 2 finished steps listed (no in-flight step shown as finished), note 'The server stopped. Saved steps are shown below. Retry to resume with the first unfinished step.', still Interrupted 2 s later, Retry task -> Completed with 8 distinct steps; the conversation's 14 message articles were all still there.",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-56",
   "built": "yes",
   "observed": true,
   "evidence": "Playwright headless chromium against node server.js (fresh DATA_DIR in work folder): `long task: plan [fail step 2]` -> article 'Task: plan' with Task status 'Failed', finished steps ['Done: Collect what is known about plan'], Retry task button, no alert; the Conversation region still held its 4 message articles (both requests and replies).",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-57",
   "built": "yes",
   "observed": true,
   "evidence": "Playwright headless chromium against node server.js (fresh DATA_DIR in work folder): empty DATA_DIR, no PROVIDER_TOKEN, Continue as Ana: region Setup reads 'Connect the offline provider with sk-local- followed by at least 12 letters or digits. You can save it here or start the server with PROVIDER_TOKEN.' with Provider token / Save token; Send is disabled until a token is saved; refused tokens show the alert 'The provider refused this token. Check its format and try again.' and keep the textbox usable and focused; the token field is masked, cleared after submit; after saving, no page, API response, or server output contains the token (it is stored in DATA_DIR/provider-token only).",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-58",
   "built": "yes",
   "observed": true,
   "evidence": "Playwright headless chromium against node server.js (fresh DATA_DIR in work folder): keyboard only: Enter on Continue as Maya; typed token in Provider token + Enter saved it (focus moved to Message); typed a message + Enter sent it; Tab order from Send ran Instruction name, Instruction text, Save instruction, Task name, Task request, Save task, Edit memory, Forget, New bot, Assistant, Rename bot, New conversation, the conversation button, Switch person, Conversation, Message; Enter on New bot focused Bot name, typing + Enter created KeyBot; Tab/typing/Enter saved instruction Tone; Enter on Use Tone then `who are you` replied 'I am KeyBot. My instructions: Be brief'; Enter on Confirm changes applied the proposal and moved focus to the Change result heading. At 375 px, Workspace/Tools toggles open panels and Escape closes them returning focus to the toggle.",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-59",
   "built": "yes",
   "observed": true,
   "evidence": "Playwright headless chromium against node server.js (fresh DATA_DIR in work folder): GET / on a fresh DATA_DIR shows only the welcome card with buttons whose accessible names are exactly 'Continue as Maya', 'Continue as Theo', 'Continue as Ana' (one each); no password field; clicking one enters the workspace.",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-60",
   "built": "yes",
   "observed": true,
   "evidence": "Playwright headless chromium against node server.js (fresh DATA_DIR in work folder): as Maya, clicked Switch person: workspace hidden and the three Continue as buttons shown again; continued as Theo from there.",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-61",
   "built": "yes",
   "observed": true,
   "evidence": "Playwright headless chromium against node server.js (fresh DATA_DIR in work folder): as Maya saved instruction Tone (Used), saved task Ping, remembered 'likes tea', started `long task: maya work`; Switch person -> Continue as Theo: Bots [Assistant] only, Saved instructions/Saved tasks/Memory/Tasks empty, 0 message articles, `who are you` -> 'I have no special instructions.', `what do you remember` -> 'I don't remember anything about you yet.'. Switch person -> Continue as Maya: Tone, Ping, 'likes tea', Task: maya work and the 4 messages all back; `who are you` -> 'My instructions: Be brief', `what do you remember` -> 'I remember: likes tea.' (also in a second run Maya's Clerk Two bot and conversations returned, Theo saw none).",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-62",
   "built": "yes",
   "observed": true,
   "evidence": "Playwright headless chromium against node server.js (fresh DATA_DIR in work folder): as Maya with 10 messages, page.reload(): no Continue as buttons, profile shows Maya, the same 10 message articles shown (cookie local_chat session).",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-63",
   "built": "yes",
   "observed": true,
   "evidence": "Playwright headless chromium against node server.js (fresh DATA_DIR in work folder): viewport 1440x900: Setup, Provider token, Save token, Bots, New bot, Rename bot, Conversations, New conversation, Conversation, Message, Send, Saved instructions (+ Instruction name/text, Save instruction), Saved tasks (+ Task name/request, Save task), Memory, Tasks, Switch person all rendered with non-zero boxes inside the viewport without opening anything; Proposed changes with Confirm/Reject at top 376, Change result at top 376, Since you were away at top 69 of the right column, a Task article with Cancel task at top 174. Narrow-only toggles (Workspace, Tools) are not shown at 1440. Memory region sits below the fold of the right column (scrolls, no menu).",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-64",
   "built": "yes",
   "observed": true,
   "evidence": "Playwright headless chromium against node server.js (fresh DATA_DIR in work folder): at widths 900, 700 and 375 (height 800): Conversation region spans the width (top 54, height 630), Message textbox and Send button visible inside the viewport, no horizontal scroll (scrollWidth == innerWidth); Bots/Tools panels folded behind buttons Workspace and Tools (aria-expanded), which open them while Message stays in view; Escape closes.",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-65",
   "built": "yes",
   "observed": true,
   "evidence": "Playwright headless chromium against node server.js (fresh DATA_DIR in work folder): no token saved: region 'Setup' (aria-labelledby heading) explains the sk-local- format and PROVIDER_TOKEN, contains textbox 'Provider token' and button 'Save token'; no token value appears anywhere.",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-66",
   "built": "yes",
   "observed": true,
   "evidence": "Playwright headless chromium against node server.js (fresh DATA_DIR in work folder): Save token with 'bad-token', 'sk-local-short', 'sk-local-abc!defghijkl' and '' each -> refused alert, Setup stays; 'sk-local-abcdefghijkl' accepted (Setup gone, replies work); PROVIDER_TOKEN 'sk-local-ABC123def4567' accepted (replies work). Acceptance is the stand-in's check().",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-67",
   "built": "yes",
   "observed": true,
   "evidence": "Playwright headless chromium against node server.js (fresh DATA_DIR in work folder): Save token with 'bad-token': role=alert 'The provider refused this token. Check its format and try again.', Setup still visible, Provider token editable and focused; a later valid token was accepted from the same Setup.",
   "spec": "stated",
   "proved": "passes",
   "proved_by": "Client edit: in public/app.js setup-form submit, `{ errorTarget: byId('setup-error') }` -> `{ errorTarget: document.createElement('p') }` (refused token now shows no alert; confirmed in Playwright: alerts []). npm test: 19/19 pass. (A server-side edit instead, lib/chat.js save-token `fail(400, ...)` -> `return this.view(sessionId);`, fails 'setup, record scoping, saved workspace and transparent provider echo'.) Both edits undone; files identical to the original; suite back to 19/19 pass."
  },
  {
   "id": "S-68",
   "built": "yes",
   "observed": true,
   "evidence": "Playwright headless chromium against node server.js (fresh DATA_DIR in work folder): after a valid token via Save token the Setup region is gone (count 0); `hello there` -> 'You said: \"hello there\". (Assistant has 1 message(s) from you in this conversation.)'; after a restart with the same DATA_DIR and no PROVIDER_TOKEN, Setup absent and `who are you` -> 'I am Assistant. I have no special instructions.'",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-69",
   "built": "yes",
   "observed": true,
   "evidence": "Playwright headless chromium against node server.js (fresh DATA_DIR in work folder): started with PROVIDER_TOKEN=sk-local-ABC123def4567 and an empty DATA_DIR: Continue as Maya shows no Setup region; `who are you` replied 'I am Assistant. I have no special instructions.'; the token string appeared in no page HTML and no /api response.",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-70",
   "built": "yes",
   "observed": true,
   "evidence": "Playwright headless chromium against node server.js (fresh DATA_DIR in work folder): after Save token: page HTML, body text and every /api response checked -> token absent; Provider token input not rendered; a message containing the token is shown and echoed as '[redacted]'; after restart same DATA_DIR: page and API still free of it; server stdout only 'Local chat is ready at ...'. Token is on disk only in DATA_DIR/provider-token (state.json does not contain it).",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-71",
   "built": "yes",
   "observed": true,
   "evidence": "Playwright headless chromium against node server.js (fresh DATA_DIR in work folder): navigation 'Bots' holds buttons with accessible names 'Assistant', 'Clerk Two' (plus New bot, Rename bot); the open bot's button has aria-current='true', others none; selecting Assistant moved aria-current to it.",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-72",
   "built": "yes",
   "observed": true,
   "evidence": "Playwright headless chromium against node server.js (fresh DATA_DIR in work folder): New bot -> Bot name 'Clerk' -> Save bot name: Bots [Assistant (not current), Clerk (aria-current=true)], heading Clerk, empty conversation; `who are you` -> 'I am Clerk. I have no special instructions.'; Assistant and its conversation still present.",
   "spec": "stated",
   "proved": "fails",
   "proved_by": "lib/workspace.js newBot: `workspace.bots.push(bot);` -> `workspace.bots.splice(0, workspace.bots.length, bot);` (new bot replaces existing ones; Playwright showed Bots [Clerk] only). npm test: 18 pass, 1 fail: 'bot references survive duplicate names, navigation, rename and restart'. Edit undone; suite back to 19/19 pass."
  },
  {
   "id": "S-73",
   "built": "yes",
   "observed": true,
   "evidence": "Playwright headless chromium against node server.js (fresh DATA_DIR in work folder): on Clerk, Rename bot filled Bot name with 'Clerk'; changed to 'Clerk Two' + Save bot name: Bots lists 'Clerk Two' (current), `who are you` -> 'I am Clerk Two. I have no special instructions.'; its conversations kept.",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-74",
   "built": "yes",
   "observed": true,
   "evidence": "Playwright headless chromium against node server.js (fresh DATA_DIR in work folder): fresh DATA_DIR, Continue as Ana and Continue as Theo: Bots navigation contains exactly one bot button 'Assistant' (aria-current=true).",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-75",
   "built": "yes",
   "observed": true,
   "evidence": "Playwright headless chromium against node server.js (fresh DATA_DIR in work folder): navigation 'Conversations' lists the open bot's conversations as buttons ('who are you', 'what did I ask first'; a new empty one 'Untitled chat'), open one aria-current='true'; clicking 'who are you' moved current to it and showed its 4 messages; switching bot shows that bot's conversations.",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-76",
   "built": "yes",
   "observed": true,
   "evidence": "Playwright headless chromium against node server.js (fresh DATA_DIR in work folder): New conversation added 'Untitled chat' marked current with an empty Conversation region; `what did I ask first` there -> 'This is the first thing you've asked.'; the earlier conversation remained listed with its history.",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-77",
   "built": "yes",
   "observed": true,
   "evidence": "Playwright headless chromium against node server.js (fresh DATA_DIR in work folder): Conversation region articles: [Message from Maya 'who are you'], [Message from Assistant 'I am Assistant. ...'], ... each showing its text (multi-line message kept). Note: names use the bot's current name (a reply given as Clerk shows as 'Message from Clerk Two' after the rename).",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-78",
   "built": "yes",
   "observed": true,
   "evidence": "Playwright headless chromium against node server.js (fresh DATA_DIR in work folder): filled textbox 'Message' and clicked button 'Send' -> person article and bot reply added to the open conversation; Message cleared.",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-79",
   "built": "yes",
   "observed": true,
   "evidence": "Playwright headless chromium against node server.js (fresh DATA_DIR in work folder): typed into Message and pressed Enter -> 'line one\\nline two' sent as one person message and answered; Message box emptied.",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-80",
   "built": "yes",
   "observed": true,
   "evidence": "Playwright headless chromium against node server.js (fresh DATA_DIR in work folder): typed 'line one', Shift+Enter, 'line two' -> Message value 'line one\\nline two', no new article (not sent).",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-81",
   "built": "yes",
   "observed": true,
   "evidence": "Playwright headless chromium against node server.js (fresh DATA_DIR in work folder): STANDIN_SLOW_MS=2500, sent `hello [slow]`: 500 ms later a role=status 'Assistant is preparing a reply…' was visible; after the wait the reply 'You said: \"hello\". ...' appeared and the status was gone.",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-82",
   "built": "yes",
   "observed": true,
   "evidence": "Playwright headless chromium against node server.js (fresh DATA_DIR in work folder): sent `hello [fail once]`: person article kept, no bot article, role=alert 'The reply failed. Retry to answer your original message.'",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-83",
   "built": "yes",
   "observed": true,
   "evidence": "Playwright headless chromium against node server.js (fresh DATA_DIR in work folder): after the failure, clicked Retry (one button): articles became [Message from Maya 'hello [fail once]', Message from Assistant 'You said: \"hello\". (Assistant has 4 message(s) ...)'] - the person message once, alert gone; `what did I ask first` still quoted the true first message.",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-84",
   "built": "yes",
   "observed": true,
   "evidence": "Playwright headless chromium against node server.js (fresh DATA_DIR in work folder): region 'Saved instructions' has textboxes 'Instruction name', 'Instruction text' and button 'Save instruction'; saving Tone='Be brief' added buttons Use Tone/Edit Tone/Delete Tone; no message added to the conversation.",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-85",
   "built": "yes",
   "observed": true,
   "evidence": "Playwright headless chromium against node server.js (fresh DATA_DIR in work folder): after saving Tone the region shows buttons named exactly 'Use Tone', 'Edit Tone', 'Delete Tone'.",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-86",
   "built": "yes",
   "observed": true,
   "evidence": "Playwright headless chromium against node server.js (fresh DATA_DIR in work folder): Use Tone on Assistant, `who are you` -> 'I am Assistant. My instructions: Be brief'; in a new conversation of Assistant same reply; on a new bot 'Other' -> 'I am Other. I have no special instructions.'",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-87",
   "built": "yes",
   "observed": true,
   "evidence": "Playwright headless chromium against node server.js (fresh DATA_DIR in work folder): before Use: 'I am Assistant. I have no special instructions.'; after Use Tone: 'I am Assistant. My instructions: Be brief'.",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-88",
   "built": "yes",
   "observed": true,
   "evidence": "Playwright headless chromium against node server.js (fresh DATA_DIR in work folder): Edit Tone filled Instruction name 'Tone' and Instruction text 'Be brief'; changed text to 'Be very brief' + Save instruction -> still one set Use/Edit/Delete Tone; Edit Tone again shows 'Be very brief'; after Use Tone `who are you` -> 'My instructions: Be very brief' (before re-Use the bot kept 'Be brief', as the README says Use copies the text).",
   "spec": "stated",
   "proved": "passes",
   "proved_by": "Client edit: public/app.js editLibrary `byId(kind + '-text').value = entry.text;` -> `byId(kind + '-text').value = '';` (Edit Tone now leaves Instruction text empty; confirmed in Playwright: 'Tone', ''). npm test: 19/19 pass. (A server-side edit instead, lib/chat.js save-instruction passing `{ ...data, itemId: undefined }`, fails 'reply reservations, library state and original history survive navigation' and both subtests of 'reopening storage reveals whether a failed save reached publication'.) Edits undone; files identical to the original; suite back to 19/19 pass."
  },
  {
   "id": "S-89",
   "built": "yes",
   "observed": true,
   "evidence": "Playwright headless chromium against node server.js (fresh DATA_DIR in work folder): Delete Tone removed Use/Edit/Delete Tone (only Save instruction left), still gone after reload.",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-90",
   "built": "yes",
   "observed": true,
   "evidence": "Playwright headless chromium against node server.js (fresh DATA_DIR in work folder): region 'Saved tasks' has 'Task name', 'Task request', 'Save task'; saving Count='how many orders can you see' added Run Count/Edit Count/Delete Count.",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-91",
   "built": "yes",
   "observed": true,
   "evidence": "Playwright headless chromium against node server.js (fresh DATA_DIR in work folder): buttons named exactly 'Run Count', 'Edit Count', 'Delete Count'.",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-92",
   "built": "yes",
   "observed": true,
   "evidence": "Playwright headless chromium against node server.js (fresh DATA_DIR in work folder): Run Count -> new articles [Message from Maya 'how many orders can you see', Message from Assistant 'I can see 3 order record(s).'] in the open conversation.",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-93",
   "built": "yes",
   "observed": true,
   "evidence": "Playwright headless chromium against node server.js (fresh DATA_DIR in work folder): Edit Count filled Task name 'Count' and Task request 'how many orders can you see'; changed request to 'how many accounts can you see' + Save task -> still one Count; Run Count -> 'I can see 2 account record(s).'",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-94",
   "built": "yes",
   "observed": true,
   "evidence": "Playwright headless chromium against node server.js (fresh DATA_DIR in work folder): Delete Count removed its three buttons; still gone after reload.",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-95",
   "built": "yes",
   "observed": true,
   "evidence": "Playwright headless chromium against node server.js (fresh DATA_DIR in work folder): after `remember that likes tea` and `remember that works in Lisbon`, region 'Memory' lists two listitems showing 'likes tea' and 'works in Lisbon' (updated without reload); another bot's Memory is empty.",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-96",
   "built": "yes",
   "observed": true,
   "evidence": "Playwright headless chromium against node server.js (fresh DATA_DIR in work folder): each memory listitem contains buttons 'Edit memory' and 'Forget'.",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-97",
   "built": "yes",
   "observed": true,
   "evidence": "Playwright headless chromium against node server.js (fresh DATA_DIR in work folder): Forget on 'likes tea' -> list ['works in Porto'], `what do you remember` -> 'I remember: works in Porto.'; persisted after reload.",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-98",
   "built": "yes",
   "observed": true,
   "evidence": "Playwright headless chromium against node server.js (fresh DATA_DIR in work folder): Edit memory on 'works in Lisbon' shows textbox 'Memory text' prefilled 'works in Lisbon'; changed to 'works in Porto' + Save memory -> list shows 'works in Porto', `what do you remember` -> 'I remember: likes tea; works in Porto.'",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-99",
   "built": "yes",
   "observed": true,
   "evidence": "Playwright headless chromium against node server.js (fresh DATA_DIR in work folder): `set the status of ORD-1001 to closed` -> region 'Proposed changes' with item 'ORD-1001 status: open → closed' and buttons Confirm changes / Reject changes; `set the total of ORD-1002 to 999` -> 'ORD-1002 total: 80 → 999'; `create an order for Northwind totalling 40` -> 'Create order / Customer: Northwind / Total: 40 / Status: open / Access: Maya only / Order ID: assigned on confirmation'.",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-100",
   "built": "yes",
   "observed": true,
   "evidence": "Playwright headless chromium against node server.js (fresh DATA_DIR in work folder): after Confirm: region 'Change result' 'Changes confirmed and applied.' (status then 'closed'); after Reject: 'Changes rejected. The records were left as they were.' (total still 80); after confirming the create: 'Changes confirmed. Created ORD-1005.'",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-101",
   "built": "yes",
   "observed": true,
   "evidence": "Playwright headless chromium against node server.js (fresh DATA_DIR in work folder): `long task: alpha` -> region 'Tasks' gets article named 'Task: alpha'; `long task: plan [fail step 2]` -> 'Task: plan' (stand-in title, markers removed).",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-102",
   "built": "yes",
   "observed": true,
   "evidence": "Playwright headless chromium against node server.js (fresh DATA_DIR in work folder): each task article has role=status aria-label 'Task status'; observed values Running, Completed, Failed, Cancelled and (after a server restart) Interrupted.",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-103",
   "built": "yes",
   "observed": true,
   "evidence": "Playwright headless chromium against node server.js (fresh DATA_DIR in work folder): Running article shows '0 of 3 steps finished.' with no step list, later 'Done: Collect what is known about alpha', etc. as an ordered list; Failed shows only the finished step 1; Cancelled shows the finished steps.",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-104",
   "built": "yes",
   "observed": true,
   "evidence": "Playwright headless chromium against node server.js (fresh DATA_DIR in work folder): Running articles carry a 'Cancel task' button (clicked on 'Task: big' at 2 of 8 -> Cancelled, finished steps kept, note 'Remaining work was stopped. Any in-flight step result was discarded. Completed steps are shown below.'); Completed/Cancelled articles have no Cancel task.",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-105",
   "built": "yes",
   "observed": true,
   "evidence": "Playwright headless chromium against node server.js (fresh DATA_DIR in work folder): 'Task: alpha' -> Task status 'Completed' after its three 'Done: ...' steps.",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-106",
   "built": "yes",
   "observed": true,
   "evidence": "Playwright headless chromium against node server.js (fresh DATA_DIR in work folder): Failed 'Task: plan' and Interrupted 'Task: audit' each showed 'Retry task'; retry resumed at the failed/next step and reached Completed; Completed and Running articles had no Retry task.",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-107",
   "built": "yes",
   "observed": true,
   "evidence": "Playwright headless chromium against node server.js (fresh DATA_DIR in work folder): same browser: started `long task: gamma [long]`, closed the tab 5 s, reopened: region 'Since you were away' listed 'Task #4 · crates — Failed — needs attention' and 'Task #6 · gamma — Completed'; with a task still going on return it listed 'Task #1 · delta — Running'; after a server restart it listed 'Task #7 · audit — Interrupted — needs attention'; on a later reload the Completed entry dropped and the failed one stayed. In a fresh browser context (no site storage) returning after tasks finished or failed showed no Since you were away region at all (see defect).",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-108",
   "built": "yes",
   "observed": true,
   "evidence": "Ran `npm test` (node --test) in the work copy: 19 tests under test/ (build-3.test.js, chat.test.js, recovery.test.js), 19 pass, 0 fail; they exercise lib/chat.js, lib/records.js, lib/store.js, lib/tasks.js, lib/workspace.js and server.js, which the running app uses. No browser/UI tests in the suite (acceptance/ scripts are not run by npm test).",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  }
 ],
 "unstated": [
  {
   "id": "U-1",
   "behaviour": "The person is held per browser by an HttpOnly session cookie; tabs of one browser share it and revalidate each other via BroadcastChannel.",
   "handling": "sound",
   "observed": true,
   "evidence": "Playwright, two browser contexts on one server: A Continue as Maya + \"hello from Maya\", B Continue as Theo + \"hello from Theo\"; after reloading each, A showed Maya with only her messages and B Theo with only his; a further send from A went to Maya (\"Assistant has 2 message(s)\"). Two tabs in A: tab2 Switch person -> Continue as Ana; tab1 re-rendered as Ana with an empty thread and its next send landed in Ana's conversation, shown as Ana. HTTP: two cookie jars (Maya, Theo) never saw each other's turns.",
   "spec": "silent",
   "told": "no",
   "told_where": ""
  },
  {
   "id": "U-2",
   "behaviour": "Every action is scoped server-side to the session's person and a per-selection generation; ids from another person's workspace return 404, an old generation returns 409.",
   "handling": "sound",
   "observed": true,
   "evidence": "HTTP: as Maya noted conversation, memory and proposal ids; same cookie Switch to Ana; POST /api/actions/open-conversation, forget-memory, confirm with Maya's botId/conversationId/itemId and Ana's generation -> 404 \"This item is unavailable in the current workspace.\"; confirm with Maya's old generation -> 409 \"The selected workspace has changed.\"; GET /api/receipt for Maya's conversation -> 404; a cookie-less send with Maya's generation -> 409. Back as Maya: \"The status of ORD-1001 is open.\" and memory still [\"likes tea\"].",
   "spec": "decided-unmarked",
   "told": "no",
   "told_where": ""
  },
  {
   "id": "U-3",
   "behaviour": "First screen holds only the three Continue as buttons; Setup and the chat appear after a person is chosen (token is saved from inside a workspace). After Switch person a reload stays on the chooser and no message box is shown.",
   "handling": "sound",
   "observed": true,
   "evidence": "Playwright, empty data, no token: GET / buttons [\"Continue as Maya\",\"Continue as Theo\",\"Continue as Ana\"], Setup region count 0, Message not visible. Continue as Maya -> Setup visible, Send disabled; sk-local-bad -> alert \"The provider refused this token. Check its format and try again.\"; sk-local-abcdefghijkl -> Setup gone, page has no token. Switch person + reload -> chooser buttons only, Message not visible. HTTP: send before token -> 409 \"Save an accepted provider token before sending a message.\"",
   "spec": "silent",
   "told": "no",
   "told_where": ""
  },
  {
   "id": "U-5",
   "behaviour": "An accepted PROVIDER_TOKEN wins over a saved one; it is never copied into DATA_DIR; while it is set, Save token is a silent no-op (Setup is hidden). With the variable unset the app needs a saved token.",
   "handling": "sound",
   "observed": true,
   "evidence": "HTTP: PROVIDER_TOKEN=sk-local-abcdefghijkl -> ready true, \"who are you\" -> \"I am Assistant. I have no special instructions.\"; POST save-token sk-local-zzzzzzzzzzzzzz -> 200 but DATA_DIR still only [\"state.json\"]; no file contains the env token. Restart with variable set -> ready, replies; restart unset -> ready false (Setup); saving sk-local-zzzz... -> ready; restart with both set -> ready, replies; provider-token file holds only the saved token. No token in any response.",
   "spec": "open",
   "told": "yes",
   "told_where": "README.md: \"`PROVIDER_TOKEN` | An accepted environment token takes precedence.\""
  },
  {
   "id": "U-6",
   "behaviour": "A refused PROVIDER_TOKEN is treated as unsaved: Setup is shown and a valid token can be saved; sending first is refused with a message to save a token.",
   "handling": "sound",
   "observed": true,
   "evidence": "HTTP: PROVIDER_TOKEN=not-a-token -> GET / 200, Continue as Maya -> ready false; save sk-local-abcdefghijkl -> ready true, \"hello\" replies. PROVIDER_TOKEN=sk-local-short -> ready false; send \"hello\" -> 409 \"Save an accepted provider token before sending a message.\"; save token -> ready, \"hello\" replies. Server output only the ready line.",
   "spec": "open",
   "told": "yes",
   "told_where": "README.md: \"A refused environment value falls back to an accepted saved token, or to Setup if neither works.\""
  },
  {
   "id": "U-7",
   "behaviour": "The saved token is stored in plain text in DATA_DIR/provider-token with mode 600, never in state.json, responses or server output; tokens typed into messages are replaced by [redacted].",
   "handling": "sound",
   "observed": true,
   "evidence": "HTTP: after Save token, files [\"provider-token\",\"state.json\"], only provider-token contains the token, mode 600; GET /api/view text has no token; \"hello [fail once]\" -> turn status failed, server output only \"Local chat is ready at ...\"; sending \"my token is sk-local-abcdefghijkl\" -> reply \"You said: \\\"my token is [redacted]\\\"...\". Playwright: after saving, page HTML has no token.",
   "spec": "silent",
   "told": "yes",
   "told_where": "README.md: \"When setup saves a token, the app stores it in a separate restricted `provider-token` file.\""
  },
  {
   "id": "U-8",
   "behaviour": "A new person, and each New bot, starts with one empty open conversation (\"Untitled chat\") so Send works at once; a new bot has no memory and no instructions; New conversation becomes the open one.",
   "handling": "sound",
   "observed": true,
   "evidence": "HTTP, empty data, as Ana: bots [\"Assistant\"], one conversation \"Untitled chat\", 0 turns; \"who are you\" -> \"I am Assistant. I have no special instructions.\"; \"what do you remember\" -> \"I don't remember anything about you yet.\"; New bot Clerk -> one \"Untitled chat\", memory [], instructions \"\"; Clerk \"who are you\" -> \"I am Clerk. I have no special instructions.\"; New conversation -> the new id is current.",
   "spec": "decided-unmarked",
   "told": "no",
   "told_where": ""
  },
  {
   "id": "U-9",
   "behaviour": "Blank names are refused (browser required-field message; server 400 \"Enter a bot name.\"); duplicate names allowed and distinguished by a stable \"Bot #n\" plus the open conversation label as visible text and aria-describedby; the textbox stops input at 80 characters and the server refuses longer names.",
   "handling": "acceptable",
   "observed": true,
   "evidence": "HTTP: new-bot \"\" and \"   \" -> 400 \"Enter a bot name.\"; second \"Assistant\" -> 200; 300 chars -> 400 \"Use at most 80 characters for a bot name.\"; 80 chars accepted. Playwright 1440px: empty Save bot name -> validation \"Please fill out this field.\"; Bots buttons both have accessible name \"Assistant\" with descriptions \"Bot #1 · remember that likes tea\" and \"Bot #2 · second assistant pears\", visible the same text (screenshot). Filling 300 z in Bot name leaves 80 characters in the box and saves an 80-character name with no message.",
   "spec": "open",
   "told": "yes",
   "told_where": "README.md: \"Bots can share a name. Each has a stable number shown in the Bots list and the chat header.\"",
   "rerun": true
  },
  {
   "id": "U-11",
   "behaviour": "Buttons are labelled by the first message (truncated at 38 characters) or \"Untitled chat\"; duplicates get \"· Chat n\" and similar openings get a distinguishing excerpt; listed in creation order; the open one has aria-current.",
   "handling": "sound",
   "observed": true,
   "evidence": "HTTP: two New conversation in one bot -> labels [\"Untitled chat\",\"Untitled chat · Chat 2\",\"Untitled chat · Chat 3\"]; first messages \"Please look up the order history for the customer called Northwind Traders\" / \"...Southwind Traders\" -> \"Please look up the order history for t… · …tomer called Northwind Traders · Chat 3\" and \"... Southwind Traders · Chat 4\"; an identical third -> \"... Northwind Traders · Chat 5\". Accessible names equal the visible labels (buttons have no aria-label).",
   "spec": "open",
   "told": "yes",
   "told_where": "README.md: \"In Conversations, similar openings show a distinguishing excerpt where available and a chat number. When openings are identical, later entries get a chat number.\"",
   "rerun": true
  },
  {
   "id": "U-13",
   "behaviour": "The last open bot and conversation are kept per person on the server (survive reload, Switch person and back, a new browser session and a restart); the unsent draft and scroll position are kept per tab in sessionStorage (kept on reload and switch-back, not in a new browser session).",
   "handling": "sound",
   "observed": true,
   "evidence": "Playwright as Maya, bot Second, its 2nd conversation, scrollTop 200, draft \"unsent draft text\": after reload {bot Second, same conversation, draft kept, scroll 200}; after Switch to Theo and back: same; new browser context with the cookie: Second, same conversation, draft \"\", scroll at bottom; after server restart + reload: Second, same conversation.",
   "spec": "open",
   "told": "no",
   "told_where": ""
  },
  {
   "id": "U-14",
   "behaviour": "One library of saved instructions and saved tasks per person, listed for every bot; Use and Run act on the open bot and conversation only; another person sees none.",
   "handling": "sound",
   "observed": true,
   "evidence": "HTTP as Maya on Assistant: save instruction Tone=\"Be brief\", task Ping=\"hello\"; New bot Other lists [\"Tone\"] and [\"Ping\"]; Use Tone + Run Ping in Other -> reply \"You said: \\\"hello\\\". (Other has 1 message(s)...)\", Other \"who are you\" -> \"I am Other. My instructions: Be brief\"; back to Assistant -> \"I am Assistant. I have no special instructions.\"; Theo sees instructions [] and savedTasks [].",
   "spec": "open",
   "told": "yes",
   "told_where": "README.md: \"Saved instructions and saved tasks are available across your bots.\""
  },
  {
   "id": "U-15",
   "behaviour": "Saving a name that already exists (case-insensitive) without Edit is refused with a message; empty name or text refused; never two entries with one name.",
   "handling": "sound",
   "observed": true,
   "evidence": "HTTP: save-instruction A=\"x\" 200; A=\"y\" -> 409 \"An entry with this name already exists. Choose Edit to change it.\", one A; \"a\"=\"y\" -> 409; Use A + \"who are you\" -> \"My instructions: x\"; name \"\" -> 400 \"Enter a name.\"; text \"\" -> 400 \"Enter the text.\"; same for save-task (P twice -> 409, one P; empty name / whitespace text -> 400).",
   "spec": "open",
   "told": "no",
   "told_where": "",
   "rerun": true
  },
  {
   "id": "U-16",
   "behaviour": "Changing the name after Edit renames the same item (no second item); Use/Edit/Delete buttons follow the new name.",
   "handling": "sound",
   "observed": true,
   "evidence": "HTTP: save-instruction with Tone's itemId and name Style -> instructions [[\"Style\",\"Be brief\"],[\"A\",\"x\"]] (Tone gone, no duplicate); save-task with Ping's itemId and name Pong -> [[\"Pong\",\"hello\"],[\"P\",\"x\"]].",
   "spec": "open",
   "told": "no",
   "told_where": ""
  },
  {
   "id": "U-17",
   "behaviour": "Use copies the text into the bot; editing or deleting the saved instruction does not change the bot until Use is chosen again; the page only says \"Custom instructions active for <bot>.\" without the text.",
   "handling": "acceptable",
   "observed": true,
   "evidence": "HTTP: save Formal=\"Be formal\", Use, \"who are you\" -> \"I am U17. My instructions: Be formal\"; edit Formal to \"Be casual\" -> still \"...My instructions: Be formal\"; Delete Formal -> still \"...My instructions: Be formal\" (bot.instructions \"Be formal\").",
   "spec": "open",
   "told": "yes",
   "told_where": "README.md: \"Use copies the saved instruction into the current bot. Select Use again to activate an edit.\""
  },
  {
   "id": "U-20",
   "behaviour": "A second send while a reply is pending is refused with an alert (not queued); repeated submission ids are deduplicated; the reply lands in its own conversation and person after switching conversation, person or reloading; a lost acknowledgement is reconciled by a receipt check so nothing is started twice, while a deliberate new send still is.",
   "handling": "sound",
   "observed": true,
   "evidence": "HTTP: \"hello [slow]\" then another send -> 409 \"A reply is on its way. Send again when it finishes.\"; same submission id twice -> one turn, second returns its receipt. \"set the status of ORD-1001 to closed [slow]\" then switch to Theo: Theo turns [] proposals []; back as Maya the proposal sits in her conversation. Playwright: status \"Second is preparing a reply…\"; Enter again -> alert, one message; reload during wait -> status shown, reply arrives; switch conversation and back -> reply in origin. Response held after server received + page closed -> new tab shows the turn and reply once; response aborted -> \"Your original submission was received.\", one copy after reload. \"long task: alpha [slow]\" with request blocked and page closed -> nothing stored; resend creates one Task: alpha.",
   "spec": "open",
   "told": "yes",
   "told_where": "README.md: \"If a send or saved-task Run loses its acknowledgement, return to the originating conversation in the same tab, reloading if needed. The app checks whether the server received it.\""
  },
  {
   "id": "U-21",
   "behaviour": "A failed reply stays failed with Retry after reload and restart, and Retry succeeds; a new message is accepted while the failed one keeps its Retry; a reply interrupted by stopping the server becomes \"interrupted\" with Retry (not automatic).",
   "handling": "sound",
   "observed": true,
   "evidence": "HTTP: \"hello [fail once]\" -> failed; restart -> still failed attempt 1; retry-reply -> complete attempt 2, repeating retry changes nothing (one copy). At a failure, send \"next\" -> accepted, failed turn kept failed. \"hello [slow]\" then kill -9 and restart -> status interrupted; retry -> complete. Playwright: alert \"The reply failed. Retry to answer your original message.\"; reload -> Retry still there; Retry -> reply shown, message once.",
   "spec": "open",
   "told": "yes",
   "told_where": "README.md: \"If the original message was received and its reply failed, use **Retry** on that turn to continue it.\""
  },
  {
   "id": "U-22",
   "behaviour": "The stored person message keeps the markers; the stand-in sees them, so \"what did I ask first\" quotes them, while the echo reply omits them.",
   "handling": "acceptable",
   "observed": true,
   "evidence": "HTTP: \"hello [fail once]\" failed, Retry -> \"You said: \\\"hello\\\". (Assistant has 1 message(s)...)\"; \"what did I ask first\" -> \"You first asked: \\\"hello [fail once]\\\".\"; Message article text \"hello [fail once]\".",
   "spec": "silent",
   "told": "no",
   "told_where": ""
  },
  {
   "id": "U-23",
   "behaviour": "A repeated remember is merged; a forget is exact (case-insensitive) match only; a non-matching forget removes nothing but the shown reply still says \"I've forgotten ...\" with no notice.",
   "handling": "poor",
   "observed": true,
   "evidence": "HTTP: \"remember that likes tea\" twice -> memory [\"likes tea\"]; \"forget tea\" -> reply \"I've forgotten \\\"tea\\\".\" memory still [\"likes tea\"]; \"forget coffee\" -> \"I've forgotten \\\"coffee\\\".\" memory unchanged; \"forget that likes tea\" -> memory []; \"remember that likes Tea\" then \"forget LIKES TEA\" -> memory [].",
   "spec": "open",
   "told": "no",
   "told_where": ""
  },
  {
   "id": "U-25",
   "behaviour": "Memory text starts filled with the current fact; Save memory updates that item.",
   "handling": "sound",
   "observed": true,
   "evidence": "Playwright: \"remember that likes tea\", Edit memory -> Memory text \"likes tea\"; changed to \"likes coffee\", Save memory -> list [\"likes coffee\"].",
   "spec": "silent",
   "told": "no",
   "told_where": ""
  },
  {
   "id": "U-26",
   "behaviour": "Management actions add no messages; only typed messages and Run write to the conversation.",
   "handling": "sound",
   "observed": true,
   "evidence": "HTTP in a fresh bot with one turn \"first q\": save/use/delete instruction, save task, rename bot -> still 1 turn; \"remember that x1\" -> 2 turns; edit-memory and forget-memory -> still 2; \"what did I ask first\" -> \"You first asked: \\\"first q\\\".\"",
   "spec": "silent",
   "told": "no",
   "told_where": ""
  },
  {
   "id": "U-27",
   "behaviour": "Memory and task progress update on their own while the page is open (polls every 400 ms).",
   "handling": "sound",
   "observed": true,
   "evidence": "Playwright without reload: after \"remember that likes tea\" the Memory list showed \"likes tea\"; Task status/finished-step samples for \"long task: alpha\": \"Running 0\", \"Running 1\", \"Running 2\", \"Completed 3\".",
   "spec": "silent",
   "told": "no",
   "told_where": ""
  },
  {
   "id": "U-29",
   "behaviour": "Proposals for readers, id and type are refused with a notice naming the editable fields (the stand-in's \"I propose...\" text is still shown above it); owner is an editable account field and is offered and applied like any other field without a warning, without changing readers.",
   "handling": "acceptable",
   "observed": true,
   "evidence": "HTTP as Maya: \"set the readers of ORD-1001 to ana\" -> reply \"I propose one change: ORD-1001 readers: maya,theo → ana. Confirm to apply it.\" plus notice \"There is no change to confirm for this request. Choose an editable field for ORD-1001 (customer, status, total)...\", no proposal; same for \"set the id of ORD-1004 to ORD-9999\" and type. \"set the owner of ACC-2001 to ana\" -> proposal ACC-2001 owner: maya → ana, confirmed -> \"Changes confirmed and applied.\"; order counts afterwards Maya 3, Theo 2, Ana 1 (unchanged).",
   "spec": "open",
   "told": "no",
   "told_where": ""
  },
  {
   "id": "U-30",
   "behaviour": "Non-numeric and out-of-precision totals, unknown fields and decimal creates are refused with correction guidance; a decimal update and any status text are offered exactly as shown; a corrected request works in the same conversation.",
   "handling": "sound",
   "observed": true,
   "evidence": "HTTP as Maya: \"set the total of ORD-1001 to banana\" -> notice \"...Use a number written in digits... For example, set the total of ORD-1001 to 42.50.\", no proposal; \"set the colour of ORD-1001 to red\" -> notice \"Choose an editable field for ORD-1001 (customer, status, total)...\"; \"create an order for Acme totalling 42.50\" -> echo reply + notice \"Use a whole amount written in digits...\"; \"what is the total of ORD-1001\" -> 125; \"set the total of ORD-1001 to 130\" -> proposal 125 → 130; \"...to 42.50\" -> proposal 125 → 42.5; \"set the status of ORD-1002 to banana\" -> proposal shipped → banana.",
   "spec": "decided-unmarked",
   "told": "yes",
   "told_where": "README.md: \"The app offers a preview only when it can represent the amount exactly and gives correction guidance for unsupported changes.\""
  },
  {
   "id": "U-31",
   "behaviour": "An undecided proposal is kept across Enter, reload, restart and switching conversations; several may be pending and an older one can still be confirmed; only Confirm changes confirms; after a decision the buttons are replaced by Change result and further confirms change nothing.",
   "handling": "sound",
   "observed": true,
   "evidence": "HTTP: proposal ORD-1002 shipped → closed; restart -> result null, status still shipped; new conversation and back -> present; second proposal shipped → cancelled, Reject -> \"Changes rejected...\"; Confirm on it -> still rejected; Confirm the older -> \"Changes confirmed and applied.\"; again -> same, status closed. Playwright: Enter in empty Message with two proposals -> nothing decided; after decisions no Confirm changes buttons remain.",
   "spec": "open",
   "told": "yes",
   "told_where": "README.md: \"Leaving the conversation preserves the pending decision.\""
  },
  {
   "id": "U-32",
   "behaviour": "The bot gives the stand-in sentence; Proposed changes lists Create order, Customer, Total, Status, \"Access: <name> only\" and \"Order ID: assigned on confirmation\"; nothing stored before Confirm; Change result names the final id.",
   "handling": "sound",
   "observed": true,
   "evidence": "HTTP as Maya: \"create an order for Northwind totalling 40\" -> \"I propose creating one order: customer Northwind, total 40, status open. Confirm to apply it.\"; before confirm \"how many orders can you see\" -> 3; Confirm -> \"Changes confirmed. Created ORD-1005.\"; count 4, \"The customer of ORD-1005 is Northwind.\" Proposal text from the page code (proposalView) not seen rendered for a create.",
   "spec": "open",
   "told": "yes",
   "told_where": "README.md: \"The app assigns new order IDs at confirmation and reports the final ID.\""
  },
  {
   "id": "U-33",
   "behaviour": "Confirm re-checks the from-value; a stale preview is not applied and Change result says it is no longer current and asks for a fresh preview; repeated confirms write nothing.",
   "handling": "sound",
   "observed": true,
   "evidence": "HTTP: Maya proposal ORD-1001 open → closed (undecided); Theo \"set the status of ORD-1001 to shipped\" + Confirm -> applied; Maya Confirm -> result expired \"Changes were left unapplied. This preview is no longer current. Ask for a fresh preview to review the current record.\"; \"what is the status of ORD-1001\" -> shipped; second Confirm -> same expired result.",
   "spec": "open",
   "told": "yes",
   "told_where": "README.md: \"A stale preview expires and requires a fresh request.\""
  },
  {
   "id": "U-34",
   "behaviour": "Ids are assigned at confirm time as the lowest unused ORD- number from 1001; concurrent creates get distinct ids; each readable only by its creator.",
   "handling": "sound",
   "observed": true,
   "evidence": "HTTP: Maya proposes North 10, Ana proposes South 20 (both pending); Ana confirms -> \"Created ORD-1006.\" (ORD-1005 already existed from an earlier probe); Maya confirms -> \"Created ORD-1007.\"; ORD-1006 readable by Ana only (customer South), ORD-1007 by Maya only (customer North), Theo sees neither.",
   "spec": "decided-unmarked",
   "told": "yes",
   "told_where": "README.md: \"The app assigns new order IDs at confirmation and reports the final ID.\""
  },
  {
   "id": "U-35",
   "behaviour": "The decision is stored on the proposal in its conversation; after reload or restart a Change result region shows it in place of the proposal, with no Confirm button left.",
   "handling": "sound",
   "observed": true,
   "evidence": "Playwright: Confirm changes then immediate reload -> Change result regions [\"Changes rejected. The records were left as they were.\",\"Changes confirmed and applied.\"], Confirm changes count 0. HTTP: proposal results [\"applied\",\"rejected\",\"expired\",\"applied\"] persisted in /api/view and after restart.",
   "spec": "decided-unmarked",
   "told": "no",
   "told_where": ""
  },
  {
   "id": "U-36",
   "behaviour": "One working copy of the records: a confirmed change is seen by every reader of that record, also after restart; non-readers still cannot see it; records/ files unchanged.",
   "handling": "sound",
   "observed": true,
   "evidence": "HTTP: Maya sets ORD-1004 status open → closed, Confirm; Maya \"closed\", Ana \"The status of ORD-1004 is closed.\", Theo \"I can't see a record called ORD-1004.\"; after restart Ana still \"closed\"; records/records.json byte-identical before and after.",
   "spec": "decided-unmarked",
   "told": "no",
   "told_where": ""
  },
  {
   "id": "U-37",
   "behaviour": "Tasks shows all of the person's tasks (every bot and conversation), newest first, each with \"Task #n\" and an Open conversation button for other conversations; never another person's.",
   "handling": "sound",
   "observed": true,
   "evidence": "HTTP as Maya: \"long task: report [long]\" in conversation 1; in conversation 2 and in a new bot the view lists [1,\"report\",\"Running\"]; Theo's view tasks []. Playwright screenshot shows \"Open conversation\" on a task from another conversation.",
   "spec": "silent",
   "told": "no",
   "told_where": ""
  },
  {
   "id": "U-38",
   "behaviour": "A second long task runs alongside the first; both shown in Tasks and both complete.",
   "handling": "sound",
   "observed": true,
   "evidence": "HTTP (STANDIN_STEP_MS=300): \"long task: alpha [long]\" then \"long task: beta\" -> both replies \"I'll work on ...\"; tasks alpha Running 0/8, beta Running 0/3; later alpha Completed 8/8, beta Completed 3/3.",
   "spec": "silent",
   "told": "no",
   "told_where": ""
  },
  {
   "id": "U-39",
   "behaviour": "With none running, the stand-in's \"I'll add ...\" reply is shown with a notice \"No step was added. No task is running in this conversation.\"; with several running it adds to the most recently started one and the turn says \"Step added to Task #n · <title> — <step>\" with a Show button.",
   "handling": "sound",
   "observed": true,
   "evidence": "HTTP: \"add step: double-check\" with no task here -> reply \"I'll add \\\"double-check\\\" to the task that is running.\" + notice \"No step was added...\"; tasks unchanged; also after Cancel. Two \"long task: dup [long]\" then \"add step: extra\" -> steering to the second (Task #5: 9 steps, last result \"Done: extra\"; Task #4: 8 steps). Page code renders \"Step added to Task #5 · dup [long]\" (not seen rendered).",
   "spec": "open",
   "told": "yes",
   "told_where": "README.md: \"The app adds the step to the most recently started running task in the conversation and links to that task by number.\"",
   "rerun": true
  },
  {
   "id": "U-40",
   "behaviour": "No message is added to the conversation when a task ends; the result stays in the task article, which is kept after reload.",
   "handling": "acceptable",
   "observed": true,
   "evidence": "HTTP: \"long task: notes\" -> Completed 3/3; conversation turns only [\"long task: notes\" / \"I'll work on \\\"notes\\\"...\"]; follow-up \"what did I ask first\" -> \"You first asked: \\\"long task: notes\\\".\"; Tasks still lists notes Completed after reload (view).",
   "spec": "silent",
   "told": "no",
   "told_where": ""
  },
  {
   "id": "U-41",
   "behaviour": "Tasks keep running server-side with the page closed; after a server stop (SIGKILL or SIGTERM) a Running task becomes Interrupted with a note and Retry task, keeps its finished steps, does not count the in-flight step, and does not resume on its own; Retry continues with the next unfinished step.",
   "handling": "sound",
   "observed": true,
   "evidence": "HTTP (STANDIN_STEP_MS=1000): \"long task: audit [long]\", 2/8 done, kill -9, restart -> Interrupted 2/8 \"The server stopped. Saved steps are shown below. Retry to resume with the first unfinished step.\"; 2.5 s later still Interrupted 2/8; Retry -> Completed with 8 distinct results in order. Same after SIGTERM with audit2. Page-closed progress seen in U-44 (both tasks ended while the tab was closed).",
   "spec": "open",
   "told": "yes",
   "told_where": "README.md: \"Any unfinished reply or running task that was stopped becomes explicitly retryable.\""
  },
  {
   "id": "U-42",
   "behaviour": "Retry task resumes at the failed step; step 1 appears once.",
   "handling": "sound",
   "observed": true,
   "evidence": "HTTP: \"long task: plan [fail step 2]\" -> Failed, results [\"Done: Collect what is known about plan\"], note \"Step 2 failed. Retry to continue from that step.\"; Retry -> Completed with [\"Done: Collect...\",\"Done: Compare...\",\"Done: Write...\"]; a stale-run Retry does nothing.",
   "spec": "decided-unmarked",
   "told": "yes",
   "told_where": "README.md: \"If a task fails or is interrupted, use Retry task to continue its unfinished steps.\""
  },
  {
   "id": "U-43",
   "behaviour": "Cancel acts at once without asking; the in-flight step's result is discarded and the note says so; finished steps stay listed; status stays Cancelled; Cancel/Retry afterwards do nothing.",
   "handling": "sound",
   "observed": true,
   "evidence": "HTTP (STANDIN_STEP_MS=3000): \"long task: big [long]\", after 4.5 s 1 step done; Cancel -> Cancelled, results [step 1], note \"Remaining work was stopped. Any in-flight step result was discarded. Completed steps are shown below.\"; 4 s later identical; Cancel again and Retry task -> still Cancelled.",
   "spec": "open",
   "told": "yes",
   "told_where": "README.md: \"Cancel preserves finished steps and discards an in-flight result.\""
  },
  {
   "id": "U-44",
   "behaviour": "\"Away\" is measured per browser and person by the task revision last seen with the Tools panel visible; on return it lists tasks changed since then plus any Running, Failed or Interrupted (failed marked \"needs attention\"); finished items drop off on the next reload, failed ones stay until resolved; waiting proposals are not reported; only the person's own tasks.",
   "handling": "acceptable",
   "observed": true,
   "evidence": "Playwright (STANDIN_STEP_MS=600): first visit region absent; started \"long task: crates [fail step 2]\" and \"long task: alpha\", closed tab, reopened -> \"Task #1 · crates — Failed — needs attention | Task #2 · alpha — Completed\"; reload -> only crates line; reload after a send and while a proposal waited -> only crates line; after Retry task completed it -> \"No task updates since your last visit.\"; Ana -> region absent, after her own task and return -> \"Task #1 · ana work — Completed\".",
   "spec": "open",
   "told": "no",
   "told_where": ""
  },
  {
   "id": "U-45",
   "behaviour": "At 1100 px and wider every panel is on screen; at 900 px and below Bots/Conversations fold behind a Workspace button and Saved instructions, Saved tasks, Memory and Tasks behind a Tools button; Escape closes a panel and returns focus to its button; Conversation, Message and Send stay in view; no horizontal scroll down to 375 px.",
   "handling": "sound",
   "observed": true,
   "evidence": "Playwright widths 1440, 1100, 900, 768, 600, 480, 375: Conversation, Message, Send in view at all, no horizontal scroll; panels visible at 1440/1100, hidden from 900 down with Workspace and Tools buttons visible; at 375 Workspace opened Bots and Conversations (focus on New bot), Escape closed (focus Workspace), Tools showed all four regions with Message still in view (screenshot); back at 1440 all visible.",
   "spec": "open",
   "told": "yes",
   "told_where": "README.md: \"On narrow windows, Workspace and Tools open the secondary panels. Escape closes an open panel and returns focus to its button.\""
  },
  {
   "id": "U-46",
   "behaviour": "A missing DATA_DIR (even nested) is created and served; an unwritable one, invalid JSON, a wrong-shape snapshot or a damaged record makes startup exit 1 with \"Cannot open the data directory. Check its permissions and restore a readable state snapshot if it is damaged.\", leaving the file untouched and records/ unchanged.",
   "handling": "sound",
   "observed": true,
   "evidence": "Started with DATA_DIR=<work>/data-gF-missing/nested/deeper -> ready, state.json created, replies work. chmod 500 empty folder -> stderr message, exit 1, no files. state.json \"{not json\" and {\"hello\":\"world\"} and a record total \"lots\" -> same message, exit 1, contents unchanged. records/records.json identical to base.",
   "spec": "decided-unmarked",
   "told": "yes",
   "told_where": "README.md: \"If startup cannot open the saved snapshot, it stops and preserves the directory contents.\"",
   "rerun": true
  },
  {
   "id": "U-49",
   "behaviour": "Field names are matched case-insensitively for lookups and updates with identical replies and previews; reader rules still applied.",
   "handling": "sound",
   "observed": true,
   "evidence": "HTTP as Maya: \"what is the STATUS of ORD-1002\" and \"...status...\" -> both \"The status of ORD-1002 is closed.\"; \"set the Status of ORD-1001 to open\" and \"set the status...\" -> same preview \"ORD-1001 status: shipped → open\"; as Ana both \"I can't see a record called ORD-1001.\"; \"what is the Customer of ord-1002\" -> \"The customer of ORD-1002 is Birch & Co.\"",
   "spec": "decided-unmarked",
   "told": "yes",
   "told_where": "README.md: \"Record field names are case-insensitive.\"",
   "rerun": true
  },
  {
   "id": "U-50",
   "behaviour": "A lookup with a suffixed id gets a notice that the identifier could not be used, with how to correct it; the stand-in's own text (given no records) reads \"I can't see a record called ORD-1001.\"; a set with a suffixed id is echoed with no proposal; ORD-1001 itself still answers.",
   "handling": "acceptable",
   "observed": true,
   "evidence": "HTTP as Maya: \"what is the status of ORD-1001A\" -> reply \"I can't see a record called ORD-1001.\" + notice \"The identifier “ORD-1001A” could not be used. Check the full record ID and ask again using its letters, hyphen and digits.\"; \"set the status of ORD-1001A to closed\" -> \"You said: ...\" no proposal; \"what is the status of ORD-1001\" -> \"The status of ORD-1001 is shipped.\"",
   "spec": "decided-unmarked",
   "told": "yes",
   "told_where": "README.md: \"If you enter a suffix such as **ORD-1001A**, check the ID in the lookup guidance and ask again.\"",
   "rerun": true
  },
  {
   "id": "U-54",
   "behaviour": "A failed write puts the server into an unavailable mode: that and every later request (including reads) return 503 with a recovery message until a restart; nothing unsaved is reported as saved; after restoring access and restarting, earlier work is present and the failed save absent.",
   "handling": "sound",
   "observed": true,
   "evidence": "HTTP: proposal pending, chmod 500 DATA_DIR; save-instruction -> 503 \"Storage is unavailable and the save outcome could not be verified. Restore write access, then restart the server with the same data directory (DATA_DIR)...\"; send and confirm -> 503 same; view -> 503; after chmod 700 without restart still 503; restart -> instructions [], turns only the earlier one, proposal undecided, ORD-1001 open. Playwright: the page alert shows the same message, Use RO absent, the name and draft kept; after restart the alert clears.",
   "spec": "decided-unmarked",
   "told": "yes",
   "told_where": "README.md: \"If a storage failure occurs during a save, restore write access and restart with the original `DATA_DIR`.\"",
   "rerun": true
  },
  {
   "id": "U-57",
   "behaviour": "A failing task is reported on its article and everything else stays usable; a storage error inside a task step switches the whole app to the 503 unavailable mode (stderr \"Background work paused. Restart with the same data directory to recover.\"); after restart the task is Interrupted with Retry.",
   "handling": "acceptable",
   "observed": true,
   "evidence": "HTTP: \"long task: crates [fail step 2]\" -> Failed with note; \"hello after failure\" -> normal reply. \"long task: other [long]\" then chmod 500 mid-task: process alive, stderr \"Background work paused...\", view and send -> 503 with the recovery message; still 503 after restoring access; restart -> crates Failed, other Interrupted.",
   "spec": "silent",
   "told": "no",
   "told_where": "",
   "rerun": true
  },
  {
   "id": "U-58",
   "behaviour": "After keyboard Reject, focus moves to that proposal's new Change result heading (Enter there does nothing); after Send focus stays in Message; after Save memory focus goes to the item's Edit memory button.",
   "handling": "sound",
   "observed": true,
   "evidence": "Playwright, two proposals: focus Reject changes of the first, Enter -> focus \"H3 Change result\" in that region; Enter again -> 1 proposal still pending, one result. After Send -> TEXTAREA message. After Save memory -> \"BUTTON Edit memory\".",
   "spec": "silent",
   "told": "no",
   "told_where": "",
   "rerun": true
  },
  {
   "id": "U-60",
   "behaviour": "Malformed bodies get 400/404 JSON errors with readable messages and an unexpected error gets 500 \"The app could not finish the request. Try reloading.\"; nothing is written to the server output for these errors or for a storage failure in a request.",
   "handling": "poor",
   "observed": true,
   "evidence": "HTTP: \"{bad json\" to /api/actions/send -> 400 \"The request could not be read.\"; [1,2] to confirm -> 400; itemId 42 -> 404; text 42 -> 400 \"Enter a message.\"; raw \"GET //[ HTTP/1.1\" -> 500 {\"error\":\"The app could not finish the request. Try reloading.\"}; server output only \"Local chat is ready at ...\"; during the U-54 storage failure the server output also stayed empty. state.json overwritten with garbage during use -> app kept serving and the next write replaced it with its in-memory state.",
   "spec": "silent",
   "told": "no",
   "told_where": "",
   "rerun": true
  }
 ],
 "extras": [
  {
   "what": "Submission receipts and a per-tab journal with a \"Recover original submission\" control for lost acknowledgements",
   "where": "lib/chat.js receipt/reserve, public/app.js submitAttempt/checkSubmission",
   "worth": "value",
   "why": "Prevents a reload or lost response from starting a send, Run or long task twice; observed reconciling a lost acknowledgement to one copy."
  },
  {
   "what": "Stable \"Bot #n\" references and duplicate-aware conversation labels with excerpts and \"Chat n\"",
   "where": "lib/workspace.js botLabels/conversationLabels",
   "worth": "value",
   "why": "Makes same-name bots and similar conversations distinguishable visually and to screen readers."
  },
  {
   "what": "Masking of sk-local- tokens typed into messages, names and memory (\"[redacted]\")",
   "where": "lib/workspace.js scrub, public/app.js safeText",
   "worth": "value",
   "why": "Keeps a pasted secret out of stored history and provider input; it does change the stored text, silently."
  },
  {
   "what": "Whole-app \"storage unavailable\" mode after any failed write, blocking reads too until restart",
   "where": "lib/store.js assertReady/storageFailure",
   "worth": "neutral",
   "why": "Honest about unverified saves, but a transient write error takes the whole app out of service until an operator restarts it."
  },
  {
   "what": "Origin/Sec-Fetch-Site checks, JSON content-type requirement, 100 kB body limit and a strict Content-Security-Policy",
   "where": "server.js body/createServer",
   "worth": "value",
   "why": "Blocks cross-site requests against the local app at no cost to normal use."
  },
  {
   "what": "Starter prompt buttons in an empty conversation and an \"Open conversation\" button on tasks from other conversations",
   "where": "public/app.js emptyThread/renderTasks",
   "worth": "value",
   "why": "Helps first use and reaching a task's discussion."
  },
  {
   "what": "Builder harness shipped with the product: acceptance/ scripts (including a Swift WebKit driver) and [tool]/ working notes",
   "where": "acceptance/, [tool]/",
   "worth": "neutral",
   "why": "Not run by npm test or the app; extra material for a maintainer to understand or ignore."
  }
 ],
 "spec_notes": "[tool]/spec.md marks most open questions as \"Open: The requester decides ...\" (token precedence C-14, naming C-19/C-21, restoration C-23, library sharing and conflicts C-35/C-39, edit/delete of an instruction in use C-37/C-38, pending sends C-31, interrupted replies C-34, editable fields C-50, preview ids C-51, cancel vs reject C-55, multiple proposals C-60, stale previews C-62, absence period C-68, steering target C-69, in-flight cancel C-71, interrupted tasks C-75, breakpoints C-79), yet the product then decides each of them without the spec recording the decision (for example Use copies instructions, ids at confirm, expire on stale, no auto-resume, panels fold at 900 px). The \"discovery\" clauses C-83 to C-98 are decided in ordinary requirement lines and pin this build's own mechanisms (C-86/C-93/C-94/C-95 the receipt and \"recover original submission\" flow, C-89 exact-amount refusal, C-90 refusing suffixed ids, C-97 length limits); a correct build need not share them. C-98 asks for safe overlapping launches on one DATA_DIR while the README only says to use one process per directory (not checked here). Silent on the per-browser person, memory forget matching beyond paraphrase, logging of errors, keyboard focus targets and task results in the conversation. No clause contradicts the request.",
 "tests_notes": "Several tests are long scenarios covering many behaviours at once: \"setup, record scoping, saved workspace and transparent provider echo\" (setup, token file mode, redaction, memory edit/forget, rename, person scoping, counts, place restore), \"reply reservations, library state and original history survive navigation\" and \"confirmation commits only the reviewed record changes exactly once\"; one failure there hides which rule broke. Tied to internals: \"reopening storage reveals whether a failed save reached publication\" mocks fs.renameSync/fs.fsyncSync; \"steering returns the committed destination when tasks share a title\" builds raw workspace objects for lib/tasks launch/steer; \"CLI preserves unsupported and nested damaged snapshots\" and \"an existing damaged snapshot is never replaced\" depend on the file names state.json/provider-token and the snapshot schema; recovery and build-3 tests drive the Chat/Store classes directly. Timing: \"failed and cancelled tasks keep committed steps\" relies on STANDIN_STEP_MS=90 with a 130 ms delay. Would fail on another correct build: the \"who are you\" after edit+Use+delete expecting \"Be direct\" (pins copy-on-Use), \"what did I ask first\" containing \"STA[fail once]TUS\" (pins keeping markers), refusal of a decimal create and the exact notice texts (/whole amount/, /editable field/, /range or precision/), \"Bot #3\" references and \"Chat 2\" labels, ids assigned at confirm (ORD-1005/ORD-1006 by confirm order), 409 for a send while a reply is pending, and the 0600 provider-token file. No test covers duplicate-name refusal of saved entries, rename-through-Edit, non-matching forget, the Since you were away logic, focus, narrow layout or error logging.",
 "maintainer": "The send path is a cross-tier protocol: lib/chat.js (submission ids, generations, receipts, attempt numbers, pending/interrupted turns) must stay in step with public/app.js (sessionStorage journal, epochs, receipt checks, recovery button), and neither side documents the contract, so a small change to either can reintroduce duplicate sends or stuck \"Checking...\" states. lib/store.js readState validates the whole snapshot shape and refuses to start on any mismatch, so every new field needs a matching validator change or existing data folders stop opening. lib/records.js recordRequest re-parses the stand-in's command grammar to fix field capitals and amounts, duplicating the provider's rules in a second place."
}
```

## Audit of delivery Z

```json
{
 "code": "Z",
 "shares": 3,
 "stated": [
  {
   "id": "S-1",
   "built": "yes",
   "observed": true,
   "evidence": "Playwright at 1440x900: GET /, Continue as Maya, saved sk-local-abcdefghijkl in Setup, typed \"Can you help me plan my week?\" + Enter -> article \"Message from Assistant\": You said: \"Can you help me plan my week?\". (Assistant has 1 message(s) from you in this conversation.); \"how many orders can you see\" -> \"I can see 3 order record(s).\"",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-2",
   "built": "yes",
   "observed": true,
   "evidence": "package.json has no dependencies/devDependencies; grep of require() in server.js, lib/, public/ finds only node: builtins, ../provider/standin and records JSON; started with plain `node server.js` with no node_modules folder.",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-3",
   "built": "yes",
   "observed": true,
   "evidence": "PORT=47811 node server.js -> \"Local chat is ready at http://127.0.0.1:47811\" and GET / 200; with PORT and DATA_DIR unset (port 3000 checked free first) -> \"ready at http://127.0.0.1:3000\", GET http://127.0.0.1:3000/ 200 with <title>Local Chat</title>.",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-4",
   "built": "yes",
   "observed": true,
   "evidence": "GET / -> 200 text/html; charset=utf-8, <!doctype html> page titled Local Chat showing Continue as Maya/Theo/Ana.",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-5",
   "built": "yes",
   "observed": true,
   "evidence": "With DATA_DIR=<work>/audit-data/d6, a session (token save, remember, long task, confirmed change) created only provider-token and state.json inside it; find -newer marker over the work folder showed no other written files. With DATA_DIR unset it created ./data/state.json in the working directory whose id matched the served storeId.",
   "spec": "stated",
   "proved": "passes",
   "proved_by": "Changed server.js `process.env.DATA_DIR ??` to `process.env.DATA_DIR_IGNORED ??` (DATA_DIR ignored, state goes to ./data): npm test still 7/7 pass (it wrote ./data/provider-token and ./data/state.json in the copy). Restored; suite back to 7/7 pass."
  },
  {
   "id": "S-6",
   "built": "yes",
   "observed": true,
   "evidence": "API probes used the app's own endpoints (POST /api/person, POST /api/actions/<name>, GET /api/view) with a cookie per client; as Maya created bot Clerk (renamed Clerk Two), 2 conversations, memory \"likes green tea\", instruction Tone=Be formal in use, saved task Count, token via Save token; stopped and restarted on same DATA_DIR with PROVIDER_TOKEN unset: same cookie shows Maya, bots [Assistant, Clerk Two], open conversation with 8 turns, memory, instructions, saved tasks, ready=true, \"what do you remember\" -> \"I remember: likes green tea.\"; confirmed ORD-1001 closed and created ORD-1005 still answered after restart; six long tasks (Completed/Cancelled/Failed with their steps) listed after restart.",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-7",
   "built": "yes",
   "observed": true,
   "evidence": "diff -r provider/ against base/provider/ shows no difference; lib/chat.js and lib/tasks.js require ../provider/standin for respond/runStep/check; every reply observed matches the stand-in rule texts.",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-8",
   "built": "yes",
   "observed": true,
   "evidence": "API probes used the app's own endpoints (POST /api/person, POST /api/actions/<name>, GET /api/view) with a cookie per client; replies shown equal stand-in text (echo, counts, field answers); remember/forget changed bot.memory; clarify: \"update ORD-1004\" then \"the status to shipped\" -> proposal ORD-1004 status open→shipped; proposal stored and shown in Proposed changes; \"long task: alpha\" launched a task with 3 steps; \"add step: check the totals\" appended the step to the running task (last result \"Done: check the totals\").",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-9",
   "built": "yes",
   "observed": true,
   "evidence": "\"HOW MANY ORDERS CAN YOU SEE\" -> \"I can see 3 order record(s).\"; \"Remember That uses metric units\" -> remembered; \"WHAT DO YOU REMEMBER\" -> list; \"What is the status of ord-1001\" -> \"The status of ORD-1001 is open.\"; first rule: \"remember that what do you remember\" -> \"I'll remember that what do you remember.\" (remember rule, not the memory list).",
   "spec": "absent",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-10",
   "built": "yes",
   "observed": true,
   "evidence": "As Maya \"what is the status of ORD-1003\" and \"set the status of ORD-1003 to closed\" -> \"I can't see a record called ORD-1003.\" with no proposal; Theo asking for Maya-created ORD-1005 -> \"I can't see a record called ORD-1005.\"; per-person reads below match readers.",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-11",
   "built": "yes",
   "observed": true,
   "evidence": "\"what is the id of <ID>\" for all 7 ids as each person: Maya reads ORD-1001, ORD-1002, ORD-1004, ACC-2001, ACC-2003; Theo reads ORD-1001, ORD-1003, ACC-2001, ACC-2002; Ana reads ORD-1004, ACC-2001, ACC-2003; all others \"I can't see a record called <ID>.\"; counts Maya 3 orders/2 accounts, Theo 2/2, Ana 1/2.",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-12",
   "built": "yes",
   "observed": true,
   "evidence": "After confirming ORD-1001 status closed and creating ORD-1005, sha256 of records/records.json and records/people.json unchanged; state.json under DATA_DIR holds the working copy with the changes; after restart Maya still reads closed and ORD-1005 Northwind.",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-13",
   "built": "yes",
   "observed": true,
   "evidence": "Fresh DATA_DIR d3b: state.json records deep-equal records/records.json; Maya \"what is the status of ORD-1001\" -> open, \"how many orders can you see\" -> 3 (after another data folder had ORD-1001 closed).",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-14",
   "built": "yes",
   "observed": true,
   "evidence": "As Maya \"create an order for Northwind totalling 40\", Confirm -> \"Changes confirmed. Created ORD-1005.\"; stored {\"type\":\"order\",\"customer\":\"Northwind\",\"status\":\"open\",\"total\":40,\"id\":\"ORD-1005\",\"readers\":[\"maya\"]}.",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-15",
   "built": "yes",
   "observed": true,
   "evidence": "Screenshot at 1440x900: centered conversation column with author labels, person turns in tinted bubbles on the right, bot replies as plain readable text on the left, clean sans-serif type, roomy spacing, composer pinned at the bottom with Enter/Shift+Enter hint; side rails for Bots/Conversations and tools.",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-16",
   "built": "yes",
   "observed": true,
   "evidence": "Replies appear as short plain paragraphs under the bot name; task progress, proposals and results appear as separate compact blocks (e.g. Proposed changes lists only \"ORD-1001 status: open → closed\" with two buttons), not mixed into the reply text.",
   "spec": "absent",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-17",
   "built": "yes",
   "observed": true,
   "evidence": "API probes used the app's own endpoints (POST /api/person, POST /api/actions/<name>, GET /api/view) with a cookie per client; conversation 1 had \"alpha one\" etc.; in a New conversation \"what did I ask first\" -> \"This is the first thing you've asked.\" and \"beta two\" -> \"(Assistant has 2 message(s) ...)\"; back in conversation 1 \"anything\" -> \"(Assistant has 4 message(s) ...)\".",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-18",
   "built": "yes",
   "observed": true,
   "evidence": "Maya's Assistant remembered \"likes tea\"; her new bot Clerk \"what do you remember\" -> \"I don't remember anything about you yet.\"; Theo's Assistant same; record answers only from readable records (S-11).",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-19",
   "built": "yes",
   "observed": true,
   "evidence": "First message \"what did I ask first\" -> \"This is the first thing you've asked.\"; later in the same conversation -> 'You first asked: \"what did I ask first\".'",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-20",
   "built": "yes",
   "observed": true,
   "evidence": "\"hello there\" -> 'You said: \"hello there\". (Assistant has 2 message(s) from you in this conversation.)'; \"  hi [slow] \" -> 'You said: \"hi\". (Assistant has 3 message(s) ...)' (marker removed, ends trimmed, N counts this message).",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-21",
   "built": "yes",
   "observed": true,
   "evidence": "\"update ORD-1004\" -> \"Which field of ORD-1004 should I change, and to what value?\" (no write); next \"the status to shipped\" -> \"I propose one change: ORD-1004 status: open → shipped. Confirm to apply it.\" with a proposal.",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-22",
   "built": "yes",
   "observed": true,
   "evidence": "UI: New bot, Bot name \"Clerk\", Save bot name -> Bots nav [Assistant, Clerk(current)]; Rename bot (textbox prefilled \"Clerk\") -> \"Clerk Prime\" listed and current; \"who are you\" -> \"I am Clerk Prime. ...\"",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-23",
   "built": "yes",
   "observed": true,
   "evidence": "UI: Conversations nav lists \"who are you\" and \"second chat here\"(current); clicking the first restored its 12 message articles and marked it current; page reload kept bot Clerk Prime and that conversation current with all articles; API: after Switch to Theo and back, Maya's last bot/conversation reopened.",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-24",
   "built": "yes",
   "observed": true,
   "evidence": "UI: saved Tone=\"Be brief\", Use Tone -> \"who are you\" -> \"I am Clerk Prime. My instructions: Be brief\"; Edit Tone filled name/text, changed to \"Be warm\", Save instruction kept one entry (Use/Edit/Delete Tone), Use Tone -> \"My instructions: Be warm\".",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-25",
   "built": "yes",
   "observed": true,
   "evidence": "UI: saved Count=\"how many orders can you see\"; Edit Count filled both fields; changed request to \"how many accounts can you see\", saved; Run Count -> \"Message from Maya: how many accounts can you see\" then \"Message from Clerk Prime: I can see 2 account record(s).\"",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-26",
   "built": "yes",
   "observed": true,
   "evidence": "UI: after \"remember that likes tea\" the Memory region lists item \"likes tea\" with Edit memory and Forget; \"what do you remember\" lists facts.",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-27",
   "built": "yes",
   "observed": true,
   "evidence": "UI: Edit memory filled Memory text with \"likes tea\"; changed to \"likes green tea\", Save memory -> list shows \"likes green tea\"; \"what do you remember\" -> \"I remember: likes green tea.\"",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-28",
   "built": "yes",
   "observed": true,
   "evidence": "\"remember that likes tea\" -> \"I'll remember that likes tea.\" and bot.memory gained \"likes tea\".",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-29",
   "built": "yes",
   "observed": true,
   "evidence": "\"forget that likes tea\" -> 'I've forgotten \"likes tea\".' and it left memory; \"forget uses metric units\" -> 'I've forgotten \"uses metric units\".' and memory became empty.",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-30",
   "built": "yes",
   "observed": true,
   "evidence": "With two facts -> \"I remember: likes tea; uses metric units.\"; with none -> \"I don't remember anything about you yet.\"",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-31",
   "built": "yes",
   "observed": true,
   "evidence": "API probes used the app's own endpoints (POST /api/person, POST /api/actions/<name>, GET /api/view) with a cookie per client; after Maya made bots, memory, an instruction, a saved task and long tasks, Theo's view showed bots [Assistant], memory [], instructions [], saved tasks [], 0 turns, 0 tasks; Theo replaying Maya's ids (open-conversation, forget-memory, use-instruction, run-task, confirm of her proposal) -> 404 \"This item is unavailable in the current workspace.\"; Theo \"add step:\" did not touch Maya's running task.",
   "spec": "stated",
   "proved": "fails",
   "proved_by": "lib/workspace.js enter(): `state.workspaces[person] = workspace` -> `state.workspaces[person] = Object.values(state.workspaces)[0] || workspace` (every person shares the first workspace; probe then showed Theo bots [Assistant, MayaSecret] and memory \"maya fact\"). npm test: 3 pass, 4 fail (setup, record scoping, saved workspace and transparent provider echo; reply reservations, library state and original history survive navigation; confirmation commits only the reviewed record changes exactly once; failed and cancelled tasks keep committed steps and ignore obsolete controls). Restored; 7/7 pass."
  },
  {
   "id": "S-32",
   "built": "yes",
   "observed": true,
   "evidence": "Maya's Assistant remembers \"likes tea\"; new bot Clerk \"what do you remember\" -> nothing; Clerk \"remember that clerk fact\"; back in Assistant -> \"I remember: likes tea.\" only.",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-33",
   "built": "yes",
   "observed": true,
   "evidence": "Remembered \"likes tea\" in Assistant conversation 1; New conversation, \"what do you remember\" -> \"I remember: likes tea.\"; later edit to \"likes green tea\" seen in both conversations.",
   "spec": "stated",
   "proved": "fails",
   "proved_by": "lib/workspace.js newConversation(): prefixed `bot.memory = [];` before `bot.conversations.push(conversation);` (probe: conv2 \"what do you remember\" -> \"I don't remember anything about you yet.\"). npm test: 6 pass, 1 fail (setup, record scoping, saved workspace and transparent provider echo: /prefer tea/ did not match). Restored; 7/7 pass."
  },
  {
   "id": "S-34",
   "built": "yes",
   "observed": true,
   "evidence": "Maya: status/tier questions answered from her readable records (ORD-1001 open, ACC-2001 gold); follow-ups after a confirmed change return the new value; Theo after Maya's confirm reads ORD-1001 closed.",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-35",
   "built": "yes",
   "observed": true,
   "evidence": "Maya \"how many orders can you see\" -> \"I can see 3 order record(s).\", accounts -> 2; Theo 2/2; Ana 1/2; after Maya created ORD-1005 her count -> 4 and Theo's stayed 2.",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-36",
   "built": "yes",
   "observed": true,
   "evidence": "\"What is the status of ord-1001\" -> \"The status of ORD-1001 is open.\"; \"what is the tier of ORD-1001\" -> \"ORD-1001 has no tier.\"; \"what is the status of ORD-1003\" (Maya) -> \"I can't see a record called ORD-1003.\"",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-37",
   "built": "yes",
   "observed": true,
   "evidence": "UI: after \"set the status of ORD-1001 to closed\" a region \"Proposed changes\" shows \"ORD-1001 status: open → closed\" with Confirm changes and Reject changes; create proposals list customer, total, status, access and \"Order ID: assigned on confirmation\".",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-38",
   "built": "yes",
   "observed": true,
   "evidence": "\"set the status of ORD-1001 to closed\" -> \"I propose one change: ORD-1001 status: open → closed. Confirm to apply it.\"; state.json records unchanged; \"what is the status of ORD-1001\" -> open; \"set the status of ORD-1003 to closed\" -> \"I can't see a record called ORD-1003.\" with no proposal.",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-39",
   "built": "yes",
   "observed": true,
   "evidence": "\"update ORD-1004\" -> \"Which field of ORD-1004 should I change, and to what value?\", ORD-1004 unchanged; \"the status to shipped\" -> same proposal text/changes as set (ORD-1004 status: open → shipped).",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-40",
   "built": "yes",
   "observed": true,
   "evidence": "\"create an order for Northwind totalling 40\" -> \"I propose creating one order: customer Northwind, total 40, status open. Confirm to apply it.\"; record count unchanged (7).",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-41",
   "built": "yes",
   "observed": true,
   "evidence": "After proposals, records in state.json unchanged and questions return old values; Reject left records alone; only POST confirm (UI Confirm changes) applied ORD-1001 closed.",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-42",
   "built": "yes",
   "observed": true,
   "evidence": "After Confirm, \"what is the status of ORD-1001\" -> closed; stored ORD-1001 {customer Acme Tools, total 125, readers [maya,theo]} unchanged otherwise.",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-43",
   "built": "yes",
   "observed": true,
   "evidence": "Confirmed create -> ORD-1005 Northwind total 40 status open, readers [maya]; Maya reads customer/total/status; Theo \"what is the customer of ORD-1005\" -> \"I can't see a record called ORD-1005.\"",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-44",
   "built": "yes",
   "observed": true,
   "evidence": "\"set the total of ORD-1002 to 99\" then Reject -> \"Changes rejected. The records were left as they were.\"; \"what is the total of ORD-1002\" -> 80; Confirm on the rejected proposal returns the same rejected result; rejected create left 7 records and Maya still sees 3 orders.",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-45",
   "built": "yes",
   "observed": true,
   "evidence": "Second Confirm on an applied proposal returned the same \"applied\" result without a second write; two parallel confirms of one create made exactly one ORD-1005 (8 records); two sends with the same submission id stored one turn.",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-46",
   "built": "yes",
   "observed": true,
   "evidence": "UI: after Confirm a region \"Change result\" reads \"Changes confirmed and applied.\" and the Proposed changes region is gone; after Reject \"Changes rejected. The records were left as they were.\"; create result \"Changes confirmed. Created ORD-1005.\"",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-47",
   "built": "yes",
   "observed": true,
   "evidence": "\"long task: alpha\" -> 'I'll work on \"alpha\" in the background and tell you when it is done.'; \"Research: Big Thing [long]\" -> 'I'll work on \"Big Thing\" ...'; steps finished one at a time at ~518 ms intervals in order.",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-48",
   "built": "yes",
   "observed": true,
   "evidence": "alpha: Done: Collect what is known about alpha / Compare the options for alpha / Write the summary of alpha; Big Thing [long]: Collect, Compare, Check part 1..5, Write the summary (8 steps).",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-49",
   "built": "yes",
   "observed": true,
   "evidence": "With STANDIN_STEP_MS empty (500 default) step completions at 557, 1075, 1593 ms (gaps ~518 ms); with STANDIN_STEP_MS=600 a running 8-step task showed 4 of 8 after ~3 s; each result \"Done: <step text>\".",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-50",
   "built": "yes",
   "observed": true,
   "evidence": "Started \"Research: Big Thing [long]\" and made no requests for 5 s -> Completed with 8 results; in Playwright closed the page with three tasks running, waited 3 s, reopened: crates Failed, alpha Completed, omega Running 4 of 8 steps.",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-51",
   "built": "yes",
   "observed": true,
   "evidence": "Playwright: reopened page showed region \"Since you were away\": \"crates — Failed — needs attention\", \"alpha — Completed\", \"omega — Running\"; 5 s later the entry updated to \"omega — Completed\"; matching Task status values in Tasks.",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-52",
   "built": "yes",
   "observed": true,
   "evidence": "During running \"gamma [long]\" sent \"add step: check the totals\" -> 'I'll add \"check the totals\" to the task that is running.' plus notice \"Step added to gamma: check the totals\"; count went 8 -> 9 and the last result was \"Done: check the totals\"; the same text in another conversation or from Theo added nothing (notice \"No step was added...\").",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-53",
   "built": "yes",
   "observed": true,
   "evidence": "While gamma's Task status was Running (1 of 9 steps), \"hello while running\" got its reply 'You said: \"hello while running\". ...'.",
   "spec": "absent",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-54",
   "built": "yes",
   "observed": true,
   "evidence": "UI: Cancel task on running \"delta [long]\" -> Task status Cancelled, note \"Remaining work was stopped. Any in-flight step result was discarded. Completed steps are shown below.\", finished steps 1-2 listed; 1.5 s later still Cancelled with 2 steps; Cancel button gone; a repeated cancel left it Cancelled.",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-55",
   "built": "yes",
   "observed": true,
   "evidence": "Playwright headless at 1440x900: as Maya sent 'long task: restart job [long]' (2 of 8 steps shown) and 'wait for me [slow]', then stopped the server by pid and restarted it on the same DATA_DIR. On reload: the conversation was intact, the pending turn showed alert 'The reply was interrupted. Retry to continue this turn.' with Retry; the task read Interrupted with 'The server stopped. Saved steps are shown below. Retry to resume with the first unfinished step.' and listed only the 3 steps that had finished; Since you were away said 'restart job — Interrupted — needs attention'. Retry produced the reply once; Retry task resumed and reached Completed with 8 distinct steps.",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-56",
   "built": "yes",
   "observed": true,
   "evidence": "Playwright headless at 1440x900: sent 'long task: audit [fail step 2]'; article 'Task: audit' Task status read Failed, steps list 'Done: Collect what is known about audit' only, note 'Step 2 failed. Retry to continue from that step.', Retry task present; the conversation's 4 messages were still shown.",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-57",
   "built": "yes",
   "observed": true,
   "evidence": "Playwright headless at 1440x900: with no token, region Setup read 'Connect the offline provider with sk-local- followed by at least 12 letters or digits. You can save it here or start the server with PROVIDER_TOKEN.' Refused tokens gave an alert and left Setup usable; the field is cleared after each attempt and the token never appeared in the DOM, API responses (/api/view, /api/person) or the state.json file (it is kept in a separate provider-token file with mode 600).",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-58",
   "built": "yes",
   "observed": true,
   "evidence": "Playwright headless at 1440x900: keyboard only: Tab reached Continue as Ana and Enter entered the workspace with focus in Message; the Tab order reached New bot, bot buttons, Rename bot, New conversation, conversation buttons, Switch person, Conversation, Message, Send, Instruction name/text, Save instruction, Task name/request, Save task. Enter on New bot focused Bot name; typing 'KeyBot' + Enter created and opened it; Instruction name, Tab, text, Tab, Enter saved 'Kb'; Space on 'Use Kb' then 'who are you' + Enter replied 'I am KeyBot. My instructions: kb text'. At 390px, Escape closed the Tools panel and returned focus to Tools.",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-59",
   "built": "yes",
   "observed": true,
   "evidence": "Playwright headless at 1440x900: first screen had buttons Continue as Maya, Continue as Theo, Continue as Ana (1 each) and no password input; clicking Continue as Maya entered the workspace.",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-60",
   "built": "yes",
   "observed": true,
   "evidence": "Playwright headless at 1440x900: as Theo, clicked Switch person; the three Continue as buttons were shown again (count 3).",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-61",
   "built": "yes",
   "observed": true,
   "evidence": "Playwright headless at 1440x900: Theo created bot Researcher, instruction Brief, memory 'I like green tea' and two conversations; Switch person, Continue as Ana showed only Assistant, 0 messages, no instructions, no memory; Switch person, Continue as Theo showed bots Assistant/Researcher, conversations 'hello one'/'second conv msg', 30 message articles, Use/Edit/Delete Brief and memory 'I like green tea'.",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-62",
   "built": "yes",
   "observed": true,
   "evidence": "Playwright headless at 1440x900: after Continue as Maya and page.reload(), person label read Maya and no Continue as button was shown; same for Theo (bots and conversations retained, open conversation still current).",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-63",
   "built": "yes",
   "observed": true,
   "evidence": "Playwright headless at 1440x900: without opening a menu (Workspace/Tools toggles hidden at 1440), Bots and Conversations navigations, Conversation, Message, Send, New bot, Rename bot, New conversation, Switch person, Tasks, Since you were away, Saved instructions, Saved tasks and Memory were all present and visible; Setup showed in the main column when no token; Proposed changes and Change result appeared in the conversation at x=338,y=228. The right Tools panel scrolls on its own (overflow auto, 1361px content in 900px) so Saved tasks/Memory are reached by scrolling the panel while Message stays at y=801.",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-64",
   "built": "yes",
   "observed": true,
   "evidence": "Playwright at 390x844: Conversation (0,54,390x674), Message and Send visible, no horizontal overflow (scrollWidth 390); Bots navigation and Memory folded away behind Workspace and Tools buttons; sending 'narrow hello' with Enter showed the reply in view; Tools opened the panel with Memory visible.",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-65",
   "built": "yes",
   "observed": true,
   "evidence": "Playwright headless at 1440x900: fresh DATA_DIR, no PROVIDER_TOKEN, Continue as Maya: region Setup visible with explanation text, textbox Provider token (1) and button Save token (1); Send disabled.",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-66",
   "built": "yes",
   "observed": true,
   "evidence": "Playwright headless at 1440x900: 'sk-local-short', 'sk-other-abcdefghijkl123' and 'sk-local-abc!defghijkl1' each gave alert 'The provider refused this token. Check its format and try again.'; 'sk-local-abcdef123456' was accepted (Setup gone). An empty field is blocked by the form's required check.",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-67",
   "built": "yes",
   "observed": true,
   "evidence": "Playwright headless at 1440x900: after each refused token an alert 'The provider refused this token. Check its format and try again.' showed, Setup stayed visible, the textbox was emptied and focused, and a following valid token was accepted.",
   "spec": "stated",
   "proved": "passes",
   "proved_by": "Removed role=\"alert\" from <p id=\"setup-error\"> in public/index.html (the refused-token message is no longer an alert): npm test still 7 pass. A server-side break (skipping provider.check in lib/chat.js save-token so a refused token is accepted) does fail 'setup, record scoping, saved workspace and transparent provider echo', but that breaks token acceptance (S-66), not the alert. Restored; suite back to 7 pass."
  },
  {
   "id": "S-68",
   "built": "yes",
   "observed": true,
   "evidence": "Playwright headless at 1440x900: saving 'sk-local-abcdef123456' removed the Setup region (count 0), no alert; then 'hello there' got 'You said: \"hello there\". (Assistant has 1 message(s) from you in this conversation.)'.",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-69",
   "built": "yes",
   "observed": true,
   "evidence": "Started with PROVIDER_TOKEN=sk-local-envtoken123456 and an empty DATA_DIR: Setup region absent (count 0), replies worked (proposals, tasks, 'who are you'); 'envtoken123456' absent from GET /, /app.js, /api/person, /api/view and the data folder (no provider-token file written).",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-70",
   "built": "yes",
   "observed": true,
   "evidence": "Saved token 'sk-local-abcdef123456' through Setup; it was absent from the page DOM, /api/view, /api/person, a save-token error response and state.json, before and after stopping the server by pid and restarting it on the same DATA_DIR (Setup not shown, replies worked after restart).",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-71",
   "built": "yes",
   "observed": true,
   "evidence": "Playwright headless at 1440x900: navigation Bots listed buttons 'Assistant[aria-current=true]', 'Researcher'; clicking Assistant moved aria-current to it and the heading/messages changed.",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-72",
   "built": "yes",
   "observed": true,
   "evidence": "Playwright headless at 1440x900: New bot, Bot name 'Helper', Save bot name: Bots listed 'Assistant', 'Helper[aria-current=true]', heading Helper, a new empty Untitled chat; Assistant still listed with its 10 messages when reopened.",
   "spec": "stated",
   "proved": "passes",
   "proved_by": "In lib/workspace.js newBot changed 'workspace.current = bot.id;' to 'workspace.current ??= bot.id;' (a new bot is created but not opened): npm test still 7 pass. Restored; suite back to 7 pass."
  },
  {
   "id": "S-73",
   "built": "yes",
   "observed": true,
   "evidence": "Playwright headless at 1440x900: Rename bot prefilled Bot name with 'Helper'; changed to 'Researcher' and Save bot name: Bots listed 'Researcher[current]'; 'who are you' replied 'I am Researcher. I have no special instructions.'",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-74",
   "built": "yes",
   "observed": true,
   "evidence": "Playwright headless at 1440x900: first Continue as Theo on this data folder: Bots listed only 'Assistant' (current); same for Ana.",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-75",
   "built": "yes",
   "observed": true,
   "evidence": "Playwright headless at 1440x900: navigation Conversations listed 'hello one', 'second conv msg[aria-current=true]'; clicking 'hello one' marked it current and showed its 10 messages.",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-76",
   "built": "yes",
   "observed": true,
   "evidence": "Playwright headless at 1440x900: New conversation added 'Untitled chat[current]' with no messages; the earlier 'hello one' stayed listed.",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-77",
   "built": "yes",
   "observed": true,
   "evidence": "Playwright headless at 1440x900: region Conversation held articles 'Message from Theo' ('hello one') and 'Message from Assistant' ('You said: \"hello one\". ...'); for a renamed bot 'Message from Researcher'.",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-78",
   "built": "yes",
   "observed": true,
   "evidence": "Playwright headless at 1440x900: filled Message 'hello one' and clicked Send: Theo's message and the bot's reply appeared in the open conversation.",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-79",
   "built": "yes",
   "observed": true,
   "evidence": "Playwright headless at 1440x900: typed 'enter sends' in Message and pressed Enter: the message and reply appeared and the box was emptied.",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-80",
   "built": "yes",
   "observed": true,
   "evidence": "Playwright headless at 1440x900: typed 'line one', Shift+Enter, 'line two': box held 'line one\\nline two' and nothing was sent (4 articles unchanged); Enter then sent it as one message with both lines.",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-81",
   "built": "yes",
   "observed": true,
   "evidence": "Playwright headless at 1440x900: sent 'think [slow]' (default 1500 ms): status 'Assistant is preparing a reply…' at 0.3 s and 1.3 s; reply arrived by 2.5 s and the status was gone.",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-82",
   "built": "yes",
   "observed": true,
   "evidence": "Playwright headless at 1440x900: sent 'please [fail once]': alert 'The reply failed. Retry to answer your original message.' with my message still shown.",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-83",
   "built": "yes",
   "observed": true,
   "evidence": "Playwright headless at 1440x900: clicked Retry after the failure: reply 'You said: \"please\". ...' appeared, 'please [fail once]' appeared once, no alert remained.",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-84",
   "built": "yes",
   "observed": true,
   "evidence": "Playwright headless at 1440x900: region Saved instructions had Instruction name, Instruction text, Save instruction (1 each); saving 'Brief' / 'Answer in one line.' added it.",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-85",
   "built": "yes",
   "observed": true,
   "evidence": "Playwright headless at 1440x900: after saving Brief, the region's buttons were 'Use Brief', 'Edit Brief', 'Delete Brief'.",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-86",
   "built": "yes",
   "observed": true,
   "evidence": "Playwright headless at 1440x900: before Use, 'who are you' gave 'I am Assistant. I have no special instructions.'; after Use Brief it gave 'I am Assistant. My instructions: Answer in one line.', also in the bot's other conversation; bot Researcher still replied 'I am Researcher. I have no special instructions.'",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-87",
   "built": "yes",
   "observed": true,
   "evidence": "Playwright headless at 1440x900: 'who are you' replied 'I am Researcher. I have no special instructions.' with none set and 'I am Assistant. My instructions: Answer in one line.' after Use Brief.",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-88",
   "built": "yes",
   "observed": true,
   "evidence": "Playwright headless at 1440x900: Edit Brief filled Instruction name 'Brief' and Instruction text 'Answer in one line.'; changed text to 'Answer in two lines.' and Save instruction: still one Brief (Use/Edit/Delete Brief), and Edit Brief again showed 'Answer in two lines.' (the open bot keeps the old text until Use Brief is chosen again, as the README says).",
   "spec": "stated",
   "proved": "passes",
   "proved_by": "In public/app.js editLibrary removed \"byId(kind + '-text').value = entry.text;\" (Edit no longer puts the text back into the textbox): npm test still 7 pass. A server-side break (lib/workspace.js saveEntry 'const entry = null;' so saving under the same name is refused as a duplicate) fails 'reply reservations, library state and original history survive navigation'. Restored; suite back to 7 pass."
  },
  {
   "id": "S-89",
   "built": "yes",
   "observed": true,
   "evidence": "Playwright headless at 1440x900: saved 'Temp', then Delete Temp: buttons went from Use/Edit/Delete Brief + Use/Edit/Delete Temp to Use/Edit/Delete Brief only.",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-90",
   "built": "yes",
   "observed": true,
   "evidence": "Playwright headless at 1440x900: region Saved tasks had Task name, Task request, Save task (1 each); saving 'Count' / 'How many orders can you see?' added it.",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-91",
   "built": "yes",
   "observed": true,
   "evidence": "Playwright headless at 1440x900: buttons 'Run Count', 'Edit Count', 'Delete Count'.",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-92",
   "built": "yes",
   "observed": true,
   "evidence": "Playwright headless at 1440x900: Run Count added 'Message from Theo: How many orders can you see?' and 'Message from Assistant: I can see 2 order record(s).' to the open conversation.",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-93",
   "built": "yes",
   "observed": true,
   "evidence": "Playwright headless at 1440x900: Edit Count filled 'Count' / 'How many orders can you see?'; changed request to 'How many accounts can you see?' and Save task: one Count remained; Run Count sent the new request and got 'I can see 2 account record(s).'",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-94",
   "built": "yes",
   "observed": true,
   "evidence": "Playwright headless at 1440x900: Delete Count left only 'Save task' in the region.",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-95",
   "built": "yes",
   "observed": true,
   "evidence": "Playwright headless at 1440x900: after 'Remember that I like tea' and 'remember that my desk is 4B', region Memory listed items 'I like tea', 'my desk is 4B'; bot Researcher's Memory was empty.",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-96",
   "built": "yes",
   "observed": true,
   "evidence": "Playwright headless at 1440x900: each memory list item had buttons 'Edit memory' and 'Forget'.",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-97",
   "built": "yes",
   "observed": true,
   "evidence": "Playwright headless at 1440x900: Forget on 'my desk is 4B' left only 'I like green tea'; 'what do you remember' replied 'I remember: I like green tea.'",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-98",
   "built": "yes",
   "observed": true,
   "evidence": "Playwright headless at 1440x900: Edit memory filled Memory text 'I like tea'; changed to 'I like green tea' and Save memory: list showed 'I like green tea', 'my desk is 4B'; 'what do you remember' replied 'I remember: I like green tea; my desk is 4B.'",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-99",
   "built": "yes",
   "observed": true,
   "evidence": "Playwright headless at 1440x900: as Maya 'set the status of ORD-1001 to closed' showed region Proposed changes 'ORD-1001 status: open → closed' with Confirm changes and Reject changes; 'Update ORD-1004' then 'the total to 99' showed 'ORD-1004 total: 45 → 99'; a create showed 'Create order / Customer: Zed / Total: 12 / Status: open / Access: Maya only / Order ID: assigned on confirmation'. Before confirming, ORD-1001 still read open.",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-100",
   "built": "yes",
   "observed": true,
   "evidence": "Playwright headless at 1440x900: Confirm changes gave region Change result 'Changes confirmed and applied.' (ORD-1001 then read closed); Reject changes gave 'Changes rejected. The records were left as they were.' (ORD-1002 still shipped); confirming the create gave 'Changes confirmed. Created ORD-1005.'",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-101",
   "built": "yes",
   "observed": true,
   "evidence": "Playwright headless at 1440x900: 'Long task: weekly review' showed article 'Task: weekly review' in region Tasks; 'long task: audit [fail step 2]' showed 'Task: audit', matching the stand-in's task.title 'audit'.",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-102",
   "built": "yes",
   "observed": true,
   "evidence": "Playwright headless at 1440x900: status 'Task status' read Running, Completed, Failed (fail step 2), Cancelled (after Cancel task) and Interrupted (after a server restart).",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-103",
   "built": "yes",
   "observed": true,
   "evidence": "Playwright headless at 1440x900: mid-run the article read '2 of 3 steps finished.' with 'Done: Collect what is known about weekly review' and 'Done: Compare the options for weekly review'; at the end all three 'Done: ...' steps were listed.",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-104",
   "built": "yes",
   "observed": true,
   "evidence": "Playwright headless at 1440x900: Cancel task present while Running (1) and absent once Completed (0); clicking it on 'big job [long]' gave Cancelled with 'Remaining work was stopped. Any in-flight step result was discarded. Completed steps are shown below.' and the 3 finished steps.",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-105",
   "built": "yes",
   "observed": true,
   "evidence": "Playwright headless at 1440x900: 'weekly review' read Completed after its 3 steps finished; 'away job [long]' Completed with 8 steps; the retried 'audit' and 'restart job' tasks also reached Completed.",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-106",
   "built": "yes",
   "observed": true,
   "evidence": "Playwright headless at 1440x900: Retry task present on the Failed 'audit' task (1) and the Interrupted 'restart job' task, absent on Completed; Retry moved status to Running and then Completed without repeating finished steps.",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-107",
   "built": "yes",
   "observed": true,
   "evidence": "Playwright headless at 1440x900: started 'long task: away job [long]', closed the page, reopened after 1.5 s: region Since you were away 'away job — Running'; reopened after it finished: 'away job — Completed'; after a server restart: 'restart job — Interrupted — needs attention'.",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-108",
   "built": "yes",
   "observed": true,
   "evidence": "npm test (node --test) ran test/chat.test.js: 7 tests, 7 pass, covering lib/store, lib/chat, lib/records, lib/tasks, lib/workspace through createServer and records.preview/decide/readable.",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  }
 ],
 "unstated": [
  {
   "id": "U-1",
   "behaviour": "The person is held per browser profile by an HttpOnly session cookie; tabs of one browser share it and are resynchronised through a BroadcastChannel; a second browser context can be another person.",
   "handling": "sound",
   "observed": true,
   "evidence": "Playwright: context A Continue as Maya + \"hello from Maya\", context B Continue as Theo + \"hello from Theo\", reload both: A shows Maya with only her messages, B Theo with only his; a further send from A lands in Maya's conversation. Second tab of A opens as Maya; Switch person to Ana there flips tab 1 to Ana (empty thread) and a send from tab 1 goes to Ana's conversation as Ana.",
   "spec": "silent",
   "told": "no",
   "told_where": ""
  },
  {
   "id": "U-2",
   "behaviour": "Every action is scoped server-side to the session cookie's person and a per-selection generation; ids of another person's conversation, memory or proposal give 404, an old generation gives 409.",
   "handling": "sound",
   "observed": true,
   "evidence": "As Maya noted conversation/memory/proposal ids, Switch to Ana in same cookie, POST /api/actions/open-conversation, /confirm (Maya's proposal id), /forget-memory with Ana's generation and Maya's ids -> 404 \"This item is unavailable in the current workspace.\"; with Maya's old generation -> 409; cookieless -> 409. Back as Maya: \"what is the status of ORD-1001\" -> open; memory still \"likes tea\".",
   "spec": "decided-unmarked",
   "told": "no",
   "told_where": ""
  },
  {
   "id": "U-3",
   "behaviour": "First screen is only the three Continue as buttons; Setup appears inside the workspace after a person is chosen, with Send disabled until a token is saved; after Switch person a reload stays on the chooser.",
   "handling": "acceptable",
   "observed": true,
   "evidence": "Playwright on empty data, no token: visible controls only \"Continue as Maya/Theo/Ana\"; Setup region not present. After Continue as Maya: Setup visible, Send disabled. Bad token -> alert text \"The provider refused this token...\"; sk-local-abcdefghijkl saved -> Setup hidden, page HTML does not contain it. Switch person, reload -> chooser shown, Message textbox not visible.",
   "spec": "silent",
   "told": "no",
   "told_where": ""
  },
  {
   "id": "U-5",
   "behaviour": "An accepted PROVIDER_TOKEN takes precedence and is not copied into DATA_DIR; while it is in use Setup is hidden and a save-token request is silently ignored; a token saved through Setup is kept in DATA_DIR/provider-token and used when the variable is unset.",
   "handling": "sound",
   "observed": true,
   "evidence": "PROVIDER_TOKEN=sk-local-abcdefghijkl: view ready=true, \"hello\" answered; POST save-token sk-local-zzzzzzzzzzzz9 -> 200 but DATA_DIR holds only state.json. Restart with variable set -> ready; unset -> ready=false (Setup); save token -> provider-token file written; restart with variable set again -> \"who are you\" answered. No response contained either token.",
   "spec": "open",
   "told": "yes",
   "told_where": "README.md: \"`PROVIDER_TOKEN` | An accepted environment token takes precedence.\""
  },
  {
   "id": "U-6",
   "behaviour": "A refused environment token is treated as unsaved: Setup is shown and Send is blocked until an accepted token is saved; a refused token in Setup gives an alert and can be retried.",
   "handling": "sound",
   "observed": true,
   "evidence": "PROVIDER_TOKEN=not-a-token: Continue as Maya -> ready=false (Setup); send -> 409 \"Save an accepted provider token before sending a message.\" PROVIDER_TOKEN=sk-local-short: ready=false; save-token sk-local-short -> 400 \"The provider refused this token. Check its format and try again.\" (shown in Setup alert in Playwright); save sk-local-abcdefghijkl -> \"hello\" answered.",
   "spec": "open",
   "told": "yes",
   "told_where": "README.md: \"A refused environment value falls back to an accepted saved token, or to Setup if neither works.\""
  },
  {
   "id": "U-7",
   "behaviour": "The saved token is stored in plain text in DATA_DIR/provider-token with mode 600, never in state.json, responses or server output; any sk-local- token text a person types is replaced with [redacted] before storage.",
   "handling": "sound",
   "observed": true,
   "evidence": "Saved token, sent \"hello [fail once]\", \"my token is sk-local-abcdefghijkl\", \"remember that token sk-local-...\"; grep of DATA_DIR: only provider-token contains it (mode 600); all view responses free of it; stored message reads \"my token is [redacted]\", memory \"token [redacted]\"; server output only \"Local chat is ready at ...\". Fail-once alert in page: \"The reply failed. Retry to answer your original message.\"",
   "spec": "decided-unmarked",
   "told": "yes",
   "told_where": "README.md: \"When setup saves a token, the app stores it in a separate restricted `provider-token` file.\""
  },
  {
   "id": "U-8",
   "behaviour": "A new person, and a new bot, start with one empty open conversation (\"Untitled chat\") so Send works at once; a new bot has no memory and no instructions; New conversation becomes the open one.",
   "handling": "sound",
   "observed": true,
   "evidence": "Fresh Ana: bots [\"Assistant\"], one conversation \"Untitled chat\", 0 turns; \"who are you\" -> \"I am Assistant. I have no special instructions.\"; \"what do you remember\" -> \"I don't remember anything about you yet.\" New bot Clerk: one empty conversation, memory [], instructions \"\", \"who are you\" -> \"I am Clerk. I have no special instructions.\" New conversation -> the new one is current.",
   "spec": "decided-unmarked",
   "told": "no",
   "told_where": ""
  },
  {
   "id": "U-9",
   "behaviour": "Blank names refused (browser required + server \"Enter a bot name.\"); names over 80 characters refused by the server and cut at 80 by the textbox; duplicate names accepted and shown as identical buttons.",
   "handling": "poor",
   "observed": true,
   "evidence": "save new-bot with \"\" and \"   \" -> 400 \"Enter a bot name.\"; 300-char name -> 400 \"Use at most 80 characters for a bot name.\" (UI textbox keeps 80). New bot \"Assistant\" accepted: Bots navigation buttons read \"Assistant\", \"Assistant [current]\" by accessible name and visually; nothing distinguishes the two before selecting.",
   "spec": "open",
   "told": "no",
   "told_where": "",
   "rerun": true
  },
  {
   "id": "U-11",
   "behaviour": "Conversation buttons are named by the first message cut to 38 characters plus an ellipsis, or \"Untitled chat\" while empty, in creation order; empty conversations and ones sharing a long opening get identical names.",
   "handling": "poor",
   "observed": true,
   "evidence": "Playwright: two New conversation clicks -> Conversations buttons \"Untitled chat\", \"Untitled chat [current]\"; two conversations starting \"Please look up the latest shipping details for customer Alpha/Beta\" -> both buttons \"Please look up the latest shipping det…\" (one marked current).",
   "spec": "open",
   "told": "no",
   "told_where": "",
   "rerun": true
  },
  {
   "id": "U-13",
   "behaviour": "The last-open bot and conversation are kept per person on the server (survive reload, Switch person and back, a new browser visit and a server restart); the unsent draft and scroll position are kept in sessionStorage for the tab (kept on reload and switch-back, lost in a new browser session).",
   "handling": "sound",
   "observed": true,
   "evidence": "Playwright as Maya on bot Second, its second conversation, scrollTop 300, draft \"unsent draft\": reload -> same bot/conversation, draft and scroll 300 kept; Switch to Theo and back -> same; new browser context with cookies -> bot Second, draft empty, scrolled to bottom; server restart + reload -> bot Second, same conversation current.",
   "spec": "open",
   "told": "no",
   "told_where": ""
  },
  {
   "id": "U-14",
   "behaviour": "Saved instructions and saved tasks are one library per person, shown for every bot; Use changes only the open bot, Run sends in the open conversation; another person sees none of them.",
   "handling": "sound",
   "observed": true,
   "evidence": "Maya on Assistant saved Tone=\"Be brief\" and Ping=\"hello\"; new bot Other lists Tone and Ping; Use Tone + Run Ping there -> reply \"You said: \\\"hello\\\". (Other has 1 ...)\", Other \"who are you\" -> \"My instructions: Be brief\"; Assistant \"who are you\" -> \"I have no special instructions.\"; Theo: instructions [] and savedTasks [].",
   "spec": "open",
   "told": "yes",
   "told_where": "README.md: \"Saved instructions and saved tasks are available across your bots.\""
  },
  {
   "id": "U-15",
   "behaviour": "A second save under an existing name (case and surrounding spaces ignored) without Edit is refused with \"An entry with this name already exists. Choose Edit to change it.\"; empty name or text refused.",
   "handling": "sound",
   "observed": true,
   "evidence": "save-instruction A=x -> 200; A=y -> 409 with that message; \"a \" -> 409; only one A with text x remains. Empty name -> \"Enter a name.\"; blank text -> \"Enter the text.\"; same for save-task (Ping duplicate 409, empty request \"Enter the text.\").",
   "spec": "open",
   "told": "no",
   "told_where": "",
   "rerun": true
  },
  {
   "id": "U-16",
   "behaviour": "Saving after Edit with a changed name renames the same item (no second entry).",
   "handling": "sound",
   "observed": true,
   "evidence": "Edit Tone (itemId) saved as Style -> instructions [\"Style=Be brief\",\"A=x\"]; Edit Ping saved as Pong -> savedTasks [\"Pong=hello\"].",
   "spec": "silent",
   "told": "no",
   "told_where": ""
  },
  {
   "id": "U-17",
   "behaviour": "Use copies the instruction text into the bot; later edits or deletion of the saved entry do not change the bot until Use is chosen again; after deleting the entry in use there is no control to clear the bot's instructions, and the page only says \"Custom instructions active for <bot>.\" without the text.",
   "handling": "acceptable",
   "observed": true,
   "evidence": "Use Formal (\"Be formal\") -> \"who are you\": \"My instructions: Be formal\"; edit Formal to \"Be casual\" -> still \"Be formal\"; delete Formal -> still \"Be formal\". Page status: \"Custom instructions active for Assistant.\"",
   "spec": "open",
   "told": "yes",
   "told_where": "README.md: \"Use copies the saved instruction into the current bot. Select Use again to activate an edit.\""
  },
  {
   "id": "U-20",
   "behaviour": "Send is guarded: the same submission id is stored once, a different send while a reply is pending is refused (409 \"A reply is on its way...\"), the page shows a status; the reply lands in its own conversation and person even after switching conversation, reloading or switching person; a lost acknowledgement is resent with the same submission id and not applied twice.",
   "handling": "sound",
   "observed": true,
   "evidence": "API: two sends with submission s1 -> 200,200 then s2 -> 409; one turn stored. Playwright: Enter twice on \"hello [slow]\" -> one message, status \"Assistant is preparing a reply…\". Switch conversation during \"[slow]\" -> other conversation empty, reply in the original. Reload during wait -> status shown, reply arrives. Maya \"set the status of ORD-1001 to closed [slow]\" then Switch to Theo: Theo sees no turns or proposals; back to Maya the proposal is there. Aborted response for \"long task: alpha [slow]\" -> alert \"The request could not be verified...\"; pressing Enter again -> still one message and one new task.",
   "spec": "open",
   "told": "no",
   "told_where": ""
  },
  {
   "id": "U-21",
   "behaviour": "A failed reply stays as a failed turn with an alert and Retry, kept after reload and restart; a new message is accepted while it stays failed; a reply interrupted by stopping the server becomes \"interrupted\" with Retry (not automatic); Retry never duplicates the person message.",
   "handling": "sound",
   "observed": true,
   "evidence": "Playwright \"hello [fail once]\": alert \"The reply failed. Retry to answer your original message.\"; reload -> alert and Retry still there; Retry -> one Maya message and the reply. API: at the failure send \"next\" -> answered; server restart, retry-reply -> first turn completes (\"Assistant has 1 message(s)\"), 3 turns total, second retry does nothing. \"hello [slow]\" + SIGKILL + restart -> turn \"interrupted\", stays so; Retry -> completes.",
   "spec": "open",
   "told": "yes",
   "told_where": "README.md: \"Any unfinished reply or running task that was stopped becomes explicitly retryable.\""
  },
  {
   "id": "U-22",
   "behaviour": "The stored and displayed person message keeps the [fail once] and [slow] markers; the first attempt still fails and Retry succeeds.",
   "handling": "acceptable",
   "observed": true,
   "evidence": "Send \"hello [fail once]\" -> failed; retry-reply -> reply \"You said: \\\"hello\\\". ...\"; \"what did I ask first\" -> \"You first asked: \\\"hello [fail once]\\\".\"; Message article reads \"hello [fail once]\".",
   "spec": "silent",
   "told": "no",
   "told_where": ""
  },
  {
   "id": "U-23",
   "behaviour": "A repeated remember is merged (case-insensitive exact match); a forget that matches no fact removes nothing but the reply still says \"I've forgotten ...\" with no notice from the app; an exact forget removes the fact.",
   "handling": "poor",
   "observed": true,
   "evidence": "\"remember that likes tea\" twice -> Memory [\"likes tea\"]; \"forget tea\" -> reply \"I've forgotten \\\"tea\\\".\" Memory still [\"likes tea\"], no notice; \"forget coffee\" -> \"I've forgotten \\\"coffee\\\".\"; \"forget that likes tea\" -> Memory []. \"remember that Likes Tea\" then \"remember that likes tea.\" -> one item.",
   "spec": "open",
   "told": "no",
   "told_where": ""
  },
  {
   "id": "U-25",
   "behaviour": "Memory text starts filled with the fact being edited; Save memory replaces that item.",
   "handling": "sound",
   "observed": true,
   "evidence": "Playwright: \"remember that likes tea\", Edit memory -> Memory text \"likes tea\"; changed to \"likes coffee\", Save memory -> list [\"likes coffee\"].",
   "spec": "silent",
   "told": "no",
   "told_where": ""
  },
  {
   "id": "U-26",
   "behaviour": "Management actions add no message; Run, Send and memory phrases typed into Message write to the conversation.",
   "handling": "sound",
   "observed": true,
   "evidence": "Playwright: article count 4 before; Save instruction, Use Tone, Save task, Rename bot, Forget, Delete Tone -> still 4; Run Ping -> 6. API: after Use/Delete/Save task/Rename/Save memory/Forget turns were [\"first one\",\"remember that x1\"]; \"what did I ask first\" -> \"You first asked: \\\"first one\\\".\"",
   "spec": "silent",
   "told": "no",
   "told_where": ""
  },
  {
   "id": "U-27",
   "behaviour": "The page polls every 400 ms: Memory and task status/steps update while the page stays open.",
   "handling": "sound",
   "observed": true,
   "evidence": "Playwright without reload: Memory list showed \"likes tea\" after the send; Task: alpha status sampled every 250 ms: Running:0, Running:1, Running:1, Running:2, Completed:3.",
   "spec": "silent",
   "told": "no",
   "told_where": ""
  },
  {
   "id": "U-29",
   "behaviour": "Changes to readers, id or type are not offered: no Proposed changes region, and a notice \"No proposal was opened. The requested change could not be safely previewed.\" (the stand-in's reply text above it still says \"I propose one change ... Confirm to apply it.\"); a change to an account's owner field is offered as an ordinary exact proposal without warning (owner does not affect who may read).",
   "handling": "acceptable",
   "observed": true,
   "evidence": "Maya \"set the readers of ORD-1001 to ana\", \"set the id of ORD-1004 to ORD-9999\", \"set the type of ORD-1004 to account\" -> 0 proposals each, notice as quoted; \"set the owner of ACC-2001 to theo\" -> proposal ACC-2001 owner: maya -> theo (rejected). Maya still sees 3 orders; state readers unchanged.",
   "spec": "open",
   "told": "no",
   "told_where": ""
  },
  {
   "id": "U-30",
   "behaviour": "Values are validated against a fixed schema: a word into total and an unknown field give no proposal (generic notice, no hint how to correct); unknown status words and decimal totals are offered exactly as shown; the corrected request works in the same conversation.",
   "handling": "acceptable",
   "observed": true,
   "evidence": "\"set the total of ORD-1001 to banana\" and \"set the colour of ORD-1001 to red\" -> no proposal, notice \"No proposal was opened. The requested change could not be safely previewed.\"; \"create an order for Acme totalling 42.50\" -> stand-in echoes (no proposal); \"set the status of ORD-1001 to banana\" -> proposal open -> banana; \"set the total of ORD-1001 to 130\" -> proposal 125 -> 130; \"to 12.5\" -> proposal 125 -> 12.5; total still 125 after rejecting.",
   "spec": "silent",
   "told": "no",
   "told_where": ""
  },
  {
   "id": "U-31",
   "behaviour": "Undecided proposals persist through reload, restart and switching conversation; several may be pending; an older one can be confirmed after a newer one is rejected; only Confirm changes confirms (Enter in Message does nothing); after a decision the buttons are replaced by Change result and repeated confirms write nothing.",
   "handling": "sound",
   "observed": true,
   "evidence": "Two proposals on ORD-1002 (delivered, lost) survived restart and switching away and back; reject newer -> \"Changes rejected...\"; confirm older -> \"Changes confirmed and applied.\"; confirm rejected one and confirm older again -> results unchanged; status delivered. Playwright: Enter in empty Message with two proposals -> still 2 proposals, 0 results; after Reject the region becomes Change result with no buttons.",
   "spec": "open",
   "told": "yes",
   "told_where": "README.md: \"Leaving the conversation preserves the pending decision.\""
  },
  {
   "id": "U-32",
   "behaviour": "The stand-in sentence plus a preview listing Create order, Customer, Total, Status, Access \"<person> only\" and \"Order ID: assigned on confirmation\"; nothing stored before confirm; Change result reports the assigned id.",
   "handling": "sound",
   "observed": true,
   "evidence": "Maya \"create an order for Northwind totalling 40\" -> proposal create {order, Northwind, open, 40}; \"how many orders can you see\" -> 3; confirm -> \"Changes confirmed. Created ORD-1005.\"; then 4 orders; \"what is the customer of ORD-1005\" -> Northwind.",
   "spec": "open",
   "told": "yes",
   "told_where": "README.md: \"The app assigns new order IDs at confirmation and reports the final ID.\""
  },
  {
   "id": "U-33",
   "behaviour": "A confirm whose from-value no longer holds is refused as expired and the person is told to ask for a fresh preview; repeating the confirm writes nothing.",
   "handling": "sound",
   "observed": true,
   "evidence": "Maya proposal ORD-1001 open -> closed pending; Theo \"set the status of ORD-1001 to shipped\" confirmed; Maya Confirm -> Change result \"Changes were left unapplied. This preview is no longer current. Ask for a fresh preview...\"; again -> same; status shipped.",
   "spec": "open",
   "told": "yes",
   "told_where": "README.md: \"A stale preview expires and requires a fresh request.\""
  },
  {
   "id": "U-34",
   "behaviour": "Order ids are assigned at confirm time as the lowest unused ORD- number across all records; two people get distinct ids.",
   "handling": "sound",
   "observed": true,
   "evidence": "Maya \"create an order for North totalling 10\" and Ana \"create an order for South totalling 20\" both pending, confirmed in turn -> \"Created ORD-1006\" and \"Created ORD-1007\"; Maya sees ORD-1006 North and cannot see ORD-1007; Ana the reverse.",
   "spec": "decided-unmarked",
   "told": "yes",
   "told_where": "README.md: \"The app assigns new order IDs at confirmation and reports the final ID.\""
  },
  {
   "id": "U-35",
   "behaviour": "The Change result is stored with the proposal in the conversation and shown after reload and restart; no further Confirm is offered.",
   "handling": "sound",
   "observed": true,
   "evidence": "Playwright: Confirm changes then reload at once -> Change result regions \"Changes rejected...\" and \"Changes confirmed and applied.\" present, 0 Confirm changes buttons.",
   "spec": "decided-unmarked",
   "told": "no",
   "told_where": ""
  },
  {
   "id": "U-36",
   "behaviour": "One working copy of the records: a change confirmed by one reader is seen by the other reader, also after restart; starting files unchanged.",
   "handling": "sound",
   "observed": true,
   "evidence": "Theo confirmed ORD-1001 -> closed; Maya \"what is the status of ORD-1001\" -> closed. records/records.json byte-identical to base after all probes; state.json holds the working copy.",
   "spec": "decided-unmarked",
   "told": "no",
   "told_where": ""
  },
  {
   "id": "U-37",
   "behaviour": "Tasks shows all of the person's tasks from every bot and conversation, each with Open conversation when it belongs elsewhere; never another person's.",
   "handling": "sound",
   "observed": true,
   "evidence": "Maya \"long task: report [long]\" in conversation 1; in conversation 2 and in bot B2 the Tasks list still shows \"report\" (UI: \"Task: report | Cancel task, Open conversation\"); Theo tasks [].",
   "spec": "silent",
   "told": "no",
   "told_where": ""
  },
  {
   "id": "U-38",
   "behaviour": "A second long task runs alongside the first; both shown in Tasks.",
   "handling": "sound",
   "observed": true,
   "evidence": "\"long task: alpha [long]\" then \"long task: beta\" -> both Running, then alpha Completed 8/8 and beta Completed 3/3.",
   "spec": "silent",
   "told": "no",
   "told_where": ""
  },
  {
   "id": "U-39",
   "behaviour": "With no running task, a notice says \"No step was added. No task is running in this conversation.\" (under the stand-in's \"I'll add ...\" reply); with several running it adds to the latest started and the notice names only the title (\"Step added to same: extra\"), so two tasks with the same title cannot be told apart from the feedback.",
   "handling": "poor",
   "observed": true,
   "evidence": "API and Playwright: \"add step: double-check\" with none running -> notice as quoted, no task created. Two \"long task: same [long]\" then \"add step: extra\" -> notice \"Step added to same: extra\"; both articles are named \"Task: same\"; only the step counts (\"1 of 9\" vs \"2 of 8\") differ.",
   "spec": "open",
   "told": "no",
   "told_where": "",
   "rerun": true
  },
  {
   "id": "U-40",
   "behaviour": "A finished task leaves no message in its conversation; its result stays in the task article, findable after reload.",
   "handling": "acceptable",
   "observed": true,
   "evidence": "\"long task: notes\" completed -> conversation turns only [\"long task: notes\", \"I'll work on \\\"notes\\\"...\"]; Tasks article shows Completed and the three steps after reload.",
   "spec": "silent",
   "told": "no",
   "told_where": ""
  },
  {
   "id": "U-41",
   "behaviour": "Tasks keep running with the page closed; on restart a running task is marked Interrupted with a note and Retry task, finished steps kept, the in-flight step not counted; Retry resumes at the next unfinished step; no automatic resume.",
   "handling": "sound",
   "observed": true,
   "evidence": "Tasks completed with no client connected (U-44 probe). \"long task: audit [long]\" SIGKILL after 2 steps -> after restart Interrupted, 2 steps, note \"The server stopped. Saved steps are shown below. Retry to resume with the first unfinished step.\"; unchanged 1.5 s later; Retry task -> Completed with 8 distinct steps. SIGTERM case -> Interrupted with 2 steps.",
   "spec": "open",
   "told": "yes",
   "told_where": "README.md: \"Any unfinished reply or running task that was stopped becomes explicitly retryable.\""
  },
  {
   "id": "U-42",
   "behaviour": "Retry task resumes at the failed step; step 1 is listed once.",
   "handling": "sound",
   "observed": true,
   "evidence": "\"long task: plan [fail step 2]\" -> Failed, 1 step, note \"Step 2 failed. Retry to continue from that step.\"; Retry task -> Completed with steps 1,2,3 each once.",
   "spec": "decided-unmarked",
   "told": "yes",
   "told_where": "README.md: \"If a task fails or is interrupted, use Retry task to continue its unfinished steps.\""
  },
  {
   "id": "U-43",
   "behaviour": "Cancel acts at once without asking; an in-flight step's result is discarded and said so; status stays Cancelled with finished steps listed.",
   "handling": "sound",
   "observed": true,
   "evidence": "STANDIN_STEP_MS=3000, \"long task: big [long]\", Cancel task mid-step 2 -> status Cancelled, note \"Remaining work was stopped. Any in-flight step result was discarded. Completed steps are shown below.\", 1 step listed; 4 s later still Cancelled with 1 step.",
   "spec": "open",
   "told": "yes",
   "told_where": "README.md: \"Cancel preserves finished steps and discards an in-flight result.\""
  },
  {
   "id": "U-44",
   "behaviour": "Since you were away is computed in the browser against a task revision saved in localStorage: on return it lists tasks changed since the last visit plus any still Running, Failed or Interrupted (marked \"needs attention\"); completed items drop after the next reload, failed ones stay until resolved; pending proposals are not reported; only the person's own tasks. In a browser with no stored revision (first visit there) the region stays hidden even when a task has failed.",
   "handling": "acceptable",
   "observed": true,
   "evidence": "Playwright: Maya started \"long task: crates [fail step 2]\" and \"long task: alpha\", closed the tab, reopened after 4 s -> \"crates — Failed — needs attention\", \"alpha — Completed\"; reload -> only crates; reload after a send and while a proposal waited -> only crates; Ana -> region hidden, 0 tasks. Fresh browser context as Maya with crates Failed -> region hidden.",
   "spec": "open",
   "told": "no",
   "told_where": ""
  },
  {
   "id": "U-45",
   "behaviour": "Below roughly 1000 px both side panels fold behind Workspace and Tools buttons (with Escape closing and returning focus); conversation, Message and Send stay in view at every width tried; at 1440 and 1024 all regions are on the main screen.",
   "handling": "sound",
   "observed": true,
   "evidence": "Playwright widths 1440, 1024: Bots, Conversations, Saved instructions, Saved tasks, Memory, Tasks visible, no toggles. 900, 768, 600, 480, 375: those hidden, Workspace and Tools buttons visible, Conversation and Message in view, no horizontal scroll. At 375 Workspace opens Bots and Conversations (focus to New bot), Escape returns focus to Workspace; Tools opens the four utility regions.",
   "spec": "open",
   "told": "yes",
   "told_where": "README.md: \"On narrow windows, Workspace and Tools open the secondary panels. Escape closes an open panel and returns focus to its button.\""
  },
  {
   "id": "U-46",
   "behaviour": "A missing DATA_DIR is created; an unwritable one, invalid JSON or an unexpected shape makes the server refuse to start with an actionable message; the damaged file is left as it was.",
   "handling": "sound",
   "observed": true,
   "evidence": "DATA_DIR=<work>/dd/p7/missing/deeper -> created, state.json written, GET / 200. Read-only (0500) folder, state.json \"{not json\" and {\"hello\":1} -> exit with \"Cannot open the data directory. Check its permissions and restore a readable state snapshot if it is damaged.\"; damaged files unchanged; records/ unchanged.",
   "spec": "silent",
   "told": "no",
   "told_where": "",
   "rerun": true
  },
  {
   "id": "U-49",
   "behaviour": "Field names are passed to the stand-in as typed: STATUS gets \"ORD-1001 has no STATUS.\"; a capitalised set offers no proposal (notice); lower case works; reader rules still apply.",
   "handling": "acceptable",
   "observed": true,
   "evidence": "Maya \"what is the STATUS of ORD-1001\" -> \"ORD-1001 has no STATUS.\"; lower case -> \"The status of ORD-1001 is closed.\"; \"set the Status of ORD-1001 to open\" -> stand-in text \"Status: nothing → open\" but no proposal, notice \"No proposal was opened...\"; lower case -> proposal closed -> open. Ana both forms -> \"I can't see a record called ORD-1001.\"",
   "spec": "silent",
   "told": "no",
   "told_where": "",
   "rerun": true
  },
  {
   "id": "U-50",
   "behaviour": "A lookup of ORD-1001A is answered with ORD-1001's value (\"The status of ORD-1001 is closed.\") with no notice that ORD-1001A does not exist; a set on ORD-1001A gets the echo reply and no proposal.",
   "handling": "poor",
   "observed": true,
   "evidence": "Maya \"what is the status of ORD-1001A\" -> \"The status of ORD-1001 is closed.\"; \"set the status of ORD-1001A to closed\" -> \"You said: ...\" echo, no proposal; \"what is the status of ORD-1001\" -> closed.",
   "spec": "silent",
   "told": "no",
   "told_where": "",
   "rerun": true
  },
  {
   "id": "U-54",
   "behaviour": "On the first failed write the store marks itself unavailable: the action and every later request (including the view) get 503 \"Storage is unavailable. Restart the server with the same data directory to recover.\"; the page shows that alert and keeps the draft and form text; after restart the earlier work is present and the failed save is absent.",
   "handling": "sound",
   "observed": true,
   "evidence": "Made DATA_DIR 0500 with the app open: Save instruction -> alert as quoted, list unchanged, name kept; send -> same alert, draft kept, no message added; restoring access without restart still 503; after restart: earlier turns present, instruction \"RO\" absent, running tasks Interrupted.",
   "spec": "silent",
   "told": "yes",
   "told_where": "README.md: \"If the server reports storage is unavailable, check the directory permissions and restart with the same directory.\"",
   "rerun": true
  },
  {
   "id": "U-57",
   "behaviour": "A failing task step only marks that task Failed and the rest stays usable; a storage error during a task step switches the whole app into a reported unavailable mode (503 with a restart instruction; server output \"Background work paused. Restart with the same data directory to recover.\").",
   "handling": "acceptable",
   "observed": true,
   "evidence": "\"long task: crates [fail step 2]\" -> Failed while other tasks and chat worked (p5/p8 probes). With DATA_DIR made read-only during running tasks: server output \"Background work paused...\" twice; /api/view 503 with the restart message; after restart tasks Interrupted and retryable.",
   "spec": "silent",
   "told": "no",
   "told_where": "",
   "rerun": true
  },
  {
   "id": "U-58",
   "behaviour": "After Reject or Confirm, focus moves to the heading of that proposal's Change result; Enter there does nothing; after Send focus returns to Message; after Save memory focus goes to the first Edit memory button.",
   "handling": "sound",
   "observed": true,
   "evidence": "Playwright with two proposals: keyboard Reject changes on the first -> focus H3 \"Change result\" in that region; Enter -> other proposal still pending (1 Proposed changes, 1 Change result). After Send -> activeElement #message. After Save memory -> \"Edit memory\".",
   "spec": "silent",
   "told": "no",
   "told_where": "",
   "rerun": true
  },
  {
   "id": "U-60",
   "behaviour": "Request errors return an honest JSON message that the page shows as an alert (malformed body -> \"The request could not be read.\"); unexpected errors would get a generic \"could not finish the request. Try reloading.\" and are not written to server output (only background failures are logged).",
   "handling": "poor",
   "observed": true,
   "evidence": "POST /api/actions/send with body \"{bad\" -> 400 \"The request could not be read.\"; confirm with object itemId -> 404; send with object text -> 400 \"Enter a message.\"; numeric submission -> 400; server output only the ready line. No route produced a 500 in my probes; server.js catch writes nothing to stderr.",
   "spec": "silent",
   "told": "no",
   "told_where": "",
   "rerun": true
  }
 ],
 "extras": [
  {
   "what": "Starter prompt buttons in an empty conversation (Count visible orders, Check an order, Start a weekly review)",
   "where": "public/app.js emptyThread",
   "worth": "value",
   "why": "Helps a new person get started; fills Message without sending."
  },
  {
   "what": "Open conversation button on task cards from other conversations",
   "where": "public/app.js renderTasks",
   "worth": "value",
   "why": "Reaches the conversation a task belongs to from the person-wide Tasks list."
  },
  {
   "what": "Redaction of any sk-local- token text a person types, in messages, replies and memory",
   "where": "lib/workspace.js scrub, public/app.js draft storage",
   "worth": "neutral",
   "why": "Protects a pasted secret but silently alters what the person wrote."
  },
  {
   "what": "Origin / Sec-Fetch-Site checks, CSP and nosniff headers",
   "where": "server.js body() and createServer",
   "worth": "value",
   "why": "Blocks cross-site requests against the local app."
  },
  {
   "what": "BroadcastChannel resync of other tabs after Switch person",
   "where": "public/app.js channel",
   "worth": "value",
   "why": "Prevents a stale tab from acting as the previous person."
  },
  {
   "what": "\"Custom instructions active for <bot>.\" status",
   "where": "public/index.html #instruction-active",
   "worth": "neutral",
   "why": "Signals instructions are active but not which text, so the copy-on-Use behaviour stays partly hidden."
  }
 ],
 "spec_notes": "[tool]/spec.md marks many points Open for the requester (C-14 token precedence, C-19 bot naming, C-21 conversation names, C-35/C-39 library scope and name conflicts, C-37/C-38 edit/delete of an instruction in use, C-62 stale proposals, C-68 away period, C-71 in-flight step, C-75 resume), yet the build decides each silently (env token wins, duplicate bot names allowed, \"Untitled chat\" / 38-char titles, person-wide library with 409 on duplicates, copy at Use, expire stale previews, browser-local away baseline, discard in-flight step, wait for Retry); the README records some of these, not the naming ones. C-1 pins Node.js 22 or newer, which the request does not. C-49 pins exact counts from the starting data. It is silent on damaged data, storage failure, field-name capitals, id prefixes, focus, and logging. No contradiction of the request found.",
 "tests_notes": "Seven scenario tests each cover many behaviours (test 1 alone covers setup, token secrecy, memory, rename, record scoping and person isolation), so one failure names a scenario, not a rule. All HTTP tests are tied to this build's own API (/api/person, /api/actions/<name>, generation/submission/run fields, 409/404 codes) and would not run against another correct build. Test 4 calls private preview/decide with internal shapes (__proto__, Infinity); test 7 constructs Store directly and relies on the file name state.json; test 1 checks the provider-token file mode. Test 6 is timing-dependent (STANDIN_STEP_MS 90 with a 130 ms delay; retry then cancel relying on the internal run counter). No test covers the page (UI focus, narrow layout, Since you were away, naming).",
 "maintainer": "lib/chat.js puts every action in one large switch inside a single store transaction, with reply and task work coordinated through turn status/attempt, task run counters and reservations plus a global \"unavailable\" flag; changing any one path risks double application or a stuck app. public/app.js is a 600-line hand-rolled renderer whose epoch/busy guards, keyed DOM reuse, sessionStorage drafts and localStorage away baseline interact subtly, and none of it is tested."
}
```

