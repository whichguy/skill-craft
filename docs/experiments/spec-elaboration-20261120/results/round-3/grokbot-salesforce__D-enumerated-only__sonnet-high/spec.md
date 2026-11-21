## Use cases

### U-1: A Salesforce user asks Grok a question from inside Salesforce, to get an answer without leaving the org
Flow: The user opens "Grok Bot" from the Lightning Experience App Launcher. They see an empty chat view with a message box and a Send button. They type a question and press Send. Their message appears in the transcript at once with a waiting indicator. When Grok's reply arrives the reply appears below the question, in full, and the waiting indicator goes away.
Source: request (a "Grok bot" in a Salesforce org)

### U-2: A user continues a conversation with follow-up questions, to get answers that build on what was already said
Flow: After a reply, the user types a follow-up that only makes sense given the earlier messages (for example "make that shorter"). The reply takes the earlier messages into account. The transcript grows downward, oldest message at the top.
Source: implied: a "bot" is conversational; a bot that forgets the previous turn is not one

### U-3: A user starts a fresh conversation, to change topic without earlier messages influencing Grok
Flow: The user activates "New chat". The transcript clears to an empty conversation. The previous conversation is still in their history. Their next message carries none of the earlier conversation to Grok.
Source: implied: by U-2 (context accumulates, so the user needs a way to reset it)

### U-4: A user returns later and finds an earlier conversation, to reread or continue it
Flow: The user opens "Grok Bot" on a later day, sees a list of their past conversations (most recent first), selects one, sees the whole transcript with timestamps, and can send another message in it.
Source: implied: users expect a chat product to remember conversations; a Salesforce org is a system of record

### U-5: A user deletes a conversation, to remove content they no longer want stored
Flow: The user chooses delete on a conversation, confirms in a confirmation prompt, and the conversation disappears from the list. If they decline the prompt nothing changes.
Source: implied: conversations are stored (U-4), so the person who wrote them must be able to remove them

### U-6: A user's message fails (Grok or the network or Salesforce fails), to know what happened and try again
Flow: The user sends a message. Something goes wrong (xAI says the key is bad, xAI is rate limiting, the call times out, xAI is down, the org is out of storage, and so on). The user's message stays in the transcript marked as failed, with a message saying which kind of problem it was and whether to retry, shorten the message, or contact the administrator. They press Retry and either get a reply or a fresh failure.
Source: implied: the bot depends on an outside system (xAI) and on Salesforce platform limits, both of which fail

### U-7: A user who is not allowed, or when the bot is switched off or not set up, tries to use it, and is told clearly why they cannot
Flow: A user without access does not see "Grok Bot" at all. A user with access opens it while an administrator has disabled the bot, or before any API key has been entered, and sees a notice that says so; the message box does not send.
Source: implied: Salesforce orgs control access by permission; an admin must be able to stop the bot; the bot cannot work before a key is entered

### U-8: A heavy user or a busy org reaches a usage limit, to be told rather than silently ignored
Flow: A user sends their 101st message within 24 hours (default per-user limit 100). Nothing is sent to Grok; the user sees that their daily limit of 100 has been reached. The same happens when the org-wide limit (default 1,000 per 24 hours) is reached by all users together.
Source: implied: each message costs money on the admin's xAI account; an operator needs a spend cap

### U-9: An administrator sets the bot up for the first time in a development org, to get it working
Flow: The administrator deploys the bot into a Developer Edition, scratch or sandbox org, assigns themselves the use and admin permission sets, opens the Admin area of "Grok Bot", enters their xAI API key (it is masked after saving), uses "Test connection" and sees success, turns on the daily cleanup schedule, then opens the chat view and sends a first message.
Source: request (a Grok bot "in a Salesforce development org"); implied: xAI requires an API key the requester must supply

### U-10: An administrator changes how the bot behaves, rotates the key, or switches the bot off, without a deployment
Flow: In the Admin area the administrator edits the model name, system prompt, limits and retention, replaces the API key, or turns the bot off. The next message any user sends obeys the new values. Turning the bot off immediately stops new messages reaching Grok while leaving users able to read and delete their history.
Source: implied: operator controls (start, stop, configure, recover from a leaked key)

### U-11: An administrator observes usage and checks the connection, to understand cost, errors and who is using the bot
Flow: The administrator opens the usage log in Salesforce, sees one entry per attempt to reach Grok with time, user, outcome, status code, token counts and latency, builds a standard Salesforce report from it, and presses "Test connection" to see whether the key and model work right now.
Source: implied: operator observation; xAI bills by tokens

### U-12: An administrator keeps data volume under control, to keep the org within its storage and retention policy
Flow: Conversations and usage entries older than the retention period (default 30 days) are removed automatically once a day. The administrator can see when the last cleanup ran and how many records it removed, and can run it on demand.
Source: implied: stored chat data is never-ending state; Developer Edition orgs have small storage

### U-13: A developer deploys, tests, upgrades, rolls back and promotes the bot, to move it beyond the development org safely
Flow: The developer deploys the bot's source into another org, runs all its automated tests (which pass without a key and without network access), redeploys a newer or older version over an org that already holds conversations and settings, and sees nothing lost. To go to production they need the tests to pass at the platform's minimum coverage.
Source: request ("development org"); implied: Salesforce requires tests and coverage to deploy to production

### U-14: Several people, or one person in several tabs, use the bot at once, and each gets a correct, separate outcome
Flow: Two users send messages at the same moment and each receives their own reply. One user double-clicks Send once and one message is sent. One user opens the same conversation in two tabs and sends from both.
Source: implied: Salesforce orgs are multi-user and browsers have tabs

## Clauses

