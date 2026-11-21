# Grokbot-local: a harder scenario for comparing Ratchet with ShipLoop (draft for the owner, 2026-11-20)

**Status: a proposal. Nothing here is built or run.** Owner, 2026-11-20: "should we have a 'create a node based
grokbot clone running on localhost' as a scenario to help drive better comparisons?" and "each of the tests should run
in an isolated, clean git repo folder".

## Why

Every case the pilot has run sits at its ceiling: all four whole-loop first builds passed every held-out check, and one
acceptance clause failed naturally in four runs (`docs/ratchet-pilot-journal.md`, section 10). Those cases can price
Ratchet and show that its parts work. They cannot show whether iterating on failed tests beats planning when a first
pass falls short, because none did.

The Grokbot request is the largest the owner has run: a customer-voice brief with about ten feature areas and much left
implied. Its Salesforce form took 6.9 hours and ended blocked
(`docs/experiments/grok-chat-full-run-review-20261114/README.md`); the Salesforce cases were retired on 2026-11-19
(commit 2cd119d12). The brief itself is in history at commit 71fa298e44db73f6afa46217377ba0ea850de916,
`test/shiploop_e2e/scenarios/grok-chat-outcome/BUILDER_PROMPT.md`.

## The request (draft; the customer paragraphs are the original's, with Salesforce and xAI taken out)

> Build and deliver a finished, working chat application that feels like seamless, elegant Grok-style chat, running on
> this computer. I want to open it, ask for help in ordinary language, and get useful answers that make my work easier.
>
> It is a Node.js app with no npm dependencies. `node server.js` serves it on the port in the PORT environment variable
> (default 3000), GET / is the app, and everything it keeps lives under the folder named by the DATA_DIR environment
> variable (default `./data`), so it survives a restart. The assistant's replies come from the stand-in in `provider/`
> (read `provider/README.md`): use it as it is for every reply and do not change it. The records the assistant may work
> with are the synthetic ones in `records/` (read `records/README.md`), which also says which person may read which.
>
> I want the conversation to be the center of the experience: polished typography, comfortable reading, clear
> composition, and replies that explain what matters without overwhelming me. When I ask a follow-up, the bot should
> understand the conversation, ask a useful clarifying question when needed, and help me reach an answer or finish a
> task.
>
> I want to name my bots and keep multiple saved conversations, returning to the right bot and discussion without
> losing my place. I should be able to save reusable instructions and tasks, use them again, and change them when my
> needs change. I want to inspect what a bot remembers about me, correct mistakes, and ask it to forget something. My
> information should stay separate from another user's, and each bot's memory should stay separate from my other bots.
>
> Within the synthetic records, I want to ask real questions, receive accurate answers grounded in records I am allowed
> to read, and follow up naturally. When I ask to create or update something, I want to see the exact proposed changes
> before deciding. Nothing should be written until I explicitly confirm that proposal. Rejecting or cancelling it
> should leave the records alone. Repeating an action or reloading at an awkward moment should not accidentally apply
> it twice, and I should understand what actually happened.
>
> For longer tasks, I want useful work to continue while the app is closed. When I return, I want an honest account of
> what finished, what is still happening, and anything that needs my attention. I want to steer ongoing work with a
> follow-up or cancel it, with a clear explanation of what can still be stopped and what has already happened. If
> something fails or is interrupted, help me recover without guessing or losing the conversation.
>
> Help me get started through guided, recoverable setup that explains what I need without exposing secrets. Make
> everyday use comfortable on a desktop, in a narrow window, and with the keyboard. Deliver the complete working
> experience so I can use it confidently.
>
> *(A last section, still to write, names what a person with a screen reader, and a check, can find: how someone picks
> who they are, and the accessible names of the main regions and controls. The Roundtable case's requests do the same.)*

## What the starting folder supplies (to build)

- **`provider/`: a stand-in for the model.** A small module with documented, fixed rules: the same input always gives
  the same reply, offline. Its replies reflect what the app handed it (the bot's instructions, what it remembers, the
  conversation so far, the records this person may read), so a check can tell whether the app assembled the right
  things. It can ask a clarifying question, propose a change, start a long task, and, on request in the message text,
  answer slowly or fail once.
- **`records/`: synthetic records and who may read them.** A few dozen records and three people with different access.
- Nothing else: the repository is otherwise empty, and each run starts in its own new Git repository in its own folder.

## The yardstick (to build): held-out checks no session sees

A browser-driven script in the style of `test/shiploop_e2e/checks/roundtable_accept.cjs` (Playwright, finding things
by role and accessible name), with the server stopped and started by the script where a check needs it. About 45
checks over the areas of the request:

| Area | Examples of what is checked |
|---|---|
| Conversation | a reply appears; a failed reply can be retried without a second copy of the message; a follow-up reaches the stand-in with the earlier turns; a clarifying question is answered by the next message |
| Bots and conversations | two named bots keep separate conversations; after a reload and after a restart the same bot and conversation are open |
| Saved instructions and tasks | saved, used again, edited; the edit is what the next use sends |
| Memory | what a bot remembers can be read, corrected and forgotten; one bot's memory never reaches another bot or another person |
| Records | an answer uses a record this person may read; a record they may not read never appears in an answer |
| Changes | the exact change is shown first; nothing is written before confirming; rejecting writes nothing; confirming twice or reloading mid-way applies it once; the outcome is stated |
| Long tasks | work goes on with the page closed; on return the account of finished, running and needs-attention items is true; cancel stops what can be stopped and says what already happened; a failure can be recovered; a restart does not lose or repeat work |
| Setup and secrets | first run is guided and can be resumed; the provider's token appears in no page and no response |
| Everyday use | no sideways scrolling at 320, 390 and 1440 pixels wide; the main flows work from the keyboard |

Calibration: there is no hand-written reference. The checks are first run on the first two independent builds (one
from each loop); every failing check is read by hand and fixed where the check is wrong. That is weaker than the
calibrated ticket cases and is said so with any result.

## The comparison

Today's ShipLoop and Ratchet on this one request, same model and effort (Sol 6.2 high), each in its own clean Git
repository, graded by the same held-out checks at the first build, at each later stage, and at the end. Read: held-out
checks passed, minutes and tokens, and for Ratchet how many checks each cycle recovered.

## What it costs

- Building the stand-in, the records, the last section of the request and the yardstick: about a working day.
- Each run: an estimate of 2 to 5 hours and 3 to 6 times the tokens of a ticket run. Unattended runs follow the
  owner's quota rules (a dedicated worktree, turn and budget caps).

## For the owner to decide

1. **Go or no-go** on building it.
2. **One large request or a ladder.** One request is the purest test of "one shot, then iterate". A ladder of three
   linked requests (chat, bots and memory; then records and changes; then long tasks and setup) also tests follow-on
   work on an existing product and keeps each run shorter. Recommended: the one large request first.
3. **The request's wording**, above, since it defines the product.
