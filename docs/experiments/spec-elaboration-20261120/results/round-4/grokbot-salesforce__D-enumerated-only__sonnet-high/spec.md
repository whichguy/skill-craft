## Use cases

### U-1: An end user asks Grok a question in a new conversation, to get an answer without leaving Salesforce
Flow: The user opens the "Grok Bot" app in Lightning Experience and lands on its "Grok Bot" tab. They see an empty conversation, a notice that what they type is sent to xAI, a message box and a Send control. They type "What is a governor limit in Salesforce?" and press Send. Their message appears at once, a progress indicator shows, then Grok's reply appears as a separate message below theirs. The conversation now appears in their conversation list, titled from their first message.
Source: request

### U-2: An end user continues the same conversation, to ask a follow-up that depends on what was said before
Flow: In the conversation from U-1 the user types "Give me an example" and presses Send. The reply is about governor limits, because the earlier messages were supplied to Grok as context. Both new messages are added below the earlier ones.
Source: implied: a bot that answers one message with no memory of the previous one is not a usable chat

### U-3: An end user comes back later, to read, resume, start afresh or delete conversations
Flow: The user opens the tab and sees their conversations, most recently active first. They open one, read it oldest message to newest, and send another message in it. They press "New conversation" to start an empty one without losing the old ones. They delete one after confirming, and it is gone from the list.
Source: implied: a conversation that can only be seen while the page is open is not a bot a person can rely on; stored data needs a way to end

### U-4: An end user gives input the bot will not take, to learn what is wrong
Flow: The user tries to send an empty or whitespace-only message (the Send control does nothing), a message longer than 10,000 characters (they are told it is too long and nothing is sent), or a message in a conversation that is full (they are told to start a new conversation).
Source: implied: wrong input and limits reached (pass 1 unhappy paths)

### U-5: An end user's message fails because Grok or the network does not deliver, to recover without retyping
Flow: The user sends a message. The request to xAI times out, is rate limited, is rejected, or the service is down. They see that the message failed and whether trying again is worthwhile. Their message stays visible, marked as failed, and they can send it again without retyping.
Source: implied: a thing the bot depends on failing

### U-6: A user meets the bot when it cannot be used, to understand why
Flow: A user without the right permission cannot see the app and cannot reach the bot's actions. A user who can see it finds it switched off by an administrator, or not yet set up (no API key), and is told so instead of seeing an error dump.
Source: implied: the operator's work, and "who is allowed to see it"

### U-7: An administrator installs the bot in a Salesforce development org, to have a working Grok bot
Flow: The administrator deploys the project to an empty Developer Edition org, assigns the permission sets to themselves and to users, enters the xAI API key in Setup, schedules the nightly clean-up job, opens the app and gets a reply to a first message. A setup guide in the project lists these steps in order.
Source: request

### U-8: An administrator configures, rotates and switches off the bot, to control behaviour and spend
Flow: In Setup the administrator changes the model, system prompt and limits, replaces the API key, or switches the bot off, without deploying code. The next message sent uses the change.
Source: implied: the operator's work (configure, stop, rotate secret)

### U-9: An administrator observes the bot, to see failures and usage
Flow: The administrator opens a "Grok Bot Logs" tab, sees recent failures newest first with their category and HTTP status, and runs standard reports on token counts recorded per reply. They cannot read other users' conversation text through the bot.
Source: implied: the operator's work (observe)

### U-10: The org tidies itself, so a small development org does not fill up
Flow: A nightly job deletes conversations and log records older than the retention period. If saving fails because storage is full, the user is told their latest exchange was not saved.
Source: implied: a piece of state needs an end; Developer Edition has a small data allowance

### U-11: A developer redeploys, or goes back to the previous version, without losing data or settings
Flow: The developer deploys a newer or an earlier commit of the project to the same org. Existing conversations are still shown, and settings and the API key the administrator set are still in force.
Source: implied: the operator's work (carry on with existing data, go back to the version before)

### U-12: A user does two things at once, to find nothing lost or duplicated
Flow: The user double-clicks Send, opens the same conversation in two tabs and sends from both, or deletes a conversation while a reply is still on its way. Each send produces exactly one message and one request, and nothing is left half-saved.
Source: implied: pass 3, parts meeting

### U-13: A developer runs the tests, to know the bot works and may be shipped past development
Flow: The developer runs all Apex tests in the org. They pass without any call to the real xAI service, and overall coverage is at least 75%.
Source: implied: Salesforce requires tests and coverage before code can go to production; tests cannot call out