### C-1: Users who hold the bot's use permission find an app named "Grok Bot" in the Lightning Experience App Launcher
Observable: A user with the use permission searches the App Launcher for "Grok Bot", sees it, opens it, and lands on the chat view.
Source: request ("Grok bot")

### C-2: Users who hold neither the use permission nor the admin permission do not see "Grok Bot" anywhere in the navigation
Observable: For a user with neither permission set, "Grok Bot" is absent from the App Launcher and from search.
Source: implied: by U-7 (access is by permission)

### C-3: The server refuses every request from a user without the required permission, whatever the entry point
Observable: A user without the use permission who calls the bot's server-side operations directly (for example from a different page, a script, or a REST call as that user) to send a message, list conversations or read a transcript gets a refusal and receives no conversation data; no call is made to xAI.
Source: implied: by C-2 (hiding the menu is not access control)

### C-4: Two assignable permission sets exist, one granting use of the chat and one granting administration, and the administration set alone does not allow chatting
Observable: A user assigned only the admin permission set sees the Admin area but sees no chat view and cannot send messages. A user assigned only the use permission set sees the chat view but no Admin area. An administrator who wants both is assigned both.
Source: choice: least privilege; the request does not name roles. The permission sets' labels and API names are left open.

### C-5: Only internal Lightning Experience users are supported; Experience Cloud users, guest users and Salesforce Classic are not
Observable: No Experience Cloud site, guest page or Salesforce Classic app exposes the bot; the chat view and the Admin area exist only in Lightning Experience for internal users.
Source: choice: smallest surface that serves a development-org bot; the request is silent

### C-6: The chat view works in the desktop browsers Lightning Experience supports; the Salesforce mobile app is not required
Observable: The bot works in current Chrome, Edge, Firefox and Safari desktop browsers in Lightning Experience. Behaviour in the Salesforce mobile app is not specified and not tested.
Source: choice: the request is silent on devices; the loosest requirement that serves a development-org bot

### C-7: Opening the chat view for the first time shows an empty conversation ready to type in
Observable: A user with the use permission who has never sent a message opens "Grok Bot" and sees an enabled message box, an enabled Send button, an empty transcript, an empty history list with a notice that no conversations exist yet, and no error.
Source: implied: by U-1 (the first time)

### C-8: Sending a message puts it in the transcript immediately and shows that a reply is awaited
Observable: When the user activates Send and none of the refusal conditions of C-60 applies, the message appears in the transcript as the user's message before any reply, and a waiting indicator is visible until the reply or a failure arrives.
Source: implied: by U-1

### C-9: The reply is shown below the message it answers, visibly distinguished from the user's own messages
Observable: After the reply arrives, it appears directly under the user's message, labelled or styled so a person can tell it came from Grok and not from themselves.
Source: implied: by U-1

### C-10: The text of Grok's reply is shown in full
Observable: If xAI returns a reply of N characters, all N characters appear in the transcript (no cut, ellipsis or "show more" that hides content), up to the output cap set in C-24.
Source: implied: by U-1

### C-11: Line breaks and indentation in a reply are preserved
Observable: A reply containing a multi-line code block shows the lines on separate lines, with their leading spaces kept. Whether Markdown is rendered as formatting is left open.
Source: implied: Grok replies contain code and lists; the rendering style is left open

### C-12: A reply appears all at once, not token by token
Observable: After Send, no partial reply text is shown; the reply text appears in one update when xAI has finished. Reason: the platform's server-side HTTP callouts return only a complete response and cannot relay a streamed one to the page.
Source: implied: runtime rule (Apex callouts are request/response)

### C-13: While a message in a conversation is awaiting its reply, a second message cannot be sent in that conversation from that page
Observable: After Send, the Send button for that conversation is disabled (or does nothing) until the reply or a failure arrives; the user can still read the transcript and can switch to another conversation.
Source: implied: by U-14 (double send) and by C-18 (context is built in order)

### C-14: The transcript is in chronological order, oldest at the top, and shows the newest message after each update
Observable: Messages are ordered by time sent or received; after a send or a reply the view is scrolled so that the newest message is visible.
Source: implied: how chat works; the user relies on order

### C-15: Each message shows its time in the viewing user's own Salesforce time zone and locale
Observable: A message sent at 17:00 UTC in January is shown as 09:00 to a user whose Salesforce time zone is America/Los_Angeles (UTC-8) and as 17:00 to a user whose time zone is UTC; the same message is shown to each in their own zone.
Source: implied: Salesforce users set a time zone; a time in a different zone is a wrong time to them

### C-16: A message that is empty or only whitespace cannot be sent
Observable: With an empty message box, or one holding only spaces, tabs and line breaks, Send is disabled or does nothing; no message is added, nothing is sent to xAI, no usage-log entry is made.
Source: implied: by U-1 (the empty case)

### C-17: A message longer than the maximum message length is refused before anything is sent, and the user is told the limit
Observable: Characters are counted as Unicode code points (an emoji counts as one). With the maximum message length at its default of 4,000 characters, a 4,001-character message is not sent; the user sees that the limit is 4,000 characters and how many characters they typed; a 4,000-character message is accepted.
Source: implied: by U-1 (the largest case); the default value is a choice (large enough for a pasted page of text, small enough to keep one call's cost and context bounded)

### C-18: The text of a message refused locally stays in the message box
Observable: After any local refusal listed in C-60 the text the user typed is still in the box so they can edit and resend it, and it has not been added to the transcript.
Source: implied: losing a long typed message on refusal is a loss of the user's work

### C-19: Each request to Grok carries the earlier messages of the same conversation in order, with each marked as the user's or Grok's
Observable: In a conversation holding user message A, Grok reply B and a new user message C, the request xAI receives has, after the system prompt, A as a user message, B as an assistant message, then C as a user message, in that order.
Source: implied: by U-2

### C-20: Only the most recent messages up to the history window are sent; the system prompt and the newest message are always sent
Observable: With the history window at its default of 20 messages, in a conversation of 30 earlier messages the request carries the 20 most recent earlier messages plus the new one (the system prompt is not counted in the 20); older messages are not sent, and all 30 still show in the transcript.
Source: choice: bounds cost and keeps requests inside the model's context size (the model's context-size figure is unconfirmed and varies by model); the default of 20 messages (10 exchanges) is chosen as ample for ordinary chat

