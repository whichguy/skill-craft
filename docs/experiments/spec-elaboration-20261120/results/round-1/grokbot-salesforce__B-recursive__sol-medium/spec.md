## Use cases

### U-1: A signed-in Salesforce user opens the bot to ask Grok a question
Flow: The authorized user opens the bot within the development org, enters a text prompt, submits it, and reads the Grok answer when the send completes successfully.
Source: request

### U-2: A first-time user finds the bot and starts with an empty chat
Flow: The user finds the bot from the authenticated Salesforce interface, opens it with no prior turns, and can tell where to enter a prompt. If access is missing, the user cannot start a chat and can tell that access is the issue when using a saved entry point.
Source: implied: a bot in a Salesforce org must be reachable by its intended users

### U-3: A user asks a follow-up to continue the current conversation
Flow: The user asks another question that refers to the last exchange and receives a reply in the same conversation. The user can also ask a separate question in a fresh conversation.
Source: implied: repeated use of a conversational bot

### U-4: A user corrects an invalid prompt to submit it successfully
Flow: The user tries a blank or over-limit prompt, sees why the bot rejected it, edits it, and submits again.
Source: implied: the prompt entry in U-1 can contain no usable input or too much input

### U-5: A user submits a prompt at the supported size boundary to receive a reply
Flow: The user enters a valid prompt at the published size ceiling in an otherwise empty conversation and submits it. The bot accepts the full prompt under healthy setup. The user sees the full text of a completed Grok answer.
Source: implied: the text interaction in U-1 has finite limits

### U-6: A user recovers from a provider failure to continue chatting
Flow: The user submits a valid prompt and sees a pending state. If authentication fails, service is unavailable, or the request times out, the user sees the failure category and can retry when service is available or ask an admin for help with setup.
Source: implied: U-1 depends on an external model service

### U-7: A user recovers from exhausted service capacity to try again
Flow: The user sends a valid prompt when the service is throttled or its allowance is exhausted, learns whether to wait or seek admin help, and can try again after capacity returns.
Source: implied: the model service used by U-1 has finite capacity

### U-8: A user clears the current conversation to start without its context
Flow: The user starts a new conversation, sees an empty transcript, and submits a prompt that uses only the new conversation's context.
Source: implied: U-3 introduces prior conversation state that the user may need to discard

### U-9: A Salesforce admin sets up the bot in the development org to make it available
Flow: The admin works in the designated development org, configures access to Grok, grants bot access, enables new requests, and verifies a live reply there. Missing or invalid setup is visible as a failure.
Source: implied: U-1 requires a working installation with authorized provider access

### U-10: A Salesforce admin grants or revokes bot access to manage who can use it
Flow: The admin grants access to an intended user and verifies that the user can send a prompt. After revocation, the same user is denied on the next send.
Source: implied: U-2 distinguishes users by access

### U-11: A Salesforce admin stops or resumes the bot to control new Grok requests
Flow: The admin disables new sends, observes that users cannot initiate a Grok request, reviews the configuration, then re-enables service and verifies a live send.
Source: implied: U-9 introduces a live integration with an operator

### U-12: A Salesforce admin diagnoses a failed send to restore service
Flow: The admin checks the reported outcome, identifies whether the failure arose in setup or during service use, corrects the cause, and verifies recovery with a new send.
Source: implied: U-6 and U-7 can require operator intervention

### U-13: A Salesforce admin changes the Grok configuration to restore or maintain service
Flow: The admin replaces a credential or selects an available Grok model, then verifies the change with a fresh prompt. If the change fails, the admin can restore the last working settings.
Source: implied: the dependencies configured in U-9 can become invalid or unavailable

### U-14: A Salesforce admin rolls back the bot to recover from a failed change
Flow: The admin pauses new sends, restores the prior working bot release or the pre-bot org state, and verifies the restored behavior in the development org. If restoration fails, the admin sees that it failed and the bot stays paused.
Source: implied: U-9 changes an org that may already be in use

### U-15: A Salesforce user keeps working with existing org data while the bot is installed
Flow: The user opens or edits an existing Salesforce record through the usual interface before and after setup and continues to use the same record subject to the same Salesforce access.
Source: implied: introducing the bot in U-9 can touch an org with existing data

### U-16: A Salesforce admin evaluates a production release to understand the deployment boundary
Flow: The admin verifies the development deployment and separately checks target-org prerequisites if a later production release is proposed.
Source: implied: the request designates a development org

### U-17: A user handles a declined answer to continue the conversation
Flow: The user asks a question that Grok declines, sees the decline, and can ask another question.
Source: implied: Grok may decline a prompt accepted by the bot

### U-18: A user reopens Salesforce to see whether a conversation was retained
Flow: The user reloads, leaves and reopens the bot, or signs out and back in, then sees the chat state available to the new page instance.
Source: implied: U-3 and U-8 make the chat lifetime relevant

### U-19: A user repeats a send gesture while waiting to avoid submitting twice
Flow: The user activates send twice quickly and observes the outcome for one pending send. After completion the user can deliberately send the same text again.
Source: implied: U-1 can be repeated before its result arrives

### U-20: A user checks where prompt text goes before sending it
Flow: The user reads the disclosure at the bot entry point or composer, then decides whether to submit their text to Grok.
Source: implied: U-1 sends user input to an external service

### U-21: An administrator verifies the target before changing the org
Flow: The admin identifies the target from Salesforce org information, proceeds only for the intended development org, and checks that an authorized end user can complete a live chat after first setup.
Source: implied: U-9 depends on selecting the right Salesforce org

### U-22: A signed-out visitor attempts to use the bot through a saved entry point
Flow: The visitor follows the entry point or attempts a send without a valid Salesforce session and cannot reach Grok through the bot.
Source: implied: U-2 requires Salesforce authorization

