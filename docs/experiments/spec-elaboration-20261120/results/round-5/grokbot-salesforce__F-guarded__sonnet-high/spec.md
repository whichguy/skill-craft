# Specification: Grok bot in a Salesforce development org

## Use cases

### U-1: A Salesforce user asks the Grok bot a question to get an answer from Grok
Flow: The user opens the Grok bot from the App Launcher, types a question in the message box, presses Send. A waiting indicator shows. The user's message appears in the transcript, then Grok's reply appears beneath it, labelled as coming from Grok.
Source: request

### U-2: A user follows up in the same conversation so Grok answers with the earlier exchange in mind
Flow: After a reply, the user types a second message that only makes sense given the first ("and what about the second one?") and sends it. Grok's answer takes the earlier messages into account. Both exchanges stay in the transcript in order.
Source: implied: a "bot" is a conversational thing; a conversation has memory of its own turns

### U-3: A user opens the bot for the first time, or starts a fresh conversation
Flow: First time: the screen shows an empty transcript, an empty message box and no past conversations. Later: the user presses New conversation; the transcript clears; the next message starts a new conversation with no memory of the old one.
Source: implied: the first-time and repeated-time edges of U-1

### U-4: A user comes back later and continues an earlier conversation
Flow: The user closes the browser, returns another day, opens the Grok bot, sees the list of their conversations, picks one, sees its whole transcript with times, and sends another message in it.
Source: implied: a bot living inside an org is used across sessions; losing the transcript on every page load would make U-2 useless in practice

### U-5: A user deletes a conversation they no longer want
Flow: The user selects Delete on a conversation, confirms in a confirmation step, and the conversation disappears from the list. Cancelling the confirmation deletes nothing.
Source: implied: stored conversations are the user's own data and storage in a development org is small

### U-6: A user sends a message the bot cannot accept
Flow: The user tries an empty or whitespace-only message (Send is unavailable), or a message longer than 4,000 characters (told it is too long, nothing sent, text kept in the box), or a message in a conversation that is full, or a 51st conversation (told what to do, text kept in the box).
Source: implied: every input has an empty case and a largest case

### U-7: A user hits a failure talking to Grok and recovers
Flow: The user sends a message; Grok's service is unreachable, slow, rate-limited, or rejects the bot's credentials. After at most 60 seconds the user sees a message saying what kind of problem it is (try again later vs. ask the administrator), their text is back in the message box, and nothing half-finished is in the transcript. They press Send again.
Source: implied: the "a thing it depends on failing" case of U-1; the bot depends on an external service

### U-8: A user opens the bot while it is switched off or not yet set up
Flow: The administrator has turned the bot off (or never entered the API key). The user can still open the screen and read old conversations; the message box is disabled and a notice says the bot is off; or, if just not set up, sending gives a message to contact the administrator.
Source: implied: the operator's "stop" and "start" work and the fresh-org state

### U-9: A person without access, or another user, tries to reach the bot or somebody else's conversation
Flow: A user who has not been given the bot's permission set does not see the app and is refused if they reach for it another way. A user with access never sees, opens, continues or deletes another user's conversation.
Source: implied: an org holds many users with different permissions; conversations are private text

### U-10: An administrator brings the bot up in a fresh development org
Flow: The administrator deploys the project to an empty Developer Edition (or scratch) org with the Salesforce CLI, enters the xAI API key in Setup, assigns the user permission set to themselves, opens the bot, sends a first message and gets a reply. If the key was mistyped, the first message instead reports a set-up problem and the call-log row shows the HTTP status Grok returned; the administrator corrects the key and tries again. A README lists these steps.
Source: request ("in a Salesforce development org")

### U-11: An administrator changes how the bot behaves
Flow: The administrator edits settings in the org (on/off, model, system prompt, maximum reply length) without deploying code. The next message sent by any user follows the new settings.
Source: implied: model names and prompts change; operators need to configure

### U-12: An administrator rotates or removes the API key
Flow: The administrator enters a new key in Setup; the next message uses it. Removing the key makes the bot report a set-up problem. The old key is never shown anywhere.
Source: implied: secrets are rotated, and the operator's "configure/recover" work

### U-13: An administrator checks what the bot is doing and why a call failed
Flow: The administrator opens the Grok call log in the org, sees one row per attempt with time, user, model, outcome, status, duration and token counts, filters to the failed ones and reads the short error summary.
Source: implied: the operator's "observe" work; calls to a paid external service need an audit trail

