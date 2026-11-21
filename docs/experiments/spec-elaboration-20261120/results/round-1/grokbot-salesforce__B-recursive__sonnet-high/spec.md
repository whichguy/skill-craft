## Use cases

### U-1: An administrator gets the Grok bot working in a Salesforce development org
Flow: The administrator deploys the bot into a Salesforce development org (Developer Edition, sandbox or scratch org, Lightning Experience on). They assign a permission set to themselves and to the people who may chat. They enter the xAI API key in the org's user interface and see the bot's status change from "not set up" to ready. They open the bot and send a test message.
Source: request ("Create a Grok bot in a Salesforce development org")

### U-2: A user asks Grok a question and reads the answer
Flow: The user opens the Grok bot in Lightning Experience. They see an empty conversation and a message box. They type a question and send it. They see their message, a waiting indicator, and then Grok's answer.
Source: request ("Grok bot")

### U-3: A user holds a multi-turn conversation
Flow: After an answer, the user types a follow-up that only makes sense given the earlier turns (for example "make it shorter"). Grok's answer takes the earlier turns into account.
Source: implied: a bot that answers in a conversation

### U-4: A user starts a fresh conversation
Flow: The user chooses "new conversation". The transcript area empties. Their next message is answered with no knowledge of the earlier conversation.
Source: implied: U-3 (a conversation needs a beginning and an end)

### U-5: A user comes back to earlier conversations
Flow: The user opens the bot on another day. They see a list of their own earlier conversations, open one, read it, send another message in it, or delete it.
Source: implied: "bot" in an org that keeps data; the operator's need to observe and the user's need to resume

### U-6: A user hits a problem and understands what to do
Flow: The user sends a message and something is wrong (nothing set up, bot turned off, empty or oversized message, Grok slow, refusing or down, too many messages sent, conversation full). They see a message saying what happened and whether retrying, changing the message or contacting the administrator is the fix. They do not lose the text they typed.
Source: implied: the bot depends on an outside service that can fail

### U-7: An administrator changes how the bot behaves, or turns it off
Flow: The administrator replaces the API key, switches the Grok model, edits the instruction that frames every conversation, changes limits, or turns the bot off and on again, all in the org's user interface with no code deployment. The next message a user sends uses the new settings.
Source: implied: API keys rotate, models are retired, an operator needs a stop switch

### U-8: An administrator observes usage and failures
Flow: The administrator opens a list of calls made to Grok. For each they see when, who, which model, how long it took, the outcome and the token counts. They filter to failures and read why each failed, without ever seeing the API key.
Source: implied: operator's work (observe)

### U-9: Someone who must not use the bot, or must not see data, tries
Flow: A user without the permission set, an external or guest user, or a user trying to read a colleague's conversation (through the tab, a record URL, a report or the API) is refused or shown nothing.
Source: implied: the bot spends money on an API key and stores private conversations

### U-10: An administrator carries on across redeploys, rolls back, and retires the bot
Flow: The administrator redeploys the bot over an existing install (newer or previous version), and stored conversations, settings and the API key are still there and working. Later they turn the bot off, remove the key and delete the data.
Source: implied: operator's work (carry on with data that already exists, go back to the version before, stop)

### U-11: A developer proves the bot works and prepares to ship beyond the development org
Flow: The developer runs all the bot's automated tests in the org with no API key and no internet access to xAI, and sees them pass with coverage figures. They deploy the same metadata to another org (sandbox or production).
Source: implied: Salesforce will not deploy to production without passing tests and coverage

### U-12: A user acts twice, in two places, or leaves mid-wait
Flow: The user double-clicks Send, sends the same conversation from two browser tabs, or reloads/closes the page while waiting for Grok. Each intended send produces one Grok call and one pair of stored messages, and a reply that was produced is not lost.
Source: implied: U-2 on a slow call (Grok can take many seconds)

### U-13: An org owner knows what leaves Salesforce
Flow: A user sees a notice that messages are sent to xAI. The org owner can verify that only the conversation text and the configured instruction, and no other Salesforce data, are sent, and only to xAI.
Source: implied: a third-party AI service receiving company users' text

## Clauses

### C-1: The bot is reached from a Lightning Experience navigation item labelled with the word "Grok"
Observable: A user with chat access opens Lightning Experience, opens the app launcher or navigation bar, finds an item whose label contains "Grok", and clicking it shows the chat screen.
Source: request ("Grok bot"); choice: a Lightning tab is the most direct place a Salesforce user finds a bot, and the request names no channel (Einstein Bot, Messaging, Slack, email and the like are not part of this)

### C-2: Opening the chat screen shows a new empty conversation with the message box ready
Observable: On opening, the transcript area contains no messages, the message box is present and empty, and a Send control is present. No conversation record has been created by opening alone.
Source: implied: U-2

### C-3: Sending a message shows it in the transcript at once with a waiting indicator
Observable: Within 1 second of the user sending a valid message, the message appears in the transcript as the user's, the message box empties, and a visible indicator shows Grok's answer is pending.
Source: implied: U-2 (Grok can take many seconds)

### C-4: Grok's answer appears below the user's message, visibly attributed to Grok
Observable: When Grok answers, the waiting indicator goes away and the answer appears after the user's message, in a way a user can tell apart from their own messages without reading the content (a label, a position or a style).
Source: request; implied: U-2