### U-23: A user reaches the conversation context limit to keep asking questions
Flow: After a long chat, the user sees when older exchanges stop informing Grok. The user can continue with newer context or start fresh.
Source: implied: U-3 adds context to a finite provider request

### U-24: A user starts fresh while a response is pending to switch topics
Flow: The user submits a slow prompt, starts a fresh conversation, and sends another prompt. A late result for the old conversation does not appear in the new chat.
Source: implied: U-6 and U-8 can overlap

### U-25: Two authorized users chat at the same time to get independent answers
Flow: Each user opens their own session, submits a prompt, and receives their own result. A limit affecting one request does not attach that failure to the other conversation.
Source: implied: multiple users enabled by U-10 can use U-1 at the same time

### U-26: A user loses contact after a send to recover without accidental resubmission
Flow: When contact drops during a send, the user learns that no answer was received and whether delivery is unknown. Any new attempt is deliberate.
Source: implied: U-6 can fail after the provider receives the prompt

### U-27: A Salesforce user asks Grok to change an org record to understand the bot's scope
Flow: The user asks the bot to modify an existing record. The user sees that the bot is limited to chat and finds the actual record unchanged by the bot.
Source: implied: the bot is inside Salesforce where users may assume chat has record access

### U-28: A Salesforce admin checks bot diagnostics after an error to troubleshoot without exposing chat content
Flow: The admin finds the failure corresponding to the affected send and reads its category without seeing the user’s prompt, the reply, or a provider secret.
Source: implied: U-12 must coexist with private conversations

### U-29: An admin completes a failed installation without starting partial service
Flow: The admin sees that installation or setup failed, identifies the incomplete step, and retries or restores the prior state. Intended users can send only after setup is complete and service is enabled.
Source: implied: U-9 may stop before all prerequisites are met

### U-30: A user receives an incomplete provider response to know whether another attempt is needed
Flow: The user sends a valid prompt and Grok stops before producing a completed answer. The bot shows that the attempt was incomplete, then the user can deliberately try again.
Source: implied: U-6 can receive a partial response rather than a completed answer

### U-31: A user resumes after a maintenance pause to continue an open chat
Flow: The user tries a valid send while the bot is paused and sees the pause outcome. After the admin resumes service without a rollback, the user can submit from the same open conversation if access remains in effect.
Source: implied: U-3 and U-11 can occur during the same chat

## Clauses

### C-1: The bot runs inside the designated Salesforce development org.
Observable: An authorized user opens the bot from within that org.
Source: request

### C-2: The answer to a successful send comes from Grok.
Observable: An authorized user submits a valid question with working setup and can match the answer shown to the text returned by a live Grok inference.
Source: request

### C-3: The development target is one Salesforce Developer Edition org.
Observable: The admin verifies the bot in one org whose Salesforce edition is Developer Edition.
Source: choice: the request leaves the type and identity of the development org open and Developer Edition provides a standalone target

### C-4: Authorized users can discover the bot in the authenticated Salesforce interface.
Observable: An authorized user finds an entry point from within the org without needing a separate external address.
Source: implied: U-2

### C-5: The bot supports typed, free-form text prompts.
Observable: A user can submit an ordinary question in their own words without selecting from a fixed set of questions.
Source: implied: U-1

### C-6: The bot shows a successful text answer in the conversation that requested it.
Observable: The user reads the returned text inside the originating chat.
Source: implied: U-1

### C-7: A newly opened bot page starts with an empty conversation.
Observable: An authorized user opens a new instance of the bot page and sees no prior turns.
Source: choice: page-lifetime conversations support a demonstration without requiring saved chat history

### C-8: A follow-up sends prior successful exchanges from the current conversation as context.
Observable: After a successful exchange that fits within the usable context budget, a follow-up sent from the same chat includes that exchange in the provider-bound conversation.
Source: choice: a conversational bot benefits from context and the request leaves conversation memory open

### C-9: A whitespace-only prompt is rejected before provider submission.
Observable: Submitting empty text or text made entirely of whitespace produces input feedback with no corresponding Grok request.
Source: implied: U-4, where there must be a question to answer

### C-10: The bot communicates its supported prompt size before submission.
Observable: A user can see the maximum accepted prompt length and its unit at the point of entry.
Source: choice: users need to know the boundary and the request leaves the presentation open

### C-11: The bot accepts a prompt exactly at its stated size ceiling when the other input conditions hold.
Observable: In an empty chat with working setup, a nonblank prompt of exactly the displayed maximum length reaches Grok in full.
Source: choice: an advertised maximum is inclusive so the user can rely on it

### C-12: The bot rejects a prompt above its stated size ceiling before provider submission.
Observable: A user attempts to submit text over the stated ceiling and sees size feedback without a Grok request.
Source: choice: rejecting oversized text preserves the user’s control of what will be sent

### C-13: The bot signals that a submitted prompt is awaiting an answer.
Observable: Under a deliberately slow provider response, the user can tell that the send is in progress.
Source: implied: U-6

### C-14: A failed send has a visible outcome.
Observable: When a send ends without a completed answer while the chat remains open and authorized, the originating user can tell the send failed.
Source: implied: U-6

### C-15: A user can edit and resubmit the text of a rejected prompt.
Observable: After rejection, the text is available to the user for correction and another submission.
Source: choice: preserving text avoids retyping and makes input recovery useful

### C-16: The user can tell when a capacity failure has an unknown recovery time.
Observable: When the bot receives a capacity rejection with no known time for recovery, it reports the capacity problem without claiming a specific time for a successful retry.
Source: choice: the service can refuse for capacity without supplying a reliable recovery time