### U-14: An administrator redeploys a newer or older version without losing anything
Flow: The administrator deploys again on top of a working org (newer version, or an earlier commit to go back). Conversations, logs, settings and the API key are as they were.
Source: implied: the operator's "carry on with data that already exists, go back to the version before"

### U-15: A developer proves the project is fit to leave the development org
Flow: The developer runs all Apex tests in the org; they pass using a simulated Grok service, no test calls the real xAI API, and coverage is at or above what a production deployment demands.
Source: implied: platform rule for deploying beyond a development environment

### U-16: Several users and several browser tabs use the bot at the same time
Flow: Two users chat simultaneously and never see each other's text. One user with two tabs on the same conversation sends from both; neither message is lost and no reply is attached to the wrong message.
Source: implied: Pass 3, the pair "two sends at once"

### U-17: An administrator keeps the org's small storage from filling
Flow: A daily clean-up removes old call-log rows and long-idle conversations. If storage is nevertheless full when a user sends, the user is told and nothing is half-stored.
Source: implied: a development org has about 5 MB of data storage and every message is a record

### U-18: A user opens the chat screen and the platform fails to load their conversations
Flow: The screen opens, the list or a transcript cannot be loaded; the user sees an error and a Retry control, presses Retry, and sees their data.
Source: implied: a thing it depends on failing, applied to the read path rather than the send path

## Clauses

### C-1: The bot is Grok, the language model from xAI, reached through xAI's own HTTP API
Observable: Every answer the bot shows is produced by a call to https://api.x.ai/v1/chat/completions; no other model or vendor answers. The request's word "Grok" is read as xAI's Grok.
Source: choice: "Grok" names xAI's model and xAI's own API is its primary public interface; third-party resellers would add a second dependency nobody asked for

### C-2: A person with the user permission set finds and opens the bot from the App Launcher in Lightning Experience
Observable: After the permission set is assigned, typing "Grok" in the App Launcher search lists an app (or tab) whose name contains "Grok"; opening it shows the chat screen with a message box, a Send control, a New conversation control and the list of that user's conversations.
Source: request

### C-3: Sending a message shows the user's message and then Grok's reply, in that order, each labelled
Observable: After Send, the transcript shows the typed text under a label identifying the user's side and, once Grok answers, the answer directly beneath it under a label that contains "Grok". Each message shows the time it was sent.
Source: request

### C-4: Each press of Send causes exactly one request to Grok
Observable: With the xAI endpoint replaced by a recording stand-in, a single Send (including a double-click, or Enter pressed twice quickly) produces exactly one request; the call log gains exactly one row.
Source: implied: U-1; a repeated request would be a thing done twice that should happen once, and costs money

### C-5: While a request is in flight the screen shows a waiting indicator and refuses further sends, conversation switches and New conversation
Observable: Between pressing Send and the reply or error appearing, a waiting indicator is visible, Send is disabled, and the conversation list and New conversation control do not respond. They work again once the reply or error is shown.
Source: choice: keeps a late reply from landing in a conversation the user has already left

### C-6: The request carries the model, the messages and the maximum reply length, and the reply is read from the first choice
Observable: The request body is JSON (`Content-Type: application/json`) with `model` equal to the configured model identifier, the configured maximum reply length in the parameter xAI documents for it (`max_tokens` or `max_completion_tokens`; which is current is unconfirmed), `stream` false, and a `messages` array (C-7). The text shown as Grok's reply is the text content of the first choice of the response; any separate reasoning text the response carries is not shown.
Source: implied: U-1; the xAI chat-completions contract

### C-7: The messages array is the system prompt, then the conversation's most recent stored messages, then the new message
Observable: Element 0 has role `system` and the configured system prompt, and is absent when the system prompt is empty. Then come at most the 20 most recent stored messages of that conversation, oldest first, each with role `user` or `assistant` and its stored text. The last element has role `user` and the new message text. Messages older than the 20 are not sent but stay visible in the transcript.
Source: choice: 20 (ten exchanges) bounds cost and request size; the request is silent on memory depth

### C-8: The API key is sent to xAI as a bearer token and nowhere else
Observable: The request to api.x.ai carries the header `Authorization: Bearer <key>`. The key appears in no other request, response, page, record, log line, error message or file of the project.
Source: implied: xAI authenticates by bearer token; a secret used for a paid service must not leak