### C-5: The answer shown is the text Grok returned
Observable: With a mocked Grok returning the text "Hello, 世界 😀\nSecond line", the transcript shows exactly those characters in that order, with the line break preserved.
Source: implied: U-2

### C-6: A follow-up in the same conversation is sent to Grok together with the earlier messages of that conversation
Observable: With Grok mocked to record requests, after two completed turns the third request contains, in order, the instruction, then the user's first message, Grok's first reply, the user's second message, Grok's second reply, then the new message.
Source: implied: U-3

### C-7: At most the 20 most recent stored messages of a conversation are sent to Grok as history
Observable: In a conversation holding 30 stored messages, the next request contains the 20 most recent of them (10 turns) plus the new message, and none of the 10 oldest. The transcript shown to the user still shows all 30.
Source: choice: unbounded history would eventually exceed Grok's context window and the platform's heap limit; 20 is generous for a chat assistant

### C-8: A new conversation's requests contain nothing from any other conversation
Observable: After "new conversation", the first request to Grok contains the instruction and the new message only, no earlier messages.
Source: implied: U-4

### C-9: Choosing "new conversation" shows an empty transcript and an empty message box
Observable: The control is present on the chat screen; choosing it empties the transcript area and the message box and the next message starts a conversation as in C-8 and C-10.
Source: implied: U-4

### C-10: A conversation exists as a stored record only once Grok's first answer in it has been stored
Observable: Opening the bot, starting new conversations, and sending messages that all fail leaves the user's list of conversations unchanged; after the first successful reply, the conversation appears in the list.
Source: choice: avoids empty or half-finished conversations piling up in a storage-limited org

### C-11: A user can list their own previous conversations, newest activity first
Observable: The chat screen offers a list of the user's conversations. Each entry shows the opening text of its first message (at least the first 40 characters, or all of it if shorter) and when it was last active in the user's own time zone. The conversation with the most recent message is first.
Source: implied: U-5

### C-12: The conversation list shows the 50 most recent and lets the user load further ones until all are shown
Observable: A user with 120 conversations sees 50, uses a "load more" action twice and sees 100 then 120, and then the action is gone.
Source: choice: bounded page size keeps the screen fast; no conversation may be unreachable

### C-13: Opening a listed conversation shows its stored messages in order (paged as C-55 says)
Observable: After opening a conversation with 6 stored messages, the transcript shows those 6 messages in the order they occurred, each attributed as the user's or Grok's.
Source: implied: U-5

### C-14: A user can delete one of their own conversations, after confirming
Observable: Choosing delete shows a confirmation; confirming removes the conversation from the list and removes all its messages everywhere they could be seen (list, record pages, reports, API queries). Cancelling changes nothing.
Source: implied: U-5 (private conversations the user may want gone)

### C-15: A stored conversation reloads identically after the page is reloaded
Observable: After a page reload, opening the conversation shows the same messages with the same text, order and attribution as before.
Source: implied: U-5

### C-16: A message that is empty or only whitespace cannot be sent
Observable: With the message box empty or containing only spaces/newlines, Send is disabled or does nothing; no request is made to Grok and nothing is stored.
Source: implied: U-6

### C-17: A message longer than 4,000 characters is refused before any call to Grok
Observable: Pasting 4,001 characters shows a message saying the limit is 4,000 and Send does not send; 4,000 characters are accepted. The typed text is kept. Characters are counted as the platform counts string length, so an emoji may count as two.
Source: choice: bounds cost, request size and storage; 4,000 characters (roughly 1,000 tokens) covers ordinary questions

### C-18: Whenever no API key is set, the bot reports that it is not set up and sends nothing
Observable: In a freshly deployed org with no key, and again after an administrator removes the key, a chat user trying to send sees a message that the bot is not set up and an administrator must finish setup; no outbound request is made.
Source: implied: U-1 (secrets cannot be shipped inside deployable metadata)

### C-19: While the administrator has turned the bot off, users see that it is off and nothing is sent to Grok
Observable: With the "enabled" setting off, opening the bot shows a notice that it is turned off; sending is not possible; no outbound request is made.
Source: implied: U-7 (stop switch)

### C-20: If Grok does not answer within the configured wait, the user is told it timed out
Observable: With Grok mocked to never answer and the wait set to 20 seconds, after about 20 seconds (not more than 22) the waiting indicator is replaced by a message saying Grok did not answer in time and that trying again may help.
Source: implied: U-6

### C-21: If Grok says the key's rate or quota limit is reached (HTTP 429), the user is told to try again later
Observable: With Grok mocked to return 429, the user sees a message that the service is busy or limited and trying again later may help; the message does not contain the raw response body.
Source: implied: U-6

### C-22: If Grok fails with a server error (HTTP 5xx), the user is told it is temporarily unavailable
Observable: With Grok mocked to return 500, 502 or 503, the user sees a message that Grok is temporarily unavailable and trying again may help.
Source: implied: U-6

### C-23: If Grok rejects the key (HTTP 401 or 403), the user is told to contact the administrator
Observable: With Grok mocked to return 401, the user sees a message that the bot has a configuration problem and the administrator should be contacted.
Source: implied: U-6