### C-17: A user can start a fresh conversation inside the bot.
Observable: Starting a fresh conversation removes the current transcript from the view and makes an empty transcript visible.
Source: choice: users who change topics need a way to discard context

### C-18: A fresh conversation excludes prior conversation turns from Grok context.
Observable: On the first send after starting fresh, the request to Grok contains no earlier turns from that user’s old conversation.
Source: choice: starting fresh discards conversation context

### C-19: A Salesforce admin can configure the bot’s connection to an authorized Grok service.
Observable: In the target org an admin can supply the provider authorization needed to get a live Grok reply.
Source: implied: U-9

### C-20: Every chat user requires an explicit bot access grant to send prompts.
Observable: A signed-in user who lacks the bot grant is denied when attempting to send, including a Salesforce admin who has setup rights only.
Source: choice: authorization to administer the integration is distinct from authorization to use it

### C-21: An authorized Salesforce admin can grant bot access.
Observable: After the grant, the intended user can send a valid prompt given working setup.
Source: implied: U-10 and C-20

### C-22: An authorized Salesforce admin can revoke bot access.
Observable: After revocation, the affected user's next send cannot reach Grok even if the bot page was already open.
Source: implied: U-10 and C-20

### C-23: An authorized Salesforce admin can disable new Grok sends for the org.
Observable: After disablement, no send that has yet to pass the dispatch authorization check reaches Grok.
Source: choice: the admin needs a reversible way to stop external activity

### C-24: An authorized Salesforce admin can re-enable new Grok sends for the org.
Observable: After re-enabling with valid setup, an authorized user can again submit a new prompt to Grok.
Source: implied: U-11 and C-23

### C-25: An authorized Salesforce admin can identify the category of a failed send.
Observable: After an unsuccessful send, an admin can tell whether the failure concerned configuration, access, capacity, timeout, or another service failure.
Source: choice: admins need enough information to recover while the diagnostic surface is left open

### C-26: An authorized Salesforce admin can replace the Grok credential.
Observable: After a successful credential change, the next newly accepted send can authenticate with the replacement.
Source: implied: U-13 and C-19

### C-27: An authorized Salesforce admin can select a Grok model available to the configured provider account.
Observable: After a successful model change, the next newly accepted send uses the selected model.
Source: choice: Grok is a family and the request does not pin a model version

### C-28: The development org can be restored to its prior bot release after an update.
Observable: An admin restores the prior working release and verifies that a fresh prompt follows that release’s behavior with valid settings.
Source: implied: U-14

### C-29: The development org can be restored to its pre-bot state following a first installation.
Observable: An admin reverses the first installation and the bot is no longer available in the org.
Source: implied: U-14

### C-30: The development deliverable targets no production org.
Observable: The admin verifies installation in the designated development org without a production deployment.
Source: implied: U-16 and the request’s development-org scope

### C-31: A Grok refusal with usable text is presented to the user.
Observable: Given a completed Grok refusal with user-facing answer text, the user sees that refusal attached to the corresponding prompt.
Source: implied: U-17

### C-32: One conversation accepts at most one pending send at a time.
Observable: While one send is pending, pressing send again in that conversation neither starts another request nor causes a deferred request after the pending send finishes.
Source: choice: concurrent sends within one chat would make follow-up context ambiguous

### C-33: The admin can identify the exact Salesforce org selected for installation.
Observable: Before making changes, the admin can verify the designated target by Salesforce org ID.
Source: choice: names and aliases can refer to the wrong org

### C-34: There is an in-org bot entry point in Salesforce Lightning Experience.
Observable: An authorized user on desktop Lightning Experience can open the bot from the Salesforce workspace.
Source: choice: the request leaves the authenticated interface open and desktop Lightning is sufficient for development use

### C-35: A visitor without a valid Salesforce session cannot send to Grok through the bot.
Observable: A signed-out visitor tries a saved bot entry point or replays the send after the session expires and no Grok request is made.
Source: implied: U-22 and the Salesforce authentication boundary in U-2

### C-36: An ordinary bot user cannot change bot configuration.
Observable: A granted non-admin attempts to change bot settings and the settings retain their prior values.
Source: implied: U-9 and U-10 distinguish administration from chat access

### C-37: A first-time install starts with new Grok sends disabled.
Observable: After installation, an authorized user's valid prompt cannot reach Grok until an admin enables the bot.
Source: choice: setup and access review must precede external traffic

### C-38: Missing essential provider settings prevent dispatch of a prompt.
Observable: With the bot enabled but its credential or model unset, an authorized user receives a setup failure and no inference request is dispatched.
Source: implied: U-9 cannot reach Grok without the essential configuration

### C-39: The admin can verify readiness with a live Grok exchange in the designated org.
Observable: With setup complete, an authorized admin or designated test user submits a non-sensitive prompt in that org and sees a Grok reply.
Source: implied: U-9 requires a working bot in the org after setup

### C-40: The bot discloses before submission that chat context is sent to xAI.
Observable: Before submitting, including on return visits, the user can read that xAI receives the submitted prompt and the earlier exchanges used as context.
Source: choice: sending externally is consequential to a user's decision to submit

### C-41: Each chat page instance has its own conversation.
Observable: A second tab opened by the same signed-in user starts empty while the first tab continues with its own turns.
Source: choice: page-scoped state gives an unambiguous boundary for parallel chats

### C-42: A failed provider attempt contributes no exchange to subsequent Grok context.
Observable: After a send ends in failure, the next valid send's context omits that failed attempt.
Source: choice: a failed attempt is not a completed question-answer exchange

### C-43: The prompt arrives at Grok with the submitted text intact.
Observable: When a valid prompt includes supported Unicode, punctuation or embedded line breaks, the outgoing prompt contains the submitted text, including those characters.
Source: implied: C-5

