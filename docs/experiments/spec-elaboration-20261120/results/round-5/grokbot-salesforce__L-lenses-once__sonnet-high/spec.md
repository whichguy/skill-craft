## Use cases

### U-1: An administrator puts the Grok bot into a Salesforce development org and gets it working
Flow: The administrator deploys the bot's source to a development org (Developer Edition, sandbox or scratch org) with the Salesforce CLI. They follow the written setup steps: enter their xAI API key in Setup, assign the chat permission set to themselves, schedule the history-cleanup job, and open the Grok app from the App Launcher. They type "Hello" and see a reply from Grok. Before the key is entered, the same attempt shows a "bot is not configured" message that tells the user to contact an administrator.
Source: request ("Create a Grok bot in a Salesforce development org"); implied: a bot that cannot be installed and keyed by one person is not usable

### U-2: A Salesforce user asks Grok a question and reads the answer
Flow: The user opens the Grok app from the App Launcher and sees the chat panel with a notice that messages are sent to xAI. They type a question and press Send. Their message appears at once in the transcript. A "Grok is replying" indicator shows and the input is disabled. After some seconds Grok's whole answer appears below their message, labelled as Grok.
Source: request ("Grok bot"); implied: a bot is something you talk to and it answers

### U-3: The user holds a conversation with follow-up questions
Flow: After Grok's first answer, the user sends "Make that shorter". Grok's answer refers to its own previous answer, because the earlier turns of the conversation are sent along with the new message. The user continues for many turns, up to the conversation's message cap.
Source: implied: a chat bot that forgets the previous turn is not a conversation

### U-4: The user starts a fresh conversation
Flow: The user clicks "New conversation". The transcript empties. Grok is no longer given anything from the earlier conversation. The user asks an unrelated question and the answer does not draw on the earlier exchange.
Source: implied: a conversation has to be able to end, and its cap (200 messages) has to be escapable

### U-5: The user leaves and comes back
Flow: The user reloads the page, navigates to another Salesforce page, or returns the next day. They open the Grok app. They see their latest conversation, with every message in order, including any answer that arrived while they were away. A conversation they have not touched for the retention period (default 30 days) is gone.
Source: implied: Lightning navigation discards page state, so continuity needs stored history; choice: storage is bounded by a retention period because a development org has little data storage

### U-6: The user meets a failure and recovers
Flow: The user sends a message and something goes wrong: the key is wrong, xAI is overloaded, xAI is slow, the network drops, they hit the hourly cap, the message is empty or too long, the bot is disabled, or the conversation is full. They see a message that says whether to wait and retry or to contact the administrator. Their typed text is not lost and they can send it again. The page does not freeze or show a raw error.
Source: implied: every call to an outside service can fail; the request names a bot that depends on xAI

### U-7: A person who should not use the bot is kept out
Flow: A user who does not hold the chat permission set does not see the Grok app. If they call the chat server code directly, they are refused. A user with the permission set sees only their own conversations, never anyone else's.
Source: implied: conversations can hold confidential text and the bot spends the administrator's paid key

### U-8: The administrator tunes, pauses and re-keys the bot
Flow: In Setup the administrator changes the model, the system prompt, the reply-length cap, the history length, the hourly per-user cap, the retention period, or switches the bot off. They replace the API key. The next message anyone sends uses the new values. No redeploy is needed. Switching off makes the chat refuse new messages and show a notice, while existing history stays readable.
Source: implied: model names, prompts and keys change over time; an operator needs a stop switch for a paid external service

### U-9: The administrator observes how the bot is doing and cleans up
Flow: The administrator opens a list of failed messages (newest first) and reads each one's failure category and HTTP status. They open conversations to see the transcripts, see token counts per answer, and delete a conversation, which removes its messages too.
Source: implied: an operator must be able to tell why a bot is failing and what it is costing

### U-10: Someone redeploys, moves or removes the bot
Flow: A developer redeploys a newer version of the source over an org that already holds conversations. Everything stored remains and keeps working. A developer deploys the same source to a second org and finds it unconfigured until a key is entered there. An administrator removes the bot by following the removal steps and the org has none of the bot's components and no scheduled job left.
Source: implied: the "operator carries on with existing data, and can go back" lines of the specification brief