### U-14: Another user, or an administrator, tries to read someone's conversation, to find they cannot
Flow: A colleague with the same permission set looks for the user's conversations in the tab, in reports, in list views and in search, and finds none of them. An administrator with the Grok Bot Admin permission set finds the same.
Source: implied: conversations may hold confidential questions

## Clauses

### C-1: The bot has a Lightning app and tab where a person chats
Observable: In Lightning Experience in a desktop browser, a user holding the "Grok Bot User" permission set finds an app named "Grok Bot" in the App Launcher. Its tab named "Grok Bot" shows a conversation list, a transcript area, a message box and a Send control.
Source: request

### C-2: The chat component can be placed on other Lightning pages
Observable: In Lightning App Builder, a component named "Grok Bot" is offered for App pages, Home pages and Record pages and for the utility bar. Placed on any of them it offers the same chat as the tab.
Source: choice: the loosest placement that lets an org use the bot where people work

### C-3: The chat is offered only on the surfaces this list names
Observable: The surfaces are Lightning Experience in a desktop browser. It is deliberately not offered in Salesforce Classic, the Salesforce mobile app, Experience Cloud sites, Slack, Service Cloud Chat or Messaging, Agentforce or Einstein Bot, Flow, or Apex triggers and batch jobs. In each of these the org's own tools show no Grok Bot component, action or entry point. Reason for leaving them out: each needs its own access, callout and data rules that the request does not ask for.
Source: choice: keeps the first version to one surface that can be fully specified

### C-4: A user without a Grok Bot permission set cannot see the bot
Observable: A user holding neither "Grok Bot User" nor "Grok Bot Admin" finds no "Grok Bot" app in the App Launcher, and opening the tab's address shows Salesforce's insufficient-privileges message.
Source: implied: U-6, "someone is allowed to see it"

### C-5: The refusal for a user without permission holds on the server, not only in the page
Observable: When a user without the "Grok Bot User" permission set causes any of the bot's server-side actions to run (send a message, list conversations, open one, delete one), the action fails with an insufficient-access error, no request goes to xAI and no record is created or changed.
Source: implied: pass 5, a rule enforced in one path and not another

### C-6: Two permission sets exist and each grants a stated set of things
Observable: "Grok Bot User" grants: the app and tab, the chat component's actions, create/read/delete on Conversation (own records), create/read on Message (own records). It grants none of: Settings, Log, edit of Message. "Grok Bot Admin" grants: edit of the Grok Bot settings, read and delete of Log records, the "Grok Bot Logs" tab. It does not include the User grants, so an administrator who also chats holds both sets. Neither set grants access to anyone else's Conversation or Message.
Source: choice: separating chatting from administering is the loosest split that stops users changing settings

### C-7: Only a conversation's owner can read it
Observable: A user's Conversation and Message records are returned to that user and to no one else in the tab, list views, reports, search, SOQL and the API. The one exception is a user whose profile or permission set holds the platform's View All Data or Modify All Data permission, who sees them by that platform rule.
Source: implied: U-14, pass 5 (someone seeing what they may not see)

### C-8: Sending the first message creates the conversation
Observable: In a new, empty conversation the user types "What is a governor limit in Salesforce?" and presses Send. One Conversation record owned by that user exists afterwards, holding that message as its first message.
Source: request

### C-9: Merely opening the tab creates no record
Observable: Opening the tab, pressing "New conversation" or reloading the page any number of times, without sending, leaves the count of the user's Conversation records unchanged.
Source: implied: pass 5 (data created that should not exist), small data allowance

### C-10: A new conversation's title comes from its first message
Observable: The conversation's title is never blank, is at most 80 characters, and is taken from the first message's text. For "What is a governor limit in Salesforce?" the title is that whole sentence.
Source: choice: the loosest rule that lets a person tell conversations apart; how longer text is shortened is left open

### C-11: Pressing Send shows the user's message immediately, then a progress indicator
Observable: After pressing Send, the user's message is visible in the transcript without waiting for Grok, and a progress indicator shows until the reply or an error appears.
Source: implied: U-1; a reply can take many seconds

### C-12: The reply arrives whole, not word by word
Observable: Grok's reply appears in the transcript in one piece once complete. Reason: Apex cannot stream a response from a callout to the browser.
Source: implied: runtime rule (Apex callout returns only a complete response)