### C-44: A provider response with no usable text is a failed send.
Observable: Given a completed response containing no user-facing answer text, the user sees a failure outcome.
Source: implied: U-6 and C-14

### C-45: The user can recover the submitted text after a failed provider attempt.
Observable: After a provider failure, the original sender can reuse that text in the current chat without retyping it.
Source: choice: users should be able to retry transient failures manually

### C-46: The composer becomes usable again after a terminal failure.
Observable: After a send fails, the user can enter or submit another prompt subject to current availability and access.
Source: implied: U-6 and U-7

### C-47: A later deliberate send may repeat an earlier prompt verbatim.
Observable: Once no send is pending, submitting the same valid text again initiates a new send under currently working setup.
Source: implied: U-19

### C-48: The bot leaves no saved transcript in browser storage.
Observable: After a chat ends, inspecting the bot’s durable browser storage yields no saved prompt or answer transcript.
Source: choice: page-lifetime chat requires no persistent browser copy

### C-49: The admin can restore a previously working model selection.
Observable: After a model change fails, the admin restores the prior selection if still available and verifies a fresh reply.
Source: implied: U-13 and C-27

### C-50: The admin can replace a failed credential change with a usable credential.
Observable: After a replacement fails, the admin can configure a still-valid prior credential or a new valid credential and verify a fresh reply.
Source: implied: U-13 and C-26

### C-51: The bot identifies itself as providing answers from Grok.
Observable: Before asking, the user can tell which model family is supplying answers.
Source: implied: U-1 and C-2

### C-52: A conversation shows successful exchanges in send order.
Observable: After two successful sends, the earlier question-answer exchange appears before the later one.
Source: choice: chronological display makes the same conversation intelligible

### C-53: A send retains the submitted prompt even if the composer changes while it is pending.
Observable: If editing is available while pending, changing the draft changes neither the dispatched prompt nor the text associated with its result.
Source: implied: U-1 binds each response to the submitted question

### C-54: A result from a discarded conversation does not appear in the replacement chat.
Observable: The user starts fresh during a delayed successful or failed send and sees no old result in the new chat.
Source: implied: U-24 and C-18

### C-55: A new conversation can send while a discarded conversation's request remains outstanding.
Observable: While the old send is unresolved, a valid send from the fresh chat can proceed subject to current access and service limits.
Source: choice: starting fresh releases the former conversation's send restriction

### C-56: Chats in independent page instances can send concurrently.
Observable: With adequate service capacity, a pending send in one authorized chat does not block a send from another authorized chat.
Source: choice: the single-pending-send rule applies to a conversation rather than the org

### C-57: A result belongs only to its originating send.
Observable: When a user's distinct sends in separate page instances complete in reverse order, each outcome appears only with the question that originated it.
Source: implied: U-25 and C-6

### C-58: A repeated notification for one send produces at most one visible answer.
Observable: Given two deliveries of the same successful completion, the originating chat shows a single answer for that send.
Source: implied: U-19 requests one answer for one send

### C-59: A send whose outcome has become terminal cannot be completed again by a late result.
Observable: After a user sees a timeout and submits another prompt, a late result from the first send changes neither the timeout outcome nor the newer answer.
Source: choice: a completed outcome must remain stable during recovery

### C-60: The admin can identify the effective model after configuration is saved.
Observable: After saving a new model selection and reopening bot settings, the admin can identify which model is in effect.
Source: choice: operators need to verify a persisted model change without viewing the secret

### C-61: Dispatched sends stay bound to the configuration used for dispatch.
Observable: A send already dispatched when settings change returns its own result or failure without being reissued under the new settings.
Source: choice: a configuration change takes effect at the next admission boundary

### C-62: Disabling new sends allows a previously dispatched send to finish.
Observable: A send that passed dispatch authorization before the pause can return its outcome to its original open conversation while the user remains authorized.
Source: choice: the stop control blocks new traffic and does not promise cancellation of submitted requests

### C-63: An outstanding result is withheld when its sender lacks bot access at delivery.
Observable: If the sender's grant is absent when the result is ready, the reply is withheld even if the grant is later restored.
Source: choice: current bot access is required at delivery so a response cannot arrive while the sender is denied

### C-64: A Salesforce session expiring while a send is pending prevents subsequent delivery into that expired session.
Observable: The user no longer has a valid session when a delayed reply arrives and cannot retrieve it through the expired session.
Source: implied: U-22 and C-35 establish the authentication boundary for bot use

### C-65: A lost reply with uncertain delivery is reported as uncertain.
Observable: When an interruption makes both the answer unavailable and delivery unknown, the user sees that the request may have reached Grok.
Source: choice: delivery can be uncertain after a network failure

### C-66: Provider submission is attempted at most once per accepted send.
Observable: When the same submission is received twice by the bot, or fails after dispatch, xAI sees at most one inference request for that submission.
Source: choice: a repeated inference can incur another charge and the user can choose to submit again

### C-67: When context must be shortened, the bot drops the oldest complete exchanges first.
Observable: When too much history is available, the next provider request uses the longest fitting suffix of complete exchanges in chronological order, with the full latest prompt.
Source: choice: recent context is useful and the user's current text takes priority

### C-68: The bot indicates when earlier exchanges are omitted from the context of an answer.
Observable: When the next completed answer uses shortened history, the user is informed that some previous exchanges were excluded.
Source: choice: the visible transcript could otherwise imply that Grok relied on all of it

### C-69: Shortening provider context preserves the current visible transcript.
Observable: After older exchanges are dropped from an outgoing request, those exchanges remain visible in the current chat.
Source: choice: provider capacity should not erase what the user can still read

