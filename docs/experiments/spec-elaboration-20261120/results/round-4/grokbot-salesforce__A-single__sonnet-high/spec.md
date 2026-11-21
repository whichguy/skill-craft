## Use cases

### U-1: A Salesforce user asks Grok a question, to get an answer without leaving Salesforce
Flow: The user opens the Grok bot in Salesforce, types a question, and sends it. A waiting indicator shows while the request is in progress. Grok's answer then appears under the question in the same conversation.
Source: request

### U-2: A user follows up in the same conversation, to get an answer that builds on what was said before
Flow: After an answer, the user sends a second message that only makes sense given the earlier ones (e.g. "make that shorter"). The answer reflects the earlier messages.
Source: implied: a "bot" is conversational; a follow-up that is answered as if it were the first message would be useless

### U-3: A user opens the bot for the very first time, to start chatting
Flow: The user has never used the bot. They open it and see an empty state with no conversations and an input they can type into immediately.
Source: implied: first-time edge of U-1

### U-4: A returning user comes back later, to resume earlier work
Flow: The user opens the bot after signing out, or days later. Earlier conversations are listed. They pick one, see every message in order, send another message, and the bot continues with that conversation's context.
Source: implied: repeated-use edge of U-1; a bot "in a Salesforce org" keeps its data in the org

### U-5: A user starts a fresh conversation, to ask about something unrelated
Flow: The user chooses to start a new conversation. The view is empty. Whatever they send is answered with no knowledge of the previous conversations. The previous conversations remain in the list.
Source: implied: repeated-use edge of U-1

### U-6: A user sends an empty message
Flow: The user clicks send with nothing typed, or with only spaces and line breaks. They see a message that there is nothing to send. Nothing is sent to Grok and the conversation is unchanged.
Source: implied: wrong-input edge of U-1

### U-7: A user sends a very large message
Flow: The user pastes a long text. At or under the limit it is sent and answered. Over the limit, they see a message naming the limit, their text stays in the input so they can shorten it, and nothing is sent.
Source: implied: largest-case edge of U-1; Salesforce text fields and callout payloads are finite

### U-8: A user sends a message while Grok cannot answer, to find out what went wrong and try again
Flow: The user sends a message. Grok times out, is unreachable, rate-limits the request, or refuses it as a bad request. The user sees an error that says which kind of problem it was in plain words, their conversation is unharmed, and they can send again.
Source: implied: unhappy paths of U-1 (a limit reached, a refused action)

### U-9: A user without access tries to use the bot
Flow: A Salesforce user who has not been given access does not see the bot in their navigation. If they reach it by a direct link or call, they are denied.
Source: implied: a dev org has many users; the operator decides who may use a paid external AI service

### U-10: A user keeps chatting until the conversation is very long, and a user receives a very long answer
Flow: The user sends many messages in one conversation until the conversation limit is reached; they are told to start a new conversation and can still read everything already there. Separately, Grok returns an extremely long answer and the user sees it up to the display limit, with a notice if it was cut.
Source: implied: largest-case edge of U-1 and U-2

### U-11: Several users chat at the same time, privately
Flow: Two users use the bot at once. Each sees only their own conversations, and each answer lands in the conversation that asked for it.
Source: implied: a Salesforce org is multi-user; conversations may contain sensitive text

### U-12: An administrator sets the bot up for the first time, to make it usable
Flow: The administrator deploys the bot into the development org, supplies a Grok (xAI) API key in the org's configuration, assigns access to users, and sends a test message successfully. No source code is edited to do this.
Source: implied: "Create a Grok bot in a Salesforce development org" — it must be creatable and usable; the API key is a secret that cannot be shipped in code

### U-13: An administrator reconfigures the bot, to rotate the key or change the model
Flow: The administrator replaces the API key or changes the Grok model name in configuration. The next message sent uses the new setting. Existing conversations continue.
Source: implied: operator configures; keys expire and models change

### U-14: An administrator starts the bot with the key missing or wrong, to find out why it fails
Flow: The key was never entered or is invalid. A user sends a message and sees a message that the bot is not set up correctly and an administrator must fix it. The administrator can tell from that message (without seeing the key) that the problem is configuration.
Source: implied: unhappy path of U-12