### C-9: Grok's reply is displayed as plain text, never as markup
Observable: If a reply contains `<script>alert(1)</script>` or `<b>x</b>` or a URL, the transcript shows those characters literally; nothing executes, nothing is bold, nothing becomes a link. Line breaks in the reply appear as line breaks.
Source: implied: model output is untrusted text; showing it as HTML would let it run script in a user's Salesforce session

### C-10: A reply appears all at once when complete, not progressively
Observable: The reply text appears in one step after the wait; partial text is never shown.
Source: choice: streaming is not requested and adds a long-lived connection; the loosest rule is that the user sees a complete reply

### C-11: A message that is empty or only whitespace cannot be sent
Observable: With nothing or only spaces/newlines in the box, Send is disabled and pressing Enter sends nothing; no request is made and no record is created. The same message presented directly to the server action is refused.
Source: implied: U-6 empty case

### C-12: A message may be at most 4,000 characters after leading and trailing whitespace is removed
Observable: A message of exactly 4,000 characters is accepted and sent. One of 4,001 is refused with a message saying the limit is 4,000 characters; nothing is sent to Grok, nothing is stored, and the typed text stays in the box. Characters are counted as the platform counts string length, so some emoji count as two.
Source: choice: the request gives no length; 4,000 keeps a request far below platform size caps

### C-13: The 4,000-character limit is enforced by the server as well as the page
Observable: A 4,001-character message sent straight to the server action (bypassing the page) is refused with the same outcome as in C-12.
Source: implied: a rule enforced in one path and not the other is a defect

### C-14: Leading and trailing whitespace is removed from a message; everything inside it is kept exactly
Observable: "  hello\n\nworld  " is stored and sent as "hello\n\nworld". Quotes, backslashes, newlines, accented letters, non-Latin script and emoji (for example `He said "hi" \ 日本語 😀`) appear in the transcript and in the request body exactly as typed.
Source: implied: U-1; users type arbitrary text

### C-15: The first message of a new conversation creates the conversation; there are no empty conversations
Observable: Opening the screen or pressing New conversation creates no record. The conversation appears in the list only after its first message has been answered.
Source: choice: avoids empty records filling small storage

### C-16: A conversation is labelled in the list by the first 80 characters of its first message
Observable: The list entry shows the first 80 characters of the first message (the whole message if shorter), with line breaks shown as spaces, and the time of its last message.
Source: choice: users need some way to tell conversations apart; 80 is a display size the request leaves open

### C-17: New conversation clears the screen and the next message has no memory of earlier conversations
Observable: After New conversation the transcript is empty; the next request's `messages` contains only the system prompt (if any) and the new message.
Source: implied: U-3

### C-18: Conversations persist across page loads, sessions and logins
Observable: After the user reloads the page, or logs out and in, the conversation list and every transcript are as they were, each message with its text, sender and time.
Source: implied: U-4

### C-19: Selecting a conversation shows its entire transcript in the order sent, and further messages continue it
Observable: The transcript lists all stored messages oldest first (including those older than the 20 sent as context). A message sent now becomes the next entry, and the request's `messages` is built per C-7 from that conversation.
Source: implied: U-4

### C-20: A conversation holds at most 100 messages; a send when it holds 100 is refused
Observable: With a conversation of exactly 100 stored messages, Send produces a message saying the conversation is full and a new one should be started; nothing is sent to Grok or stored; the text stays in the box. With 98 stored messages, a send succeeds and the conversation then holds 100.
Source: choice: bounds storage; 100 is five times the 20-message context window of C-7, so a conversation can run well past what Grok is shown before it is full

### C-21: A user may hold at most 50 conversations; the first message of a 51st is refused
Observable: With 50 conversations, sending the first message of a new one produces a message saying the limit is 50 and that one must be deleted first; nothing is sent to Grok or stored; the text stays in the box. Nothing is deleted automatically to make room.
Source: choice: bounds storage and list length without silently destroying user data

### C-22: Deleting a conversation asks for confirmation and then removes the conversation and all its messages
Observable: Delete shows a confirmation step. Confirming removes the entry from the list and every message of it; opening the screen again does not show it. Cancelling leaves everything. If the deleted conversation was open, the screen returns to the empty new-conversation state.
Source: implied: U-5

