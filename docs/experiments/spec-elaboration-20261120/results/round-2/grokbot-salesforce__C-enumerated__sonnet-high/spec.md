# Specification: Grok bot in a Salesforce development org

## Use cases

### U-1: A Salesforce user chats with Grok for the first time, to get an answer
Flow: The user opens the App Launcher, opens the "Grok Bot" app, and lands on its "Grok Bot" tab. They see an empty conversation panel, an empty conversation list, a text box and a Send control. They type "What is a roll-up summary field?" and press Send. Their message appears at once with a waiting indicator; when Grok's reply arrives it replaces the indicator, labeled as Grok's. The conversation now appears in the list, titled from their first message.
Source: request (a Grok bot in a Salesforce org)

### U-2: A Salesforce user carries on a multi-turn conversation, to get answers that build on earlier ones
Flow: In the conversation from U-1 the user types "Give me an example" and sends. Grok's reply refers to the roll-up summary field from the earlier turn. The transcript shows all four messages in the order sent.
Source: implied: a bot that is a chat; a chat that forgets the last turn is not usable

### U-3: A user returns to, starts and deletes conversations, to keep their own history tidy
Flow: The user sees their conversations in the list, newest activity first. They select an old one and see its full transcript, send another message in it, press "New chat" to start a fresh one, and delete one they no longer want after confirming a prompt.
Source: implied: conversations are kept (U-1), so they can be found again and removed

### U-4: A user's message fails, so they understand what happened and try again
Flow: The user sends a message while Grok's provider is unreachable or rejects the call. Their message stays in the transcript marked as failed, with a plain-language reason and a Retry control. They press Retry later and get a reply with no duplicate of their message.
Source: implied: Grok is an outside service that can fail (request: "a Grok bot")

### U-5: A user reaches a usage limit, to be told rather than silently ignored
Flow: The user sends more messages than their allowance in a rolling hour (or the org passes its daily allowance). The next send is refused with a message saying which limit applies and when it frees; the text they typed is still in the box.
Source: implied: an outside paid service needs a cost bound; no one else can bound it

### U-6: An administrator installs the bot into a Salesforce development org, to have a working Grok bot there
Flow: The administrator runs the project's documented deploy command against a Developer Edition or scratch org, with no prior setup. The deploy finishes with no errors. They open the README and follow its numbered setup steps. The bot is installed but switched off and has no key.
Source: request ("Create a Grok bot in a Salesforce development org")

### U-7: An administrator connects Grok and switches the bot on, and knows that it worked
Flow: The administrator gets an API key from their xAI account, enters it in Salesforce Setup, assigns themselves the Grok Bot Admin permission set, opens the "Grok Bot Admin" tab, presses "Test connection", sees a success result showing the model and response time, then turns Enabled on. A user then completes U-1.
Source: implied: U-1 cannot work until a key exists; "turn it on for the first time and know that it worked"

### U-8: An administrator gives a user access, and takes it away from one user, to control who may chat
Flow: The administrator assigns Grok Bot User to a user; that user sees the app. The administrator later unassigns it from one user; that user no longer sees the app or can send, and the others are unaffected.
Source: implied: use of a paid outside service must be controllable per person

### U-9: An administrator tunes the bot and undoes a bad setting, to change how it behaves without a redeploy
Flow: On the "Grok Bot Admin" tab the administrator edits the model, system prompt, temperature, maximum output, history window, timeout, limits and retention, saves, and the next message a user sends follows the new values. They press "Restore defaults" after a bad edit.
Source: implied: configuration; undo something done by mistake

### U-10: An administrator switches the bot off for everyone, to stop it at once
Flow: The administrator turns Enabled off. Users opening the bot see that it is switched off and cannot send; their past conversations remain readable. They turn it on again later.
Source: implied: turn it off for everyone

### U-11: An administrator watches the bot and finds the one failure among many successes, to fix a problem or answer a complaint
Flow: The administrator opens the "Grok Bot Admin" tab and sees counts for the last 24 hours (attempts, successes, failures by category, tokens, average time). They open the "Failed — last 24 hours" list of the request log, find a failed request, see its category, HTTP status and xAI's error text, and, if a user complains, open that user's conversation.
Source: implied: watch while it runs

### U-12: An administrator keeps stored data within bounds, to stay inside a small development org's storage
Flow: The administrator sets retention to 30 days and presses "Schedule daily cleanup". Each day conversations with no activity for more than 30 days, and old log records, are deleted. They can see when cleanup last ran and how much it deleted, and they can run it now.
Source: implied: data this creates must have an end; a Developer Edition org has about 5 MB of data storage

### U-13: An administrator changes the key, redeploys, and removes the bot, to recover or retire it
Flow: The administrator replaces the key in Setup after the old one is revoked and the bot works on the next message. They redeploy the project over the installed bot and nothing they configured is lost. Later they run the removal command and no Grok component remains.
Source: implied: rotate, go back, undo

### U-14: A developer prepares the bot to move beyond a development org, to avoid a surprise at deployment
Flow: The developer runs the Apex tests, reads the README's "Before production" section, and sees what must be true before the same project can be deployed to production.
Source: implied: "development org" implies that something comes after it

## Clauses

### C-1: The bot is reachable as a Lightning app
Observable: A user who holds the Grok Bot User permission set sees an app labeled "Grok Bot" in the Lightning Experience App Launcher; opening it shows a tab labeled "Grok Bot" containing the chat panel and the conversation list. A user without that permission set sees neither the app nor the tab.
Source: request (a bot in the org must be somewhere a user can open it)

### C-2: The chat panel is also available to place on any Lightning page
Observable: In Lightning App Builder, a component labeled "Grok Bot" can be dragged onto any Lightning app, home or record page; a page with it behaves exactly as the tab does.
Source: choice: a reusable component is the loosest way to let admins put the bot where users already work, and costs nothing beyond the tab

### C-3: The first-time empty state tells the user there is nothing yet
Observable: A user with no conversations who opens the tab sees an empty message box, a conversation list that states there are no conversations yet, and no error.
Source: implied: U-1 (the first time)

### C-4: A message of 1 to 10,000 characters is accepted
Observable: After removing leading and trailing whitespace, a message of 1 to 10,000 characters can be sent; a message of exactly 10,000 characters is sent and a message of exactly 1 character is sent.
Source: choice: 10,000 characters (about 2,500 tokens) is far more than a chat turn needs and, with the history window, keeps one call inside every Grok model's context

### C-5: An empty or whitespace-only message cannot be sent
Observable: With nothing in the box, or only spaces, tabs or line breaks, the Send control is disabled and pressing Enter sends nothing and creates nothing.
Source: implied: U-1 (empty case)

### C-6: A message over 10,000 characters is not sent, truncated, or cleared
Observable: Once the trimmed text exceeds 10,000 characters the user sees that it is over the limit and by how many characters, Send is disabled, and the text in the box is unchanged.
Source: implied: C-4 (the largest case)