### U-15: An administrator redeploys or restarts the bot over an org that already has data
Flow: The administrator deploys the same or a newer version of the bot into the org where users already have conversations. The deployment succeeds, and users find their conversations, the configuration and access assignments exactly as before.
Source: implied: operator restarts and carries on with the data that exists today

### U-16: An administrator goes back to the previous version of the bot
Flow: After a newer version causes trouble, the administrator deploys the previous version. The bot works as the previous version did and no conversation recorded under the newer version is lost.
Source: implied: operator goes back to the version before

### U-17: An administrator wants the bot to sit alongside what the org already has
Flow: The org already has users, permission sets, objects, and automation. After the bot is deployed, all of that behaves as before; the only differences are the bot's own additions.
Source: implied: touches things that already exist

## Clauses

### C-1: A message sent by a user is answered by Grok, in the same conversation
Observable: With a valid key configured, the user types "Say hello" and sends it. After a wait, a reply written by Grok appears directly after the user's message in the same conversation.
Source: request

### C-2: The answer shown is the answer Grok (xAI) returned
Observable: The reply text is the content returned by xAI's Grok chat service for that request, not a canned or locally generated reply. Disconnecting the network or revoking the key makes replies stop.
Source: request

### C-3: Earlier messages of the same conversation are given to Grok as context
Observable: The user sends "My name is Priya." and then in the same conversation sends "What is my name?". The reply says Priya.
Source: implied: U-2

### C-4: At least the 20 most recent messages of the conversation are given as context
Observable: In a conversation with 40 messages, the next message sent is answered with the 20 most recent messages (user and Grok together) taken into account. Older ones may be left out.
Source: choice: Grok's context is finite and a callout payload is bounded; a fixed floor tells users how far back the bot is guaranteed to remember

### C-5: A new conversation has no memory of other conversations
Observable: After telling Grok a name in one conversation, the user starts a new conversation and asks for the name. Grok does not know it.
Source: implied: U-5

### C-6: Both the user's message and Grok's reply are saved in the conversation, in order
Observable: After an exchange the user signs out, signs in, and opens the conversation. Both messages are present, user message first, then Grok's reply, with the text unchanged.
Source: implied: U-4

### C-7: The first time a user opens the bot, they see an empty state
Observable: A user who has never sent a message sees no conversations and an input ready for typing. No error is shown.
Source: implied: U-3

### C-8: A user's earlier conversations are listed and can be reopened
Observable: A user with three conversations sees all three in the list, can select any one, and sees its full message history. The list shows most recently active first.
Source: implied: U-4; the ordering is a choice: the most recently used is the one most likely wanted

### C-9: A user can start a new, empty conversation at any time
Observable: Choosing "new conversation" shows an empty conversation. The first message sent creates a conversation that appears in the list. The previous conversation is unchanged.
Source: implied: U-5

### C-10: An empty or whitespace-only message is not sent
Observable: Sending "" or "   \n  " shows a message that there is nothing to send. No request goes to xAI and no message is added to the conversation.
Source: implied: U-6

### C-11: A message of up to 10,000 characters is accepted
Observable: A message of exactly 10,000 characters is sent and answered normally.
Source: choice: a bound is needed because a message must fit a Salesforce text field and a Grok request; 10,000 characters covers a long pasted document excerpt

### C-12: A message of more than 10,000 characters is refused, and the text is kept
Observable: A message of 10,001 characters is not sent; the user sees a message that contains the number 10,000. No xAI request is made, nothing is added to the conversation, and the typed text is still in the input.
Source: implied: U-7

### C-13: While a message is awaiting its answer, the user sees a waiting indicator and cannot send again from that conversation
Observable: After clicking send, a visible waiting indicator appears and send is unavailable until the reply or an error arrives. Clicking send twice in quick succession results in exactly one user message and one request to xAI.
Source: implied: a reply can take many seconds; double-submits would duplicate messages and spend the user's quota

### C-14: A reply that has not arrived within 120 seconds is reported as a timeout
Observable: If Grok has not answered 120 seconds after the send, the user sees an error stating the request timed out. No reply is added to the conversation, and the user can send again.
Source: implied: U-8; the number is the platform's maximum wait for a callout from Salesforce, so no longer wait is possible

### C-15: When Grok cannot be reached or reports a server fault, the user is told to try again
Observable: When the connection to xAI fails or xAI answers with a server error (HTTP 5xx), the user sees an error saying Grok is unavailable and to try again. The conversation is unchanged and a later send can succeed.
Source: implied: U-8