### C-23: Deleting a conversation is not blocked by, and does not remove, its call-log rows
Observable: After deleting a conversation that has log rows, the delete succeeds and the log rows still exist with an empty conversation reference.
Source: implied: logs are the administrator's record (C-45), independent of the user's choice to delete

### C-24: A turn is stored only after Grok has answered successfully, and then as a pair
Observable: After any failed or refused send the conversation contains neither the user's message nor a reply from that attempt. After a success it contains both. A stored user message is never without its reply, even if the browser was closed while waiting.
Source: implied: U-7; a half-stored turn would put two user messages in a row in the context sent to Grok and show a question with no answer

### C-25: After any failed send the user's text is back in the message box, unchanged
Observable: After any message that refuses or fails a send (every clause that says nothing is sent or stored) the message box holds exactly the text the user sent so they can send it again.
Source: implied: U-7; the user should not retype

### C-26: A Grok failure of the "set-up problem" kind tells the user to contact their administrator
Observable: When the key is missing or empty, or Grok answers HTTP 400, 401, 403 or 404, the error shown says the bot is not available because of a set-up problem and to contact an administrator. It does not say to try again later.
Source: implied: U-7; the user can do nothing about it, the administrator can

### C-27: A Grok failure of the "temporary" kind tells the user to try again later
Observable: When Grok answers HTTP 429, 500, 502, 503 or 504, when the connection cannot be made, or when there is no answer within 60 seconds, the error shown says the problem is temporary and to try again later. It does not mention the administrator.
Source: implied: U-7

### C-28: Any other Grok failure shows a generic failure message
Observable: Any other non-2xx status, an HTTP 2xx whose body is not valid JSON, a response with no choices, a first choice with no text, or a reply of only whitespace, shows a generic message saying the answer could not be obtained. The three messages of C-26, C-27 and C-28 are distinguishable from each other.
Source: implied: U-7; the list of statuses cannot be complete, so the remainder needs a rule

### C-29: The bot gives up waiting for Grok after 60 seconds
Observable: With a stand-in that never answers, the user sees the C-27 message no sooner than 60 and no later than 75 seconds after pressing Send; no reply from that attempt is ever shown or stored afterwards.
Source: choice: the platform allows at most 120 seconds for all callouts in one request (default per call is 10 seconds, too short for reasoning models); 60 leaves headroom

### C-30: The bot never retries a failed request to Grok by itself
Observable: A stand-in that answers 503 receives exactly one request per Send; the retry happens only when the user presses Send again.
Source: choice: automatic retries multiply cost and consume the 120-second request budget

### C-31: Error messages shown to users contain no secret and no internals
Observable: No error text shown to a user contains the API key, any part of Grok's response body, a stack trace, a record Id, or an HTTP header.
Source: implied: U-7 and C-8

### C-32: Replies cut short by the maximum reply length are shown with a note that they were cut short
Observable: When the first choice's finish reason is `length` and it has text, the text is shown and stored, with a visible note that the reply was cut off; the turn is a success. If a cut-off reply has no text it falls under C-28.
Source: choice: showing a truncated answer as if complete would mislead; the request is silent

### C-33: Settings are an on/off switch, the model identifier, the system prompt and the maximum reply length
Observable: An administrator can see and edit exactly these four values in the org without deploying code, in addition to the API key (C-38). Nothing else is configurable: not temperature, not the xAI address, not the timeout, not the context depth, not per-user quotas.
Source: choice: the dimension of operator controls is listed and everything left out is deliberately left out to avoid features the request does not ask for

### C-34: After the first deployment the settings hold working defaults
Observable: Without the administrator touching settings: the switch is on; the model identifier is a Grok chat model identifier that xAI documented as generally available at build time (the builder confirms the current identifier; unconfirmed here); the system prompt is non-empty text telling Grok it is an assistant inside Salesforce; the maximum reply length is 2,048 tokens.
Source: choice: a freshly deployed bot should work as soon as the key is entered; 2,048 leaves room for reasoning models that spend part of the limit before answering

### C-35: Settings values are validated when saved
Observable: Saving a blank model identifier, a system prompt over 4,000 characters, or a maximum reply length that is not a whole number from 64 to 8,192 is refused with a message naming the field; the previous value stays. An empty system prompt is accepted and means no system message is sent.
Source: choice: bounds; the 8,192 ceiling is the builder's to confirm against the chosen model's output limit (unconfirmed)