### C-7: The user's message appears immediately with a waiting indicator
Observable: Within 1 second of pressing Send, the sent message is in the transcript labeled as the user's own ("You") with the time it was sent, a waiting indicator sits beneath it, and the text box is empty.
Source: implied: U-1 (a reply can take tens of seconds, the user must see that the message was taken)

### C-8: Grok's reply appears labeled as Grok's, whole
Observable: When the reply arrives, the waiting indicator is replaced by the reply labeled "Grok", showing the complete text received, with the time it was received.
Source: request (a Grok bot)

### C-9: Message text is displayed as plain text and never interpreted as markup
Observable: A reply (or user message) containing `<script>alert(1)</script>` or `<b>x</b>` is displayed with those characters visible and literal; no script runs and nothing is bold.
Source: implied: model output is untrusted input; the request does not say how replies render

### C-10: Enter sends the message
Observable: With text in the box, pressing Enter sends it.
Source: choice: the common chat convention; the loosest way to make multi-line input and fast sending both possible

### C-11: One message at a time is in flight per conversation
Observable: From the moment a message is sent until it has a reply or is marked failed, Send is disabled for that conversation. Other conversations stay usable meanwhile, including sending in them.
Source: implied: U-2 (a reply must follow its message; two overlapping turns would give Grok an incoherent history)

### C-12: A conversation is created on the first send, not before
Observable: Opening the tab or pressing "New chat" creates no stored record; the conversation appears in the list only once its first message is sent. Opening and leaving the tab 10 times without sending leaves the count of the user's conversations unchanged.
Source: choice: empty conversations are clutter and, in a 5 MB development org, cost storage

### C-13: A conversation is titled from its first message
Observable: The title is the first message with each run of whitespace collapsed to one space and cut to its first 80 characters. A first message of "  Hello\n\nthere  " gives the title "Hello there"; a 200-character first message gives a title of exactly 80 characters.
Source: choice: any short, derived title serves; this one needs no extra call and no extra cost

### C-14: Each call to Grok carries the system prompt, then the recent exchange history, then the new message
Observable: In the request sent to Grok, the messages are in this order: a system message holding the configured system prompt (omitted when the prompt is blank); then up to the configured number of most recent completed messages of that conversation (a completed message is a user message that has a reply, or that reply, including a reply cut off at the output limit), oldest first, each marked as the user's or the assistant's; then the new user message as the last item.
Source: implied: U-2 (a multi-turn conversation)

### C-15: A message that failed, is pending, or was refused is never sent to Grok as history
Observable: In a conversation holding a failed user message followed by a later successful exchange, the request for the next message contains the successful exchange and does not contain the failed message. A message that was refused before sending (C-38) is not stored and so cannot appear.
Source: implied: U-4 (a message with no reply would leave two user turns in a row and charge for text Grok never answered)

### C-16: A call to Grok carries nothing about the user or the org's records
Observable: The request body and headers sent to Grok contain only the system prompt, the conversation texts (C-14), and the model, temperature and maximum-output settings, plus the credential. They contain no user name, e-mail address, username, user Id, org Id, org name, and no field value of any Salesforce record.
Source: choice: privacy first, since the request asks for a bot and not for access to the org's data; sending nothing extra is the loosest rule that protects users

### C-17: The call goes to one fixed destination
Observable: Every call is an HTTPS POST to `https://api.x.ai/v1/chat/completions` (xAI's OpenAI-compatible chat endpoint; confirm path against xAI's current documentation when building). No other host or path is ever contacted by the bot.
Source: request (a Grok bot)

### C-18: The text shown is the text of the first choice Grok returned
Observable: The reply shown and stored equals, character for character, the message content of the first choice in Grok's response; the bot adds, drops and rewrites nothing in it.
Source: implied: the user asked for Grok, not for Grok edited

### C-19: A reply cut off by the output limit is shown, with a notice that it was cut off
Observable: When Grok's response says it stopped because it reached the maximum output length, the full received text is shown with a visible note that the answer was cut short; the message is not marked as failed.
Source: implied: C-18 and the max-output setting (a reply can hit it)

### C-20: Messages show their sent or received time in the viewer's own time zone
Observable: A message sent at 14:05 UTC shows 10:05 to a user whose Salesforce time zone is US Eastern in summer (UTC-4), and 14:05 to a user on UTC.
Source: choice: the user's Salesforce time zone is the one they already set

### C-21: The conversation list shows only the user's own conversations, newest activity first
Observable: Each entry shows the title and the date and time of the latest message in it. The entry whose latest message is most recent is first. Conversations of other users never appear.
Source: implied: U-3

### C-22: Selecting a conversation shows its complete transcript
Observable: The panel shows every stored message of the conversation, including those older than the history window, oldest first, user messages and replies interleaved as sent, failed ones included and marked.
Source: implied: U-3

### C-23: A message sent in an old conversation continues it
Observable: After sending in an old conversation, Grok's request contains that conversation's earlier exchanges per C-14 and the new reply is stored in the same conversation.
Source: implied: U-3

### C-24: "New chat" starts an empty panel and removes nothing
Observable: Pressing "New chat" shows an empty transcript and empty box; the list is unchanged; the previous conversation is still in the list unmodified.
Source: implied: U-3

### C-25: A user can delete their own conversation after confirming
Observable: Delete asks for confirmation; on confirming, the conversation and all of its messages disappear from the list and the panel and cannot be opened again by the user. On cancelling, nothing changes.
Source: implied: U-3

### C-26: A conversation with a message in flight cannot be deleted
Observable: While a message in the conversation is waiting for its reply, Delete is refused with a message that a reply is pending, and the conversation is untouched.
Source: choice: deleting under an in-flight call would orphan the reply; waiting at most the timeout is cheap

### C-27: A user may hold at most 100 conversations
Observable: When the user already has 100 conversations, sending the first message of a new one is refused with a message to delete one first; the text stays in the box, and the 100 are unchanged. Sending in an existing conversation still works.
Source: choice: bounds storage in a 5 MB development org; 100 is far above normal use of a chat history

### C-28: A conversation holds at most 100 user messages
Observable: A conversation with 100 stored user messages (failed ones counted, replies not counted, so at most 200 stored messages) refuses the next new send with a message to start a new chat; the text stays in the box. A conversation with 99 accepts one more. Retry of an already stored failed message is not a new message and is still accepted.
Source: choice: bounds storage and keeps the transcript usable; counting user messages guarantees a reply always fits