### C-24: If Grok cannot be reached at all (connection failure), the user is told it could not be reached
Observable: With the callout failing before any response (for example an unreachable host), the user sees a message that Grok could not be reached and trying again may help.
Source: implied: U-6

### C-25: If Grok returns a successful response with no usable answer text, the user is told no answer was produced
Observable: With Grok mocked to return HTTP 200 with empty answer text, missing answer text, or a body that is not the expected structure (for example an HTML page), the user sees a message that no answer was produced; no empty Grok message is stored or shown.
Source: implied: U-6

### C-26: When a send fails, the user's text is back in the message box, ready to send again
Observable: After any failure in C-18 to C-25, C-81 or C-111, the user's text is in the message box unchanged, can be sent again as it is, and the transcript no longer shows it as a sent message.
Source: choice: persisting only answered turns keeps stored conversations consistent; the platform also forbids writing records before a callout in the same transaction, which makes storing after the call the natural order

### C-27: Every user-visible error says whether retrying, changing the message, or contacting an administrator is the remedy
Observable: Across all errors in this specification, each shown message is one of three kinds: "try again" (timeout, 429, 5xx, unreachable, no usable answer, platform busy, hourly limit reached), "contact your administrator" (not set up, turned off, key rejected, any other 4xx such as model not found), or "change your message or start a new conversation" (empty, too long, conversation full, conversation too long for Grok, conversation no longer exists). A reader can tell the kind without technical knowledge.
Source: implied: U-6

### C-28: A user may send at most 60 messages to Grok in any rolling hour; the 61st is refused with a message saying to try again later
Observable: A user who has had 60 calls made to Grok in the past 60 minutes (counted as C-48 says) is refused on the 61st with no outbound request; the message says to try again later. After the oldest of the 60 is more than 60 minutes old, sending works again. The limit is changeable by the administrator (C-105).
Source: choice: protects the org's xAI spend from a runaway user or script; 60 per hour exceeds ordinary human use

### C-29: A conversation holds at most 200 messages; once full the user is told to start a new conversation
Observable: When a conversation holds 200 stored messages, the message box is disabled with a notice to start a new conversation, and no request is made. The earlier messages remain readable.
Source: choice: bounds record counts per conversation and the cost of loading one

### C-30: An administrator can enter and replace the xAI API key in the org's user interface without deploying code
Observable: In Setup or the bot's administrator screen, the administrator finds a place to enter the key. After saving, the next chat message uses the new key and not the old one; a mocked Grok that accepts only the new key answers it.
Source: implied: U-1, U-7

### C-31: After the key is saved, no screen, API response, log or page source shows its value
Observable: Setup shows the key field as set but masked or empty; the chat screen's network responses, the call log, Apex debug logs at the finest level and the page source never contain the key's text.
Source: implied: U-1 (a secret)

### C-32: The administrator can choose which Grok model is used, in the org's user interface, without deploying code
Observable: Changing the model setting to "model-x" makes the next request to Grok name "model-x" as its model.
Source: implied: U-7 (models are retired and replaced)

### C-33: The bot ships with a non-blank default model name that the administrator may change
Observable: In a freshly deployed org the model setting is non-blank. The default is a current general-purpose Grok chat model at build time; its exact identifier must be verified against xAI's published model list when building (unconfirmed here).
Source: choice: the request names no model; a working bot out of the box needs one

### C-34: The administrator can set the instruction that frames every conversation
Observable: Changing it makes the next request to Grok carry the new text as its first, system-role message (see C-104). Clearing it entirely results in requests with no system message.
Source: implied: U-7

### C-35: The administrator can set the maximum length of Grok's answer, from 1 to 8,192 tokens, default 2,048
Observable: The next request carries the configured maximum. A value of 0 or 8,193 is refused when saving, with a message naming the allowed range.
Source: choice: bounds spend and ensures an answer fits in a stored message; default 2,048 suits chat

### C-36: The administrator can set how long the bot waits for Grok, from 5 to 100 seconds, default 60
Observable: A value of 4 or 101 is refused when saving with a message naming the range. A configured 30 gives a timeout after about 30 seconds (see C-20).
Source: choice: the platform allows at most 120 seconds of callout wait per transaction (see C-79); 100 leaves room to store the result

### C-37: The administrator can turn the bot on and off
Observable: The enabled setting is a switch, on in a freshly deployed org. Switching it off or on takes effect for the next send (see C-19, C-64).
Source: implied: U-7

### C-38: Every attempt to call Grok is recorded in a call log the administrator can open
Observable: After one successful and one failed send, the log lists two entries, each showing time, the user, whether it was an administrator test, the model named in the request, duration in milliseconds, outcome (success, or the failure kind of C-20 to C-25, C-72, C-81 or C-111), the HTTP status if there was one, and for successes the prompt, answer and total token counts reported by Grok (blank where Grok reported none).
Source: implied: U-8

### C-39: A call log entry never contains the API key, the instruction text, or any message text
Observable: Searching all call log fields for the key, for a message the user sent and for Grok's answer text finds nothing. A failure entry may contain Grok's short error message (at most 255 characters).
Source: implied: U-8, U-13 (the log is operator-facing and must not become a second copy of private conversations)