### C-70: Rollback starts with new sends disabled.
Observable: When the admin starts a release rollback, new sends stop reaching Grok before the restore proceeds.
Source: choice: pause is a clear boundary for changes to an active service

### C-71: Rollback retires conversations opened under the superseded release.
Observable: Once rollback takes effect, an open chat from the superseded release cannot continue submitting its accumulated conversation to Grok.
Source: choice: a reset boundary prevents conversation state from crossing release versions

### C-72: xAI requires valid API authentication for a Grok inference.
Observable: An admin with a missing or rejected xAI API key cannot get a live Grok reply through the bot.
Source: implied: U-9 under the xAI API bearer authentication rule. [xAI API authorization](https://docs.x.ai/developers/rest-api-reference/management/auth)

### C-73: An xAI rate-limit response is handled as temporary throttling.
Observable: When the configured xAI team or model reaches a rate cap and xAI returns HTTP 429, the user sees a throttling outcome with guidance to try later. The exact target account and model caps are unconfirmed until setup.
Source: implied: U-7 under the xAI RPS and TPM limits, which vary by team and model. [xAI rate limits](https://docs.x.ai/developers/rate-limits)

### C-74: An exhausted provider spending allowance requires operator recovery when xAI reports it distinctly.
Observable: When xAI explicitly reports exhausted allowance, the user is directed to an admin for recovery. The target account's exact allowance is unconfirmed until setup.
Source: implied: U-7 under xAI's prepaid credit and invoiced spending rules. [xAI API billing](https://docs.x.ai/console/billing)

### C-75: A Grok request fits within the selected model's context window.
Observable: For a long conversation, an outbound request fits the configured model's context ceiling including its required output budget. The exact model limit is unconfirmed until selection.
Source: implied: U-23 under xAI's per-model context-length rule. [xAI model limits](https://docs.x.ai/developers/rest-api-reference/inference/models)

### C-76: An Apex-backed bot can reach xAI only through an endpoint permitted for Salesforce callouts.
Observable: If Salesforce has no applicable endpoint authorization for the Apex callout, a send produces a setup failure without reaching xAI.
Source: implied: U-9 under Salesforce Apex callout endpoint authorization. [Salesforce callout endpoints](https://developer.salesforce.com/docs/atlas.en-us.apexcode.meta/pages/apex_callouts_named_credentials.htm)

### C-77: If Salesforce external credentials are used, the runtime identity needs access to the selected principal.
Observable: With principal access absent for the identity that makes the callout, the send cannot authenticate through that principal.
Source: implied: U-9 under Salesforce external credential principal authorization. [Salesforce external credential principals](https://developer.salesforce.com/docs/platform/named-credentials/references/named-credentials-reference/nc-glossary.html)

### C-78: If Apex performs the callout, an Apex transaction has at most 120 seconds of cumulative callout timeout.
Observable: A provider that stalls beyond the Apex transaction's 120-second callout ceiling cannot supply a successful reply within that transaction.
Source: implied: U-6 under Salesforce's cumulative Apex callout timeout limit. [Salesforce execution governors](https://developer.salesforce.com/docs/platform/apex-dev/references/apex-dev/apex-gov-limits.html)

### C-79: If Apex performs the callout with its default timeout, it cannot wait for a reply past 10 seconds for that callout.
Observable: With the Salesforce default unchanged, a provider response delayed past 10 seconds does not complete that Apex callout successfully.
Source: implied: U-6 under the Salesforce default Apex callout timeout. [Salesforce Apex callout limits](https://developer.salesforce.com/docs/atlas.en-us.apexcode.meta/connectapi/apex_gov_limits.htm)

### C-80: If Apex performs the callout, an Apex transaction cannot make more than 100 callouts.
Observable: Under a shared transaction scenario, a successful Grok exchange cannot depend on a 101st Salesforce callout from the same transaction.
Source: implied: U-25 under the Salesforce Apex callout count limit. [Salesforce execution governors](https://developer.salesforce.com/docs/platform/apex-dev/references/apex-dev/apex-gov-limits.html)

### C-81: A synchronous Apex callout cannot exchange a request or response larger than 6 MB.
Observable: With a request or response above 6 MB, the synchronous callout cannot complete the Grok exchange successfully.
Source: implied: U-5 under the Salesforce synchronous Apex callout payload limit. [Salesforce Apex callout limits](https://developer.salesforce.com/docs/atlas.en-us.apexcode.meta/connectapi/apex_gov_limits.htm)

### C-82: If Apex performs the callout, Grok cannot be reached from an Apex transaction with pending uncommitted writes.
Observable: An attempted Apex callout while such work is still pending fails without delivering the prompt to Grok.
Source: implied: U-9 under Salesforce Apex transaction-control rules. [Salesforce transaction control](https://developer.salesforce.com/docs/platform/apex-dev/references/apex-dev/langcon-apex-transaction-control.html)

### C-83: An expired development org cannot serve the in-org bot.
Observable: If Salesforce makes the selected Developer Edition org inaccessible after inactivity, an authorized user can no longer open its bot. Salesforce documents 180 days without a login before legacy orgs are queued for deletion. The selected org's edition variant is unconfirmed until setup.
Source: implied: U-1 under the Salesforce Developer Edition expiration policy. [Salesforce Developer Org Expiration](https://help.salesforce.com/s/articleView?id=sf.admin_de_org_expiration.htm&language=en_US&type=5)

### C-84: A future production release containing Apex uses Salesforce's production deployment process.
Observable: The admin cannot create or edit the bot's Apex directly in the production org to release it.
Source: implied: U-16 under Salesforce's prohibition on direct Apex development in production. [Salesforce Apex deployment](https://developer.salesforce.com/docs/platform/apex-dev/references/apex-dev/apex-deploying.html)

### C-85: A future production deployment containing Apex cannot pass with failed required Apex tests.
Observable: If a required Apex test fails during validation of a production deployment, the admin sees a failed validation for that release.
Source: implied: U-16 under Salesforce production Apex deployment test requirements. [Salesforce production validation](https://developer.salesforce.com/docs/platform/api-metadata/references/file-based-calls/meta-deployrecentvalidation.html)

### C-86: A future production Apex deployment using all or all local tests needs at least 75% aggregate coverage.
Observable: The target validation fails its coverage criterion below 75% aggregate Apex coverage in that mode.
Source: implied: U-16 under Salesforce production Apex coverage rules for those test modes. [Salesforce production validation](https://developer.salesforce.com/docs/platform/api-metadata/references/file-based-calls/meta-deployrecentvalidation.html)

### C-87: A future production Apex deployment using all or all local tests requires coverage of each Apex trigger.
Observable: If a trigger in scope has zero coverage, the production validation fails its trigger coverage criterion even when aggregate coverage is at least 75%.
Source: implied: U-16 under Salesforce production trigger coverage rules. [Salesforce production validation](https://developer.salesforce.com/docs/platform/api-metadata/references/file-based-calls/meta-deployrecentvalidation.html)

### C-88: A future production Apex deployment using specified tests needs at least 75% coverage per deployed Apex class or trigger.
Observable: The target validation fails its coverage criterion if an individual deployed class or trigger is below 75% in that mode.
Source: implied: U-16 under the Salesforce RunSpecifiedTests rule. [Salesforce specified tests](https://developer.salesforce.com/docs/platform/api-metadata/guide/meta-deploy-run-specific-tests.html)

### C-89: A future deployment that packages Salesforce external credentials still needs the secret provisioned for the target org.
Observable: Installing credential metadata alone does not yield authenticated callouts with the target's unpopulated credential.
Source: implied: U-16 under Salesforce's restriction on packaging external credential secrets. [Salesforce credential provisioning](https://developer.salesforce.com/docs/platform/named-credentials/guide/nc-populate-external-credentials.html)

### C-90: Before a send, the user can see that clearing chat has no effect on any applicable xAI audit retention.
Observable: Before submitting, a user can see that clearing chat does not erase audit copies held by xAI. xAI documents a default audit retention period of 30 days.
Source: choice: distinguish the local clear action from xAI's API retention rule. [xAI API security](https://docs.x.ai/developers/faq/security)

### C-91: Existing Salesforce records retain their pre-installation values when the bot is introduced.
Observable: An admin compares unchanged records before and after bot installation and observes the same field values.
Source: implied: U-15 and the request adds a bot to an org

### C-92: Existing Salesforce record access remains governed by the pre-existing Salesforce permissions.
Observable: The same user is allowed or denied access to the same existing record before installation and after a bot grant.
Source: implied: U-15 and the request grants no additional CRM access

### C-93: Existing Salesforce navigation remains available after bot installation.
Observable: A user can open an existing app or page through its original Salesforce navigation after installation.
Source: implied: U-15 and the request adds an entry point

### C-94: Reversing the bot installation preserves changes users made to unrelated Salesforce data while it was installed.
Observable: After rollback, a legitimate record edit made during the bot's lifetime remains in the org.
Source: implied: U-14 and U-15

### C-95: Reversing the bot installation preserves unrelated Salesforce configuration changes made while it was installed.
Observable: An unrelated admin setting changed during bot operation retains its newer value after bot rollback.
Source: implied: U-14 reverses the bot change

### C-96: The bot does not fetch Salesforce record data to enrich a prompt.
Observable: A user asks about an existing record without supplying its field values. The provider-bound request contains no content drawn from that record by the bot.
Source: choice: the request leaves CRM grounding open and a chat-only bot needs no access to stored records

### C-97: The bot does not perform Salesforce record operations on behalf of a chat user.
Observable: A user asks Grok to create, update or delete a record and no such record operation is performed by the bot.
Source: choice: the request describes a bot without CRM action requirements

### C-98: Grok receives no Salesforce session credential in inference traffic.
Observable: Inspection of a provider-bound request reveals no Salesforce session token generated or attached by the bot.
Source: implied: U-1 uses separate Salesforce and xAI trust boundaries

### C-99: The bot sends no Salesforce user identifiers in inference content unless the user supplies them as chat text.
Observable: An observer of a provider-bound inference sees no Salesforce user ID or login automatically added to the chat content.
Source: choice: model inference requires the conversation rather than Salesforce account data

### C-100: The xAI credential is unavailable to the chat client.
Observable: Inspection of the bot page, its ordinary client traffic, and its browser storage reveals no xAI credential.
Source: implied: U-9 and U-10 distinguish using the bot from possessing its authorization

### C-101: Bot setup does not expose a previously configured xAI secret in readable form.
Observable: After saving a secret, an admin reopening the bot configuration sees no readable copy of the saved value.
Source: choice: admins need to replace a credential without making it retrievable through bot setup

### C-102: Bot diagnostics exclude provider credentials.
Observable: Inspection of bot diagnostics after a failure finds no xAI key or authentication header value.
Source: implied: U-28 and C-19

### C-103: Bot diagnostics exclude conversation text.
Observable: Inspection of bot diagnostics after a failure finds neither the submitted text nor the returned answer body.
Source: choice: troubleshooting requires a category and correlation without a copy of the chat

### C-104: The bot does not create a persistent chat transcript in Salesforce.
Observable: After a successful conversation, an authorized admin inspecting the bot's stored Salesforce data finds no saved prompt or answer transcript.
Source: choice: the page-lifetime conversation requires no saved Salesforce transcript

### C-105: A new user of the same browser cannot see the previous user's transcript.
Observable: After one user signs out and another signs in on the same browser, the second user cannot read the first user's messages through the bot.
Source: implied: U-18 and U-25

### C-106: Bot access is enforced on every send path.
Observable: A user lacking bot access cannot cause a Grok request by submitting through a saved or directly invoked send entry point.
Source: implied: U-10, since revocation must be effective even away from normal navigation

### C-107: Provider text is inert in the Salesforce page.
Observable: Opening an answer that contains script-like text executes none of that text in the Salesforce page.
Source: implied: U-1 displays externally supplied text within a signed-in Salesforce session

### C-108: The bot runs no model-requested tools.
Observable: A Grok result that proposes a tool call causes no tool invocation by the bot.
Source: choice: text answers are sufficient for the request and no external action was requested

### C-109: An end user's prompt cannot change the configured Grok destination.
Observable: Entering a different destination in chat does not change where the bot sends the prompt.
Source: implied: U-9 and U-13 reserve provider configuration for the admin

### C-110: Ordinary users cannot read administrative bot diagnostics.
Observable: An authorized chat user without admin rights cannot retrieve diagnostic details reserved for an admin.
Source: implied: U-12 and U-28 give troubleshooting to the admin

### C-111: A successful send shows the full completed reply text returned for display.
Observable: Given a completed Grok response with multiple paragraphs that fits the supported response limits, the user can read through to the last returned paragraph in the bot.
Source: implied: U-5 and C-6

### C-112: A provider-reported incomplete generation is reported as incomplete.
Observable: If Grok reports an incomplete result, such as reaching its output token limit, the bot reports a failed attempt due to incomplete generation.
Source: choice: treating an incomplete generation as a failed send keeps the conversation context consistent. [xAI incomplete responses](https://docs.x.ai/developers/model-capabilities/text/best-practices)

### C-113: Each send has a finite, published wait deadline.
Observable: From the time the bot accepts a send, an unresponsive dependency results in a terminal timeout by the bot's stated elapsed wait limit while the chat is open and responsive.
Source: choice: a user needs an end to waiting and the exact product deadline can be chosen to fit the deployed setup

### C-114: A timeout is identifiable as such to the sender.
Observable: When the bot's wait expires while the user's chat remains open, the user can tell that the bot timed out waiting for the result.
Source: implied: U-6 distinguishes this recovery path

### C-115: A rejected provider credential is identifiable as a setup problem to the sender.
Observable: When xAI rejects the API authorization, the user sees that administrator intervention is needed for setup.
Source: implied: U-6 and U-12 under xAI's API authentication failure rule. [xAI API errors](https://docs.x.ai/developers/debugging)

### C-116: A transport or provider outage is identifiable as a service failure to the sender.
Observable: When the provider is unreachable or reports a service error, the current user sees an unavailable-service outcome for that attempt.
Source: implied: U-6

### C-117: A user-facing failure does not show raw provider error bodies.
Observable: When the provider responds with an error containing backend detail, the ordinary user sees a product-level failure instead of the raw response body.
Source: choice: actionable user feedback does not require displaying provider internals

### C-118: The sender can refer an unsuccessful send to an admin without sharing its content.
Observable: For a failed inference attempt with an available admin diagnostic, the sender can give the admin a reference that identifies that attempt without including the prompt or answer.
Source: choice: a reference makes troubleshooting concurrent failures possible without copying chat text

### C-119: Diagnostic availability has a documented lifetime.
Observable: The admin can tell the time window after the failure during which its diagnostic can be retrieved.
Source: choice: diagnostics are useful for recovery and need an explicit end without prescribing a retention period

### C-120: Expired bot diagnostics cease to be retrievable through the bot's diagnostic surface.
Observable: After the documented time window from the failure ends, an admin can no longer retrieve the diagnostic through the bot's diagnostic surface.
Source: choice: the diagnostic lifetime should bound what the product exposes

### C-121: The admin can see whether the bot currently admits new sends.
Observable: The admin can distinguish enabled from disabled after reopening bot settings.
Source: choice: an operator needs to verify stop and resume without making an inference

### C-122: The admin can tell whether first-time installation completed.
Observable: For a failed or interrupted setup, the admin can identify which prerequisite failed or remains incomplete.
Source: implied: U-29 and U-9

### C-123: An incomplete first installation cannot accept sends.
Observable: After a partial installation attempt, a user cannot cause that incomplete installation to submit a prompt to Grok.
Source: choice: failed first-time setup must stay inactive until the operator finishes setup

### C-124: An admin can retry first-time setup after a partial failure.
Observable: After correcting the cause of an interrupted first install, the admin retries and can bring the bot to a working state in the same org.
Source: implied: U-29 and U-9

### C-125: The admin can find the setup procedure for the installed bot.
Observable: The admin can find the prerequisites, activation steps, and way to verify a live send for the installed release.
Source: choice: an installation should be operable by another admin without guessing missing setup

### C-126: The admin can find the restore procedure for the installed bot.
Observable: The admin can find how to reverse first installation or restore the previous working release, as applicable.
Source: choice: rollback should be usable by an admin other than the person who installed the bot

### C-127: An asynchronous Apex callout cannot exchange a request or response larger than 12 MB.
Observable: With a request or response above 12 MB, the asynchronous callout cannot complete the Grok exchange successfully.
Source: implied: U-5 under the Salesforce asynchronous Apex callout payload limit. [Salesforce Apex callout limits](https://developer.salesforce.com/docs/atlas.en-us.apexcode.meta/connectapi/apex_gov_limits.htm)

### C-128: The user can tell before submitting that the bot provides chat without operating on Salesforce records.
Observable: Opening the bot lets the user find its record access scope before entering a question about records.
Source: choice: placement in Salesforce otherwise suggests that the bot can operate on org data

### C-129: Users need only their Salesforce session to use the configured bot.
Observable: An authorized user can complete a send using the configured org integration without signing into xAI or supplying a personal key.
Source: choice: an org-managed integration lets intended users use the Salesforce bot directly

### C-130: Reload does not restore a draft from the previous page instance.
Observable: A user reloads with unsent text and the new composer starts without that draft.
Source: choice: drafts follow the same page boundary as the conversation

### C-131: A disabled bot identifies the pause to authorized users.
Observable: An authorized user whose valid send is blocked by the admin's stop control sees that sends are disabled for the org.
Source: choice: distinguish a deliberate pause from an unexpected provider outage

### C-132: A pause followed by resume preserves an authorized user's open conversation.
Observable: Without leaving the open chat or changing release, a user sends after service resumes and the conversation can use its earlier successful exchanges.
Source: choice: stopping new provider traffic does not require losing the open transcript

### C-133: A signed-in user denied chat access sees an access-specific outcome.
Observable: A Salesforce user without a bot grant opens a saved bot entry point or attempts to send from an already open chat and can tell that bot access is required.
Source: implied: U-2 and U-10 distinguish access denial from service failure

### C-134: A provider-rejected model selection is identifiable as a configuration failure.
Observable: If the selected model becomes unavailable to the configured credential, an attempted send reports a setup problem requiring administrator attention.
Source: implied: U-13 and the xAI model availability boundary. [xAI model availability](https://docs.x.ai/developers/rest-api-reference/inference/models)

### C-135: The effective prompt size ceiling fits a new conversation under the current model configuration.
Observable: After a model change takes effect, an empty chat shows an applicable ceiling low enough for its largest valid prompt to fit with the required generation budget.
Source: choice: a published size boundary must remain usable when the operating model changes

### C-136: The sender can recover when an open page has a stale size ceiling.
Observable: If a prompt is rejected after an admin changes the effective ceiling, the user sees the current limit for correction.
Source: choice: an already open page can outlive the settings it displayed

### C-137: Starting a fresh conversation discards its predecessor's unsent draft.
Observable: After the user starts fresh with unsent text in the old composer, the new conversation's composer is empty.
Source: choice: the draft is part of the conversation the user discarded

### C-138: Starting a fresh conversation does not promise to recall a prompt already dispatched to xAI.
Observable: If the user clears the chat after xAI receives a prompt, the product does not claim that the earlier send was canceled.
Source: choice: discarding local chat cannot reverse external delivery

### C-139: A failed release rollback is visible to the admin.
Observable: An unsuccessful restore is shown as failed or incomplete rather than as a restored release.
Source: implied: U-14 requires the admin to tell whether restoration succeeded

### C-140: A failed release rollback leaves new sends disabled.
Observable: After an unsuccessful restore, a new send cannot reach xAI while the restore is unresolved.
Source: choice: a partially restored release cannot be exposed as available service

### C-141: The prior bot configuration can be restored as part of release recovery.
Observable: Where restoring the previous release needs earlier settings, the admin can recover those settings or reprovision currently valid equivalents to verify the restored release.
Source: choice: restoring behavior can require configuration beyond the installed release itself

### C-142: Provider authorization is sent only over an authenticated encrypted connection to the intended xAI service.
Observable: If the xAI service's secure connection cannot be verified, the bot does not deliver the credential to that destination.
Source: implied: U-9 relies on the authenticated HTTPS xAI API. [xAI API authorization](https://docs.x.ai/developers/rest-api-reference/management/auth)

### C-143: The bot does not ask xAI to save chat exchanges for later API retrieval.
Observable: For an inference API that offers retrievable response storage, inspecting the request shows that the bot declines such storage, including when storage is the provider default.
Source: choice: a page-scoped conversation does not need externally retrievable chat history. [xAI response storage](https://docs.x.ai/developers/rest-api-reference/inference/chat)

### C-144: Only an authorized Salesforce admin can grant or revoke bot access.
Observable: A chat-only user attempts to change a bot access grant, including their own, and the effective authorization does not change.
Source: implied: U-10 gives control of the chat grant to the admin

### C-145: A new send uses the access decision current at dispatch authorization.
Observable: If a user starts a send but loses access before it passes authorization for dispatch, no inference request for that send reaches Grok.
Source: implied: U-10, C-22 and C-106

### C-146: A rejected configuration update leaves the previously saved setting in effect.
Observable: When the bot rejects a change without saving it, reopening setup shows the previously effective setting.
Source: choice: a rejected save must not partially replace working configuration

### C-147: Reversing the first installation removes bot-specific access grants.
Observable: After uninstall or first-install reversal, the admin cannot find a remaining bot-specific grant from that installation.
Source: choice: reverting the bot should remove the access it introduced

### C-148: Reversing the first installation retires its org-side provider credential configuration.
Observable: After reverting a first install, the admin finds no usable Grok credential configuration created solely for that bot installation in the org.
Source: choice: the development org should retain no bot-created provider access after reversal

### C-149: A revoked chat grant is never restored implicitly by a bot rollback.
Observable: If an admin revokes a user's grant and then restores a prior bot release, that user is still denied until an admin grants access again.
Source: choice: rollback restores the release and must not undo a separate access revocation

### C-150: A submitted prompt is identifiable in the chat while its send is pending.
Observable: During a deliberately slow inference, the user can see which submitted text the pending send refers to.
Source: choice: users need to distinguish the text awaiting an answer from anything in the composer

### C-151: Each individual submission has a finite acceptance window.
Observable: Replaying a captured submission after its acceptance window closes cannot dispatch it to Grok even if the chat is still open.
Source: choice: expired submissions must be distinguishable from new intentional sends without tracking duplicates indefinitely