### C-16: When xAI rate-limits the request (HTTP 429), the user is told it is a rate limit
Observable: The user sees an error that mentions that a rate limit was reached and to try again later. The conversation is unchanged and a later send can succeed.
Source: implied: U-8 (a limit reached)

### C-17: When Salesforce itself is too busy to make the call, the user is told to try again
Observable: When the org has too many long-running requests in progress (Salesforce allows 10 at a time), a user whose send is refused for that reason sees a message that the bot is busy and to try again shortly. No data is lost or duplicated.
Source: implied: U-8; a platform rule limits concurrent long-running requests in an org, and every bot call is one

### C-18: When xAI rejects the key (HTTP 401 or 403), the user is told the bot is misconfigured and the key is not shown
Observable: The user sees a message that the bot is not set up correctly and an administrator must act. The message does not contain the key or any part of it.
Source: implied: U-14

### C-19: When no key has been configured, no request is sent and the user is told the bot is not set up
Observable: With the key never entered, a send shows the same kind of message as a rejected key (the bot is not set up and an administrator must act). No request to xAI is made.
Source: implied: U-14

### C-20: A refusal written by Grok is shown as an ordinary reply
Observable: When Grok answers with text declining a request, that text appears as Grok's reply in the conversation, like any other reply.
Source: implied: Grok may decline; declining is an answer, not an error

### C-21: When xAI rejects the request for any other client reason (other HTTP 4xx), the user sees a failure message with no internal details
Observable: The user sees a message that the request could not be completed. The message contains no key, no request headers, and no stack trace. The conversation is unchanged.
Source: implied: U-8

### C-22: A failed send adds nothing to the conversation and does not affect later context
Observable: After any error (timeout, unreachable, rate limit, rejected), the transcript has the same messages as before the send, and the user's typed text is still in the input so they can send again. A later successful send gives Grok no trace of the failed one.
Source: choice: the simplest rule that leaves no half-finished exchange to explain or repair

### C-23: Replies up to 100,000 characters are shown in full
Observable: A reply of 100,000 characters is saved and displayed completely.
Source: choice: a stored reply must fit a Salesforce long text field (131,072 characters at most); 100,000 leaves margin

### C-24: A reply longer than 100,000 characters is cut at 100,000 and the user is told it was cut
Observable: When Grok returns more than 100,000 characters, the first 100,000 are shown and a notice says the reply was shortened.
Source: choice: companion to the limit above; a silent cut would mislead

### C-25: A conversation holds at most 200 messages
Observable: In a conversation with 200 messages (user and Grok together), sending is refused with a message to start a new conversation. All 200 remain readable, and no request goes to xAI.
Source: choice: needed so a single conversation cannot grow without bound

### C-26: Only users who have been given access can see and use the bot
Observable: A user with the bot's access sees it in their navigation and can use it. A user without that access does not see it, and a direct link or direct call to it is denied.
Source: implied: U-9

### C-27: Access is given to a user by assigning one named access grant that the administrator can assign and remove
Observable: The administrator assigns the bot's permission set to a user: the user can then use the bot. The administrator removes it: the user can no longer use the bot, and their past conversations are not deleted.
Source: implied: U-9, U-12

### C-28: A user can see only their own conversations
Observable: User A's conversations are not in user B's list, are not readable by B by opening a link, and are not returned to B by any bot query.
Source: choice: private by default is the safest rule that serves a chat bot; sharing was not asked for

### C-29: Simultaneous users do not affect each other
Observable: Users A and B send messages at the same time. A's reply appears in A's conversation, B's reply appears in B's, and neither sees the other's text.
Source: implied: U-11