### C-29: Every failure ends in exactly one of these named categories
Observable: A send that passed validation and failed ends in exactly one of: (1) Not configured — no usable credential, or the user is not authorized to use it; (2) Key rejected — HTTP 401 from xAI; (3) Access denied — HTTP 403 from xAI (permission or account credits; which of these xAI signals by 403 is unconfirmed); (4) Request rejected — any HTTP status that is not 2xx and not 401, 403, 408, 429 or 5xx, including 400 (bad parameter, unknown model, conversation too long for the model's context) and 404; (5) Rate limited — HTTP 429; (6) Provider error — HTTP 5xx; (7) Timed out — no complete response within the configured timeout, or HTTP 408; (8) Network failure — no HTTP response because of DNS, connection or TLS failure; (9) Unusable reply — HTTP 2xx whose body is not the expected shape or whose reply text is empty; (10) Salesforce limit — the platform refused or stopped the call for a governor or concurrency limit, or any other unexpected server-side error; (11) Save failure — a reply was obtained but could not be stored (storage full, or its conversation deleted meanwhile). No failure is shown as an uncategorized error.
Source: implied: U-4 (a dependency failing, every way it can), and the operator needs the same list (see the log clause)

### C-30: The user is told the failure category in plain language
Observable: The failure shown for a message names its category in words (not the number); for category 11 it states that the reply is shown but was not saved.
Source: implied: U-4

### C-31: A failure message shows no secret and no raw provider text
Observable: The text shown to the user for any failure contains no API key, no authorization header, no raw response body from xAI, no stack trace and no Apex exception text.
Source: implied: the user is not the operator; a leaked detail could be a secret

### C-32: A failed message stays in the transcript, marked failed, with Retry
Observable: After a failure in categories 1 to 10, the user's message remains in the transcript with a failed mark, the category message (C-30) and a Retry control. It is still there after reloading the page and after reopening the conversation.
Source: implied: U-4 (data the user typed is never lost on the way); forced by the platform rule that an HTTP callout cannot follow an uncommitted database write in the same transaction, so the message is stored before the call is made

### C-33: Retry re-sends the same message without duplicating it
Observable: Pressing Retry on a failed message sends that same text again using the current settings and the history of completed messages before it; the transcript still shows that message once; on success the failed mark is cleared and the reply appears beneath it; on a new failure the new category replaces the old one.
Source: implied: U-4

### C-34: The bot never retries a call by itself
Observable: One send, or one Retry, produces at most one request to Grok, even after a timeout, 429 or 5xx.
Source: choice: an automatic retry would double the cost on a slow call and, with the platform's 120-second cap on callout time per transaction, could not complete anyway

### C-35: Each user may send at most a set number of messages per rolling hour
Observable: When a user has made the configured number of counted attempts (C-37) in the last 60 minutes, the next send is refused; it is accepted again once the oldest counted attempt is more than 60 minutes old.
Source: implied: U-5; the number is an operator setting (see the setting clause)

### C-36: The org as a whole may have at most a set number of attempts per rolling 24 hours
Observable: When all users together have made the configured number of counted attempts in the last 24 hours, every user's next send is refused until the oldest counted attempt is more than 24 hours old.
Source: implied: U-5; protects against the bill of an outside service

### C-37: Only attempts that reached the call are counted toward the limits
Observable: Counted: every send or Retry that passed all refusal checks, whatever its outcome (success or any category in C-29). Not counted: sends refused before the call (C-38 members), and the operator's Test connection.
Source: choice: cost follows calls made, so refusals are free; counting failures prevents a tight retry loop from escaping the limit

### C-38: A refused send is not stored, not sent and not counted, and the user is told why
Observable: A send is refused, and creates no message, calls nothing and counts nothing, when any of these holds: the bot is switched off; the user lacks permission; the user's hourly limit is reached; the org's daily limit is reached; the conversation already has 100 user messages (for a new message, not for a Retry); the conversation already has a message in flight; the user already has 100 conversations and this would be a new one; the message is empty or over 10,000 characters after trimming; the conversation does not exist or belongs to someone else; the message cannot be stored (C-140). The user sees which reason applied (the typed text stays, C-147). The order of this list is the order of precedence (C-124).
Source: implied: U-5; every one of these is enforced where the call is made, not only in the page

### C-39: A refusal for a limit says when it frees
Observable: The message for the hourly limit states the clock time (in the user's time zone) at which the oldest counted attempt leaves the 60-minute window; for the daily limit it states the same for the 24-hour window.
Source: implied: U-5

### C-40: The panel always tells the user that messages go to xAI
Observable: Whenever the panel is shown, in every state (empty, populated, failed, disabled), it displays a notice stating that what they type is sent to xAI's Grok service and that Grok's replies can be wrong. The notice cannot be dismissed.
Source: implied: users have a right to know a third party receives what they type; the request is silent

### C-41: The panel always tells the user that conversations are stored and visible to administrators
Observable: Whenever the panel is shown it displays a notice stating that conversations are stored in Salesforce and can be read by administrators.
Source: implied: see C-40; and the administrator-visibility choice in C-92

### C-42: The bot is a custom chat built for Grok, not an Einstein Bot or Agentforce agent
Observable: Nothing the bot does depends on Einstein Bots, Agentforce, Messaging or Omni-Channel being enabled in the org; the org needs none of them turned on for U-1 to U-5 to work. The bot does not appear in Agentforce or Einstein Bot setup.
Source: choice: the request names Grok, an xAI model that those Salesforce products do not offer as a built-in choice (unconfirmed for the current release); a direct integration is the only reading that delivers "a Grok bot"

### C-43: Messages are text only
Observable: The box accepts typed or pasted text only. Pasting or dropping an image or file adds nothing to the message and sends nothing to Grok; there is no attach, dictate or speak control.
Source: choice: the request names a chat bot; attachments would send files to a third party and need their own rules

### C-44: Grok's own web, X and code-execution tools are not used
Observable: The request to Grok contains no tool, search or live-data options; replies come from the model alone. The bot never fetches a URL on a user's behalf.
Source: choice: tools would let a third party fetch content and add per-use cost the operator did not set a limit for

### C-45: The user interface is in English only
Observable: All labels, notices and messages the bot shows are in English whatever the user's Salesforce language. Grok replies in whatever language the user wrote in; the bot does not interfere.
Source: choice: the request names no other language

### C-46: The supported surface is Lightning Experience in a desktop browser
Observable: In Lightning Experience in a current desktop browser that Salesforce supports, every clause holds. The bot is not offered in Salesforce Classic, the Salesforce mobile app or Experience Cloud sites; whether it renders there is not specified.
Source: choice: the request names a development org and no channel; this is the narrowest surface that serves a developer

### C-47: The panel can be used by keyboard and screen reader
Observable: The box, Send, New chat, each conversation in the list, Delete and Retry are each reachable and operable by keyboard alone, in a sensible order; each has an accessible name; a new reply or a new failure is announced by a screen reader without the user moving focus; text and controls meet WCAG 2.1 level AA contrast.
Source: implied: a user interface in an org a company runs; accessibility is the platform's own standard (SLDS)

### C-48: A reply is saved even if the user leaves while it is pending
Observable: A user sends a message, then closes the tab or reloads before the reply arrives. When they reopen the conversation after the call would have finished, the message has its reply (or its failure mark with a Retry control), with no resend needed.
Source: implied: U-1 (a reply can take tens of seconds; browsers get closed); the server-side call completes regardless of the browser

### C-49: A message still in flight is shown as awaiting a reply
Observable: Opening a conversation whose last message has no reply yet and has not timed out shows the waiting indicator beneath that message (see C-148 for when it resolves).
Source: implied: C-7, C-48

### C-50: A message with no outcome after the timeout plus 30 seconds becomes a Timed out failure
Observable: A message that has been in flight for longer than the configured timeout plus 30 seconds (so at most 150 seconds; with the default of 60, 90 seconds) is shown as failed with category Timed out and a Retry control, even if the server never recorded an outcome. The time is counted from the send, or the Retry, that started the attempt.
Source: implied: C-29 and the platform rule that some limit errors cannot be caught, which would leave a message "waiting" forever; a piece of state must have an end

### C-51: A message ends in exactly one outcome
Observable: Once a message is stored as replied or as failed, a later arrival (for example a very late reply after the Timed out mark of C-50) does not change it. No message ever has two replies.
Source: implied: C-50 and C-33 (things arriving late or twice)

### C-52: Double activation of Send sends once
Observable: Double-clicking Send, or pressing Send and Enter in quick succession, produces one stored user message, one request to Grok and one count against the limits. Double-clicking Retry produces one request to Grok and one count.
Source: implied: C-11 (the same intent from the same user, twice)

### C-53: Opening a conversation that no longer exists is handled
Observable: A user who selects a conversation deleted meanwhile (by themselves in another tab, by an administrator, or by retention cleanup) sees a message that it no longer exists, and the list refreshes to drop it; nothing else is affected.
Source: implied: C-25 and the retention clause (things disappearing under a view of them)

### C-54: Each stored message records what the operator and the page need
Observable: Every stored message holds: the conversation it belongs to; who sent it (the user or Grok); its text; the time it was stored; its state (in flight, replied, failed); for a failed one, its failure category; for a Grok reply, the model it was generated by and whether it was cut off by the output limit. An administrator can see all of these on the record.
Source: implied: C-8, C-19, C-29, C-32 each need state to persist across reloads

### C-55: A conversation is owned by the user who started it
Observable: The conversation's owner is the user who sent its first message and cannot be changed by that user; a conversation record shows its owner, title, creation time and time of latest message.
Source: implied: C-21

### C-56: Only the owner and administrators can read or delete a conversation
Observable: When user B tries to read, list, open, send in, retry in or delete user A's conversation or its messages by any route (the bot's own screen, record URL, list view, report, or API), the answer is that it is not found or access is denied; nothing of A's is returned or altered.
Source: implied: private chat content; the request is silent so it is private by default

### C-57: The Grok Bot User permission set contains exactly what U-1 to U-5 need and no more
Observable: A user who holds only a profile with no extra access plus the Grok Bot User permission set can do everything in U-1 to U-5 in the org: the app, tab, component, the server-side logic, the credential, and create, read and delete of their own conversations and messages. The same user cannot read the request log or the settings (the bot tells them only whether it is switched on or off), cannot open the admin tab, and cannot see anyone else's conversations.
Source: implied: C-1, C-56; the platform rule that a callout also needs the user to be granted the credential's principal

### C-58: A conversation's data outlives the user's active status
Observable: When a user is deactivated, their conversations and messages stay stored (and readable by administrators) until retention deletes them; when reactivated, the user sees them again.
Source: implied: nothing in the request says deactivation deletes data; Salesforce users are deactivated, not deleted

### C-59: History never begins with a reply
Observable: When the configured history window of N messages would start with a Grok reply, that reply is dropped, so that the first history item is a user message. With N = 3 and completed messages U1 A1 U2 A2 the request contains U2 A2 then the new message (not A1 U2 A2).
Source: implied: C-14 (a window cut between a question and its answer would give an answer with no question)

### C-60: The deploy adds exactly these components, each with "Grok" in its name
Observable: After the deploy, the org holds: a Lightning app "Grok Bot"; a tab "Grok Bot" (the chat); a tab "Grok Bot Admin" (settings, test, summary, cleanup); a tab for the request log; a tab for conversations (for administrators); the chat component (C-2); the admin component; three custom objects (conversation, message, request log); the store for settings (C-73); the credential used to reach xAI; two permission sets "Grok Bot User" and "Grok Bot Admin"; the server-side logic; the automated tests; and the cleanup job's logic. Nothing else is added. Each carries "Grok" in its label.
Source: request ("create ... in a Salesforce development org"); the list is a dimension of the deploy, so it is complete here

### C-61: One documented command deploys the project to a Developer Edition or scratch org
Observable: In a freshly created Developer Edition org, and in a freshly created scratch org, the command given in the README completes with zero component errors and zero test failures, with no other component required to exist first. Deploying to a sandbox is not tested or promised.
Source: choice: a "development org" is a Developer Edition or scratch org; a single command is the least a developer can be asked to remember

### C-62: A freshly deployed bot is off
Observable: Immediately after a first deploy, the setting "Enabled" is off. A user who holds the Grok Bot User permission set and opens the bot sees that it is switched off (C-88).
Source: choice: a deploy must never send a user's text to a third party before the administrator has decided to; "turn it on for the first time and know that it worked" needs an off state to start from

### C-63: The README gives the setup steps in this order
Observable: The README states, numbered and in this order: (1) deploy; (2) get an API key from the xAI console (https://console.x.ai) and enter it in Setup (C-65); (3) assign Grok Bot Admin to the administrator and Grok Bot User to users; (4) open the "Grok Bot Admin" tab and press "Test connection"; (5) turn Enabled on; (6) press "Schedule daily cleanup". Each step names where in Salesforce it is done and what the administrator sees when it has worked.
Source: implied: U-6, U-7, U-12; the only way a person who has not seen the code can set it up

### C-64: The project contains no secret
Observable: Searching the whole project (source, README, scripts, tests, configuration) finds no xAI API key, and the project deploys without one.
Source: implied: C-65, the platform rule that a secret entered in a credential cannot be deployed from source

### C-65: The key is entered in Salesforce Setup
Observable: The administrator enters the xAI API key on the credential's page in Setup (no code, no deploy). Until they do, the org holds no key (so a freshly deployed bot has none).
Source: implied: U-7

### C-66: Replacing the key takes effect on the next message
Observable: After the administrator saves a new key in Setup, the next message any user sends is authenticated with the new key; no deploy, logout or settings change is needed. When the old key was revoked, messages fail with "Key rejected" until the new key is saved, and succeed after.
Source: implied: U-13

### C-67: "Test connection" is a control on the admin tab
Observable: The "Grok Bot Admin" tab has a "Test connection" control which sends one fixed short prompt to Grok using the current model and timeout settings, and no conversation history.
Source: implied: U-7 ("know that it worked")

### C-68: "Test connection" shows a success or a categorized failure within the timeout plus 5 seconds
Observable: On success the tab shows "success", the model name Grok reports, the elapsed milliseconds and the token counts returned. On failure it shows the category from C-29 (members 1 to 10), the HTTP status when there was one, and xAI's error text when there was one. The result appears no later than the configured timeout plus 5 seconds after pressing the control.
Source: implied: U-7

### C-69: "Test connection" works while the bot is off
Observable: With Enabled off, "Test connection" still runs and shows its result.
Source: implied: U-7 (the test must run before the bot is first turned on)

### C-70: The admin tab shows the last test's time and result
Observable: The tab shows when "Test connection" was last pressed and by whom, and its result, until the next test replaces it; this survives page reload and different administrators. With no test yet, it says none has been run.
Source: implied: U-7, U-11

### C-71: The admin tab and its controls are for administrators only
Observable: A user without the Grok Bot Admin permission set cannot see the "Grok Bot Admin" tab, and cannot change a setting, run a test, run or schedule cleanup, or restore defaults by any route, including calling the server-side logic directly.
Source: implied: C-57

### C-72: The Grok Bot Admin permission set includes everything the user set includes
Observable: A user holding only Grok Bot Admin can complete U-1 to U-5, and can also use the admin tab, read and delete every user's conversations and messages, and read the request log. It does not allow editing any user's message text or sending as another user.
Source: choice: an administrator who cannot try the bot cannot know it works; read and delete are the least that "watch it" and "undo a mistake" need

### C-73: The operator controls are exactly these
Observable: The "Grok Bot Admin" tab offers settings: Enabled, Model, System prompt, Temperature, Maximum output tokens, History window, Timeout, Hourly limit per user, Daily limit for the org, Retention days; and actions: Test connection, Restore defaults, Run cleanup now, Schedule daily cleanup, Unschedule daily cleanup. Nothing else changes the bot's behaviour except the key (C-65) and the permission sets (C-90).
Source: implied: U-9; a dimension (the controls), so listed in full

### C-74: Setting "Enabled" is off by default and switches the bot
Observable: Enabled is on or off; default off. Its effect is C-88 and C-89.
Source: choice: C-62

### C-75: Setting "Model" is a text value, default `grok-4`
Observable: Model must be 1 to 100 characters, each a letter, digit, dot, underscore or hyphen; the default is `grok-4`. Its value is the model identifier in every request. Whether `grok-4` is still the best default when the bot is built is unconfirmed; the value is what "Test connection" confirms or rejects.
Source: choice: the request names "Grok" and no version; model names change often, so the operator, not the code, owns the value

### C-76: Setting "System prompt" is free text, 0 to 4,000 characters, with a default
Observable: The default is a non-empty instruction that tells Grok it is a helpful, concise assistant for Salesforce users. A blank value is accepted and causes no system message to be sent (C-14). A value of 4,001 characters is rejected.
Source: choice: the request says what the bot is, not how it should behave; an operator-owned prompt is the loosest way to let the operator decide

### C-77: Setting "Temperature" is a number from 0 to 2 with 2 decimal places, default 0.7
Observable: Values such as 0, 0.7 and 2 are accepted; 2.01, -0.1 and "abc" are rejected. The value is sent as the temperature in every request. The 0 to 2 range follows xAI's documentation and is unconfirmed against the current API.
Source: choice: a general-purpose assistant default

### C-78: Setting "Maximum output tokens" is a whole number from 1 to 8,000, default 2,048
Observable: 1, 2,048 and 8,000 are accepted; 0 and 8,001 are rejected. The value is the cap on the reply length in each request. A reply at the cap shows the C-19 notice.
Source: choice: 8,000 keeps ten full replies plus the maximum history inside a 131,072-token context and keeps the response far below the platform's 6 MB limit on synchronous responses

### C-79: Setting "History window" is a whole number from 0 to 100, default 20
Observable: 0 sends no history (each message stands alone); 100 is the largest. 101 is rejected. The value is N in C-14 and C-59.
Source: choice: 20 messages covers ordinary chat and keeps the cost per call bounded

### C-80: Setting "Timeout" is a whole number of seconds from 5 to 120, default 60
Observable: 5 and 120 are accepted; 4 and 121 are rejected. A call with no complete response after this many seconds ends as "Timed out". The ceiling is 120 because the platform allows no more than 120 seconds of callout time in a transaction.
Source: choice: 60 seconds is long enough for most replies and short enough that a stuck call is noticed

### C-81: Setting "Hourly limit per user" is a whole number from 1 to 1,000, default 30
Observable: 1 and 1,000 are accepted; 0 and 1,001 are rejected. It is the number in C-35.
Source: choice: 30 messages an hour is about one every two minutes, an ordinary chat pace

### C-82: Setting "Daily limit for the org" is a whole number from 1 to 100,000, default 1,000
Observable: 1 and 100,000 are accepted; 0 and 100,001 are rejected. It is the number in C-36.
Source: choice: bounds the bill of a development org

### C-83: Setting "Retention days" is a whole number from 1 to 365, default 30
Observable: 1 and 365 are accepted; 0 and 366 are rejected. It is the age in C-104 and C-105.
Source: choice: 30 days keeps a small development org's 5 MB of storage from filling

### C-84: A save with any invalid setting saves nothing
Observable: When one or more values are outside their range, the tab shows which setting and its allowed range, and every setting keeps the value it had before the save, including the valid ones that were edited in the same save.
Source: implied: U-9 (a half-applied configuration is worse than none)

### C-85: A saved setting applies from the next message sent
Observable: The next message sent after a save, by any user, uses the new values (visible in the request and in the limits). A message already in flight uses the values it began with. No logout, redeploy or reload is needed.
Source: implied: U-9 ("see the configuration take effect")

### C-86: "Restore defaults" resets every setting except Enabled, after confirmation
Observable: After confirming, Model, System prompt, Temperature, Maximum output tokens, History window, Timeout, Hourly limit, Daily limit and Retention days take the defaults in C-75 to C-83; Enabled keeps whatever it was. Cancelling changes nothing.
Source: choice: resetting to defaults must not silently turn the bot on, and a bad edit is not a reason to turn it off

### C-87: The admin tab shows who last changed the settings and when
Observable: After any save or Restore defaults the tab shows the administrator's name and the date and time; it survives reload.
Source: implied: U-9, U-11 (find what changed)

### C-88: When Enabled is off, users cannot send
Observable: A user opening the bot sees a notice that the administrator has switched it off; Send is disabled; existing conversations can still be listed, opened and deleted. A send made anyway (for example from a page loaded before the switch-off) is refused (C-38) and nothing is sent to Grok.
Source: implied: U-10

### C-89: Switching Enabled off does not cancel messages already in flight
Observable: A message sent before the switch-off still receives its reply or failure and is stored.
Source: implied: C-48 and C-51; the call cannot be recalled

### C-90: Removing Grok Bot User from a user takes the bot away from that user only
Observable: After the unassignment, that user no longer sees the app, tab or component, and any send, retry, open, list or delete they attempt is refused by the server; other users are unaffected; their stored conversations remain.
Source: implied: U-8

### C-91: Re-assigning Grok Bot User restores a user's access to their own history
Observable: After re-assigning, the user sees the conversations they had before.
Source: implied: C-90 and C-58

### C-92: An administrator can open any user's conversation
Observable: A holder of Grok Bot Admin can open any conversation and its messages from the conversations tab, list views, reports and record pages, with all fields in C-54.
Source: choice: operators must be able to answer a complaint or investigate abuse; the notice in C-41 tells users

### C-93: An administrator can delete any user's conversation
Observable: A holder of Grok Bot Admin can delete any conversation with all its messages; afterwards the owner no longer sees it (C-53).
Source: choice: sensitive text pasted by a user must be removable by someone

### C-94: The request log has one record for each counted attempt, each test and each logged refusal
Observable: Each counted attempt (C-37) yields exactly one log record, written whether or not the user later sees the reply; each Test connection yields one; each send refused because the bot is off, or the hourly limit, or the daily limit yields one. Other refusals (C-38) do not.
Source: implied: U-11 ("watch it while it runs")

### C-95: Each log record has one of these outcomes
Observable: Success; Success (cut off at the output limit); the eleven failure categories of C-29; Refused: bot off; Refused: hourly limit; Refused: daily limit.
Source: implied: U-11 (one list, the same words, for users, operators and the summary)

### C-96: Each log record holds these fields
Observable: Time; user; conversation (blank once the conversation is deleted); message (likewise); outcome; HTTP status (when a response was received); duration in milliseconds; model; prompt tokens, completion tokens and total tokens as returned by xAI (when returned); a flag marking a Test connection; error detail of at most 1,000 characters (xAI's error text when given, otherwise a short description).
Source: implied: U-11

### C-97: The log never holds a key or the text of any message
Observable: No field of any log record contains the API key, a user's message text or Grok's reply text, as written by the bot. (xAI's own error text, passed through in error detail, is not altered or inspected.)
Source: implied: C-65; the log is read by administrators more widely than the conversation it came from

### C-98: Only holders of Grok Bot Admin can read the log
Observable: A user with only Grok Bot User cannot see the log tab, list views, reports or records of it, nor retrieve them through the API.
Source: implied: C-57

### C-99: The log has two ready list views
Observable: On the log tab, a list view named "Failed — last 24 hours" shows requests of the last 24 hours with any of the eleven failure outcomes, newest first, tests included; a list view named "All requests" shows every record newest first.
Source: implied: U-11 ("find the one thing that went wrong among the many that went right")

### C-100: The admin tab shows a 24-hour summary
Observable: The tab shows, for the last 24 hours rolling: number of counted attempts; number of successes (including cut off); number of failures for each of the eleven categories; sum of total tokens; mean duration of successes in milliseconds; number of sends refused for each of the three logged refusals (bot off, hourly limit, daily limit). Test connections are excluded from all of these.
Source: implied: U-11

### C-101: The summary agrees with the log
Observable: For the same 24-hour window, each number in the summary equals the number obtained by counting or summing the log records with the matching outcomes (tests excluded). A tester who counts the log gets the same numbers.
Source: implied: C-100

### C-102: The bot writes no key and no message text to Salesforce debug logs
Observable: With debug logging at its most detailed level (FINEST) for a user while they send a message, the resulting debug log lines contain neither the API key nor the text of the user's message or of Grok's reply.
Source: implied: C-97; debug logs are a second place an administrator reads

### C-103: Deleting a conversation leaves no copy of its text that the bot wrote
Observable: After a conversation is deleted, no record the bot wrote in the org holds its message text (the log never held it, C-97), other than a copy restorable from the Recycle Bin (C-110).
Source: implied: C-25, C-97

### C-104: Conversations with no activity for more than the retention period are deleted
Observable: When cleanup runs, every conversation whose latest message is more than "Retention days" days old is deleted with all its messages; a conversation whose latest message is within the period is not touched. At 30 days, a conversation last active 31 days ago is deleted and one last active 29 days ago is kept.
Source: implied: U-12 (data must have an end)

### C-105: Log records older than the retention period are deleted
Observable: When cleanup runs, every log record older than "Retention days" days is deleted; younger ones are kept.
Source: implied: U-12

### C-106: Cleanup finishes however much there is to delete
Observable: With 25,000 expired messages and 3,000 expired log records, a cleanup run deletes all of them without error (the platform allows only 10,000 rows of deletion in one transaction, so cleanup works in several).
Source: implied: C-104 and the platform's per-transaction limits

### C-107: "Schedule daily cleanup" schedules cleanup once a day
Observable: After pressing it, cleanup runs every day at 02:00 in the org's time zone.
Source: choice: a scheduled Apex job is not deployable as data and must be started by an administrator, and 02:00 is a conventional quiet hour

### C-108: The admin tab shows the last cleanup run
Observable: The tab shows when cleanup last ran, whether it succeeded or failed, how many conversations, messages and log records it deleted, and, for a failure, a short reason.
Source: implied: U-12 ("know that it worked")

### C-109: "Run cleanup now" runs cleanup immediately
Observable: Pressing it runs the same cleanup as C-104 and C-105, whether or not a schedule exists, and the tab then shows the result as in C-108.
Source: implied: U-12

### C-110: An administrator can restore a deleted conversation from the Recycle Bin
Observable: A conversation deleted by a user or administrator (not by cleanup, C-154) can be restored by an administrator from the Salesforce Recycle Bin within the platform's retention for deleted records (15 days), with its messages; it then reappears in the owner's list.
Source: implied: U-13 (undo something done by mistake); the platform rule for deletes

### C-111: The README states the small storage of a Developer Edition org
Observable: The README states that a Developer Edition org has about 5 MB of data storage (unconfirmed for the current edition), that each stored record counts for about 2 KB regardless of its text length, so a few thousand messages fill it, and that a reply that cannot be stored because the org is full shows as "Save failure" (C-29).
Source: choice: the figures are the platform's and explain C-27, C-28 and C-83

### C-112: A removal command deletes every Grok component
Observable: Running the removal command named in the README removes every component listed in C-60 and their data; afterwards no app, tab, object, permission set, credential, setting or scheduled cleanup job named Grok exists in the org. The README warns that all conversations and logs are deleted with it.
Source: implied: U-13 ("go back to the version before"); for a first release the version before is none

### C-113: Redeploying the project over an installed bot loses nothing the administrator set
Observable: After a redeploy, all ten setting values (C-73) are what they were before it, the key in the credential still works, permission-set assignments are intact, and every conversation, message and log record is still there.
Source: implied: U-13; the platform rule that deploying a settings record overwrites its values, which this must not do

### C-114: The source of everything deployed is in a Salesforce DX project kept in version control
Observable: The repository holds a Salesforce DX project (an `sfdx-project.json` and source for every component in C-60) so that deploying a given commit reproduces that version, and an earlier commit can be redeployed to go back.
Source: choice: "create ... in a development org" must be repeatable in another org; version control is the usual way to go back

### C-115: Of two simultaneous sends in one conversation, exactly one is accepted
Observable: A user with the same conversation open in two tabs presses Send in both within the same second. One message is stored and sent to Grok; the other tab shows the refusal "a message is in flight" and keeps its text in the box. The same holds for a Send against a Retry, and for two Retries.
Source: implied: C-11 across two parts of the system meeting (two tabs)

### C-116: Conversations are independent of one another while in flight
Observable: A user who sends in conversation X and, before X's reply, sends in conversation Y gets two calls to Grok, each carrying only its own conversation's history; each reply is stored in its own conversation; neither is lost, swapped or duplicated.
Source: implied: C-11 (only same-conversation overlap is forbidden)

### C-117: A limit can be passed only by sends accepted at the same moment
Observable: When a user is one attempt below the hourly limit and sends in five different conversations at once, between one and five are accepted; once those attempts exist, every further send is refused until the window frees. Sends made one after another never pass a limit. The same holds for the daily limit across users.
Source: choice: strict serialization of all sends would slow every user; the overshoot is bounded by what is in flight at once

### C-118: A transcript shows each user message followed by its own reply or failure
Observable: The transcript is ordered by the time each user message was first sent; the reply or failure for a message appears directly beneath it, including a reply to a Retry that completes after later messages were sent.
Source: implied: C-33 (retry arrives late)

### C-119: A reply that cannot be stored because its conversation was deleted is still shown once
Observable: If the conversation is deleted (by an administrator, or by the user in another tab) while a reply is in flight, the originating page shows the reply once, marked "not saved" (category 11), and no record of it exists in the org. Reloading the page does not bring it back.
Source: implied: C-26 only blocks the user's own delete from the same tab; administrators and other tabs can still delete

### C-120: "Run cleanup now" is refused while a cleanup is running
Observable: When a cleanup run (scheduled or manual) is in progress, pressing "Run cleanup now" shows that one is already running and starts nothing; counts of deleted records are therefore never reported twice.
Source: implied: scheduled and manual cleanup can overlap

### C-121: A settings save made from a stale form is refused
Observable: If administrator B saves settings after administrator A saved a change that B's form had not loaded, B's save is refused with a message naming who changed the settings and when, and asking to reload; nothing is overwritten.
Source: choice: silent last-writer-wins would undo another administrator's change without anyone knowing

### C-122: Removing Grok Bot User does not cancel a message in flight
Observable: A message sent before the permission was removed still receives its reply or failure and is stored; the user sees it only after the permission is given again (C-91).
Source: implied: C-90 against C-48

### C-123: The "Test connection" control is disabled while a test runs
Observable: From pressing it until a result is shown, the control is disabled and shows that a test is running; no second test starts.
Source: implied: C-67, a repeated press

### C-124: When several refusals apply, the first in C-38's order is reported and logged
Observable: With the hourly limit and the daily limit both reached, the refusal shown is the hourly one and the log has a single "Refused: hourly limit" record. With the bot off and a message that is empty, the refusal shown is "bot off".
Source: choice: one reason is enough to act on; the order of C-38 is the order of cheapest to most specific

### C-125: The limits count exactly the attempts the log records as counted
Observable: A counted attempt is one whose log record has a success or failure outcome, a test flag of false, and a time within the window. An administrator who deletes log records frees the matching capacity.
Source: choice: one source for both the limits and the summary (C-101) keeps them from disagreeing

### C-126: A failure to write the log does not change what the user sees
Observable: When the log record cannot be written (for example the org's storage is full), the user's reply or failure is shown and stored exactly as if it had been written.
Source: implied: the log is for operators; it must not take the user's reply down with it

### C-127: A platform concurrency refusal is shown as "Salesforce limit"
Observable: When Salesforce refuses the request because too many long-running requests are active in the org at once, the message is stored as failed with category "Salesforce limit", the user is told to try again later, and Retry is offered. The platform's exact figure (documented as 10 concurrent requests running over 5 seconds in a production org, lower in some development orgs) is unconfirmed.
Source: implied: runtime rule: each reply holds a request open for up to the timeout

### C-128: The browser never contacts xAI
Observable: A recording of the browser's network traffic while using every function of the bot shows requests only to the org's own Salesforce hosts, and none to x.ai or any other third-party host. No browser-side allow-list entry (trusted site) is needed in Setup.
Source: implied: C-65 (the key could not stay secret if the browser held it); runtime rule on cross-origin calls from Lightning pages

### C-129: The automated tests all pass and cover at least 75% of the bot's server-side code
Observable: Running all the project's tests in a fresh org reports zero failures and at least 75% line coverage across the bot's server-side code (75% is the platform's floor for deploying to production). No test calls xAI; every call to Grok in a test is replaced by a stand-in response, and no test needs a key.
Source: implied: U-14; runtime rule: Apex tests may not make real callouts, and production deploys need 75%

### C-130: The README has a "Before production" section with these items
Observable: The section lists, as things to do or check before the bot goes beyond a development org: (1) the tests of C-129 pass in the target org during deploy; (2) the credential is created again and its key entered in the target org, since a secret does not travel with a deploy; (3) the organization's data-protection owner has reviewed xAI's terms, data retention and location, because what users type goes to xAI outside any Salesforce data-protection agreement or Einstein Trust Layer; (4) the storage and the limits of C-35, C-36 and C-83 are sized for real use, since production storage and traffic differ from a development org; (5) who holds Grok Bot User and Grok Bot Admin is decided; (6) "Schedule daily cleanup" is pressed in the target org; (7) the notices in C-40 and C-41 match the organization's policy.
Source: implied: U-14, "development org"; a dimension (what ships beyond), so listed in full

### C-131: The README states what the org needs before deploy
Observable: The README states that the org must have Lightning Experience on and My Domain deployed, that no Einstein, Agentforce or Messaging licence is needed (C-42), and that the person deploying needs the Salesforce CLI and administrator rights in the org. It names the xAI account requirement: a team with an API key and available credit (credit exhaustion shows as category 3 or 5, which one is unconfirmed).
Source: implied: U-6; the platform rule that a deploy needs these before it will run at all

### C-132: A failed deploy installs nothing
Observable: When the deploy fails (for example in an org without Lightning Experience, or on a test failure), the org has none of the components in C-60 afterwards, and the command's output names the first cause.
Source: implied: U-6 (unhappy path); runtime rule: a metadata deploy is all-or-nothing

### C-133: A failure to schedule cleanup is shown with its reason
Observable: When scheduling fails (for example the org already has the platform maximum of 100 scheduled Apex jobs), the tab shows that nothing is scheduled and gives the platform's reason.
Source: implied: U-12 (unhappy path); runtime rule: 100 scheduled Apex jobs per org

### C-134: An interrupted cleanup leaves consistent data and finishes on the next run
Observable: If a run stops partway (for example on an error), every conversation that remains has all its messages, no message remains without its conversation, the tab shows the failure (C-108), and the next run deletes what is still expired.
Source: implied: C-106 (partial completion)

### C-135: A deploy changes no existing component
Observable: Comparing the org's metadata before and after the first deploy, the only differences are the additions in C-60. No existing object, field, page layout, profile, permission set, app, flow, Apex class, sharing setting or org-wide default is altered or removed.
Source: implied: "what must not change": the org may hold other work

### C-136: The bot reads and writes no Salesforce record outside its own
Observable: In every function of the bot, the only records created, changed or deleted are conversations, messages, log records, the settings, and the scheduled cleanup; no record of any other object (for example Account, Contact or Case) is read to build a request or changed by a reply.
Source: choice: C-16 (nothing of the org's data goes to xAI), and a reply must never act on the org

### C-137: A reply can cause nothing to happen
Observable: Whatever the text of a reply (for example one asking the user to click something, or containing a URL, or instructions to the bot), the bot creates, changes, deletes, sends or opens nothing because of it. A URL in a reply is shown as text and is not a clickable link.
Source: choice: a reply is untrusted text from a third party; the loosest safe rule is that it is shown and nothing more

### C-138: Every server-side operation checks the caller's right itself
Observable: Each of these operations, when called directly (not through the page) by a user who lacks the right, is refused and changes nothing: list conversations, open a conversation, send, retry, delete (the user's own conversation: owner or Grok Bot Admin only); read settings, save settings, restore defaults, test connection, read the summary, run cleanup, schedule cleanup, unschedule cleanup (Grok Bot Admin only).
Source: implied: C-56, C-71, "a rule enforced in one path and not another"; a dimension (the operations), so listed in full

### C-139: A stored user message holds the text trimmed of surrounding whitespace
Observable: A message sent as "  hi there \n" is stored, shown and sent to Grok as "hi there"; whitespace and line breaks inside the text are unchanged.
Source: choice: C-4 and C-5 judge the trimmed text, so this is the text that is meant

### C-140: A message that cannot be stored is refused before any call
Observable: When the user's own message cannot be stored (for example the org's data storage is full), nothing is sent to Grok, nothing is counted, the user is told that the message could not be saved, and the typed text stays in the box. This is a refusal of C-38, last in its order.
Source: implied: C-32 (the message is stored before the call) and C-111

### C-141: The admin summary shows zeros, not errors, when there is nothing to count
Observable: With no log records in the last 24 hours the tab shows 0 for every count and the sum, and shows that the mean duration is not available.
Source: implied: U-6 (the first time), C-100

### C-142: Line breaks and runs of spaces in a message are preserved when displayed
Observable: A reply or user message of "a\n\n  b" is displayed with a blank line between a and b and two spaces before b.
Source: implied: C-9 (displaying as text must not flatten code and lists a model replies with)

### C-143: Shift+Enter adds a line break and sends nothing
Observable: With text in the box, pressing Shift+Enter inserts a line break at the cursor and sends nothing.
Source: choice: the common chat convention (see C-10)

### C-144: Grok's reply is requested whole, not streamed
Observable: Each call asks Grok for a single complete response (no streaming); the reply appears in the transcript all at once, after the call returns.
Source: implied: runtime rule: Apex on Salesforce cannot stream a callout's response to the browser

### C-145: A message sent in an old conversation moves it to the top of the list
Observable: After sending in a conversation that was fourth in the list, it is first in the list.
Source: implied: C-21

### C-146: The user is told whether trying again can help
Observable: The failure shown says either to try again later (categories 5, 6, 7, 8, 9, 10) or to contact the administrator (categories 1, 2, 3, 4); category 4 adds that a very long conversation may be the cause and a new chat may help.
Source: implied: U-4 (a user who is told only "failed" cannot tell whether to wait or to ask)

### C-147: A refused send leaves the typed text in the box
Observable: After any refusal in C-38 the text the user typed is still in the box, unchanged, so it can be sent again or copied.
Source: implied: C-38 (data the user typed is never lost on the way)

### C-148: A reply or failure stored for an open conversation appears without a reload
Observable: When the reply or failure of a message in flight is stored, it appears in the open conversation within 10 seconds, with no reload by the user.
Source: choice: 10 seconds is short enough to feel live and long enough to avoid flooding the server

### C-149: Pressing "Schedule daily cleanup" while it is scheduled creates no second schedule
Observable: Pressing it again tells the administrator that it is already scheduled; the org then holds exactly one scheduled cleanup job.
Source: implied: C-107 (the same step twice)

### C-150: The admin tab shows whether cleanup is scheduled, and when it next runs
Observable: The tab shows "scheduled" with the next run's date and time, or "not scheduled"; "Unschedule daily cleanup" changes it to "not scheduled" and no further run happens.
Source: implied: U-12 (undo and know the state)

### C-151: "Test connection" creates no conversation or message and counts toward no limit
Observable: A test creates no conversation and no message, writes one log record marked as a test (C-96), and is not counted toward the hourly or the daily limit (C-37).
Source: implied: C-37, C-67

### C-152: The key is never shown after it is saved
Observable: After saving, no screen of Setup or of the bot, no API response, no record field and no log displays the key in clear; Setup shows the field masked or absent.
Source: implied: U-7 (an administrator's key is as secret as a password)

### C-153: A message marked failed as Timed out no longer blocks sending in its conversation
Observable: Once a message in flight is shown as failed (C-50), Send is enabled again for that conversation and a new message can be sent there.
Source: implied: C-11 against C-50 (a piece of state, "in flight", must have an end)

### C-154: Records deleted by cleanup are removed permanently
Observable: A conversation, message or log record deleted by a cleanup run is not in the Recycle Bin afterwards and cannot be restored.
Source: choice: cleanup exists to free storage, and records in the Recycle Bin still count against a development org's 5 MB until it is emptied

### C-155: Salesforce users with platform-wide data rights keep them
Observable: A user who holds the platform permission "View All Data" or "Modify All Data" can read, and with "Modify All Data" delete, any conversation, message or log record through standard Salesforce screens, without holding Grok Bot Admin; the bot does not try to prevent it. In this specification "administrator" means a holder of Grok Bot Admin.
Source: implied: runtime rule: the platform's data rights override sharing; stated so that C-56 is read as binding the bot's own access paths and not those rights