### C-21: Messages that failed are not sent to Grok as context in later requests
Observable: After a failed message X followed by a successful message Y, the request for Y does not include X.
Source: implied: a failed message has no reply; sending it as context would show Grok an unanswered question

### C-22: The system prompt is sent first when it is non-empty, and omitted when empty
Observable: With a non-empty system prompt configured, the request xAI receives has it as the first message with the system role. With an empty system prompt, no system message is in the request.
Source: implied: admin controls (U-10); the default prompt's wording is left open but must be non-empty and must tell Grok that it is an assistant used inside Salesforce

### C-23: Conversations can hold at most 200 messages (counting both the user's and Grok's)
Observable: When a conversation holds 200 messages, the next Send is refused, nothing is sent to xAI, and the user sees that the conversation is full and that they should start a new chat.
Source: choice: bounds the size of one conversation's stored data and its display; the request is silent. This limit is fixed and not an admin setting (deliberately left unconfigurable to keep the controls list short).

### C-24: The output cap is sent with every request, and a reply cut off at the cap is marked as cut off
Observable: With the maximum reply tokens at its default of 1,024, the request xAI receives limits output to 1,024 tokens. If xAI reports that the reply stopped because of that length limit, the stored and displayed reply is followed by a notice that it was cut off at the length limit. The exact field name xAI expects for the cap is unconfirmed and must be checked against the xAI documentation at build time.
Source: choice: default value; bounds the cost of one message and keeps every reply within a stored field (the upper bound of 4,096 tokens, about 16,000 to 20,000 characters, is far below the 131,072-character limit of a Salesforce long text area)

### C-25: Replies are shown as plain text; markup inside them is never executed
Observable: If Grok's reply contains the text `<script>alert(1)</script>` or `<img src=x onerror=alert(1)>`, the transcript shows those characters as text; no alert fires, no image request is made and no element is added to the page.
Source: implied: output from an outside system is untrusted; Salesforce pages run with the user's session

### C-26: Text in any language, and emoji, are stored and shown exactly as sent and received
Observable: A message "こんにちは 👋 café" is shown unchanged in the transcript, is sent unchanged to xAI, and after the page is reloaded is shown unchanged; the same holds for a reply containing such characters.
Source: implied: Grok answers in many languages; Salesforce stores Unicode

### C-27: The chat view always tells the user that their messages are sent to xAI, a third party outside Salesforce
Observable: Whenever the chat view is displayed, a notice is visible without scrolling or hovering stating that messages are sent to xAI (Grok) outside Salesforce and that confidential or regulated data should not be entered unless the organisation permits it. The wording is left open. Reason: calls to a third-party model do not pass through Salesforce's own AI protections such as the Einstein Trust Layer.
Source: implied: Salesforce orgs hold regulated customer data; the user is entitled to know where text goes

### C-28: Fixed interface text is in English only
Observable: Labels, notices and error messages of the bot are in English whatever the user's Salesforce language; Grok's replies are in whichever language Grok chooses.
Source: choice: the request is silent; translation is not needed to serve a development-org bot

### C-29: Every control in the chat view and the Admin area can be operated with the keyboard alone and has a name a screen reader announces
Observable: Using only Tab, Shift+Tab, Enter and Space a user can focus and activate Send, New chat, each conversation in the list, delete and its confirmation, and Retry; a screen reader reads a meaningful name for each.
Source: implied: Salesforce's accessibility standard for custom Lightning components (WCAG 2.1 AA)

### C-30: A newly arrived reply or error is announced to screen readers without the user moving focus
Observable: When a reply or an error appears, a screen reader announces it (or announces that a new message arrived) while focus stays in the message box.
Source: implied: C-29

### C-31: "New chat" starts an empty conversation and leaves earlier ones untouched
Observable: After the user activates "New chat" the transcript is empty and the message box is empty; the earlier conversation remains in the history list with all its messages.
Source: implied: by U-3

### C-32: A conversation is not stored until its first message is sent
Observable: Activating "New chat" repeatedly without sending anything adds no entries to the history list and creates no stored conversation.
Source: choice: avoids empty clutter in a small-storage org; the request is silent

### C-33: A conversation's title is the first 80 characters of its first message
Observable: After sending "Draft a two-line apology for a late shipment", the history list shows that text as the conversation's title; a first message of 200 characters shows its first 80 characters.
Source: choice: the user needs a recognisable label; the request is silent; the 80-character length matches the standard record-name field size

### C-34: The history list shows the user's own conversations, most recently active first
Observable: A user with conversations last active on Mon, Wed and Tue sees them in the order Wed, Tue, Mon. A conversation moves to the top when a message is sent or received in it.
Source: implied: by U-4

### C-35: The history list shows 50 conversations at a time and offers a way to see more
Observable: A user with 120 conversations sees 50, activates "Show more" and sees 100, activates it again and sees all 120; the control is not offered when there is nothing more.
Source: choice: bounds page load size; the request is silent

### C-36: The history list when empty says so
Observable: A user with no conversations sees a notice that they have none, and no list rows.
Source: implied: by U-4 (the empty case)

### C-37: Selecting a conversation in the history list shows its whole transcript and lets the user continue it
Observable: After selecting a conversation of 12 messages the user sees all 12 in order with their times, including any that failed (with their failed marking) and can send a 13th message, which carries the earlier messages as context per C-19.
Source: implied: by U-4