### U-11: Two sends overlap
Flow: The user double-clicks Send, or has the app open in two browser tabs and sends from both. Only one request for the conversation is in flight at a time. The second attempt is refused with a "reply in progress" message and nothing is sent to Grok for it. The user clicks "New conversation" while an answer is pending. The answer lands in the old conversation and the new one stays empty.
Source: implied: a bot that sends twice is billed twice; the Lightning UI makes two tabs ordinary

### U-12: A developer verifies the bot and prepares it for another org
Flow: The developer runs all Apex tests in the org. They pass without any real call to xAI and cover enough code for a deployment to production. They are told, in the setup notes, which steps must be repeated per org.
Source: implied: Salesforce will not deploy Apex to production without passing tests and enough coverage; the request names a development org, which implies later promotion

## Clauses

### C-1: The bot is a chat page inside a Lightning app that appears in the App Launcher in Lightning Experience
Observable: A user holding the chat permission set opens the App Launcher in Lightning Experience and finds an app whose name contains "Grok". Opening it shows the chat panel. The bot is offered nowhere else: not in Salesforce Classic, not in the Salesforce mobile app, not in Experience Cloud sites, not to guest users.
Source: choice: the request does not say where the bot lives; a single Lightning app is the smallest place a user can find

### C-2: Two permission sets control access: one to chat, one to administer
Observable: Setup lists two permission sets for the bot. A user holding only the chat one can use the chat and cannot open or change the settings. A user holding the administer one can open and change the settings and read every conversation. The names are the builder's choice, but the setup notes give them.
Source: implied: use cases U-7 and U-8 need two roles

### C-3: A user without the chat permission is refused in the interface and at the server
Observable: A user without the chat permission set does not see the Grok app in the App Launcher. If the chat server methods are called directly for that user, the call is refused with an access error, no record is written and no call to xAI is made.
Source: implied: U-7; the rule must hold on every path, not only in the screen

### C-4: A user can read only their own conversations and messages
Observable: User B, holding the chat permission set, cannot see user A's conversations or messages through the chat panel, through a list view, through a report or through a SOQL query. Only user A, and administrators holding the administer permission set, can.
Source: implied: U-7; conversations may contain confidential text

### C-5: The xAI API key is held as a secret and is never readable after it is saved
Observable: The key is not in the deployed source, not in any custom object or setting record, not in any field a user can query, and not visible in Setup after saving (the field shows masked or empty). Searching the debug log of a full chat exchange for the key finds nothing.
Source: implied: a paid credential must not leak; Salesforce provides credential storage for exactly this

### C-6: The API key never reaches the browser
Observable: Inspecting every network response and all page data delivered to the user's browser does not reveal the key or any Authorization header.
Source: implied: C-5 must hold on the wire, not only at rest

### C-7: The key is entered by an administrator in Setup after deployment, and until then the bot says it is not configured
Observable: Deploying to an org that has never held a key and sending a message gives a failure of category "not configured" that tells the user to contact an administrator; no secret exists in the org. After an administrator enters the key in Setup, the next message succeeds with no further deployment. Secrets do not travel with source deployment, which is why the step exists in every org.
Source: implied: U-1 and U-10; runtime rule: a secret credential value cannot be deployed as source metadata

### C-8: The bot calls only the xAI chat-completions endpoint, https://api.x.ai/v1/chat/completions, authenticated with the bearer key
Observable: Capturing the org's outbound callouts during a chat shows requests of method POST to https://api.x.ai/v1/chat/completions with an Authorization bearer header, and requests to no other host. No administrator step to allow the host (such as a Remote Site Setting) is needed beyond what deployment brings.
Source: request ("Grok bot"); implied: Grok is reached through xAI's API; xAI's endpoint and its OpenAI-compatible shape are an outside fact, unconfirmed against the current xAI documentation at spec time