### C-40: Conversations are deleted automatically once their latest message is older than the retention period, default 30 days
Observable: A conversation whose latest message is 31 days old is gone after the next daily cleanup (with all its messages); a conversation whose latest message is 29 days old remains.
Source: choice: a Developer Edition org has only 5 MB of data storage; unbounded transcripts would fill it

### C-41: Redeploying the bot over an existing install keeps stored conversations and the call log
Observable: After redeploying the same or a different (newer or previous) version, previously stored conversations open as before and earlier call log entries are still listed.
Source: implied: U-10

### C-42: The bot is deployable from source to a fresh Developer Edition org with no manual metadata creation
Observable: A single deployment succeeds on an org with Lightning Experience and My Domain enabled (and likewise on a sandbox or scratch org); afterwards the only manual steps are assigning permission sets and entering the key.
Source: implied: U-1, U-11

### C-43: Two permission sets exist, one for chat users and one for administrators, assignable independently
Observable: After deploy, Setup lists a permission set for chat users and a permission set for administrators, each with "Grok" in its label. Assigning only the first lets a person chat but not open settings, status or the call log. Assigning only the second lets a person open settings, status and the call log.
Source: implied: U-1, U-9 (someone must be allowed to use the bot and someone allowed to run it)

### C-44: A chat user needs no access granted by hand beyond the chat permission set
Observable: A newly created internal user, given only the chat permission set, can open the bot and have a message answered with no further grants (no credential-principal access, object access or Apex access added by an administrator). Reason: Salesforce lets a user's callout use a stored credential only if the user's permissions include that credential's principal, so the chat permission set must carry it.
Source: implied: U-1; runtime rule

### C-45: An administrator status screen shows whether setup is complete as a checklist
Observable: The screen lists, each marked done or not done: API key entered; a non-blank model; bot turned on; at least one user holds the chat permission set; daily cleanup scheduled (with the time of its last run if it has run). In a fresh org after deploy the key item is not done. Entering the key makes it done without any other change.
Source: implied: U-1 (the administrator needs to tell "ready" from "not ready")

### C-46: An administrator can send a test message to Grok from the status screen and see the outcome
Observable: A "test" action sends a fixed short prompt to Grok with the current settings and shows either success with the answer text, or the failure kind (as in C-20 to C-25) with the HTTP status. No conversation is stored; the test appears in the call log; it does not count toward any user's hourly limit.
Source: implied: U-1 ("send a test message") and U-8

### C-47: One API key and one set of settings serve the whole org
Observable: Two different chat users sending messages cause requests that carry the same key and the same model, instruction, maximum length and wait settings. There is no per-user key.
Source: choice: the request names one bot in one org; per-user keys would let personal xAI accounts bypass the org's controls

### C-48: The hourly limit counts calls made to Grok by the user across all their conversations and tabs, excluding refusals made before calling and administrator tests
Observable: A user who has had 55 calls made (successful and failed, over any conversations or tabs) and 20 messages refused for being empty or too long is still allowed 5 more calls in the hour; the 61st call is refused.
Source: implied: C-28 (what is counted must be stated); choice: failed calls count because xAI may still throttle or bill them

### C-49: Once the API key has been entered, cleanup of old data runs at least once every 24 hours with no further administrator action
Observable: After the key is entered and nothing else is done, the platform's scheduled jobs list shows the cleanup job, and the status screen's "cleanup scheduled" item is done with a last-run time that is never more than 25 hours old while the org is running.
Source: implied: C-40 (retention needs something to enforce it)

### C-50: Only Grok's final answer text is shown and stored; any internal reasoning text the model returns is neither shown nor stored
Observable: With Grok mocked to return both reasoning text ("because...") and an answer ("42"), the transcript and the stored message contain "42" and not the reasoning text.
Source: implied: U-2 (reasoning-capable Grok models return a separate reasoning field)

### C-51: Messages are plain typed or pasted text; the chat screen offers no attachment or image upload
Observable: The chat screen has no attach, upload or image control; pasting an image into the message box adds no content.
Source: choice: the request asks for a bot, not a multimodal assistant; attachments would need file storage and extra limits

### C-52: Text in any script, and emoji, sent by the user or returned by Grok is stored and shown unchanged
Observable: A message "Grüße 你好 🙂 مرحبا" sent and answered, then the conversation reopened after a reload, shows the same characters in the same order in the user's message, and an identical mocked answer is shown identically.
Source: implied: U-2, U-5

### C-53: The bot's own screens, labels and messages are in English
Observable: All fixed text on the chat, status and settings screens is English whatever the user's language setting. Grok's answers are in whatever language Grok returns.
Source: choice: the request is in English; translation is beyond the request

### C-54: A user with no stored conversations sees an indication that there are none
Observable: For a user with zero stored conversations, the list area shows a statement that there are no previous conversations, not a blank area or an error.
Source: implied: U-5 (the first time)