### C-38: Everything the user saw in a conversation is still there after the page is reloaded or the user signs in again
Observable: After a reload or a new login, the user's conversations and each conversation's messages, including failures, are present as before the reload.
Source: implied: by U-4

### C-39: A reply of any length within the output cap is stored in full
Observable: A 16,000-character reply, when the conversation is reopened later, is shown in its full 16,000 characters.
Source: implied: C-10 together with C-38; the storage field size of the platform must not cut it

### C-40: Deleting a conversation requires confirmation
Observable: Activating delete on a conversation shows a confirmation prompt naming the conversation; nothing is deleted until the user confirms.
Source: implied: by U-5; deletion is permanent per C-42

### C-41: Declining the delete confirmation changes nothing
Observable: After the user declines, the conversation is still in the list with all its messages.
Source: implied: by U-5

### C-42: Confirming a delete permanently removes the conversation and all of its messages
Observable: After confirming, the conversation is absent from the history list, its transcript cannot be reopened (not by the user, not from a Salesforce recycle bin or similar undelete), and its messages cannot be retrieved by the user through the bot.
Source: implied: by U-5; a user deleting stored chat expects it gone

### C-43: A reply that arrives after its conversation was deleted is discarded and does not recreate the conversation
Observable: The user sends a message, deletes that conversation before the reply arrives, and then the reply arrives: the history list still does not contain the conversation, and no stored messages exist for it.
Source: implied: where two actions meet (delete during an in-flight send)

### C-44: A user can see only their own conversations and messages
Observable: User A's conversations and messages never appear in user B's history list or transcript, including when B has a higher role in the role hierarchy than A, is A's manager, or has the admin permission set of the bot.
Source: implied: chat content is private; Salesforce sharing would otherwise let role-hierarchy managers read records

### C-45: Salesforce system administrators who hold the platform's own "View All Data" or "Modify All Data" permission can still read stored conversations through standard Salesforce tools; the bot's admin permission set adds no access to conversation content
Observable: A user with only the bot's admin permission set who queries or reports on messages sees none of the message text of other users. A user with the platform-wide View All Data permission can see all, because the platform grants it and the bot cannot override it.
Source: implied: runtime rule (View All Data / Modify All Data override sharing); the bot's admin set is least-privilege

### C-46: When the administrator has switched the bot off, sending is refused with a notice that the bot is disabled
Observable: With Enabled off, a user who presses Send sees a notice that the bot is currently disabled by the administrator; nothing is sent to xAI; no usage-log entry is made for it.
Source: implied: by U-7, U-10

### C-47: When the bot is switched off, users can still read and delete their conversations
Observable: With Enabled off, the history list and transcripts are visible and delete still works.
Source: implied: by U-10 (stop without destroying; users' stored data stays theirs to control)

### C-48: When no API key has been entered, sending is refused with a notice that the bot is not set up and the administrator must finish setup
Observable: In an org where no key has been entered, or the key has been cleared, Send shows that notice; nothing is sent to xAI. Reason: the platform cannot make the call without the credential.
Source: implied: by U-7 (before a key exists)

### C-49: When xAI rejects the key, the user's message is marked failed and the user is told the bot's credentials need the administrator's attention
Observable: When xAI responds HTTP 401 or 403, or HTTP 400 with an error indicating an invalid or missing API key, the message is marked failed with a notice telling the user to contact the administrator (not to retry or edit the message). The precise body xAI uses for an invalid key on a 400 is unconfirmed.
Source: implied: by U-6; xAI's documentation states that 400, 401 and 403 can denote key problems

### C-50: When xAI rate-limits the request (HTTP 429), the message is marked failed and the user is told to try again shortly
Observable: With xAI answering HTTP 429, the message is marked failed with a notice that the service is receiving too many requests and that retrying in a little while is appropriate. xAI's rate limits (requests and tokens per period, depending on the account's spending tier) are unconfirmed here and are set by xAI, not by this bot.
Source: implied: by U-6; xAI documents 429 for exceeding rate limits

### C-51: When no reply arrives within the response timeout, the message is marked failed and the user is told it timed out
Observable: With the response timeout at its default of 60 seconds and xAI taking longer, at 60 seconds (give or take a few seconds of platform scheduling) the message is marked failed with a notice that Grok did not answer in time and that retrying is possible.
Source: implied: by U-6; the default is a choice (long enough for slower reasoning models, short enough that the user is not left waiting for minutes)

### C-52: A reply that xAI sends after the timeout has fired is discarded
Observable: After a timeout failure is shown, a late reply from xAI never appears in the transcript, not then and not after reloading; the message stays failed.
Source: implied: where two things meet (a reply that arrives late); showing a reply under a message already marked failed would contradict C-58

### C-53: When xAI is unavailable or unreachable, the message is marked failed and the user is told it is a temporary problem
Observable: When xAI responds with any HTTP status 500 to 599, or the connection cannot be made (name resolution, connection refused, TLS failure), the message is marked failed with a notice that Grok is temporarily unavailable and a retry later is suggested.
Source: implied: by U-6 (a thing it depends on failing)

### C-54: When xAI rejects the request itself, the message is marked failed and the user is told to change or shorten the message, or contact the administrator if it keeps happening
Observable: Any xAI HTTP 4xx status other than 401, 403, 429 and the key-related 400 of C-49 (for example 400 for a malformed or too-long request, 404 for an unknown model, 413) marks the message failed with a notice of this kind.
Source: implied: by U-6; the model name is admin-editable so a wrong model name is possible

### C-55: When xAI answers successfully but with no reply text, the message is marked failed and the user is told Grok returned no reply
Observable: An HTTP 200 response whose reply content is empty or missing marks the message failed with a notice that Grok returned no reply; no empty reply bubble is shown.
Source: implied: by U-6 (an edge of success)

