## Use cases

### U-1: An end user asks Grok a question inside Salesforce, to get an answer without leaving the org
Flow: The user opens the Grok tab in Lightning Experience, types a question (for example "What is the capital of France?") and presses Send. Their message appears in the conversation, a waiting indicator shows, then Grok's reply appears below their message.
Source: request (a Grok bot in a Salesforce org)

### U-2: An end user follows up in the same conversation, to get answers that build on what was said before
Flow: After the reply in U-1 the user types "And its population?" and sends it. The reply is about Paris, because Grok is given the earlier messages.
Source: implied: a bot is a conversation, not a series of unrelated questions

### U-3: An end user opens the bot for the first time, to see what to do
Flow: A user who has never used it opens the Grok tab. They see no past conversations, an empty conversation with a box to type in, and no error.
Source: implied: the first-time case

### U-4: An end user sends a message that cannot be sent (empty, whitespace only, too long), to find out why it was refused
Flow: The user presses Send on an empty box, or on a box containing only spaces/line breaks, or on text longer than the limit. Nothing is sent to Grok; they see why, and their typed text is still in the box.
Source: implied: unhappy paths for input; limits of the platform and of the Grok API

### U-5: An end user waits for a slow reply, to know the bot has not frozen
Flow: After Send, a waiting indicator shows. The user cannot send a second message in that conversation until the first has a reply or an error. If Grok does not answer in time, they see an error rather than waiting forever.
Source: implied: a callout to an external service takes seconds; the platform limits a callout to 120 seconds

### U-6: An end user meets a failure (Grok not set up, key rejected, rate limit reached, timeout, Grok down), to know what to do next
Flow: The user sends a message and sees an error that says which kind of problem it is (admin must fix vs. try again later). Their message stays in the conversation marked as failed, with a way to retry. After the problem is fixed or passes, they retry and get the reply.
Source: implied: unhappy paths; refused action; limit reached

### U-7: An end user reloads the page or closes the tab while waiting, to come back to a sane state
Flow: The user sends a message, then reloads or leaves. When they return and open the conversation, the message is there, followed either by Grok's reply or marked as failed with a retry; never stuck waiting forever.
Source: implied: the repeated time / restart case; the platform forces the message to be saved before the outbound call

### U-8: An end user starts a new conversation, to ask about something unrelated
Flow: The user presses New conversation. The view empties and Grok will have no memory of the earlier one. The earlier conversation stays available in the list.
Source: implied: the repeated time

### U-9: An end user returns to an earlier conversation, to read it or carry on
Flow: The user sees a list of their own conversations, most recently active first, each with a title. They open one, see all its messages in order, and send another message that Grok answers in the context of that conversation. If they have many conversations, the list loads in pages.
Source: implied: the repeated time; the largest case

### U-10: An end user has a very long conversation, to keep chatting until the system stops them cleanly
Flow: The user keeps sending messages. At the maximum number of messages the next send is refused with a message telling them to start a new conversation; the existing messages remain readable.
Source: implied: the largest case

### U-11: An end user receives a reply containing markup, very long text or special characters, to read it safely
Flow: Grok's reply contains line breaks, HTML-like text such as `<script>alert(1)</script>`, or a very long answer. The user sees the text as plain text; nothing is executed; an over-long reply is cut at a stated limit and marked.
Source: implied: content from an outside service is untrusted; the platform has field size limits

### U-12: Another user in the same org tries to see someone else's conversations, to be refused
Flow: User B (not an administrator) opens the Grok tab, or queries the data through reports or the API. They see only their own conversations.
Source: implied: conversations are personal data sent to an outside service

### U-13: A user without access tries to use the bot, to be refused
Flow: A user who has not been given the Grok permission set sees no Grok tab and cannot invoke the bot through the platform's APIs.
Source: implied: an admin decides who may spend the organisation's Grok quota

### U-14: An administrator sets the bot up in a fresh development org, to make it work
Flow: The admin deploys the project, enters the Grok API key in Setup (not in source), optionally picks the model, assigns the permission set to users, and sends a test message from the Grok tab that gets a reply. A README gives these steps.
Source: request (Create a Grok bot in a Salesforce development org); implied: an operator starts and configures it

### U-15: An administrator changes the key or the model, to rotate a secret or move to another Grok model
Flow: The admin updates the key or the model name in Setup. The next message anyone sends uses the new value, with no redeploy. Existing conversations are unaffected.
Source: implied: an operator configures it

### U-16: An administrator redeploys, upgrades or goes back to an earlier version, to carry on with data that exists today
Flow: The admin deploys the project again, or deploys an older version of it, over an org that already holds conversations and a stored key. Deployment succeeds; conversations and the key are still there; the bot keeps working.
Source: implied: start, restart, carry on with existing data, go back to the version before