### C-9: The browser never contacts xAI itself; every Grok request comes from the server
Observable: A network trace of the browser while chatting shows no request to any x.ai host. The rule the runtime imposes is that Lightning pages may not call arbitrary external hosts (Content Security Policy), so the call must be made by server code.
Source: implied: runtime rule (Lightning Content Security Policy); also protects C-6

### C-10: Each request to Grok carries exactly these items: the system prompt, the history window, the new message, the model name and the reply-length cap
Observable: The request body of a callout holds (a) the system prompt as the first message if it is not blank (C-26), (b) the prior messages chosen by C-22 in chronological order with their roles, (c) the new user message last, (d) the configured model (C-28), and (e) the maximum reply tokens (C-29). Nothing else about the user or the org is in the body.
Source: implied: U-3; choice: nothing beyond this is sent, because the data leaves the org

### C-11: No Salesforce record data and no user identity are sent to Grok unless the user typed it
Observable: The callout carries no Salesforce record content, no user name, email or Id, and no org Id or URL, except text the user typed into their message.
Source: implied: the bot talks to a third party; choice: the loosest rule that keeps org data from leaving by itself

### C-12: The chat panel tells the user, before they send, that their messages are sent to xAI
Observable: The panel shows, on first view, a visible notice stating that messages are sent to xAI's Grok service.
Source: choice: users need to know where their text goes; the request is silent

### C-13: The bot never creates, changes or deletes any Salesforce business data on the strength of what Grok says
Observable: After any conversation whatever Grok replied (including text that asks the bot to do something), no record of any standard or custom object other than the bot's own conversation and message records has been created, changed or deleted by the bot.
Source: choice: the request asks for a bot that converses, not an agent with write tools; this closes the door on a reply acting on the org

### C-14: The chat accepts typed text only
Observable: The panel has no control to attach files or images, and Grok's replies are shown as text only.
Source: choice: the request names no attachments; text is the loosest form that serves a bot

### C-15: An empty message cannot be sent
Observable: A message that is empty, or only spaces, tabs and line breaks, cannot be sent: the Send control is disabled or a send does nothing. No call to Grok is made and no record is written.
Source: implied: U-6; every input field takes empty input

### C-16: The panel stops a message longer than 4,000 characters and shows how far over it is
Observable: After removing leading and trailing whitespace, a message of exactly 4,000 characters can be sent and one of 4,001 cannot. The panel shows the current character count against 4,000 and the amount over. Nothing is sent.
Source: choice: the request gives no limit; 4,000 characters is large for a chat turn and keeps requests well inside the callout size limits

### C-17: The server also rejects a message longer than 4,000 characters or empty after trimming
Observable: Calling the server method directly with a 4,001-character message, or with an empty or whitespace-only message, returns a rejection, writes no record and makes no call to xAI.
Source: implied: a rule enforced in the screen and not on the server is a rule that can be bypassed

### C-18: The user's message appears in the transcript, labelled as theirs, as soon as they send it, before the answer arrives
Observable: Within about one second of pressing Send, the transcript shows the typed text as the latest entry, labelled as the user's.
Source: implied: U-2

### C-19: While an answer is pending the panel shows a "Grok is replying" indicator and does not accept another send
Observable: From pressing Send until the answer or failure arrives, an indicator is visible and the Send control and input are disabled. Pressing Enter or clicking Send again does nothing.
Source: implied: U-2 and U-11; a double-click must not send twice

### C-20: Grok's answer appears all at once, after the user's message, labelled as Grok
Observable: The answer is not shown word by word. It appears as one complete entry labelled as Grok, below the message it answers. The runtime does not let the server push partial output to the page during one request, which forces this.
Source: implied: U-2; runtime rule: a synchronous server call returns one result

### C-21: Grok's answer is shown as plain text with its line breaks kept, and any markup in it is shown as characters and never run
Observable: If Grok's reply contains `<script>alert(1)</script>` or `<b>x</b>`, the transcript shows those characters literally; no script runs and nothing is rendered as bold. Line breaks in the reply appear as line breaks.
Source: implied: a reply from an outside service is untrusted content; choice: plain text is the loosest rendering that is safe