### C-30: Only the conversation's own messages are sent to xAI
Observable: Inspecting the request sent to xAI shows the user's messages, Grok's earlier replies in that conversation, and nothing read from other Salesforce records (no contacts, accounts, cases, users' names or emails).
Source: choice: the request asks for a Grok bot, not for CRM data to be shared with a third party; sending none is the safest reading

### C-31: The bot tells users that their messages are sent to xAI's Grok
Observable: A visible statement in the bot's interface says that messages are sent to xAI's Grok service.
Source: implied: a third party processes what users type; users must be able to know that

### C-32: The bot contacts only xAI's API
Observable: Network monitoring of the org during use shows outbound requests from the bot only to xAI's API host.
Source: implied: Salesforce requires each outbound endpoint to be authorized, and an AI bot has no business calling others

### C-33: Text from users and from Grok is shown and stored faithfully
Observable: A message containing line breaks, quotes, emoji and non-Latin characters (e.g. "line1\nline2 \"q\" 😀 日本語") appears in the conversation, after a reload, exactly as typed.
Source: implied: edge case of U-1

### C-34: Replies are displayed as plain text and never run as markup or script
Observable: If a reply contains `<script>alert(1)</script>` or `<b>x</b>`, the characters appear literally; no script runs and no formatting is applied.
Source: implied: Grok output is untrusted input rendered inside a Salesforce page

### C-35: Messages from the user and from Grok are visually distinguishable
Observable: In a conversation, a user can tell by appearance and label which messages are theirs and which are Grok's.
Source: implied: U-1

### C-36: The deployment package contains no API key
Observable: Searching all deployed files (source, configuration, test data) for the key finds nothing; a freshly deployed bot has no key.
Source: implied: U-12; secrets must not be committed or shipped

### C-37: The administrator supplies the API key in the org after deployment, without editing code, and it takes effect immediately
Observable: The administrator enters the key in the org's configuration. The next message sent after that succeeds, without a new deployment.
Source: implied: U-12

### C-38: The API key is never shown to users or written to records or logs
Observable: The key does not appear in any bot screen, any error message, any conversation record, any debug log, or any response to a non-administrator.
Source: implied: U-12, U-14; a leaked key lets others spend the owner's quota

### C-39: An administrator can replace the key at any time without losing data
Observable: After the key is replaced, the next message uses the new key; every conversation made before is intact.
Source: implied: U-13

### C-40: The Grok model is a setting the administrator can change without code
Observable: After the administrator changes the model name in configuration, the next message is sent to xAI with that model name. Existing conversations continue.
Source: implied: U-13; Grok model names change often

### C-41: With only the key entered, the bot works, because a default model is already set
Observable: A newly deployed bot with a valid key and no other configuration answers a message.
Source: choice: the fewest steps for first-time setup

### C-42: A model name that xAI does not accept is reported as a failure that names the model setting
Observable: When the model name is invalid, the user sees a failure message (as for a rejected request), and the administrator is able to learn from the message that the model setting is wrong.
Source: implied: U-13 unhappy path

### C-43: Deploying the bot again over an org that already has it succeeds and changes none of the data or settings
Observable: Deploying the same version twice reports success both times. Afterwards the conversations, the configured key and model, and access assignments are the same as before.
Source: implied: U-15

### C-44: A newer version of the bot reads the conversations saved by an older one
Observable: After deploying a newer version over an org with conversations from an older one, each conversation opens with all its messages in order.
Source: implied: U-15

### C-45: Deploying the previous version after a newer one keeps all saved conversations
Observable: After going back to the previous version, every conversation that existed before the going back, including those created while the newer version was running, is still stored and readable by its owner.
Source: implied: U-16; Salesforce destroys the stored data when a field or object is removed by a deployment, so going back must not remove the places conversations are saved

### C-46: Deploying the bot changes nothing that already exists in the org, other than adding its own components
Observable: Comparing the org before and after deployment, existing objects, fields, flows, triggers, permission sets, user assignments, and page layouts are unchanged; no existing user's access changes.
Source: implied: U-17

### C-47: The bot's own automated tests all pass at deployment, with at least 75% coverage of its code, with no key configured and no network
Observable: A deployment that runs the bot's tests reports every one passing and coverage of the bot's Apex code of at least 75%; no test makes a real request to xAI.
Source: implied: U-12; Salesforce requires 75% coverage to deploy Apex to production and forbids real callouts in tests, so the same package must be deployable later

### C-48: The bot works in a Salesforce Developer Edition (development) org without extra licences or paid add-ons
Observable: On a freshly created Developer Edition org, deployment succeeds and a message can be sent with only the API key added.
Source: request (development org); choice: the loosest reading is that nothing beyond a standard development org is needed

### C-49: The bot can be used from a place in Salesforce that a user reaches by ordinary navigation
Observable: A user with access finds the bot by name in the Salesforce Lightning navigation and opens it in one click.
Source: choice: "a bot in Salesforce" needs somewhere to be used; any ordinary navigable place serves