### U-17: A developer deploys the project and runs its tests, to know it is sound before using it further
Flow: The developer deploys to a development org with Salesforce CLI and runs all Apex tests. They pass without network access and without an API key, and the coverage meets the platform's threshold for later promotion to production.
Source: implied: Salesforce development practice; callouts are not allowed in tests

### U-18: A security-conscious administrator checks what leaves the org and what a user can learn, to trust the bot
Flow: The admin inspects what is sent to xAI (only the chat messages), where it is sent (only the Grok API host), and confirms that the key never appears in the browser, in records, in logs or in error messages.
Source: implied: sending data to an external service; secrets in an org

### U-19: The org's existing users and data go on as before, to be undisturbed by the bot
Flow: After deployment, users without the permission set see the org exactly as before; existing records, standard objects, profiles and page layouts are not changed.
Source: implied: where this touches things that already exist

## Clauses

### C-1: The bot is reachable as a tab in Lightning Experience
Observable: A user with the permission set (C-34) opens a Lightning Experience app navigation and finds a tab whose label contains "Grok". Opening it shows the chat.
Source: request

### C-2: Sending a message returns a Grok reply in the conversation
Observable: The user types "What is the capital of France?" and presses Send. The message appears in the conversation, and below it a reply appears that is visibly distinguished as coming from Grok rather than from the user.
Source: request

### C-3: Replies come from the xAI Grok API using the configured model
Observable: When a message is sent, the org makes an HTTPS chat-completion request to the xAI API with the API key from the administrator's configuration (C-38) and the model name from C-42, and the text of the answer shown to the user is the text in Grok's response.
Source: request (Grok bot)

### C-4: One send makes one request to Grok
Observable: A successful send of one message produces exactly one outbound request to Grok, whatever the length of the conversation. A retry (C-17) produces exactly one further request.
Source: implied: platform limits on callouts per transaction; cost of Grok usage

### C-5: Outbound requests go only to the Grok API host
Observable: Every outbound request the bot makes goes to the host api.x.ai; no other host is contacted.
Source: implied: U-18; the platform requires outbound endpoints to be explicitly allowed

### C-6: Only the conversation's messages are sent to Grok
Observable: The request body contains the conversation's messages and the model and generation settings. It contains no other Salesforce record, and no name, email address or username of the user.
Source: choice: the loosest privacy rule that still serves the user; the bot has no feature that needs other org data

### C-7: Grok is given the earlier messages of the conversation
Observable: In a conversation of 10 or fewer messages, the request carries all of them in the order sent, each marked as from the user or from Grok. In a longer conversation it carries at least the 10 most recent, in the same order. A follow-up such as "And its population?" after the France question is answered about France.
Source: implied: U-2; choice: at least 10 so that the platform's heap and Grok's cost stay bounded

### C-8: A message that failed and was not retried is not sent to Grok as context
Observable: After a failed message (C-16) the user sends a different new message. The request to Grok does not contain the failed message's text. If the failed message is later retried successfully, it and its reply are part of the context of later requests.
Source: choice: a message Grok never answered would otherwise appear as two consecutive user turns

### C-9: First-time empty state
Observable: A user with no conversations opens the tab and sees an empty list or a "no conversations yet" indication, an empty message box, and no error.
Source: implied: U-3

### C-10: Empty or whitespace-only messages are refused
Observable: Pressing Send with an empty box, or a box containing only spaces, tabs or line breaks, sends nothing to Grok, adds nothing to the conversation, and the user sees that a message is needed (or Send is unavailable until text is typed).
Source: implied: U-4

### C-11: A message of 4,000 characters is accepted
Observable: A message of exactly 4,000 characters is sent and answered like any other.
Source: choice: a limit is needed to bound request size; 4,000 characters fits a long question and keeps the context from C-7 within the platform's heap

### C-12: A message of 4,001 or more characters is refused and kept in the box
Observable: Pressing Send with 4,001 characters sends nothing to Grok, adds nothing to the conversation, shows the user an error that names the limit 4,000, and leaves the typed text in the box so it can be shortened.
Source: choice: companion to C-11

### C-13: A waiting indicator shows while Grok is answering
Observable: From the moment Send is accepted until a reply or an error is shown, a visible waiting indicator is on screen.
Source: implied: U-5

### C-14: A second message cannot be sent in a conversation that is waiting for a reply
Observable: While the indicator of C-13 is showing, the Send control is disabled (or pressing it sends nothing); only one request is made for one message even if Send is pressed twice quickly.
Source: implied: U-5; double submission