### C-55: Opening a conversation shows its 50 most recent messages and lets the user load 50 earlier ones at a time until all are shown
Observable: Opening a 120-message conversation shows messages 71 to 120 in order; a "show earlier" action shows messages 21 to 120, then 1 to 120, and then the action is gone. Opening never fails on account of a conversation's size.
Source: choice: bounds one screen load (the platform's 6 MB synchronous heap could be exceeded by 200 maximum-size messages); refines C-13

### C-56: A notice on the chat screen states that messages are sent to xAI's Grok service
Observable: Whenever the chat screen is shown (empty or with a conversation open) a visible statement says that what the user types is sent to xAI, the service behind Grok.
Source: implied: U-13

### C-57: A cut-off answer is flagged
Observable: With Grok mocked to return text and a finish reason of "length", the answer is shown in full as returned together with a notice that it stopped at the maximum length; reopening the conversation shows the notice again.
Source: implied: C-35 (a maximum length means answers can end early)

### C-58: A new conversation appears in the user's list as soon as its first answer arrives, without reloading the page
Observable: After the first reply in a new conversation, the list on the same screen already shows it at the top.
Source: implied: C-10, C-11

### C-59: Each successful send is stored as one inseparable pair, the user's message followed immediately by Grok's answer
Observable: In any stored conversation the messages alternate user, Grok, user, Grok from the start; there is never a user message without the Grok answer after it, nor a Grok answer without the user message before it, including after failures, timeouts and concurrent use.
Source: choice: follows from C-126; keeps stored history valid for the next request

### C-60: Two sends in the same conversation at the same time (for example from two tabs) are both answered and both stored, each as an adjacent pair
Observable: Sending "A" in tab 1 and "B" in tab 2 within the same second yields a stored conversation of four messages: A with its answer adjacent and B with its answer adjacent, in either pair order, never interleaved.
Source: implied: U-12

### C-61: The 200-message limit is never exceeded, even by simultaneous sends
Observable: With a conversation holding 198 messages, two sends at the same time: one is stored and the other is told the conversation is full (as in C-29) and keeps its text in the box; the conversation never holds 202.
Source: implied: C-29 meeting C-60

### C-62: A send whose conversation is deleted before the answer arrives stores nothing
Observable: Starting a send in tab 1, deleting the conversation in tab 2, then letting Grok answer: no message from that send is stored anywhere, and no conversation record reappears.
Source: implied: U-12, C-14

### C-63: A change to a setting applies to the next call to Grok, never to one already in progress
Observable: Changing the model from "m1" to "m2" while a call naming "m1" is pending leaves that call as it was; the next call names "m2".
Source: implied: U-7

### C-64: Turning the bot off lets calls already in progress finish and be stored
Observable: With one call pending, switching the bot off, the pending one still shows and stores its answer; the next send attempt then gets the "turned off" message of C-19.
Source: implied: U-7, C-19

### C-65: Simultaneous sends may exceed the hourly limit only by the number of sends in progress at the same moment; sequential sends never can
Observable: At 59 calls in the hour, a single send brings the user to 60 and the next is refused. Three sends at the same instant at 59 may leave the count at up to 62, but a later send is refused.
Source: choice: an exactly enforced limit across simultaneous requests would need locking that the platform makes costly; the limit protects spend, so a small overshoot is tolerable

### C-66: Deleting the conversation that is open clears the transcript to a new empty conversation
Observable: After confirming delete on the open conversation, the screen shows the empty state of C-2.
Source: implied: U-5

### C-67: While a reply is pending, the user cannot send again, start a new conversation, or open another conversation
Observable: From the moment Send is pressed until the answer or an error shows, the Send control, the new-conversation control and the conversation list entries are disabled.
Source: choice: keeps one pending state per screen

### C-68: Closing or reloading the page while a call is pending does not by itself make a second call
Observable: Sending, then closing the tab and reopening the conversation after a minute, leaves the call log with exactly one entry for that send and the mocked Grok with exactly one request.
Source: implied: U-12

### C-69: A repeated submission of the same send, identified by one identifier generated when Send is pressed, stores at most one pair
Observable: Submitting the same send twice (including simultaneously) to the chat's server entry point leaves exactly one user message and one answer stored; a second submission arriving after the first completed returns the stored answer without a new call to Grok.
Source: implied: U-12 ("a thing done twice that should happen once"); choice: simultaneous duplicates may each call Grok, but only one pair is stored

### C-70: A failure to write the call log entry does not make the user's send fail
Observable: With the log unwritable, the user still sees and stores the answer as normal.
Source: implied: the log (C-38) is a side record of the chat

### C-71: If an answer was received but could not be stored, the user still sees it, marked as not saved
Observable: With storage refused after Grok answered, the transcript shows the user's message and Grok's answer with a notice that they were not saved and will not be part of the conversation history; after reload they are absent; the next send in that conversation does not include them.
Source: implied: U-6; runtime rule (a Developer Edition org has about 5 MB of data storage, and once it is full record creation fails)

### C-72: An answer arriving after the wait has expired is discarded
Observable: With Grok mocked to answer 5 seconds after a 3-second wait expired, the user has already seen the timeout message; the late answer is never shown or stored, and the log entry's outcome is timeout.
Source: implied: C-20

### C-73: Cleanup deletes a conversation together with all its messages, never part of one
Observable: After any cleanup run, no conversation is missing messages; each either remains whole or is gone with all its messages.
Source: implied: C-40 meeting C-59

### C-74: Cleanup runs whether the bot is on or off
Observable: With the bot off for 31 days, cleanup still removes conversations and log entries older than the retention period.
Source: implied: C-19 meeting C-40

### C-75: Cleanup that finds more expired data than one run can delete continues until none remains
Observable: With 30,000 expired conversations present, repeated cleanup activity without administrator action leaves none of them; no run fails on a platform limit and gives up on the rest.
Source: runtime rule (one transaction can delete at most 10,000 records); implied: C-40

### C-76: A change to the retention period applies at the next cleanup run, in both directions
Observable: Reducing retention from 30 to 7 days makes the next run delete conversations idle for 8 days; raising it back afterwards restores none.
Source: implied: C-40, U-7

### C-77: Changing the model mid-conversation keeps the conversation's history
Observable: After the model setting changes, the next request in an existing conversation contains the same earlier messages C-6 describes and names the new model.
Source: implied: U-7 meeting U-3

### C-78: The user's browser communicates only with Salesforce; every call to xAI is made from Salesforce's servers
Observable: Browser developer tools show no request to any host other than hosts belonging to Salesforce (the org's own domains and Salesforce's content delivery) while chatting.
Source: implied: C-31; runtime rule (Salesforce's content security policy blocks browser calls to hosts not on its trusted list, and a browser call would expose the key)

### C-79: One submission of a send causes at most one request to Grok, with no automatic retry
Observable: With Grok mocked to return 503, the mock receives exactly one request for that submission. The user may send again, which is a new submission.
Source: runtime rule (all callouts in one transaction may wait a combined 120 seconds, so a retry after a long wait cannot fit); choice

### C-80: Grok's answer appears all at once when complete, not progressively
Observable: While pending, the transcript shows only the waiting indicator; when done, the whole answer appears in one step.
Source: runtime rule (Apex receives a callout's response only when it is complete; there is no streaming to the page)

### C-81: If the platform refuses to run the request because too many long requests are already running in the org, the user is told it is busy and to try again
Observable: When the platform answers with its concurrent-requests-limit error, the user sees a "try again" message (C-27), their text is kept, and nothing is stored. The platform's limit is on the order of 10 requests running 20 seconds or more at once in an org; the exact figure is unconfirmed.
Source: runtime rule

### C-82: The bot's automated tests run and pass in the org with no API key set and no network access to xAI
Observable: Running all the bot's Apex tests in a fresh org with no key entered and outbound calls to api.x.ai impossible reports every test passed.
Source: runtime rule (tests cannot make real callouts); implied: U-11

### C-83: The bot's automated tests cover at least 85% of the bot's Apex lines in aggregate
Observable: The org's reported coverage for the bot's classes, taken together, is 85% or more after running all bot tests.
Source: runtime rule (production deployment requires at least 75% coverage and all tests passing); choice: 85% gives headroom

### C-84: A deployment to another org succeeds when its tests pass
Observable: A validation-only deploy of the bot's metadata to a different org (sandbox or production) with default test running succeeds, with the bot's own tests passing there.
Source: implied: U-11; runtime rule (production deployment runs tests)

### C-85: The deployment includes authorisation to call xAI, so no callout registration is added by hand
Observable: After deploy and key entry, the first send reaches xAI with no Setup step to allow the host.
Source: runtime rule (Apex may only call endpoints registered in the org)

### C-86: The chat screen works with Lightning Web Security turned on
Observable: With Lightning Web Security enabled, the chat and status screens work and the browser console shows no errors from the bot's components.
Source: runtime rule (current orgs run components under Lightning Web Security)

### C-87: Any answer Grok returns within the maximum length setting is stored in full
Observable: With Grok mocked to return a 32,000-character answer (within 8,192 tokens), the stored message and the reopened transcript hold all 32,000 characters.
Source: runtime rule (a long text field holds at most 131,072 characters); implied: U-5

### C-88: Deploying adds only the bot's own components and changes nothing else in the org
Observable: After deployment, the items changed in the org are only those belonging to the bot; existing profiles, permission sets, sharing settings, standard objects and other apps are unchanged.
Source: implied: "in a Salesforce development org" that already holds other things

### C-89: No API key value exists anywhere in the deployable source
Observable: A text search of the whole source tree for the prefix "xai-" followed by key-like characters finds nothing.
Source: implied: C-31

### C-90: The bot sends requests only to xAI's API at https://api.x.ai, over HTTPS
Observable: Every outbound request captured during a test run has host api.x.ai and scheme https; none goes anywhere else.
Source: implied: U-13; choice: a fixed endpoint cannot be repointed to an unvetted server (that xAI keeps this host is unconfirmed)

### C-91: The data sent to Grok is only the instruction, the conversation messages, the model name and the maximum length
Observable: A captured request body holds the system instruction, the history, the new message, the model and the maximum token setting, and no Salesforce record data, no user name, email or Id, and no org Id.
Source: implied: U-13; choice

### C-92: The bot can only converse; it cannot read, create, change or delete other Salesforce records on a user's behalf
Observable: Telling a mocked Grok to "delete my account" changes nothing in the org; captured requests carry no tool or function definitions; the bot touches only its own conversation, message and log records.
Source: choice: the request asks for a bot, not CRM actions; excluded to avoid agentic risk

### C-93: A conversation and its messages are visible only to the user who created it, through every way of looking
Observable: User B, holding the chat permission set, cannot see user A's conversation through the chat list, a direct record URL, a report, a list view, global search or an API query (each returns no rows or an access error). This holds for administrators too unless they hold the platform's "View All Data" or "Modify All Data".
Source: implied: U-9; runtime rule (those two permissions override record visibility)

### C-94: A user cannot create or edit message or conversation records except by using the bot
Observable: Creating a message or editing a stored message through the record UI, a data import or the API as a chat user is refused. A chat user's only direct change is deleting their own conversation (C-14).
Source: implied: U-9 ("a rule enforced in one path and not another"); choice: tampering would let users forge what Grok said

### C-95: Every way into the bot's server side refuses a user without the matching permission set
Observable: A user without the chat permission set who calls the chat entry point directly (as a script against the platform's API would) gets an access error and no request is made to xAI. A user without the administrator permission set calling the status, settings, test or log entry points gets an access error and no data.
Source: implied: U-9

### C-96: Nothing publicly reachable triggers a call to xAI
Observable: An unauthenticated request to the org's public sites or REST endpoints cannot cause any request to xAI.
Source: implied: U-9 (the key spends the org's money)

### C-97: Text from users and from Grok is displayed as text, never run as markup or script
Observable: A mocked answer "<script>alert(1)</script><img src=x onerror=alert(2)>" shows those characters literally in the transcript; no alert occurs and no element is created. The same holds for a user message containing it.
Source: implied: U-2 (Grok's output is untrusted input to a page)

### C-98: The size, count, rate and on/off limits apply to every way of sending, not only the chat screen
Observable: A direct call to the chat entry point with a 4,001-character message, or while the bot is off, or over the hourly limit, or at 200 messages, is refused exactly as the chat screen would refuse it, with no outbound request.
Source: implied: U-9, U-6 ("a rule enforced in one path and not another")

### C-99: Error messages shown to users never contain Grok's raw response, a stack trace, an internal identifier or the key
Observable: With Grok mocked to return a 400 whose body contains "internal-secret-123", the user's message does not contain that text.
Source: implied: U-6, U-8

### C-100: The text of a stored message is identical to the text that was displayed
Observable: The transcript shown right after an answer and the transcript after reload show identical text for every message (apart from the notices of C-57 and C-71).
Source: implied: U-5 ("data lost on the way")

### C-101: Cleanup deletes nothing younger than the retention period
Observable: After a cleanup run, a conversation whose latest message is 29 days old (retention 30) and a call log entry 29 days old are still present.
Source: implied: C-40

### C-102: Missing or invalid settings make the bot behave as "not set up", never as a bot with a guessed value
Observable: With the model setting blank, or the wait set outside 5 to 100 by a route that bypassed the save check, a send shows the "not set up" message and makes no request.
Source: implied: C-18, C-35, C-36

### C-103: The chat screen and the status screen are usable by keyboard alone
Observable: Message box, Send, new conversation, the list, delete and the status screen's actions are all reachable and operable by keyboard.
Source: implied: U-2; choice: standard Lightning accessibility, no specific key binding

### C-104: The system instruction is sent with every request
Observable: With a non-blank instruction, every request in a conversation (the first and the fifth) starts with it as a system message.
Source: implied: C-34 and C-6

### C-105: The administrator can set the per-user hourly call limit, from 1 to 1,000, default 60
Observable: A value of 0 or 1,001 is refused when saving with a message naming the range. A saved value applies from the next send (for example, 5 makes the 6th call in an hour refuse).
Source: choice: bounds as stated (see C-28)

### C-106: The administrator can set the retention period, from 1 to 365 days, default 30
Observable: A value of 0 or 366 is refused when saving with a message naming the range. A saved value is used by the next cleanup run (see C-76).
Source: choice: bounds as stated (see C-40)

### C-107: The bot ships with a non-blank default instruction
Observable: In a freshly deployed org the instruction setting is non-blank, and the first request after key entry carries it (C-104).
Source: choice: the request supplies no instruction; its wording is left to the builder

### C-108: If Grok rejects the request with any other 4xx status than 401, 403 and 429 (for example an unknown model), the user is told to contact the administrator
Observable: With Grok mocked to return 404 or 400 (not about conversation length), the user sees a "contact your administrator" message (C-27); the call log entry shows the status.
Source: implied: U-6, U-7 (models are retired and replaced)

### C-109: While the bot is turned off, existing conversations can still be read and deleted
Observable: With the bot off, a user can open the list, open a conversation, read it and delete it; only sending is unavailable.
Source: implied: C-19, C-14 (turning the bot off must not trap a user's data)

### C-110: The bot adds no content filtering of its own; any message within the limits is sent and any answer is shown
Observable: A message that is non-empty and at most 4,000 characters is always sent to Grok (if no other rule refuses it); the answer, including one in which Grok declines to help, is shown as returned.
Source: choice: moderation belongs to xAI's service; a second filter would give users inconsistent behaviour

### C-111: If Grok says the request is too long for the model's context, the user is told to start a new conversation
Observable: With Grok mocked to return a 400 whose error says the context length is exceeded, the user sees a message saying the conversation has become too long and to start a new one (C-27); their text is kept. The exact wording xAI uses is unconfirmed, so the builder matches on status 400 together with a context-length indication in the error.
Source: implied: C-7 (20 messages of up to 8,192 tokens each may exceed a model's context)

### C-112: An administrator can delete all the stored conversations and call log entries of one chosen user, after confirming
Observable: The administrator screen offers the action for a chosen user; after confirmation, that user's conversations (with their messages) and log entries are gone and other users' are untouched. Cancelling changes nothing.
Source: implied: U-10 (data of a person who left, retiring)

### C-113: An administrator can delete all stored conversations and call log entries of everyone, after confirming
Observable: The action asks for confirmation; after confirming, the list for every user is empty and the call log is empty; the settings and key are unchanged.
Source: implied: U-10

### C-114: Apart from Grok's own time, a send adds no more than 3 seconds
Observable: With Grok mocked to answer in 1 second, the answer appears within 4 seconds of pressing Send, on an org holding 120 conversations for the user.
Source: choice: a bot that adds visible lag beyond the model's own is unusable; 3 seconds is a generous bound

### C-115: Opening the chat screen with 120 stored conversations shows the list within 3 seconds
Observable: With a user holding 120 conversations, the chat screen shows the first 50 list entries within 3 seconds of being opened.
Source: choice: companion to C-12

### C-116: An administrator can narrow the call log to one outcome and to one user
Observable: Filtering to outcome "timeout" lists only timeout entries; filtering to a user lists only that user's entries; both together list the intersection.
Source: implied: U-8 ("filter to failures")

### C-117: Redeploying the bot over an existing install keeps the API key
Observable: After redeploying, the next send is answered without the key being entered again.
Source: implied: U-10

### C-118: Redeploying the bot over an existing install keeps the settings the administrator has changed
Observable: With the model changed to "m2" and the wait to 30 seconds, after redeploying the settings still read "m2" and 30 and are used by the next send.
Source: implied: U-10

### C-119: Deleting a conversation that is already gone shows no error
Observable: Confirming delete in tab 2 on a conversation already deleted in tab 1 (list not refreshed) shows no error, and the list is correct after refresh.
Source: implied: U-12 meeting C-14

### C-120: An answer that Grok produced while the page was closed is not lost
Observable: Sending, closing the tab before the answer, with Grok answering after the tab closed (within the wait): reopening that conversation later shows the stored pair.
Source: implied: U-12

### C-121: Guest and external (portal or Experience Cloud) users get no access to the bot
Observable: A guest user, or a portal user, opening the bot's pages or calling its entry points gets an access error and no request is made to xAI.
Source: choice: the bot is for internal users only; external users would multiply cost and exposure

### C-122: When an answer or an error appears, a screen reader announces it without the user moving focus
Observable: With a screen reader running, the arrival of an answer or an error message is spoken without any focus change.
Source: implied: C-103; the same users meeting C-80 (answers arrive after a wait)

### C-123: The instruction text is not stored as a message and not shown in the transcript
Observable: After a conversation, the stored messages and the transcript contain none of the instruction text.
Source: implied: C-104

### C-124: An empty call log shows that there are no entries
Observable: In a fresh org the log screen shows a statement that no calls have been recorded, not a blank area or an error.
Source: implied: U-8 (the first time)

### C-125: A new message in an opened conversation continues that conversation
Observable: After opening a stored conversation with 6 messages and sending a message, the answer is appended after the 6th, the stored conversation holds 8 messages, and the request to Grok carried the earlier messages as C-6 and C-7 describe.
Source: implied: U-5

### C-126: Nothing from a failed send is stored
Observable: After any failure in C-18 to C-25, C-81 or C-111, the stored conversation (as seen after reload, or the list if it was a new conversation) contains no trace of that message.
Source: choice: see C-26 (persisting only answered pairs, C-59)

### C-127: A send that is refused because its conversation no longer exists tells the user so and returns the text to the message box
Observable: After the situation in C-62, the user sees a message that the conversation no longer exists (kind "change your message or start a new conversation", C-27) and their text is in the message box.
Source: implied: C-62

### C-128: Call log entries are deleted automatically once they are older than the retention period
Observable: A call log entry created 31 days ago (retention 30) is gone after the next cleanup.
Source: choice: see C-40 (the log holds no message text but still occupies storage)

### C-129: A key pasted with leading or trailing spaces or line breaks works
Observable: Entering the key with a trailing newline results in requests whose credential carries the key without the whitespace; the administrator test of C-46 against a mock accepting only the exact key succeeds.
Source: implied: C-30 (keys are copied from a web page)

### C-130: When the request between the user's browser and Salesforce itself fails (connection dropped, session expired), the user is told to try again and keeps their text
Observable: With the network cut between sending and the reply, the user sees a "try again" message (C-27) and the text is back in the message box; a session that has expired shows the platform's sign-in rather than a blank screen.
Source: implied: U-6 (a pending screen can fail independently of Grok)

### C-131: The transcript shows the newest message after one is added
Observable: After a send or an answer is added, or a conversation is opened, the transcript is positioned so the newest message is visible without the user scrolling.
Source: implied: U-2 (a long conversation otherwise hides the answer)

### C-132: The status screen, call log and administrator actions are reachable from navigation shown only to administrators
Observable: A user with the administrator permission set sees navigation to the status screen and the call log in the Grok app; a user with only the chat permission set sees neither.
Source: implied: C-43, C-45 (how an administrator finds the screens)