### C-36: A settings change applies to the next message sent after it is saved
Observable: Change the model identifier, send a message: the request body carries the new value. No deployment, restart or waiting time is needed. A request already in flight is unaffected (C-83).
Source: implied: U-11

### C-37: Only holders of the administrator permission set can see or change settings
Observable: A user with only the user permission set cannot open the settings screen, and cannot read or write the settings through the Salesforce API or a report.
Source: implied: U-9, U-11

### C-38: The API key is entered by an administrator in Setup, takes effect on the next message, and is never shown again
Observable: After deployment there is a documented place in Setup where an administrator types the key. After saving it, no screen, API response or deployment retrieval shows the key's value to anyone, including the administrator. Entering a new one replaces it; the next request carries the new key. The project's source files contain no key.
Source: implied: U-10, U-12; the platform does not allow a secret to travel in deployable metadata

### C-39: With the bot switched off, users can read and delete conversations but cannot send
Observable: The screen shows a notice that the bot is switched off; the message box and Send are disabled; no request to Grok is made. The list and transcripts remain readable and Delete still works.
Source: implied: U-8

### C-40: The server refuses a send while the switch is off, even from a page loaded earlier
Observable: A user who loaded the page while the bot was on and sends after it was switched off gets the C-39 notice; no request to Grok is made.
Source: implied: a rule enforced in one path and not the other is a defect

### C-41: A request already in flight when the bot is switched off completes normally
Observable: The reply, if it arrives, is shown and stored; the next send is refused.
Source: choice: cancelling a running callout is not possible and half-outcomes are worse

### C-42: An enabled bot without a key gives the C-26 message
Observable: With the key never entered, or removed, Send shows the set-up-problem message of C-26 and the log row records outcome SetupProblem (C-45).
Source: implied: U-8, U-12

### C-43: A user without the user permission set does not see the bot and is refused at the server
Observable: The App Launcher search for "Grok" lists nothing; opening the tab's address shows insufficient privileges; calling the bot's server actions as that user returns an authorization error, creates no record and sends nothing to Grok.
Source: implied: U-9

### C-44: The user permission set alone is enough to chat
Observable: A user given only the user permission set, with no other permission, can complete U-1 to U-5 with no further set-up.
Source: implied: U-10; the platform separately requires outbound-credential access for the running user, which the permission set must therefore carry

### C-45: Every attempt that reaches Grok writes one call-log row with these fields: time, user, conversation, model, outcome, HTTP status, duration, three token counts and an error summary
Observable: After a send that reached the point of calling Grok, one row exists holding: the time of the attempt; the user; the conversation the message was sent in (empty for a failed first message, which creates none, and after that conversation is deleted); the model identifier used; an outcome that is exactly one of Success, SetupProblem, TemporaryProblem, OtherFailure, SaveFailed (the spellings are free; the five meanings are fixed: C-26 kind, C-27 kind, C-28 kind, Grok replied but the turn could not be stored, and success); the HTTP status (empty when there was none); the duration in milliseconds; prompt, completion and total token counts as reported by Grok (empty when not reported); and an error summary of at most 255 characters (empty on success).
Source: implied: U-13

### C-46: Sends refused before Grok is called write no call-log row
Observable: Refusals under C-11, C-12, C-20, C-21, C-40, C-43, C-49, C-70 and C-72 leave the log unchanged.
Source: choice: the log is a record of calls to a paid service

### C-47: The call log never contains the API key, message text or reply text
Observable: Searching all fields of all log rows for the key, for a test message's text and for a reply's text finds nothing.
Source: implied: C-8; the transcripts are the user's private data and must not be copied into an administrator-wide table

### C-48: Only holders of the administrator permission set can see call-log rows
Observable: A user with only the user permission set cannot open the log screen and cannot read rows via the API or a report. An administrator can open the log and filter or sort by outcome.
Source: implied: U-13, U-9

### C-49: Conversations are visible only to their owner
Observable: In the bot's screens and server actions, a user sees, opens, continues and deletes only conversations they own. User B supplying the identifier of user A's conversation to any server action is refused with the same "not found" outcome as for an identifier that does not exist; no transcript text is revealed and nothing is sent to Grok. The administrator permission set does not widen this. (Holders of the platform's View All Data or Modify All Data permission keep the platform's own visibility, which the bot does not try to remove.)
Source: implied: U-9, U-16