### C-15: The user gets a reply or an error within 120 seconds of pressing Send
Observable: If Grok has not answered, the user sees a timeout error no later than 120 seconds after Send; the waiting indicator is gone and the user can act again.
Source: implied: the platform allows a single callout at most 120 seconds

### C-16: The user's message is kept even when Grok's reply fails
Observable: When any failure of C-19 to C-24 occurs, the user's message is still in the conversation, is marked as failed, and is still there (still marked failed) after the page is reloaded and the conversation reopened.
Source: implied: U-6; the platform does not allow an outbound call after unsaved database changes in the same transaction, so the message is saved first and the call is made after

### C-17: A failed message can be retried
Observable: Next to a failed message there is a Retry action. Using it makes one new request to Grok for that message; on success the reply appears below that message, the message no longer shows as failed, and the message appears in the conversation once, not twice.
Source: implied: U-6

### C-18: A message left without a reply shows as failed when the conversation is reopened
Observable: If the user reloaded or left while waiting (U-7) and returns more than 120 seconds after sending, a message that has no reply shows as failed with the Retry action; it does not show as still waiting.
Source: implied: U-7; the call can have been lost with the page

### C-19: Missing configuration gives a "not set up" error without contacting Grok
Observable: When no API key has been configured, sending a message makes no outbound request and shows the user an error saying the bot is not set up and that an administrator must configure it. The message is marked failed (C-16).
Source: implied: U-6; U-14 (operator state before setup)

### C-20: A rejected key gives an error for the administrator
Observable: When Grok answers with HTTP status 401 or 403, the user sees an error saying access to Grok was refused and that an administrator should check the configuration. The message is marked failed.
Source: implied: U-6

### C-21: A rate limit gives a try-again-later error
Observable: When Grok answers with HTTP status 429, the user sees an error saying Grok is busy or the limit has been reached and to try again later. The message is marked failed.
Source: implied: U-6; a limit reached

### C-22: A timeout gives a try-again error
Observable: When Grok does not answer before the time in C-15, the user sees an error saying the request timed out. The message is marked failed.
Source: implied: U-5, U-6

### C-23: A server or network failure gives a try-again-later error
Observable: When Grok answers with an HTTP status of 500 or above, or the connection fails, the user sees an error saying Grok is unavailable and to try again later. The message is marked failed.
Source: implied: U-6

### C-24: An empty or unusable reply is treated as a failure
Observable: When Grok answers with status 200 but with no answer text, or with a body that cannot be read as an answer, the user sees an error, the message is marked failed, and no blank reply is added to the conversation.
Source: implied: the request takes for granted that Grok returns an answer

### C-25: The user can start a new conversation
Observable: A New conversation control empties the message view. The next message sent is answered by Grok without any text from earlier conversations in the request, and the earlier conversation remains in the list.
Source: implied: U-8

### C-26: A new conversation appears in the list only once its first message is sent
Observable: Pressing New conversation and then leaving without sending adds nothing to the list of conversations.
Source: choice: avoids empty entries piling up

### C-27: A conversation's title is taken from its first message
Observable: After the first message "What is the capital of France?" the list shows a title that begins with that text. For a first message longer than 80 characters the title is its first 80 characters.
Source: choice: some title is needed to tell conversations apart; 80 characters fits a list row

### C-28: The list shows only the user's own conversations, most recent activity first
Observable: The list contains each of the user's conversations once, ordered by the time of their latest message, newest first, and no one else's.
Source: implied: U-9, U-12

### C-29: The list loads 50 conversations at a time
Observable: A user with 120 conversations sees the 50 most recent at first, and a "load more" control brings the next 50, then the last 20, until all are reachable.
Source: choice: a page size is needed so that the list loads quickly and stays within platform limits; no conversation may become unreachable

### C-30: Opening a conversation shows all its messages in the order sent, and it can be continued
Observable: Selecting a conversation from the list shows every message and reply it holds, oldest first, including messages sent within the same second as each other, in the order they were sent. A message then sent is answered in the context of C-7.
Source: implied: U-9

### C-31: A conversation accepts 100 user messages
Observable: The 100th message the user sends in a conversation is accepted. When the user sends a 101st, it is refused with a message that says to start a new conversation, nothing is sent to Grok, and all earlier messages remain readable. Messages marked failed count toward the 100; a retry (C-17) does not count again.
Source: choice: bounds how much data one conversation holds so that opening it stays within platform limits

### C-32: A user cannot see other users' conversations
Observable: User B, who is not an administrator with the "View All Data" permission, sees none of user A's conversations or messages in the Grok tab, and cannot read them through reports, list views or the API.
Source: implied: U-12