### C-13: Every message is labelled as the user's or Grok's
Observable: Each message in the transcript carries a label that says whether it is from the user or from Grok. The two labels differ.
Source: implied: U-1 ("a separate message")

### C-14: Each message shows when it was sent
Observable: Each message shows its date and time in the viewer's own Salesforce time zone.
Source: choice: lets a returning user tell when things happened; format left open

### C-15: One send makes exactly one request to xAI
Observable: Each send that is accepted (not refused under C-5, C-28, C-29, C-30, C-32, C-60 or C-83) causes exactly one HTTP request to xAI, with no automatic retry on failure; the one exception is that no request is made when no API key is set (C-61). A second request is made only when the user presses Send or the retry control again.
Source: choice: one call a send keeps cost predictable and stays far below the platform's limit of 100 callouts per transaction

### C-16: The request goes to xAI's chat-completions endpoint
Observable: The request is a POST to https://api.x.ai/v1/chat/completions, with JSON body and the API key sent as a bearer token, non-streaming. (The endpoint is xAI's public one; check it against xAI's current documentation before shipping.)
Source: request: "Grok" is xAI's model, reached through xAI's API; the address is a fact about the world

### C-17: The only host the bot contacts is api.x.ai
Observable: With all outbound traffic from the org observed, every request the bot makes goes to api.x.ai over HTTPS, and no other host is contacted.
Source: implied: pass 5; Salesforce permits callouts only to endpoints an administrator has authorised

### C-18: The request body carries these parts and no others
Observable: The body holds: the model name from settings; the system prompt from settings as the first message with role "system"; the prior messages that fall within the context window (C-19) as "user" or "assistant" messages, oldest first; the new message as the last "user" message; the maximum output tokens from settings; streaming turned off. Nothing else about the user, the org or any Salesforce record is in it.
Source: implied: U-2; pass 5 (data sent that the user did not choose to send)

### C-19: Grok is given the last N prior messages as context
Observable: The prior messages supplied are the most recent N messages of the conversation that have status "Sent" (N is the "History messages" setting, default 20), oldest first, not counting the new message or the system prompt. In a conversation of 30 sent messages, the request holds the system prompt, the latest 20 of them, then the new message.
Source: choice: bounds request size and cost; keeps the request far under Apex's 6 MB synchronous heap

### C-20: Messages that failed or are still pending are not given to Grok as context
Observable: A message with status "Failed" or "Pending" is absent from the request body of every later send in that conversation.
Source: implied: pass 3, partial completion (a failed question has no answer and would confuse the next one)

### C-21: The user is told when the earlier part of a conversation is no longer in Grok's context
Observable: In a conversation holding more than N sent messages, the transcript shows a notice that earlier messages are not included in what Grok sees; the full history still shows in the transcript. In a conversation with N or fewer it shows no such notice.
Source: choice: a person relies on knowing why the bot has "forgotten" something

### C-22: No Salesforce identity is sent to xAI
Observable: The captured request body and headers (other than the bearer key) contain none of the user's Salesforce Id, username, email address, name, or the org's Id or name. The OpenAI-style "user" field is absent.
Source: choice: the loosest rule that protects people from having their identity attached to what they type

### C-23: No record data is read or sent unless the user types it
Observable: On an Account page showing an account named "Acme Industrial", the user asks "What account is this?". The request body holds none of that page's record fields. The bot reads no Salesforce business record to build a request.
Source: choice: first version sends only what a person types; the request is silent on record context

### C-24: Users are told that their messages go to xAI
Observable: A notice that messages are sent to xAI (an outside service) is visible in the chat whenever the message box is, in every state, including a conversation just opened and a conversation with failed messages.
Source: implied: pass 5; people should know confidential text leaves Salesforce