### C-50: Messages sent to xAI contain only the system prompt, the conversation's included messages, the new message, the model and the maximum reply length
Observable: A recording stand-in sees no Salesforce record data, user name, email address, user Id, org Id or any other field beyond those listed.
Source: implied: users type into an org that holds customer data; the bot must not widen what leaves the org

### C-51: The screen tells users that what they type is processed by xAI's Grok service
Observable: A notice is visible on the chat screen at all times, saying that messages are sent to xAI's Grok service.
Source: choice: informed use of an external service; wording and placement are the builder's

### C-52: The only host the org contacts for the bot is api.x.ai, and only from the server side
Observable: A network recording of a full session shows the browser talking to Salesforce only; the org's outbound traffic for the bot goes only to api.x.ai.
Source: implied: C-8; a browser-side call would expose the key

### C-53: Nothing Grok says has any effect on Salesforce data
Observable: A reply telling the bot to "delete all accounts" or containing a link causes no change to any record and no further fetch; the bot reads no Salesforce record on a user's behalf.
Source: choice: the request asks for a chat bot; actions on org data would be a feature it does not cover

### C-54: A daily clean-up removes call-log rows older than 30 days and conversations idle for more than 90 days
Observable: After the job runs, no log row has an age over 30 days and no conversation has a last-message time more than 90 days old; a conversation with a message 89 days ago is untouched; deleting a conversation removes its messages (C-22).
Source: choice: bounds storage; 30 and 90 days are chosen figures the request leaves open

### C-55: The daily clean-up is started by one documented administrator step
Observable: The README gives the single step that schedules the clean-up; until it is taken nothing is purged. (The platform does not carry a scheduled job inside deployable metadata.)
Source: implied: runtime rule on scheduled jobs; C-54

### C-56: The bot is offered in Lightning Experience in a desktop browser only
Observable: The chat screen works in Lightning Experience in a current desktop browser. Salesforce Classic, the Salesforce mobile app, Experience Cloud sites and guest or external users are not supported; the README says so.
Source: choice: the request names no surface; a single supported surface is the loosest rule that serves a development org

### C-57: The bot needs no paid or optional Salesforce product and no installed package
Observable: Deployed to a Developer Edition org that has no Einstein, Agentforce or Data Cloud feature enabled and no managed package installed, the deployment succeeds and U-1 works.
Source: choice: "a Grok bot" is read as a self-contained chat bot, not an Agentforce agent; this avoids depending on features a given development org may lack

### C-58: The project deploys to an empty Developer Edition or scratch org with the Salesforce CLI and, with the key entered and the permission set assigned, nothing else is needed
Observable: On an org with no earlier version, one CLI deployment of the project succeeds with no error that stops it. Afterwards the only manual steps are those of C-62: enter the key, assign the permission set(s), and (optionally) schedule the clean-up. No one has to authorize api.x.ai separately in Setup; the deployment already contains that authorization.
Source: request ("in a Salesforce development org"); implied: U-10

### C-59: A repeat deployment onto a working org leaves existing conversations, messages, call-log rows, settings values and the API key as they were
Observable: With conversations, log rows, a changed system prompt and a key in place, deploying the same project again changes none of them; the next send works without re-entering anything.
Source: implied: U-14; operator "carry on with data that already exists"

### C-60: Going back to an earlier version is done by deploying the earlier version of the project, and keeps all data
Observable: Deploying an earlier commit over a newer one restores the earlier behaviour; no conversation, message, log row, setting value or key is deleted by it (the project contains no step that deletes stored data or the objects that hold it).
Source: implied: U-14; operator "go back to the version before"

### C-61: Deployment only adds to the org; it changes nothing that existed before
Observable: Retrieving an org's existing configuration (standard profiles, existing custom objects, existing permission sets, sharing settings, other apps) before and after deploying the project shows no difference except the added items.
Source: implied: Pass 5, what must not change; a bot must not alter an org it is placed in

### C-62: A README gives the operator's steps: deploy, enter key, assign the two permission sets, schedule the clean-up, send a first message and check the log, change settings, rotate the key, switch off, go back to an earlier version
Observable: The README in the project lists at least those steps (each in a few lines, each naming where in Setup or which command), and also lists the unsupported surfaces (C-56) and the limits of C-12, C-20, C-21 and C-54.
Source: implied: U-10, U-12, U-14, C-55