### C-33: Without the permission set the bot cannot be used
Observable: A user who has not been assigned the permission set (C-34) sees no Grok tab, and a call to the bot's server-side entry points from that user is refused.
Source: implied: U-13

### C-34: A permission set gives a user what they need
Observable: A permission set whose name contains "Grok" exists after deployment. Assigning it to a user is all that is needed (beyond C-38 having been done once) for that user to see the tab and to send messages and read their conversations. It does not let the user see or change the API key.
Source: implied: U-13, U-14

### C-35: Grok's replies are shown as plain text
Observable: A reply containing `<script>alert(1)</script>` or `<b>bold</b>` shows those characters literally; no script runs and no formatting is applied. Line breaks in the reply are preserved.
Source: implied: U-11; content from an outside service must not run in the user's session

### C-36: The user's own messages are shown as plain text
Observable: A message typed as `<img src=x onerror=alert(1)>` is shown literally, in the conversation and in the list title, and nothing runs, both right after sending and after reopening the conversation.
Source: implied: U-11

### C-37: A very long reply is cut at 100,000 characters and marked
Observable: A reply of 100,000 characters or fewer is shown in full. A longer reply is stored and shown as its first 100,000 characters followed by an indication that it was cut.
Source: choice: below the platform's 131,072-character long-text field limit, with room for the indication

### C-38: The administrator provides the Grok API key in Setup, with no code change
Observable: After deployment the administrator can enter the key through Salesforce Setup. Once entered, messages are answered (C-2) with no further deployment or code edit.
Source: implied: U-14

### C-39: The API key is not in the project source or deployable metadata
Observable: Searching every file in the project directory for a real key finds none; the files deployed to the org contain no key; deploying them to a new org leaves it unconfigured (C-19).
Source: implied: U-14, U-18; the project source can be shared or committed

### C-40: The API key is never exposed to users, records, logs or errors
Observable: The key does not appear in the page or in any response the browser receives, in any record the bot creates, in the debug logs of a send, or in any error message shown to the user.
Source: implied: U-18

### C-41: Changing the key takes effect on the next message
Observable: After the administrator replaces the key in Setup, the next message sent by any user is sent with the new key; no redeployment is needed and existing conversations are unchanged.
Source: implied: U-15

### C-42: The Grok model is a setting with a working default
Observable: Out of the box, with only the key entered, messages are answered by a Grok model. The administrator can change the model name in Setup without redeploying; the next message is sent with the new name. An invalid name results in Grok's refusal being shown as an error that leaves the message marked failed.
Source: choice: Grok model names change over time, so the user relies on being able to move to another without code changes

### C-43: A README describes the setup
Observable: The README at the root of the project lists, in order, how to deploy, where to enter the key, how to choose the model, how to assign the permission set, and how to check it works with a first message. Following it in a new development org gives a working bot.
Source: implied: U-14

### C-44: The project deploys to a development org with Salesforce CLI
Observable: From the project directory, `sf project deploy start` to a Developer Edition or scratch org completes successfully without any manual edit of the files.
Source: request (a Salesforce development org)

### C-45: Deployment only adds
Observable: Deploying the project changes no standard object, standard field, existing profile, existing custom object or existing record in the org, and contains no destructive changes; apart from the tab, a permission set and what the bot itself needs, nothing in the org is different.
Source: implied: U-19 (existing things this touches)

### C-46: Redeploying leaves data and key in place
Observable: Deploying the same project a second time succeeds. Conversations created before, and the stored key and model setting, are still present and the bot still answers.
Source: implied: U-16

### C-47: Conversations survive upgrade and going back
Observable: After deploying a newer version, or an earlier version, of the project over an org holding conversations, those conversations still open, show all their messages and can be continued. No deployment of this project deletes conversation data.
Source: implied: U-16

### C-48: Apex tests pass without network or key
Observable: Running all of the project's Apex tests in the org reports every test passing, with no outbound request actually made to Grok and no API key configured.
Source: implied: U-17; the platform does not make real callouts during tests

### C-49: Apex code coverage is at least 75%
Observable: After running all tests, the org-wide Apex code coverage for the project's classes is at least 75%.
Source: implied: U-17; the platform requires 75% coverage to deploy Apex to production

### C-50: The tests exercise the behaviours of this specification
Observable: Among the passing tests there are ones for a successful reply, the context sent to Grok, each error kind of C-19 to C-24, the 4,000-character boundary, the 100-message boundary, and one user not seeing another's conversations.
Source: implied: U-17

### C-51: Users without the permission set see no change in the org
Observable: A user not assigned the permission set sees the same apps, tabs, layouts and data as before deployment.
Source: implied: U-19