### C-22: Each request carries up to the N most recent earlier messages of the same conversation, oldest first
Observable: With N = 20, in a conversation of 30 earlier successful messages the request body holds the 20 most recent of them in chronological order, followed by the new message. A conversation of 3 earlier messages sends all 3. Older messages remain stored and visible and are not sent.
Source: implied: U-3; choice: a window keeps request size and cost bounded

### C-23: A message that failed, and its absence of an answer, is not sent as history in later requests
Observable: After a failed attempt, the next successful request contains neither the failed user message nor any failure notice among its history messages. The failed text sent again by the user appears once.
Source: choice: a message Grok never answered is not part of the conversation Grok had

### C-24: A "New conversation" control starts an empty conversation and the earlier one is no longer sent or shown
Observable: Clicking "New conversation" empties the transcript. The next request carries no message from the earlier conversation. The earlier conversation's stored records still exist until retention or deletion removes them.
Source: implied: U-4

### C-25: The history window N is an administrator setting; default 20, allowed 2 to 50
Observable: The settings carry "history messages sent" with default 20; a value of 2 to 50 inclusive is used as given.
Source: choice: the request is silent on context length; a bounded window with a default

### C-26: The system prompt is sent as the first message if it is not blank, and it is not shown in the transcript
Observable: With a non-blank system prompt, the first message in the callout body is the system prompt with the system role. With a blank prompt, no system message is in the body. The transcript never shows it.
Source: implied: U-8; a bot needs a way to be given its role

### C-27: The default system prompt is non-blank and tells Grok it is an assistant for Salesforce users
Observable: In an org with no settings change, the callout's first message is a non-blank system prompt that describes Grok as an assistant helping users of a Salesforce org. Its exact wording is not fixed.
Source: choice: a bot in Salesforce is expected to be useful to Salesforce users out of the box

### C-28: The model is an administrator setting, sent exactly as entered; the default is grok-4
Observable: The callout's model field equals the model setting. Default is the text `grok-4`. The bot makes no check that the name is valid and relies on xAI's answer. Whether `grok-4` is still offered by xAI at build time is unconfirmed.
Source: choice: the request says "Grok" and no model; the model catalogue changes, so the name is a setting

### C-29: The reply length is capped by an administrator setting; default 2,048 tokens, allowed 1 to 8,192
Observable: The callout carries the maximum reply token value from settings: 2,048 by default, a value of 1 to 8,192 inclusive used as given.
Source: choice: bounds cost and the size of what is stored; runtime rule: a stored long text field holds at most 131,072 characters, and the synchronous response size is limited (6 MB heap), so replies must be bounded

### C-30: When xAI says the reply was cut off by the length cap, the user sees the partial answer and a note that it was cut off
Observable: If xAI's response reports finish reason "length", the transcript shows the partial text with a visible note stating the answer was shortened, and the message is recorded as successful.
Source: implied: C-29 creates the case; a silently truncated answer misleads

### C-31: The bot waits up to 100 seconds for Grok's answer and then gives up with a timeout failure
Observable: When xAI does not answer within 100 seconds the user sees a "try again later" failure (C-41) and the message is recorded failed with category timeout. Salesforce allows at most 120 seconds for one callout and for all callouts in one request together, which is why the figure is below 120.
Source: choice: 100 seconds, below the platform's 120-second ceiling; runtime rule: callout timeout maximum 120 seconds

### C-32: The bot never retries a failed request on its own
Observable: For any failure, the callout log shows exactly one request to xAI for that send. Only the user pressing Send again makes another.
Source: choice: an automatic retry could double the billing and, with a 100-second wait, the 120-second platform ceiling

### C-33: A conversation holds at most 200 messages; at the limit a send is refused and the user is told to start a new conversation
Observable: Counting user and Grok messages, including failed ones, a conversation with 200 messages refuses a further send: no callout, no record, and the user is told to click "New conversation". A conversation with 199 accepts one more user message.
Source: choice: bounds storage in an org whose data storage is small (a Developer Edition org holds 5 MB; the exact figure is unconfirmed) and bounds what the panel loads