### C-25: Grok's reply is shown as plain text and cannot run code
Observable: A reply containing `<script>alert(1)</script>` and `<img src=x onerror=alert(1)>` displays those characters literally, and no alert appears. Line breaks and runs of spaces in the reply (for example, indented code) are preserved.
Source: implied: pass 5 (a model's output is untrusted; script injection)

### C-26: Grok's output never causes an action
Observable: Nothing in a reply creates, changes or deletes any Salesforce record other than the conversation's own Message records, makes a request to any host, or alters any setting. The bot gives Grok no tools and no way to act.
Source: implied: pass 5 (must never happen)

### C-27: Text outside plain English survives unchanged
Observable: Sending "こんにちは 👋 café" displays it unchanged in the transcript, shows it unchanged when the conversation is reopened later, and passes it unchanged to xAI.
Source: implied: pass 2 (a text field must hold what people type)

### C-28: An empty or whitespace-only message cannot be sent
Observable: With the message box empty, or holding only spaces, tabs or line breaks, pressing Send sends nothing, creates no record, and starts no request.
Source: implied: U-4

### C-29: Messages longer than 10,000 characters are refused
Observable: The maximum message length is 10,000 characters (the "Max input characters" setting, default 10,000). A message of 10,000 characters is accepted. One of 10,001 is refused with an error that states the limit; nothing is saved and no request is made. The message box shows how many characters are used out of the limit.
Source: choice: bounds cost and storage; stays well under a Long Text Area field's 131,072-character maximum

### C-30: The length limit is enforced on the server as well as in the page
Observable: A message of 10,001 characters that reaches the server by any path is refused with the same error, no request goes to xAI and no record is created.
Source: implied: pass 5 (a rule enforced in one path and not another)

### C-31: The Send control is unavailable while a reply is pending in that conversation
Observable: From the moment the user presses Send until the reply or error appears, the Send control for that conversation is disabled, so double-clicking it produces one message, one record and one request.
Source: implied: U-12

### C-32: A conversation holds at most 200 messages
Observable: A send is accepted only if the conversation holds 198 or fewer messages (all statuses counted), so a user message and its reply fit within 200. At 199 or 200 messages the user is told to start a new conversation, nothing is saved and no request is made. Concurrent sends from two windows may push a conversation past 200 by at most one message pair per concurrent send; that is accepted.
Source: choice: bounds the cost of loading a conversation and the storage of a small org

### C-33: Replies cut short by the output limit are marked
Observable: When xAI reports that the reply stopped because it reached the token limit (finish reason "length"), the reply is saved and shown with a note that it was cut off at the limit. A reply that ended normally (finish reason "stop") shows no such note, and a reply with non-empty text and any other finish reason is shown and saved without one.
Source: implied: pass 2 (a maximum output setting means some replies end early)

### C-34: A reply with no text is a failure
Observable: A response from xAI that has a success status but no choice, or an empty or missing reply text, is treated as a failure in category "Unexpected response" (C-40) and no reply message is saved.
Source: implied: pass 2 (what the bot does when the answer is absent)

### C-35: Each failure falls in exactly one category, and every outcome is covered
Observable: Every outcome that is not a usable reply falls in exactly one of these categories: "Configuration" (the key is missing, the xAI endpoint is not authorised for the org, or HTTP 404, which means the model name is unknown to xAI); "Authentication" (HTTP 401 or 403, including a key that has been revoked or an account out of credit); "Rate limit" (HTTP 429); "Rejected request" (HTTP 400, 413 or 422); "Provider error" (any HTTP 5xx, or no response because of a network failure that is not a timeout, such as a refused connection, a failed name lookup or a failed TLS handshake); "Timeout" (no response within the timeout setting); "Unexpected response" (a success status with an unusable body per C-34, a body that is not valid JSON, any other HTTP status, including 3xx and other 4xx); "Platform busy" (the platform refused to run the request because the org had too many long-running requests); "Internal error" (any other unexpected error in the bot's own code).
Source: implied: U-5, pass 4; no outcome may be left to guess

### C-36: A failure tells the user whether trying again is worthwhile, and shows no technical detail
Observable: For "Rate limit", "Provider error", "Timeout" and "Platform busy" the user sees a message that says the request failed and that trying again later may work. For "Configuration", "Authentication", "Rejected request", "Unexpected response" and "Internal error" the message says the request failed and that they should contact their administrator. No message shows xAI's own error text, the API key, an HTTP body, a stack trace or an Apex exception name.
Source: implied: U-5, pass 5 (secrets and internals shown to a user)

### C-37: A failed message stays and can be resent without retyping
Observable: After a failure the user's text is still shown in the transcript, marked "Failed" with the reason's category, and a retry control on it sends the same text again as a new send, which then follows C-15. The failed message is kept; a successful retry adds a new message and reply.
Source: implied: U-5

### C-38: A send that fails still records the user's message
Observable: After any failure in C-35, including a closed browser tab, the conversation holds the user's message with status "Failed" (or "Pending", see C-39), never a reply with no question, and never a question that vanished. Reason: Salesforce forbids a callout after uncommitted database changes in the same transaction, so the user's message is saved in one step and the request to xAI made in the next.
Source: implied: runtime rule (callout cannot follow uncommitted DML), pass 3 (partial completion)

### C-39: A message with no outcome after 5 minutes is shown as failed
Observable: A user message still "Pending" 5 minutes after it was created (for example the server stopped mid-request) shows as "Failed" with the category "Internal error" when the conversation is opened, and counts as failed for C-20.
Source: choice: gives pending state an end; 5 minutes is well beyond the 120-second maximum callout wait

### C-40: A request waits no longer than the timeout setting
Observable: The timeout setting is whole seconds from 5 to 120 and defaults to 100. With xAI made to answer after a longer delay, the user sees the "Timeout" failure within the timeout plus 15 seconds of pressing Send. The upper bound is Salesforce's maximum of 120 seconds for one callout; its default of 10 seconds would cut off ordinary Grok replies.
Source: implied: runtime rule (callout timeout default 10 s, maximum 120 s); the default of 100 is a choice

### C-41: Too many long-running requests shows a busy message
Observable: When Salesforce refuses a send because the org already has its permitted number of requests running longer than 5 seconds at once (10 for the org; the exact figure for a Developer Edition org is unconfirmed), the page shows the "Platform busy" message from C-36 and shows the user's message as failed with the retry control (C-37), so it can be resent without retyping. The platform refuses the request before any bot code runs, so no Log record is written for it, and the stored status of the message is set to "Failed" by the page's next action or, if that does not happen, by C-39.
Source: implied: runtime rule (concurrent long-running request limit), pass 4

### C-42: A reply that could not be saved is still shown, with a notice
Observable: If xAI answered but saving the reply fails (for example data storage is full; a Developer Edition org's data storage is 5 MB, unconfirmed for any given org), the reply is still shown in the current view with a notice that this exchange was not saved and will be gone after reload, and the user's message is stored as "Failed" with category "Internal error", which is also written to the Log (C-43).
Source: implied: pass 3 (partial completion), pass 4 (storage cap)

### C-43: A failed send writes one log record, except where listed
Observable: Each failure in C-35 other than "Platform busy" writes exactly one Log record. Also not logged: a refusal for no permission (C-5), an input refusal (C-28, C-29, C-30, C-32), and a send while the bot is switched off (C-60).
Source: implied: U-9

### C-44: A Log record holds these fields and no others of its own
Observable: Occurred At (date-time), User (who sent), Conversation (may be empty once the conversation is deleted), Category (one of C-35's nine; "Platform busy" never appears, see C-41), HTTP Status (empty when there was no response), Provider Error Code (xAI's short error code if any, at most 100 characters, otherwise empty), Elapsed Milliseconds (time the request took), Model (the model name used).
Source: choice: enough to diagnose without keeping conversation text

### C-45: Logs never contain message content or the key
Observable: No Log record, and no debug-log line written by the bot's own code, contains any user message text, any reply text, xAI's free-text error message or the API key. (Salesforce's own debug-log output of callout bodies at FINER and finer levels is the platform's and is outside this.)
Source: implied: pass 5 (confidential text leaking into places many people can read)

### C-46: An administrator can list failures newest first
Observable: A user holding "Grok Bot Admin" opens the "Grok Bot Logs" tab and sees Log records newest first, with at least Occurred At, User, Category, HTTP Status and Model shown, and can filter them by Category.
Source: implied: U-9

### C-47: Each stored reply records its usage
Observable: Each reply Message holds the prompt token count and the completion token count that xAI reported (empty if xAI sent none), the model name used, and xAI's finish reason, so that a standard Salesforce report can total tokens by user and by day.
Source: implied: U-9 (spend observation)

### C-48: A Conversation record holds these fields
Observable: Title (up to 80 characters), Owner (the user who created it), Last Activity (date-time of the latest send in it), and Salesforce's own created and modified stamps. It holds nothing else of its own.
Source: choice: the smallest set that serves C-10, C-51 and C-52

### C-49: A Message record holds these fields
Observable: Conversation, Role ("User" or "Assistant"), Content (long text, up to 131,072 characters), Status ("Pending", "Sent" or "Failed"), Failure Category (one of C-35's nine, or empty), Model, Prompt Tokens, Completion Tokens, Finish Reason, and Salesforce's own created stamp. A reply from Grok has Role "Assistant" and Status "Sent". It holds nothing else of its own.
Source: choice: the smallest set that serves C-19, C-20, C-33, C-37 and C-47

### C-50: A user cannot edit or delete a single message
Observable: A user holding "Grok Bot User" who tries to edit a Message's Content or delete one Message in the standard UI, a report, or the API is refused. A message disappears only when its whole conversation is deleted by the user (C-57) or purged (C-62).
Source: implied: pass 5 (history that can be altered after the fact is not trustworthy)

### C-51: Opening the tab lists the user's own conversations, most recently active first
Observable: Each entry shows the title and its last activity date and time. A user with 3 conversations sees exactly those 3, the one most recently sent in first.
Source: implied: U-3

### C-52: A sent message moves its conversation to the top of the list
Observable: After the user sends in an older conversation, that conversation is first in the list and its Last Activity is the time of that send, whether or not the send then succeeds.
Source: implied: U-3; pass 3 (the purge in C-62 relies on it)

### C-53: The list shows 50 conversations at a time, and all can be reached
Observable: A user with 120 conversations first sees the 50 most recent and a control that loads the next 50, repeated until all 120 have been shown.
Source: choice: page size 50 is a choice; the need is that every conversation is reachable

### C-54: A user with no conversations sees an empty state
Observable: A user with no conversations sees a message saying they have none yet, an empty transcript, and a working message box.
Source: implied: pass 1 (the first time, the empty case)

### C-55: Opening a conversation shows every message, oldest first
Observable: Opening a conversation with 6 stored messages shows all 6, in the order sent, including messages marked "Failed". Where two messages were stored at the same moment, the user's message comes before the reply to it.
Source: implied: U-3

### C-56: "New conversation" starts an empty one and keeps the others
Observable: Pressing it shows an empty transcript with the message box ready, and the previous conversation is still in the list unchanged.
Source: implied: U-3

### C-57: Deleting a conversation asks first, then removes it and its messages for good
Observable: Pressing delete shows a confirmation. Confirming removes the conversation from the list and deletes its Conversation record and all of its Message records, which then do not appear in the Recycle Bin. Cancelling changes nothing. Log records that name the conversation stay, with the conversation field empty.
Source: implied: U-3; choice: asking first because the deletion is permanent

### C-58: Deleting a conversation while a reply is pending discards the reply
Observable: If the user deletes a conversation while a request in it is in flight, then when xAI answers no Message record is created, no orphan record is left, and the user is told the conversation was deleted. The request already sent to xAI is not recalled.
Source: implied: U-12, pass 3 (one undone while the other runs)

### C-59: The same conversation open in two windows loses nothing
Observable: With one conversation open in two windows and a message sent from each, both are accepted, each produces its own reply, and reloading either window shows both exchanges, stored in the order the server accepted them. A window does not update by itself when the other one sends; it shows the new messages after the conversation is reopened or the page is reloaded.
Source: implied: U-12, pass 3 (two at once); choice: no live sync

### C-60: When the bot is switched off, users can read but not send
Observable: With the "Enabled" setting off, the chat shows a notice that the bot is switched off. The Send and retry controls do nothing, no request goes to xAI, and no record is created. Existing conversations can still be opened and deleted. A send already in flight when the setting is switched off completes normally.
Source: implied: U-6, U-8 (stop)

### C-61: Before a key is set, the bot says it is not set up
Observable: In an org where no API key has been entered (for example just deployed, or moved to another org or a refreshed sandbox, since secrets do not travel with a deployment), a send shows the "Configuration" failure message from C-36, makes no request to xAI, and writes a Log record with category "Configuration".
Source: implied: U-6, U-11; runtime rule (credential secrets are not carried by metadata deployment)

### C-62: A nightly job removes expired conversations and logs
Observable: A job named "Grok Bot Purge", scheduled to run once a day between 01:00 and 05:00 in the time zone of the administrator who scheduled it, deletes every Conversation (with its Messages) whose Last Activity is older than the retention period and every Log record whose Occurred At is older than it. The retention period is the "Retention days" setting, default 30. A conversation whose Last Activity is within the period is never deleted by it. Purged records do not appear in the Recycle Bin.
Source: implied: U-10; the period and the time of day are choices

### C-63: The purge copes with more records than one transaction can delete
Observable: With 25,000 expired Message records (spread over 150 expired conversations), one night's run of the purge deletes all of them and the job ends with no error. Reason: Apex permits 10,000 DML rows in one transaction, so the deletion has to be split across several transactions.
Source: implied: runtime rule (DML row limit of 10,000 per transaction)

### C-64: The settings an administrator controls are exactly these nine
Observable: Enabled; API key; Model; System prompt; Max output tokens; History messages; Max input characters; Timeout seconds; Retention days. There is no per-user quota, no per-day message cap and no allow-list of users beyond the permission sets. These are left out deliberately: xAI's own spend limits, the Enabled switch and permission-set assignment already cap cost, and a quota counted from Conversation records could be avoided by deleting the conversations. There is also no control to run the purge on demand; it runs on its schedule.
Source: implied: U-8; choice: the omissions

### C-65: Each setting has a default
Observable: On a fresh deployment, Enabled is on; Model is "grok-4" (xAI's model names change; confirm it is current before shipping, and the administrator can change it); Max output tokens is 2048; History messages is 20; Max input characters is 10,000; Timeout seconds is 100; Retention days is 30; the System prompt is a non-empty text that tells Grok it is an assistant answering a Salesforce user's questions; the API key is empty.
Source: choice: working values so the first reply needs only the key

### C-66: A setting outside its allowed range is refused
Observable: Saving a value outside these ranges shows an error naming the setting and the range, and keeps the previous value: Max output tokens 1 to 8,192; History messages 1 to 30; Max input characters 1 to 20,000; Timeout seconds 5 to 120; Retention days 1 to 365; Model not blank; System prompt not blank and at most 10,000 characters. With History messages at its top of 30 and the other maxima, a request body is under about 1,000,000 characters and a reply under about 35,000, which is meant to fit Apex's 6 MB synchronous heap (that fit is unconfirmed and must be tested at the maxima).
Source: choice: values; implied: runtime rule (6 MB synchronous heap, 120 s callout maximum)

### C-67: Settings are edited in Setup by an administrator, with no code deployment
Observable: A user holding "Grok Bot Admin" changes any setting in Salesforce Setup, and no deployment is involved. A user without that permission set cannot change any of them.
Source: implied: U-8, pass 2 ("someone is allowed to")

### C-68: A settings change applies to the next send, not to one in flight
Observable: After a change is saved, the next message sent follows it (a new Model appears in that request's body, a new History messages count changes what context is sent). A request already in flight finishes under the values it started with.
Source: implied: pass 3 (one arriving during the other)

### C-69: The API key is held where nobody can read it back
Observable: After the key is saved, no screen, report, API response or log shows it again (Setup shows it masked or empty). It is not in the browser's traffic, in any Salesforce record the bot owns, or in the project's source files.
Source: implied: pass 5; Salesforce credential secrets are write-only

### C-70: Replacing the key takes effect on the next send
Observable: After the administrator saves a new key, the next send uses the new key and an old, revoked key is never sent again. A send already in flight finishes with the key it started with.
Source: implied: U-8, pass 3

### C-71: The messages' text is never sent from the browser to xAI
Observable: In the browser's network traffic during a chat, no request goes to api.x.ai; all of them go to Salesforce. Reason: the key must stay on the server.
Source: implied: pass 5 (the key must not reach the browser)

### C-72: The project deploys to an empty Developer Edition org
Observable: In a source-format Salesforce DX project, `sf project deploy start` against a newly created Developer Edition org finishes with status Succeeded, and the org then holds everything the other clauses name: the app, the tabs, the component, the Conversation, Message and Log objects, the two permission sets, the settings and a place to enter the API key.
Source: request: "in a Salesforce development org"

### C-73: A setup guide lists the steps after deployment, in order
Observable: The project's setup guide lists: (1) assign "Grok Bot User" and "Grok Bot Admin" to the administrator, (2) enter the xAI API key in Setup, (3) schedule "Grok Bot Purge", (4) open the app and send a first message. An administrator who does only these steps gets a reply to "Hello" within the timeout.
Source: implied: U-7, C-61, C-62: they are steps a deployment cannot do

### C-74: Redeploying does not reset what an administrator set
Observable: After a redeploy of the project (any commit), the settings values the administrator saved and the API key are still in force, and the "Grok Bot Purge" schedule still exists.
Source: implied: U-11, pass 3

### C-75: Redeploying keeps all stored conversations and shows them correctly
Observable: Conversations and messages created by an earlier deployed version are listed and shown correctly by the current one, including those lacking fields added later (such fields are simply empty), and a redeploy deletes none of them. Later versions only add fields, never remove or repurpose one.
Source: implied: U-11 (carry on with data that exists, go back to the version before); choice: additive changes only

### C-76: Going back to an earlier commit works
Observable: Deploying an earlier commit over the current one finishes without error, and the chat still opens, lists and sends.
Source: implied: U-11

### C-77: The tests run without calling xAI
Observable: Running all Apex tests in the org passes every test, and no test makes a real request to xAI. Reason: Salesforce does not allow real callouts in tests, so responses are simulated.
Source: implied: runtime rule (no callouts in tests); U-13

### C-78: The tests cover each failure category and each limit
Observable: There is at least one passing test for a usable reply and for each of the eight categories in C-35 other than "Platform busy" (which the platform raises before any bot code runs and a test cannot produce), for the three input refusals (empty, 10,001 characters, conversation at 199 messages), for a message count within the context window, for the disabled state and for the purge.
Source: implied: U-13

### C-79: Coverage meets the figure Salesforce demands for production
Observable: The org's overall Apex code coverage is at least 75% after the tests run. Salesforce requires that figure to deploy code to production; a development org does not enforce it.
Source: implied: runtime rule (75% coverage for production deployment)

### C-80: Moving to another org needs the key entered again and nothing else secret
Observable: After deploying to a sandbox or production org, the bot works once the administrator enters the key (C-61 describes what users see until then). No secret is carried by the deployment itself.
Source: implied: runtime rule (credential secrets not deployable); the demands of shipping beyond development

### C-81: The chat can be used from the keyboard and announces results
Observable: The message box, Send, retry, New conversation, delete and its confirmation, the list entries and "load more" can each be reached and operated with the keyboard alone. A screen reader announces the arrival of a reply and of an error without the user moving focus.
Source: choice: accessibility basics the platform's own components give; the request is silent

### C-82: A successful exchange leaves both messages "Sent"
Observable: From the moment the user's message is saved until the outcome is known it has status "Pending". When Grok's reply has been saved, the user's message and the reply both have status "Sent". The user's message is changed to "Failed" only under C-35's failures, C-39, C-41 and C-42.
Source: implied: C-19 and C-20 depend on the status; pass 3 (partial completion)

### C-83: If the user's message cannot be saved, nothing is sent
Observable: When saving the user's message fails (for example data storage is full), the user is told the message was not sent, no request goes to xAI, and no Message record is left behind. The user's text stays available to resend. A Log record with category "Internal error" is written if the Log can itself be saved.
Source: implied: pass 3 (partial completion); runtime rule (database writes can fail on a full org)

### C-84: A conversation that no longer exists is reported, not silently recreated
Observable: If a conversation was deleted in another window or purged, then opening it, or sending in it, shows a message that it no longer exists and refreshes the list. No request goes to xAI, no new conversation is created and no record is created.
Source: implied: pass 3 (one undone while the other runs)

### C-85: Leaving a conversation while a reply is pending does not lose the reply
Observable: The user sends in conversation A, then opens conversation B (or presses "New conversation") before the reply arrives. The reply is saved in A, and when A is next opened the reply is there. Sending in B or in the new conversation is not blocked by A's pending reply.
Source: implied: U-12, pass 3

### C-86: Redeploying works while the purge job is scheduled
Observable: With "Grok Bot Purge" scheduled, a redeploy of the project that changes the classes the job runs finishes with status Succeeded. Reason: Salesforce refuses to deploy a changed Apex class that has scheduled jobs pending unless the deployment setting that allows deployments while Apex jobs are pending or in progress is on (its exact name is unconfirmed); the setup guide says to turn it on.
Source: implied: runtime rule; U-11

### C-87: A failed purge run does not stop later ones
Observable: If a night's run of "Grok Bot Purge" ends in error, the schedule stays in place, the next night's run deletes the expired records the failed run left, and no Message record is ever left without its Conversation.
Source: implied: pass 3 (partial completion), a thing it depends on failing

### C-88: All text the bot shows is in English
Observable: Labels, notices and error messages shown by the bot are in English for every user whatever their language setting; no translation is provided.
Source: choice: the request is silent; translations are not needed for a development org

### C-89: One user's pending send does not block that user's other conversations, or other users
Observable: While one user's reply is pending, that user can send in a different conversation, and every other user can send, each with their own request (subject to C-41).
Source: implied: pass 3 (two at once)