### C-63: All text the bot shows is in English
Observable: Labels, notices and error messages are in English for every user regardless of locale. Grok's replies are in whatever language Grok chooses.
Source: choice: the request names no language; translation is a feature it does not cover

### C-64: Message and conversation times are shown in the viewing user's own time zone and locale
Observable: A message sent at 14:00 UTC is shown at 14:00 to a user whose Salesforce time zone is UTC and at 09:00 to a user on UTC-5 (applying the platform's daylight-saving rules).
Source: implied: C-3, C-16; a time with no zone is ambiguous

### C-65: The chat can be operated from the keyboard
Observable: Focus can reach the message box, Send, New conversation, each conversation and each Delete by Tab. In the message box, Enter sends and Shift+Enter inserts a line break. The waiting indicator and error messages are announced to assistive technology.
Source: choice: standard chat conventions; a user relies on Enter sending

### C-66: If the conversation list or a transcript cannot be loaded, the user is told and can retry
Observable: When the server fails to return the list or a transcript, the screen shows an error message and a Retry control instead of an empty list; pressing Retry asks again. An empty list is never shown for a failed load.
Source: implied: U-18; an empty list on failure would suggest data loss

### C-67: A first-time user sees an empty list with a hint, and an enabled message box
Observable: A user who owns no conversations sees a list area saying there are no conversations yet, an empty transcript, and a message box that is ready to type in (when the bot is on).
Source: implied: U-3 first-time edge

### C-68: Two sends in the same conversation from two tabs both succeed or fail on their own and neither is lost
Observable: A user sends from tab A and, while it waits, from tab B (same conversation). After both finish, reloading shows every successful turn as an intact user-message-then-reply pair; no reply sits next to a different user message; a failed one is absent. The second request does not contain the first's reply as context if it was sent before that reply existed.
Source: implied: U-16; the pair "two sends at once"

### C-69: The limits of 100 messages and 50 conversations are checked again when a turn is stored, and never exceeded
Observable: With a conversation holding 98 messages, two sends from two tabs both reach Grok. One turn is stored (100 messages); the other is not stored, the user is shown the C-20 message, the text returns to the box, and the log row has outcome SaveFailed. The same holds for two simultaneous first messages that would make a user's 51st conversation (C-21).
Source: implied: U-16; a limit checked only before a long wait is not a limit

### C-70: Sending to a conversation that has been deleted, or no longer exists, is refused
Observable: Tab A deletes a conversation that tab B still shows. Sending from tab B shows a message that the conversation no longer exists; nothing is sent to Grok and nothing is stored; the text returns to the box; the screen can start a new conversation.
Source: implied: U-16; the pair "delete while send"

### C-71: If the turn cannot be stored after Grok has replied, the user is told it could not be saved and nothing of the turn is stored
Observable: When storing fails (for example the org's data storage is full), the user sees a message that the answer could not be saved and to try again later or contact the administrator; the transcript is unchanged; the text returns to the box; the log row has outcome SaveFailed. The reply that arrived is not shown as if stored.
Source: implied: U-17; Developer Edition data storage is small (about 5 MB, unconfirmed) and every message is a record

### C-72: Removing a user's permission set takes effect at their next action
Observable: After the user permission set is unassigned, the user's next press of Send, Delete or opening of a conversation is refused as in C-43, without logging out; nothing is sent to Grok.
Source: implied: U-9; the pair "access revoked while a session is open"

### C-73: A send reaches Grok before anything is written for it
Observable: A send with a reply succeeds and a send with a failure writes only its log row; no send ever fails with the platform's "uncommitted work pending" error.
Source: implied: runtime rule: the platform refuses a callout after a database write in the same transaction; C-24 therefore forces the turn to be stored after the reply

### C-74: When the platform refuses a send because too many long requests are running at once, the user sees the temporary-problem message
Observable: When more long-running synchronous requests are in progress in the org than the platform's concurrency limit (10 requests longer than 5 seconds each; the figure for development orgs is unconfirmed), the refused send shows the C-27 message, the text returns to the box, and nothing is stored. Because Grok is never called, no call-log row is required for it.
Source: implied: runtime rule on concurrent long-running requests; a 60-second wait (C-29) makes it reachable with a handful of users

### C-75: A response too large for the platform to hold is treated as a failure of the generic kind
Observable: A response exceeding the platform's callout size cap (6 MB for a synchronous request) shows the C-28 message; nothing is stored. With the limits of C-7 and C-35 the request itself stays well under the cap.
Source: implied: runtime rule on callout payload size

### C-76: Any unexpected platform error during a send shows the generic failure message and stores nothing
Observable: If the platform raises an error not covered above (for example a governor limit), the user sees the C-28 message, the text returns to the box, and the transcript is unchanged; the screen remains usable. If Grok had already been called, the log row has outcome OtherFailure.
Source: implied: Pass 4; no error may leave a half-stored turn (C-24)

### C-77: The project carries Apex tests that pass in a development org, use only a simulated Grok service and cover the platform's production minimum
Observable: Running all the project's Apex tests in the org reports no failures; no test sends a request to api.x.ai; overall Apex code coverage of the project is at least 75% (the platform's minimum for production deployment) and every class containing logic is at least 75%. The tests include: a successful send; a follow-up carrying context; each of C-26, C-27, C-28 and the timeout; the 4,000, 100 and 50 limits at and over the boundary; switch off; no permission; another user's conversation; and the call-log row's fields.
Source: implied: U-15; runtime rule: production deployments require passing tests and 75% coverage, and tests may not make real callouts

### C-78: The chat screen loads nothing from outside Salesforce
Observable: A network recording of opening the screen and sending a message shows no script, stylesheet, font, image or other request to any host other than the org's own Salesforce domains.
Source: implied: C-52; the platform's content security rules block outside hosts unless each is trusted

### C-79: Every refusal in this specification is enforced by the server, whatever the page does
Observable: Calling the server action directly, as the same user, with a request that the page would have blocked — empty message (C-11), over 4,000 characters (C-12), full conversation (C-20), 51st conversation (C-21), bot switched off (C-40), no permission (C-43, C-72), another user's or non-existent conversation (C-49, C-70) — gives the same refusal as through the page, with nothing sent to Grok and nothing stored.
Source: implied: Pass 5, "a rule enforced in one path and not another"

### C-80: The bot imposes no limit on how many messages a user may send per hour or per day
Observable: A user may send as many messages as the limits of C-20 and C-21 allow, as fast as each reply returns; the bot never refuses on rate. xAI's own limits show up as C-27 (HTTP 429).
Source: choice: a per-user rate limit is a feature the request does not ask for; stated so the omission is deliberate

### C-81: Simultaneous senders are independent
Observable: Users A and B send at the same moment; the stand-in answers "red" to A's request and "blue" to B's. A sees "red" only, B sees "blue" only; each reply is stored in its sender's own conversation.
Source: implied: U-16

### C-82: Nothing specific to one org is built into the project
Observable: Deploying the same project to a second, different org works after that org's own key is entered and its permission set assigned; no org Id, username, instance address or key was baked in.
Source: implied: runtime rule: what a production deployment demands; U-15

### C-83: A request already in flight is unaffected by a settings or key change
Observable: Change the model identifier or key while a request waits: that request completes with the values it started with; the next one uses the new values.
Source: implied: the pair "configuration change while a send runs"

### C-84: There are two permission sets, and what each grants is exactly this
Observable: The user permission set grants: opening the chat screen, and creating, reading and deleting the holder's own conversations and messages, and sending messages. It grants nothing on settings or the call log. The administrator permission set grants: reading and changing settings, and reading and deleting call-log rows. It grants no chat access and no access to other users' conversations; an administrator who also wants to chat is assigned both.
Source: implied: U-9, U-10, U-11, U-13; the dimension of what each role may do is listed so no role gets more than listed

### C-85: The chat screen tells users that conversations are deleted automatically after 90 days without a new message
Observable: A notice on the chat screen states the 90-day period of C-54.
Source: choice: data removed on a timer should not be a surprise; wording is the builder's

### C-86: When more than one refusal condition applies to a send, the user sees at least one of the applicable refusals and nothing is sent
Observable: A 4,001-character message sent while the bot is switched off is refused with the C-12 or the C-39 message; no request goes to Grok; nothing is stored. Which of the applicable messages appears is not specified.
Source: choice: the request cannot decide an order of checks, and the user relies only on being refused