### C-56: When the platform refuses the call because of its concurrent-request limit, the message is marked failed and the user is told the system is busy and to try again shortly
Observable: When Salesforce rejects the work because too many long-running requests are running in the org at once, the message is marked failed with a notice that the system is busy.
Source: implied: runtime rule (Salesforce caps concurrent long-running requests per org; the exact figure of 10 requests running 5 seconds or longer is unconfirmed here)

### C-57: When the org has no storage left to save the message, the message is not sent to xAI and the user is told it could not be saved
Observable: In an org whose data storage is full (a Developer Edition org's data storage is small; the figure of 5 MB is unconfirmed), pressing Send shows a notice that the message could not be saved because the org is out of storage and to contact the administrator; no call is made to xAI.
Source: implied: runtime rule (data storage cap); by U-6

### C-58: A failed message stays in the transcript, marked failed, with a Retry action
Observable: After any failure (C-49 to C-56 and C-62; C-57 is different because the message was never saved, and its text stays in the message box per C-18), the user's message is still in the transcript carrying a visible "failed" marking and a Retry action, together with the notice that says what kind of problem it was.
Source: implied: by U-6; losing the user's message on failure is data loss

### C-59: Retry sends the same message text again as a new message at the end of the transcript, replacing the failed one, and results in exactly one message and at most one reply
Observable: After a failure the user presses Retry. The failed marking and the failed copy are gone; the same text appears once at the bottom of the transcript with a new time and a waiting indicator; when the call succeeds one reply appears under it. A second press of Retry while that retry is awaiting a reply does nothing. The conversation's message count does not grow by the replaced copy.
Source: implied: by U-6; Pass 3 (duplication); choice: replacing at the end keeps chronological order (C-14) and context order (C-19) true even if later messages were answered in between

### C-60: In each of these conditions the message is refused without any call to xAI: no use permission, bot disabled, no key entered, message blank, message over the maximum length, conversation full, another message in the conversation still awaiting its reply, the user's limit reached, the org-wide limit reached, the org out of storage
Observable: For each of the ten conditions, a mock xAI server receives zero requests and the user sees a notice specific to that condition.
Source: implied: by C-3, C-16, C-17, C-23, C-46, C-48, C-57, C-65, C-69, C-71 (a single list so that the dimension is complete). Retry (C-59) goes through the same checks as a first send.

### C-61: The bot never retries a failed call to xAI by itself
Observable: When xAI answers 429, 5xx or times out, the mock xAI server sees exactly one request for that Send; further requests arrive only when the user presses Retry.
Source: choice: automatic retries would multiply cost and delay and could repeat a billed call; the user decides

### C-62: A message that has been waiting for a reply for longer than the response timeout plus 30 seconds is shown as failed
Observable: If the user closes the page, loses connection or the platform loses track while a message is awaiting a reply, then when the user reopens the conversation, any message waiting longer than (response timeout + 30 seconds) is shown as failed with Retry, no longer counts toward any limit, and no longer blocks sending in that conversation (C-65); no message shows as waiting forever. The state of a user message is exactly one of: waiting, answered, failed. A reply that was on its way when the page was closed may be lost.
Source: implied: Pass 3 (partial completion; a state with an end); runtime rule (a browser request abandoned by closing the page cannot deliver its reply); choice: the 30-second grace

### C-63: The user's message is saved before Grok is contacted
Observable: With xAI deliberately made to hang, a second session of the same user reloading the conversation sees the sent message present (marked waiting); it is never absent while a call is outstanding. Reason: the platform forbids making an HTTP callout after saving records in the same transaction ("uncommitted work pending"), so saving and calling are separate steps in a fixed order.
Source: implied: runtime rule; by C-38

### C-64: Pressing Send twice quickly (double-click or double Enter) sends one message and makes one call to xAI
Observable: Two activations of Send within 500 milliseconds produce one message in the transcript and one request at the mock xAI server.
Source: implied: by U-14

### C-65: A second send in a conversation that already has a message waiting is refused, including from a second tab or window
Observable: A user with the same conversation open in two tabs sends from tab 1 and, while it waits, sends from tab 2: tab 2 gets a notice that a message in this conversation is still awaiting its reply, and adds nothing; the mock xAI server sees one request.
Source: implied: Pass 3 (two things at once); by C-13

### C-66: Messages in different conversations, or from different users, may wait on Grok at the same time
Observable: A user with two conversations sends a message in each within one second; both are sent and both receive their replies.
Source: implied: by U-14

### C-67: At least 25 messages from different users can be waiting on Grok at the same time without the platform's concurrent-request limit refusing any of them
Observable: With a mock xAI server that takes 30 seconds to answer, 25 users each send one message within a few seconds; all 25 are accepted and all 25 receive their replies. Reason: if the bot held a Salesforce request open for each waiting call, Salesforce's cap on concurrent long-running requests per org (unconfirmed, believed to be 10) would refuse more than that many.
Source: choice: 25 is a decided floor for "a team using it at once"; runtime rule

### C-68: A user's reply wait never lasts longer than the response timeout
Observable: With a mock xAI server that never answers, the user sees the failure of C-51 at the configured timeout and not later than the timeout plus 10 seconds.
Source: implied: C-51; the platform's maximum for one callout or continuation is 120 seconds, which bounds the setting in C-79

### C-69: Each user is limited to a number of messages per rolling 24 hours, default 100
Observable: With the per-user limit at 100, a user (administrators included) who has had 100 messages answered or currently awaiting a reply within the last 24 hours has their 101st Send refused (C-60); a different user is unaffected.
Source: implied: by U-8; the default is a choice (generous for individual use, a ceiling on one person's cost)

### C-70: When the per-user limit is reached the user is told the limit and that it frees up as older messages age past 24 hours
Observable: The notice states the number 100 (the configured limit), says that the limit is per 24 hours, and does not state a wrong reset time.
Source: implied: by U-8

### C-71: The org-wide limit is the number of messages answered across all users within a rolling 24 hours, default 1,000, and reaching it refuses further sends for everyone
Observable: With the org-wide limit at 1,000, once 1,000 messages across all users have been answered or are awaiting a reply within the last 24 hours, every user's next Send is refused with a notice that the organisation's daily limit has been reached and the administrator can raise it; sends succeed again once older messages age past 24 hours or the administrator raises the limit.
Source: implied: by U-8; the default is a choice (an operator-level spend cap sized for a development org)

### C-72: Failed attempts do not count toward either limit
Observable: A user whose 40 attempts all failed with 5xx, timeout or 429 still has their full limit available; only messages that received a reply, and messages currently awaiting one, count; a message that fails releases its place at once.
Source: choice: the user should not lose allowance to an outage; the loosest rule that serves them

### C-73: Messages sent at the same moment can never take a user or the org past a limit
Observable: With the per-user limit at 100 and 99 messages used, two sends issued in the same second from two conversations result in exactly one being accepted and one refused as over the limit. The same holds for the org-wide limit across users.
Source: implied: Pass 3 (two at once); must-never: a rule enforced in one path and not another

### C-74: The administrator can edit the bot's settings in the bot's Admin area, with these defaults: bot enabled = on; model = "grok-4"; system prompt = a non-empty default; maximum message length = 4,000 characters; history window = 20 messages; maximum reply tokens = 1,024; response timeout = 60 seconds; per-user limit = 100 per 24 hours; org-wide limit = 1,000 per 24 hours; retention = 30 days
Observable: In a freshly set-up org the Admin area shows each of those ten settings with exactly these values; the administrator can change each and save. The model name "grok-4" is a choice and its currency is unconfirmed: the builder must check xAI's model list at build time and use a model name xAI accepts. Temperature and other sampling settings are deliberately not settings; xAI's defaults apply.
Source: implied: by U-10; choice for each default value and for leaving sampling parameters out (they are not needed to serve the user)

### C-75: Each setting rejects values outside its allowed range, naming the setting, and leaves the stored value unchanged
Observable: Saving a value outside these ranges is refused with an error naming that setting: model 1 to 100 characters and not blank; system prompt 0 to 4,000 characters; maximum message length 100 to 20,000; history window 1 to 100; maximum reply tokens 16 to 4,096; response timeout 5 to 120 seconds; per-user limit 1 to 10,000; org-wide limit 1 to 1,000,000; retention 1 to 365 days. The setting keeps its previous value.
Source: choice for each bound; the upper bound of the response timeout (120 seconds) is forced by the platform's maximum for a callout or continuation

### C-76: Only holders of the admin permission can see or change settings, the key, Test connection, and the cleanup controls
Observable: A user with only the use permission, opening the Admin area's address directly or calling its server operations, sees nothing of settings and cannot change any; the key is never returned to them.
Source: implied: by U-10; must-never: a rule enforced in one path and not another

### C-77: A saved settings change applies to the next message sent after the save
Observable: An administrator changes the model from "grok-4" to another name; the next request to xAI, from any user, carries the new model name; a request already waiting for a reply is not altered.
Source: implied: by U-10

### C-78: The Admin area provides exactly these controls: edit settings, enter or replace the API key, clear the API key, Test connection, turn the daily cleanup schedule on or off, Run cleanup now, and view the last cleanup result
Observable: An administrator sees each of these seven controls in the Admin area; there is no control to read a stored key, to impersonate a user, or to read other users' messages.
Source: implied: by U-9, U-10, U-12 (the operator's work: start, stop, configure, observe, recover)

### C-79: The API key is entered once, is masked after saving, and can never be displayed again
Observable: After saving, the key field shows a placeholder indicating a key is stored (for example dots or "key saved") and never the key text; there is no control to reveal it.
Source: implied: secrets must not be readable back, by anyone, including administrators

### C-80: Replacing the key makes the next message use the new key and discards the old one
Observable: After the administrator saves a new key, the next request to the mock xAI server carries the new key as bearer token; the old key is not used again and is not stored anywhere.
Source: implied: by U-10 (rotate after a leak)

### C-81: Clearing the key puts the bot into the not-set-up state
Observable: After the administrator clears the key, the next Send is refused per C-48 and the Admin area shows that no key is stored.
Source: implied: by U-10 (revoke)

### C-82: The key never appears in any page, any server response to the browser, any usage-log entry, any error message, any Salesforce debug log of the bot's own code, any notification, or the bot's deployable source
Observable: Searching all of these after a send, a failure and a Test connection run for the key text finds nothing.
Source: implied: Pass 5 (must never: a secret exposed)

### C-83: Test connection sends one short fixed message to xAI with the stored key and model and reports the outcome to the administrator
Observable: Pressing Test connection shows within the response timeout one of: success (with the model name and latency in milliseconds) or a failure naming the same outcome categories used for users in C-49 to C-56, plus for the administrator only the HTTP status and the short error message text xAI returned.
Source: implied: by U-9, U-11

### C-84: Test connection creates no conversation, counts toward no limit, and is logged as a test
Observable: After a Test connection run, no new conversation appears for anyone, no user's or the org's message count changes, and the usage log gains one entry whose kind is "test".
Source: implied: by U-11; Pass 3 (an admin tool meeting quotas)

### C-85: With no key stored, Test connection reports not set up and makes no call
Observable: The result says no key is stored; the mock xAI server receives no request.
Source: implied: by C-48

### C-86: The bot sends calls only to https://api.x.ai/v1/chat/completions
Observable: Every request the bot makes to any outside system goes to exactly that address over HTTPS; no setting changes the host; there are no calls to any other host. In this specification "a mock xAI server" means a stand-in that receives and records what would be sent to that address (for example Apex HttpCalloutMock in tests, or a recording proxy). The path is believed current and is to be checked against xAI's documentation at build time.
Source: choice: the request names xAI's Grok; fixing the host prevents a settings change from sending conversations to another party

### C-87: Each request authenticates with the stored key as an HTTP bearer token
Observable: The request's Authorization header is "Bearer " followed by the stored key; no request is made without it.
Source: implied: xAI's API requires it

### C-88: A request to xAI contains only: the model name, the messages (system, earlier, new), and the output cap (plus fixed protocol flags)
Observable: The JSON body the mock xAI server receives has no content other than those three, apart from fixed protocol flags (such as turning streaming off) that carry no user or org information. Whether xAI's optional fields are used is left open as long as none carries identity or Salesforce data.
Source: choice: minimum necessary disclosure; the loosest rule that serves the user's privacy

### C-89: A request to xAI never carries the user's name, username, email, Salesforce ID, or the org's ID
Observable: Searching the request body and headers received by the mock xAI server for the sending user's name, username, email and 15- or 18-character Salesforce IDs, and for the org ID, finds nothing, unless the user typed it in their own message.
Source: implied: Pass 5 (must never: personal data leaves the org beyond what the user typed)

### C-90: Nothing from Salesforce records is sent to xAI except what the user typed in the conversation
Observable: A user viewing an Account record's page and then typing "hello" in the bot causes a request containing "hello" and the earlier conversation, and no field values from the Account or any other record.
Source: choice: the request does not say Grok should see CRM data; sending it silently would be a privacy surprise

### C-91: Grok's replies are text only; they cannot read or change any Salesforce record, setting, permission or file
Observable: A reply that says "delete all accounts" or contains what looks like a command or a link causes no change in the org; the bot has no mechanism to act on a reply.
Source: choice: the request asks for a conversational bot, not an agent; Pass 5 (must never: a model output changes data)

### C-92: Each request uses exactly the model name currently set by the administrator
Observable: With the setting "grok-4-fast" (or any valid name) the request body's model field is that exact string.
Source: implied: by C-74, C-77

### C-93: Error notices shown to users never contain the key, xAI's raw response text, a stack trace, an internal class or method name, another user's data, or the org's ID
Observable: Across every failure in C-49 to C-57, the notice text shown to the user contains none of these six things.
Source: implied: Pass 5 (must never: information leaked in errors)

### C-94: Every attempt that reaches the stage of calling xAI, and every Test connection, is recorded as one usage-log entry
Observable: After 3 successful Sends, 1 timeout and 1 Test connection, the usage log shows 5 new entries. Sends refused locally under C-60 and for blank or over-length text make no entry.
Source: choice: gives the operator observation (U-11) without filling a small-storage org with refusals

### C-95: A usage-log entry holds: time (stored in UTC), user, conversation (blank if later deleted), kind (chat or test), model, outcome, HTTP status (blank if none was received), prompt tokens and completion tokens as reported by xAI (blank if none), and latency in milliseconds
Observable: An entry for a successful send shows all nine of those values; an entry for a timeout shows blank HTTP status and blank token counts.
Source: implied: by U-11 (every field the operator needs to see cost, errors and who)

### C-96: A usage-log entry's outcome is exactly one of: Success, Cut off, Not set up, Key rejected, Rate limited, Timed out, xAI unavailable, Request rejected, No reply, Platform busy
Observable: Each entry shows one of these ten values: Success (reply received), Cut off (reply received but stopped at the length limit), Not set up (Test connection with no key only), Key rejected (C-49), Rate limited (C-50), Timed out (C-51), xAI unavailable (C-53), Request rejected (C-54), No reply (C-55), Platform busy (C-56). Storage-full refusals (C-57) make no entry. The exact labels are left open; the ten distinct meanings are required.
Source: implied: by U-11; a closed list so reports can group

### C-97: The usage log holds no message text and no key
Observable: No field of any usage-log entry contains the text of a user's message or of a reply, or any part of the key.
Source: implied: Pass 5; the log is visible to administrators who by C-45 are not entitled to read conversations

### C-98: Administrators can see and report on the usage log with standard Salesforce list views and reports; users who are not administrators cannot see it
Observable: A holder of the admin permission can open a list view of usage entries and build a report grouping by user, outcome and day; a holder of only the use permission cannot see any entries, including their own.
Source: implied: by U-11

### C-99: Deleting a conversation leaves its usage-log entries in place with the conversation reference cleared
Observable: After a user deletes a conversation that had 4 usage entries, the usage log still shows the 4 entries with a blank conversation.
Source: implied: by C-42 and C-71 (limits depend on the log, so deleting chat must not give a user their allowance back)

### C-100: Conversations whose last activity is older than the retention period are removed automatically, together with all their messages
Observable: With retention at the default 30 days, a conversation whose last message was 31 days ago is absent from its owner's history and has no stored messages after the next cleanup run; one whose last message was 29 days ago remains.
Source: implied: by U-12; the default is a choice (long enough to return to work, short enough for a small-storage org)

### C-101: A conversation's age for retention is the time of its latest message sent or received
Observable: A conversation created 60 days ago in which a message was sent 2 days ago is not removed at 30 days retention.
Source: implied: C-100 (the meaning of "older"); Pass 3 (cleanup meeting an active conversation)

### C-102: A conversation is removed whole or not at all by cleanup
Observable: After a cleanup that was interrupted (for example by a platform limit), no conversation exists with some of its messages missing.
Source: implied: Pass 3 (partial completion); Pass 5 (must never: data lost on the way)

### C-103: Usage-log entries older than the retention period are removed automatically
Observable: At 30 days retention, entries 31 days old are gone after the next cleanup, entries 29 days old remain.
Source: implied: by U-12; the log is state with an end

### C-104: Cleanup completes correctly when more than 10,000 records are due for removal, over as many runs or steps as needed
Observable: With 25,000 expired messages and 3,000 expired conversations, repeated cleanup (the same scheduled run or further runs) removes all of them without an error stopping it permanently and without leaving the next run unable to start. Reason: the platform allows at most 10,000 records changed by one transaction (the figure is believed current and is unconfirmed).
Source: implied: runtime rule

### C-105: A daily cleanup runs automatically once the administrator has turned the schedule on, and the Admin area shows whether it is on
Observable: With the schedule on, a cleanup runs once in every 24 hours (the time of day is left open); with it off, none runs on its own; the Admin area shows "on" or "off" truthfully. The schedule is not part of the deployable source and is turned on by the administrator after setup, because the platform keeps scheduled jobs outside deployments.
Source: implied: by U-12; runtime rule

### C-106: "Run cleanup now" runs the same cleanup immediately
Observable: Pressing it removes everything due per C-100 and C-103 and updates the last cleanup result of C-107.
Source: implied: by U-12 (operator control)

### C-107: The Admin area shows when the last cleanup ran, how many conversations and how many usage entries it removed, and whether it finished or failed
Observable: After a run that removed 7 conversations and 12 entries, the Admin area shows the run's time, the numbers 7 and 12, and "finished"; after a failed run it shows "failed".
Source: implied: by U-12 (observe)

### C-108: Lowering the retention setting applies at the next cleanup run, and raising it never brings removed data back
Observable: At retention 30, changing to 7 and running cleanup removes conversations idle for more than 7 days; changing back to 30 does not restore any.
Source: implied: Pass 3 (a setting changed while data exists)

### C-109: Redeploying the bot's source over an org that already has it, whether a newer or an older version, does not change stored settings, the stored key or any conversation, message or usage entry
Observable: After a redeploy, the Admin area shows the same setting values and "key stored", and the same conversations and usage entries are present.
Source: implied: by U-13 (carry on with existing data; go back to the previous version)

### C-110: Deploying the bot's source to a new Developer Edition, scratch or sandbox org needs only three manual steps: assign the permission sets, enter the key, turn the cleanup schedule on
Observable: After a deploy and those three steps, a first message sent in the chat view receives a reply; no code or metadata edits are needed, and nothing else (outbound-call registration, tabs, app, settings defaults) needs to be configured by hand.
Source: implied: by U-9, U-13; choice for the exact set of three steps

### C-111: All the bot's automated tests pass in an org with no key and no network access
Observable: Running every test of the bot in a freshly deployed org with no key stored reports zero failures and makes no real call to xAI (the platform does not allow real callouts in tests, so tests use stand-ins).
Source: implied: by U-13; runtime rule (test code cannot make callouts)

### C-112: The bot's automated tests cover at least 75% of its server-side code lines overall
Observable: The org's code-coverage report for the bot's server-side code is at least 75% overall. Reason: Salesforce requires at least 75% overall coverage, with all tests passing, to deploy to a production org; a development org does not enforce it, but the bot must be ready to ship.
Source: implied: runtime rule; by U-13

### C-113: Nothing of the bot's behaviour depends on data that already exists in the org
Observable: In a freshly created org with no records, every clause above holds; in an org with thousands of Accounts and Users, the bot behaves identically.
Source: implied: Pass 5 (the bot must work regardless of what the org holds); the bot reads and writes no standard object data

### C-114: A reply is shown only in the conversation it belongs to, even if the user has opened a different conversation while waiting
Observable: The user sends a message in conversation A, switches to conversation B before the reply arrives, and the reply arrives: B's transcript is unchanged; opening A later shows the reply under its message.
Source: implied: Pass 3 (one use arriving during another)

### C-115: Installing the bot changes nothing that exists in the org
Observable: After a deploy, no standard object, page layout, profile or existing permission set differs from before, and a user without the bot's permissions sees no difference in their org.
Source: implied: Pass 5 (what must not change)

### C-116: If a reply cannot be saved because the org has run out of storage, the reply is still shown to the user, with a notice that it was not saved
Observable: With storage full at the moment the reply arrives, the user sees the reply in the transcript with a notice that it will not be there after reloading; the message is not shown as failed.
Source: implied: Pass 3 (partial completion after the call was made and billed); choice: showing a reply already paid for is the loosest rule that serves the user

### C-117: A failure to write a usage-log entry never prevents the user from receiving their reply
Observable: With the usage log unwritable (for example storage full), a successful Grok reply still appears in the transcript.
Source: implied: Pass 3 (observation must not break the product)

### C-118: Pressing "Run cleanup now" while a cleanup is already running does not start a second one
Observable: The administrator is told a cleanup is already running; the last-cleanup counts of C-107 are not double-counted and no error occurs.
Source: implied: Pass 3 (two of the same job at once)

### C-119: Each message in a transcript displays its sender (the user or Grok), its text, its time and, for the user's own messages that are not answered, whether it is waiting or failed
Observable: A transcript row shows those four things; a user message that has been answered shows no waiting or failed marking.
Source: implied: by C-8, C-9, C-15, C-58 (the parts of a message, listed)

### C-120: Turning the bot off, or clearing or replacing the key, while a message is awaiting its reply does not disturb that message
Observable: A user's message is awaiting a reply when the administrator switches Enabled off; the reply, if it arrives, is shown and stored normally. Only messages sent after the change are subject to it.
Source: implied: Pass 3 (an operator action meeting a use in flight)