### C-34: Each user may send at most 30 messages to Grok in any rolling 60 minutes (administrator setting)
Observable: With the default, a user's 30th attempt in an hour that reaches the callout stage is made and their 31st is refused with a message saying the hourly limit is reached: no callout, no record. When their oldest counted attempt is more than 60 minutes old they may send again. Failed attempts that reached the callout stage count. Refusals do not count. The limit is counted on the server, so two tabs cannot exceed it.
Source: choice: the key is the administrator's paid credential; the request names no cost control, and 30 is a chosen default

### C-35: Only one request per conversation may be in flight at a time, across tabs and devices; a marker older than 120 seconds is ignored
Observable: While a send is awaiting its answer, a second send into the same conversation from any tab, browser or device is refused with a "reply in progress" message and makes no callout and no record. If the first request died without finishing, a send into the conversation is accepted again once 120 seconds have passed since it began.
Source: implied: U-11; choice: 120 seconds because no request can legitimately last longer than the platform's 120-second callout ceiling

### C-36: An answer that arrives after the user clicked "New conversation" is stored in, and shown with, the conversation it was asked in
Observable: With a send pending, the user clicks "New conversation" and then sends in the new conversation. The pending answer appears only in the original conversation's records and never in the new transcript. The new conversation's own send is not blocked by the old one.
Source: implied: U-11

