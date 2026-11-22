# One look at a delivered product

This folder ({work}) holds a product that was built and delivered for the request below. Every check passes. Its
builders' specification and working notes are in `docs/shiploop/`.

This look asks one question: now that the product runs, is there anything a user or an operator needs that it does
not do, or that it does without anyone having been told?

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

## What to weigh
- The product itself. Start it and use it as its users and operators would: the request's own examples, values at
  and just past each limit, wrong and odd input, the features next to what was asked, a restart, what its documents
  promise. Use it; do not only read it.
  Where it has a page, drive the page for real with Playwright from a Node script:
  `const { chromium } = require('/Users/dadleet/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright')` and
  `chromium.launch({ executablePath: '/Users/dadleet/Library/Caches/ms-playwright/chromium_headless_shell-1243/chrome-headless-shell-mac-arm64/chrome-headless-shell' })` (headless). Close every browser you open.
- The request, read once more for what it implies and the specification does not state.
- The specification and notes in `docs/shiploop/`, for a choice the builders made that the request did not settle.

## What to write
Write `docs/shiploop/look.md` and change nothing else: not the product, not a test, not another document.

**Shortfalls.** Each thing the product does not do that a user or an operator would care about and the request's
intent covers. For each: what is needed; the exact steps that show the product falling short (the commands or page
actions, what came back, what should have); and how much it matters: `high` (loses data, misleads a user or breaks
what worked), `medium` or `low`. A shortfall is not a new feature, a matter of taste or hardening nobody asked for.
If another correct product could behave differently and nobody would miss it, leave it out. Try what you suspect
before you write it: a shortfall you did not see happen does not belong here.

**Choices the customer was not told.** Each place where the request left something open, the product does
something reasonable there, and neither the request nor the documents delivered with the product (not counting
`docs/shiploop/`) say what it does. One line each: the open point, and what the product does.

Write the single line "Nothing found." under a heading whose list is empty.

## Conduct
Work only inside {work}; temporary files go in {tmp}. Use a free port you pick yourself and data files under
{tmp}. Stop every process you start, by its process id, before you finish; never stop processes by name.