### C-37: What the transcript shows is what is stored; no answer is shown that was not saved
Observable: After a send, reloading the page shows the same messages in the same order as the panel showed before reloading. If saving the answer fails (for example because the org's data storage is full), the user sees a failure of category "save failed" (C-40) and no Grok answer is shown for that send.
Source: implied: U-5 and "data lost on the way must never be true"

### C-38: Sending works while the history is being saved
Observable: In an org with the bot installed, a send produces both the user message record and the Grok answer record and the user sees the answer; no "uncommitted work pending" error appears. Salesforce forbids a callout after unsaved database changes in the same request, so the builder must order work so this holds.
Source: implied: U-2; runtime rule: callout after uncommitted DML is refused by the platform

### C-39: When an administrator has switched the bot off, new messages are refused and a notice is shown; history stays readable
Observable: With "enabled" off, the panel shows a notice that the bot is switched off, sending produces a refusal with no callout and no record, and the existing transcript is still shown. Switching it on again restores sending with no other step.
Source: implied: U-8; an operator needs a stop for a paid external service

### C-40: Failures that need an administrator tell the user to contact an administrator; the members are: not configured, key or access rejected, model or request rejected, other unexpected response, save failed
Observable: These cases show a message advising the user to contact their administrator, and no suggestion to retry immediately: (a) no key entered; (b) HTTP 401 or 403 from xAI; (c) HTTP 400 or 404 from xAI (including an unknown model); (d) any other HTTP status outside 200 to 299 that is not in C-41, including 3xx and 4xx other than 408 and 429; (e) the answer could not be saved (C-37). Each is recorded failed with its category.
Source: implied: U-6; choice: the split is by who can fix it, which is what a user relies on

### C-41: Failures that clear by themselves tell the user to try again later; the members are: xAI rate limited, xAI server error, timeout, network failure, empty or unreadable answer
Observable: These cases show a message advising the user to try again later: (a) HTTP 429; (b) HTTP 408 or any 500 to 599; (c) the 100-second timeout (C-31); (d) no network answer (connection refused, DNS failure, dropped connection); (e) a 2xx response with no answer text or with a body that cannot be read as an answer. Each is recorded failed with its category.
Source: implied: U-6; the same split as C-40

### C-42: The user never sees xAI's raw error text, a stack trace, the key or another user's data in a failure message
Observable: Any failure message in the panel is the bot's own text for its category, with no HTTP body, exception text, class name or credential in it.
Source: implied: U-6; internal details help an attacker and confuse a user

### C-43: After a failure the user's message stays in the transcript marked as not delivered and its text is put back in the input box
Observable: After any failure that follows a send, the transcript shows the user's message with a visible "not delivered" mark, no Grok entry under it, and the input box holds the same text, so the user can press Send again. Pressing Send again produces a new message and one new request.
Source: implied: U-6; the user's typing must not be lost

### C-44: When the browser's request to the server itself fails, the panel shows an error and keeps the user's text
Observable: If the connection between the browser and Salesforce drops or Salesforce refuses the request (for example because the org has too many concurrent long-running requests; the exact org figure, around 10 in production and fewer in developer orgs, is unconfirmed), the panel shows a "could not send, try again" message, re-enables the input and keeps the typed text. No answer is shown.
Source: implied: U-6; runtime rule: concurrent long-running request limit

### C-45: Every attempt that passed the local checks is stored as a message record with its outcome
Observable: An attempt that reaches the callout stage leaves a user message record, and either a Grok answer record, or the user message record marked failed with the category and the HTTP status where one exists. Refusals made before the callout stage (empty, too long, bot off, hourly cap, conversation full, reply in progress, no access) leave no record.
Source: implied: U-9; choice: refusals are not worth the storage

### C-46: Opening the app shows the user's latest conversation, oldest message first
Observable: Opening the Grok app shows the user's most recently active conversation that has not been closed by "New conversation", with every message in time order, including any answer that arrived while the page was closed.
Source: implied: U-5

### C-47: With no conversation yet, or after "New conversation", the panel shows an empty prompt and the first send creates the conversation
Observable: A user opening the app for the first time sees no messages and an invitation to type. Their first send creates a conversation record owned by them.
Source: implied: the first-time edge of U-2

### C-48: A conversation record holds: owner, started time, last activity time, status (open or closed), and the time a request began awaiting an answer
Observable: A conversation record shows these five items to an administrator. "Closed" is set on a conversation when its owner clicks "New conversation". The "request began" time is blank when nothing is pending.
Source: implied: C-24, C-35, C-50

### C-49: A message record holds: its conversation, role (user or Grok), text, time sent, order within the conversation, status (success or failed), failure category, HTTP status, failure detail, model used, finish reason, prompt tokens and completion tokens
Observable: An administrator opening a message record sees these thirteen items. Failure fields are blank on successes. Model, finish reason and token counts are filled on Grok answers where xAI's response carries them and otherwise blank. Failure detail is xAI's error message cut to 500 characters, or blank when there is none, and never holds the key.
Source: implied: U-9; choice: 500-character detail aids diagnosis without storing whole response bodies

### C-50: A conversation, with all its messages, is deleted when its last activity is older than the retention period; default 30 days, allowed 1 to 365
Observable: A daily job removes every conversation whose last activity is more than the retention period ago, together with its messages, whether open or closed, in batches, so that a large number does not exceed platform limits. A conversation 29 days idle remains and one 31 days idle is removed (default). The job exists only after the scheduling step of the setup notes has been done, because Salesforce does not schedule jobs on deployment.
Source: choice: state needs an end and a development org's data storage is small; runtime rule: scheduled Apex must be scheduled in the org

### C-51: Deleting a conversation deletes its messages, and a message cannot exist without its conversation
Observable: An administrator deleting a conversation finds none of its messages left, by list view or query. No message record is ever found with no conversation.
Source: implied: U-9; "data left behind" must not be true

### C-52: The administrator settings are: enabled, model, system prompt, history messages sent, maximum reply tokens, messages per user per hour, retention days
Observable: Setup shows exactly these seven settings for the bot. The key is entered through the credential storage (C-7), not among them.
Source: implied: U-8; this is the list of every control an operator has

### C-53: Setting defaults are: enabled on, model grok-4, a non-blank Salesforce-assistant prompt, 20 history messages, 2,048 tokens, 30 messages per hour, 30 days
Observable: In an org where nobody has changed settings, the bot behaves as these values say. Allowed ranges: history messages 2 to 50 (C-25), reply tokens 1 to 8,192 (C-29), messages per hour 1 to 500, retention days 1 to 365.
Source: choice: defaults let a freshly keyed bot work; the request gives none

### C-54: A setting that is blank, not a number where a number is needed, or outside its range is never used; its default is used instead
Observable: With messages per hour set to 0 or 501, or history messages set to 1 or 51, or reply tokens set to 8,193, the bot behaves as with the default for that setting.
Source: implied: every number has a boundary; choice: fall back rather than fail

### C-55: With no settings record at all, the bot uses the defaults and is switched on
Observable: Right after deployment, before anyone opens the settings, a keyed org's bot answers using the defaults.
Source: implied: first-time edge of U-1

### C-56: Only holders of the administer permission set can change the settings
Observable: A user with only the chat permission set cannot open the settings page or edit its values.
Source: implied: U-7 and U-8

### C-57: A settings change takes effect on the next message anyone sends, with no redeploy
Observable: After an administrator saves a changed setting, the next callout reflects it. A request already awaiting its answer is unaffected.
Source: implied: U-8

### C-58: Replacing the API key takes effect on the next message and keeps all history
Observable: After the administrator saves a new key, the next send authenticates with it. Existing conversations and messages are unchanged and can be continued.
Source: implied: U-8; keys are rotated

### C-59: The administrator has a list of failed messages, newest first, showing time, category, HTTP status and the owning user
Observable: An administrator opens the bot's failed-message list view and sees every message marked failed, newest at the top, with those four items per row.
Source: implied: U-9

### C-60: Token usage reported by xAI is stored with each Grok answer
Observable: When xAI's response carries prompt and completion token counts, the answer's message record shows them; when it does not, they are blank.
Source: implied: U-9; an operator of a paid service must be able to see usage

### C-61: The source deploys to a development org with the Salesforce CLI, and a written setup guide lists the steps an operator must do afterwards
Observable: A single deploy command against a Developer Edition org, sandbox or scratch org succeeds with no errors, and the repository's setup notes list, in order: deploy; enter the API key in Setup; assign the chat permission set; assign the administer permission set to administrators; schedule the cleanup job; open the app; the removal steps (C-64); and the per-org repeat for another org. Following them gives a working bot.
Source: request ("in a Salesforce development org"); implied: U-1

### C-62: Redeploying a newer version keeps all stored conversations, messages and settings
Observable: After redeploying over an org that holds conversations, messages and settings, all of them are still there and the bot keeps working with them, with no manual step beyond what the setup notes say.
Source: implied: U-10; "carry on with data that already exists"

### C-63: Deploying the bot changes nothing that already existed in the org
Observable: After deployment, every pre-existing profile, permission set, standard and custom object and field, flow, Apex class, trigger, page and setting is unchanged; the only differences are the bot's own new components.
Source: implied: the bot is added to an org whose existing behaviour must stay

### C-64: Following the removal steps leaves the org with none of the bot's components, data, permission set assignments or scheduled job
Observable: After the removal steps, Setup holds no bot object, class, page, app, permission set or scheduled job, the stored conversations and messages are gone, and the org behaves as before installation. The steps are in the setup notes.
Source: implied: U-10; "go back to the version before"

### C-65: Apex tests pass in the development org, make no real call to xAI, and cover enough code to deploy to production
Observable: Running all of the bot's Apex tests in the org gives zero failures and zero real outbound calls (Salesforce forbids callouts in tests, so a simulated xAI is used). Test coverage of each of the bot's Apex classes is at least 75%, the figure Salesforce requires for deploying to production (org-wide 75% and all tests passing).
Source: implied: U-12; runtime rule: production deployments require 75% coverage and passing tests

### C-66: The debug log never holds the API key or the text of a user's message or of Grok's answer
Observable: With the highest debug log level on for a user, a full send leaves nothing in the log that contains the key, the user's typed text or Grok's answer text.
Source: implied: C-5 and C-11; logs are readable by more people than the conversation is

### C-67: The chat panel can be used with the keyboard alone and announces a new answer to screen readers
Observable: A user can reach the input, the Send control and "New conversation" with Tab, and send with the keyboard. When an answer or a failure appears, the panel announces it through a live region.
Source: choice: the request is silent; this is the loosest rule that does not shut out keyboard and screen-reader users
