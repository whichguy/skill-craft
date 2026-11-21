## Use cases

### U-1: A Salesforce user opens the bot to get a Grok answer
Flow: In the Salesforce development org, the user opens Grok, enters a question, submits it, and sees Grok’s reply in the org.
Source: request

### U-2: A Salesforce user returns to the bot to ask another question
Flow: The user asks a follow-up, starts a fresh conversation when needed, and can return to an empty conversation later.
Source: implied: a bot can be used more than once

### U-3: A Salesforce user corrects a refused submission to continue chatting
Flow: The user tries a blank prompt, an oversized prompt, or another send while a reply is pending. The bot reports the applicable restriction. The user can correct the prompt or wait before trying again. At the conversation limit the user starts a fresh chat.
Source: implied: submitting a prompt can fail validation or reach a limit

### U-4: A Salesforce user handles a failed Grok request to continue chatting
Flow: The user submits a valid prompt. If Grok cannot provide a reply, the bot reports the failure in place and the user can decide whether to submit again.
Source: implied: the Grok service can fail

### U-5: A Salesforce user attempts to open or send to Grok to learn whether access is available
Flow: The user signs in to the development org. A user with bot access can open it when enabled. A user without bot access or trying to use a disabled bot cannot submit a prompt.
Source: implied: Salesforce is an authenticated org and an administrator can restrict an integration

### U-6: A Salesforce user reviews what leaves the org before sending a prompt
Flow: In the chat, the user sees what text is sent to xAI, chooses what to type, then sends or leaves without asking Grok.
Source: implied: U-1 sends user-entered text to an external service

### U-7: A Salesforce administrator enables the bot to verify the first live answer
Flow: The administrator identifies the development org, configures an authorized xAI credential and Grok model, verifies a live response, grants a pilot user access, and enables the bot. The pilot user opens it and obtains a live Grok answer. If verification fails, the administrator sees the failure category and can fix the configuration before enabling.
Source: implied: U-1 needs an operational installation

### U-8: A Salesforce administrator changes the integration to keep Grok working
Flow: The administrator changes the model or replaces the xAI credential and verifies the effective configuration. The administrator can tell a saved configuration from one that has passed live verification.
Source: implied: the integration’s model and credential can become unusable

### U-9: A Salesforce administrator suspends chat to stop new requests
Flow: The administrator disables the bot for the org or revokes the entitlement for one user. They can inspect the effective setting or assignment, then verify the affected user cannot send.
Source: implied: U-5 needs a way to withdraw access

### U-10: A Salesforce operator finds a failed attempt to diagnose it
Flow: The user reports the reference shown with a failed send. The operator looks up the reference, sees the recorded outcome and reason, and can distinguish it from nearby successful requests without reading chat text.
Source: implied: U-4 needs an operational diagnosis path

### U-11: A Salesforce administrator rolls back the bot to recover from a bad change
Flow: The administrator disables it, restores the last working settings or version if available, verifies a live answer, and explicitly re-enables the bot. If there is no earlier working version or restored verification fails, the bot can stay off.
Source: implied: U-7 and U-8 need a recovery path

### U-12: A Salesforce user works with existing org records after the bot is introduced
Flow: The user opens and works with records, automation, and navigation already present before the bot was installed. They can also use Grok separately without migrating records into the bot.
Source: implied: the request adds a bot to an org with potentially existing data


## Clauses

### C-1: The bot is usable from inside a Salesforce development org.
Observable: A user opens the bot from the target development org and sees the interface there.
Source: request

### C-2: The bot obtains its answers from Grok.
Observable: A normal submitted prompt produces answer text from a live Grok request.
Source: request

### C-3: The bot accepts a user-entered text prompt.
Observable: A user can enter a question in a text input and intentionally submit it.
Source: implied: U-1 needs a way to ask a question

### C-4: The bot identifies which prompt a successful reply answers.
Observable: When a reply appears, the user can tell which submitted prompt it answers.
Source: implied: U-1 needs a recognizable answer

### C-5: A fresh conversation begins empty.
Observable: On opening a fresh conversation, the user sees no prior messages and can enter a first prompt if the bot is available.
Source: implied: U-1 and U-2 need an initial state

### C-6: An empty prompt is refused.
Observable: Submitting zero characters produces an input-required indication without a provider request.
Source: implied: U-3 needs a prompt with content

### C-7: A failed Grok request is visibly unsuccessful.
Observable: When a send fails, the bot shows that no answer was obtained for that attempt. Failure text does not appear as a Grok reply.
Source: implied: U-4 needs to distinguish a failure from an answer

### C-8: A caller without bot access cannot send a prompt.
Observable: A signed-in user without bot authorization cannot invoke Grok through the bot entry point, including by opening it directly.
Source: implied: U-5 requires access enforcement

### C-9: The delivery targets one authorized Salesforce development org.
Observable: An administrator can identify the target by its Salesforce org ID before accepting the installation. No production or second org is part of delivery.
Source: choice: one target is the smallest scope that fulfills the request. The actual org ID is unconfirmed and must come from the authorized deployment target

### C-10: The bot has an identifiable entry in the signed-in Salesforce Lightning navigation.
Observable: An authorized user can find an entry identifiable as Grok using Salesforce navigation without an externally supplied URL.
Source: choice: an internal Lightning entry makes one bot discoverable in the org without adding channels

### C-11: An unsigned visitor must sign in to use the bot.
Observable: Opening the bot while signed out requires Salesforce authentication before access can be evaluated.
Source: implied: U-5 occurs in a Salesforce org

### C-12: The bot operates as a text chat.
Observable: The user can submit and read text. Attachments, images as inputs or generated outputs, voice, streaming, and public or messaging channels are excluded for this development-org bot.
Source: choice: text is enough to ask questions and read Grok replies

### C-13: A nonblank prompt can contain up to 4,000 Unicode code points.
Observable: Counting the submitted text before trimming, including spaces and line breaks, 4,000 code points pass length validation and 4,001 are refused with the limit shown. A supplementary character counts as one code point.
Source: choice: bound the payload while preserving ordinary text prompts

### C-14: A valid prompt preserves the text entered by the user.
Observable: The text reaching Grok preserves case, whitespace, line breaks, and Unicode. Whitespace inspection for blank validation does not change the text.
Source: choice: quoted text and examples should retain their meaning

### C-15: A follow-up supplies the successful pairs from the current conversation as context.
Observable: Grok receives the prior user prompts and their displayed Grok replies in the order shown, followed by the newly submitted prompt. Drafts, pending prompts from another send, and failed attempts are excluded.
Source: choice: let follow-up questions refer to what the user actually saw

### C-16: A conversation can have up to 10 successful pairs.
Observable: The tenth successful reply can appear. The next send is refused with the 10-pair limit and a way to start a fresh chat. Failed attempts count as zero pairs.
Source: choice: keep context bounded without silently dropping earlier turns

### C-17: Each Grok request asks for at most 1,024 output tokens.
Observable: The request received by xAI specifies a maximum output-token budget of 1,024. The budget includes any reasoning tokens that the selected model counts against its provider limit.
Source: choice: bound the cost and response size of a dev-org request

### C-18: The chat explicitly starts over on user request.
Observable: The new-chat control clears the displayed prompts, replies, failures, and draft from that view and offers an empty input. The next request carries no prior user or assistant turns.
Source: choice: users need a way to reset context, including when the conversation reaches its limit

### C-19: Conversation content lasts only while its chat view remains open.
Observable: Reloading, closing the view, navigating away from the chat, or signing out ends that local conversation. Returning starts empty. Reopening from another tab, browser, or device starts empty too.
Source: choice: session-only chat is sufficient for development use without transcript storage or synchronization

### C-20: The bot explains its chat lifetime before the first send.
Observable: A first-time user can see that this chat is temporary and will be lost on leaving the view.
Source: choice: make the session-only decision visible before users rely on it

### C-21: The bot discloses the xAI data transfer before the first send.
Observable: Before submission the chat says the text of the current prompt and prior successful pairs in this chat is sent to xAI.
Source: choice: putting the disclosure at the point of submission lets users choose what to send

### C-22: A Grok send transmits only the minimum data for text inference.
Observable: Inspection of the outgoing request shows the selected Grok model, generation settings, the ordered user and assistant text, and the xAI authentication and ordinary protocol metadata required by the service. The bot supplies no Salesforce records, record context, Salesforce user ID, org ID, cookies, or diagnostics as separate inputs.
Source: choice: a standalone text bot needs no connection to org data

### C-23: The selected model must be an xAI Grok model that supports text turns and a bounded text reply.
Observable: The administrator can compare the configured model against the models available to the target xAI team. A model with no supported text input and text answer is unavailable for this bot.
Source: implied: U-1 requires a Grok service capable of the selected chat behavior

### C-24: The bot can use the xAI service only with authorization to run inference.
Observable: If the xAI team lacks usable API access, model permission, or any required billing or credit, the installation cannot be verified as ready.
Source: implied: U-1 depends on the target xAI team's ability to make a real request

### C-25: A new installation starts with chat disabled.
Observable: Before the administrator activates it, even an assigned user cannot send an ordinary chat request.
Source: choice: make initial external access deliberate

### C-26: The administrator can inspect whether chat is enabled.
Observable: The org-wide enable control shows exactly two effective states, enabled or disabled, and reports whether a requested change took effect.
Source: choice: one binary control is enough to suspend ordinary chat

### C-27: The administrator can assign bot use to an individual Salesforce user.
Observable: After granting the entitlement, the administrator can see the user as assigned. The assigned user can use the enabled bot subject to service availability.
Source: choice: support a pilot and an explicit audience without provisioning everyone

### C-28: The administrator can revoke one user’s bot entitlement.
Observable: On revocation, the administrator can confirm that the user is unassigned. Other individually authorized users remain entitled.
Source: choice: an individual suspension does not require an org-wide interruption

### C-29: The administrator can save one active Grok model.
Observable: The setup view shows the exact saved model identifier or that none is configured. A newly saved identifier is the one selected for the next live verification.
Source: choice: one active choice supports model replacement without adding a model picker to chat

### C-30: The administrator can provision the org’s xAI authentication credential.
Observable: The authorized administrator can provide a first or replacement credential for the target org. Setup shows whether one is configured.
Source: choice: support initial provisioning and rotation without requiring chat users to obtain keys

### C-31: An administrator can verify Grok connectivity while chat is disabled.
Observable: The administrator explicitly runs a live check using a harmless synthetic text prompt selected by the bot. The caller sees whether a usable Grok answer was obtained.
Source: choice: verify inference before exposing ordinary sends without transmitting chat or record content

### C-32: The administrator can distinguish saved settings from verified settings.
Observable: For the current configuration, the administrator sees one of unverified, verification in progress, verified, or verification failed. A successful check shows its completion time.
Source: choice: saving settings is not evidence that the service accepted them

### C-33: Chat cannot be enabled before the current configuration passes live verification.
Observable: Attempting activation with missing settings, an unverified configuration, a check in progress, or a failed check leaves chat disabled and indicates what must be resolved.
Source: choice: an explicit live check is the activation gate

### C-34: Changing the saved model or replacing the credential disables ordinary chat.
Observable: After a successful change, the administrator sees chat disabled until they verify the new settings and explicitly re-enable it.
Source: choice: apply the same readiness gate to replacement settings

### C-35: An ordinary chat user has no operator controls.
Observable: A user with only chat entitlement cannot grant or revoke entitlement, enable or disable chat, change the model or credential, initiate live verification, look up diagnostic records, or restore settings or releases, including through direct invocation.
Source: choice: keep administration separate from ordinary use

### C-36: An operator can find an admitted request by its reference.
Observable: For a reference received from chat or verification, the operator can find the matching entry during the 7-day lookup window.
Source: choice: isolate a specific attempt without searching by chat contents

### C-37: A diagnostic entry exposes only the operational fields needed to identify an attempt.
Observable: An operator sees the request reference, request type (chat or verification), admission time, finish time if known, model identifier, outcome, and reason for failed or unknown outcomes. Prompt and reply text, Salesforce user identity, credentials, raw headers and bodies, stack traces, and token usage are excluded.
Source: choice: support correlation with minimal retained data

### C-38: An admitted request has a single diagnostic outcome.
Observable: The entry is pending before resolution, succeeded when a usable provider reply is known, failed for a known rejection or unusable result, or outcome unknown when it is unknown whether xAI completed inference. Delivery to the user is separate from the provider outcome.
Source: choice: distinguish verified results from interrupted observations

### C-39: Diagnostic lookup covers the 7 days following admission.
Observable: At 7 × 24 hours after its start, an attempt no longer appears in operator lookup or history. The product does not offer longer-term log export or archives.
Source: choice: a short operational window is sufficient in a development org

### C-40: There is no migration of pre-existing org data into chat.
Observable: After installation, the first conversation starts empty even when the target org already contains users, records, files or automation.
Source: choice: the bot has no dependency on existing business data

### C-41: An administrator can restore a previously working bot configuration.
Observable: With ordinary chat disabled, the administrator can reapply the previous model and provision a usable credential independently of any previous secret. If available, the restored configuration must pass the same verification gate before explicit reactivation.
Source: choice: recovery must work without retrieving stored secrets

### C-42: An administrator can restore the last working bot release when one exists.
Observable: After restoring that release in the same development org, the administrator sees ordinary chat disabled pending verification and explicit reactivation. For an initial install, the recovery state is disabled with no earlier bot release to restore.
Source: choice: the operator can recover from a release regression even when changing settings alone is insufficient

### C-43: A submitted prompt is visibly pending until it can be resolved.
Observable: After submission, the user can see which prompt is awaiting a reply. The pending indication ends on a displayed reply, a displayed error, or the end of the conversation view.
Source: implied: U-1 and U-4 need to distinguish waiting from completion

### C-44: A conversation admits at most one pending send at a time.
Observable: While a send is pending in that conversation, another send is refused or unavailable. It is not queued for later and creates no second Grok request.
Source: choice: a follow-up must have an unambiguous prior context

### C-45: An admitted send creates at most one Grok inference request.
Observable: A double-click or repeated delivery of the same logical submission, including after terminal completion, produces at most one outbound inference and one diagnostic entry. A separate deliberate submission after completion is a new attempt even if the text is identical.
Source: choice: prevent duplicate answers and charges while allowing intentional repetition

### C-46: The bot does not automatically resubmit failed inference.
Observable: After a timeout, lost connection, provider refusal, or service error, the operator observes no second outbound call for that attempt. A new send requires an explicit user or administrator action.
Source: choice: a lost or delayed response can already have incurred a charge

### C-47: An unsuccessful send leaves its prompt recoverable within the current conversation.
Observable: After a failure, the user can recover the exact text of that attempted prompt for editing or resubmission without retyping it. Existing successful pairs remain available as context.
Source: choice: limit the cost of a transient failure without automatically resending

### C-48: An ended conversation cannot receive a late reply.
Observable: If a user chooses a new chat, reloads, leaves, or signs out while waiting, a delayed result cannot populate a replacement view. The already submitted xAI request may still finish and be charged.
Source: choice: leaving a view is local abandonment and cannot promise remote cancellation

### C-49: Simultaneous conversations are independent.
Observable: Two separately opened views, whether for the same user or different users, can send their own prompts. A reply or failure is visible only in its submitting conversation. A request for another view’s conversation is refused even if both views belong to the same user.
Source: choice: isolate view state without imposing an org-wide queue or cross-tab session

### C-50: Disabling chat rejects new ordinary sends even from an already-open view.
Observable: Once the change has taken effect, a still-entitled user holding the old view receives a disabled indication on the next send attempt. No inference is started for it.
Source: choice: the control must govern admission without relying on a page refresh

### C-51: Revoking a user rejects new sends from that user’s already-open view.
Observable: Once removal has taken effect, the revoked user receives an access refusal on a subsequent send without an outbound call.
Source: choice: the per-user control must govern admission without relying on a page refresh

### C-52: Suspending chat prevents delivery of a pending ordinary reply to the affected user.
Observable: If disabling chat or removing that user’s entitlement takes effect before a pending answer is released by the bot, that answer is withheld, including if access is restored before it arrives. The waiting view, if still open, gets an availability or access error. The dispatched call may still finish in xAI.
Source: choice: suspension should prevent new disclosure without claiming to cancel inference

### C-53: Each attempt uses the settings current when its call is admitted.
Observable: A model or credential change affects later admissions. A dispatched call is never resent using changed settings or reattributed to the new model.
Source: choice: an in-flight request must have a stable identity

### C-54: Only the current configuration can become verified.
Observable: After a model or credential change, setup shows the new settings as unverified. A check already running for the prior settings cannot approve the new ones, even if the old settings are subsequently saved again.
Source: choice: setup must not open chat on stale evidence

### C-55: A failed configuration change does not partially apply.
Observable: When saving a model change or credential replacement fails, the administrator sees the failure. The effective saved settings and readiness are the pre-change ones.
Source: choice: a rejected setup change must not silently leave an ambiguous configuration

### C-56: Inference is refused when the attempt cannot be made visible to operators.
Observable: If the bot cannot register an attempt for diagnostics before dispatch, the caller gets a temporary failure and no provider request is made.
Source: choice: each charged attempt needs a traceable reference

### C-57: A request left pending cannot remain pending indefinitely.
Observable: At 120 seconds from admission, a diagnostic lookup for a still-unresolved request shows outcome unknown with the unavailable category.
Source: choice: an operator must be able to distinguish an abandoned observation from active work

### C-58: An unapproved Salesforce outbound destination cannot be used for a Grok send.
Observable: If Salesforce outbound authorization for the integration is missing or blocked, the live check reports a configuration failure without obtaining a reply.
Source: implied: U-7 is subject to Salesforce’s outbound site authorization rule. [Salesforce outbound callout authorization](https://developer.salesforce.com/docs/platform/apex-dev/references/apex-dev/apex-callouts-named-credentials.html)

### C-59: A request rejected by Salesforce’s external credential permissions cannot reach Grok.
Observable: If the integration uses a Salesforce external credential, a user missing access to its principal sees a configuration failure even if entitled in the bot.
Source: implied: U-5 is subject to Salesforce principal access mapping where external credentials are used. [Salesforce credential glossary](https://developer.salesforce.com/docs/platform/named-credentials/references/named-credentials-reference/nc-glossary.html)

### C-60: An installed Salesforce external credential needs authentication material in its target org.
Observable: When such a credential is installed in a fresh org without its token, verification remains unsuccessful until authentication is provisioned there.
Source: implied: U-7 is subject to Salesforce’s rule that secret authentication material does not travel in credential metadata packages. [Salesforce credential provisioning](https://developer.salesforce.com/docs/platform/named-credentials/guide/nc-populate-external-credentials.html)

### C-61: Grok inference requires successful authentication to the xAI API.
Observable: Inference goes over HTTPS to api.x.ai with a valid inference bearer credential. A missing or rejected credential cannot yield a successful verification or chat reply.
Source: implied: U-1 is subject to xAI’s inference authentication rule. [xAI API authentication](https://docs.x.ai/developers/rest-api-reference/inference)

### C-62: A provider rate-limit refusal ends the current attempt.
Observable: When xAI rejects a send with HTTP 429 the user sees a rate-limit indication. The selected model’s requests-per-second and tokens-per-minute caps come from the xAI team tier and model. The exact effective figures are unconfirmed until the team and model are known.
Source: implied: U-4 is subject to the xAI per-model rate limits. [xAI rate limits](https://docs.x.ai/developers/rate-limits)

### C-63: A context too large for the selected model cannot produce a normal reply.
Observable: If xAI rejects the full prompt and conversation for exceeding its context budget, the user sees a context-limit failure with a way to shorten the prompt or start a fresh chat. The context-window ceiling in tokens is model-specific and its exact figure is unconfirmed until the model is selected.
Source: implied: U-2 is subject to the model’s context limit. [xAI text models](https://docs.x.ai/developers/model-capabilities/text/generate-text)

### C-64: The bot cannot promise that local chat reset deletes xAI’s copies.
Observable: The disclosure identifies xAI as a separate processor whose retention depends on the configured team. xAI documents a default 30-day audit retention period and a Zero Data Retention option. The exact policy of the target team is unconfirmed.
Source: implied: U-6 is subject to the provider’s retention policy. [xAI API security and retention](https://docs.x.ai/developers/faq/security)

### C-65: Salesforce Apex callout exhaustion prevents a reply.
Observable: If Apex performs the inference callout, a send blocked by Salesforce’s ceiling of 100 callouts per transaction is unsuccessful.
Source: implied: U-4 is subject to the Salesforce Apex per-transaction callout count when Apex performs the callout. [Salesforce Apex limits](https://developer.salesforce.com/docs/platform/apex-dev/references/apex-dev/apex-gov-limits.html)

### C-66: An admitted request can reach Grok when diagnostic registration requires a Salesforce write.
Observable: If Apex performs the callout, successfully registering an otherwise valid attempt does not cause a subsequent uncommitted-work error that prevents its inference.
Source: implied: U-1 and U-10 are subject to Salesforce’s rule that an Apex callout cannot run with uncommitted work in the callout transaction. [Salesforce transaction control](https://help.salesforce.com/s/articleView?id=Error-You-have-uncommitted-work-pending-Please-commit-or-rollback-before-calling-out&language=en_US&type=1)

### C-67: The bot stops waiting for the provider after at most 45 seconds of callout time.
Observable: If the service does not return within 45 seconds of dispatch, the attempt ends as a timeout from the caller’s perspective. The app does not treat that as proof that xAI stopped work.
Source: choice: bound waiting below Salesforce’s 120-second transaction ceiling when Apex performs the callout

### C-68: An active chat view stops waiting on a send after at most 60 seconds.
Observable: Measured from the user’s submit action while the view remains active and responsive, a send with no terminal answer by 60 seconds shows a timeout or connection error. A later response does not replace that error or become context.
Source: choice: bound waiting even when admission or the return connection stalls

### C-69: A scratch org ceases to serve the bot when the org expires.
Observable: If the authorized target is a scratch org, its lifetime is 7 days by default and at most 30 days. Users can no longer use that installation after expiration.
Source: implied: U-1 is subject to the Salesforce scratch-org lifespan when that type of development org is selected. [Salesforce development org options](https://developer.salesforce.com/docs/platform/apex-dev/references/apex-dev/apex-intro-get-dev-account.html)

### C-70: Production acceptance of any Apex would require Salesforce deployment validation.
Observable: If promoted later with Apex, Salesforce requires passing deployment tests. For the ordinary production test level the coverage threshold is at least 75% overall with some coverage on each trigger. With RunSpecifiedTests each deployed Apex class and trigger requires at least 75% coverage from the selected tests.
Source: implied: the requested development scope leaves any later production deployment subject to Salesforce’s Apex coverage and test-level rules. [Salesforce metadata deployment](https://developer.salesforce.com/docs/platform/api-metadata/references/file-based-calls/meta-deploy.html)

### C-71: A future target org cannot inherit a live-ready status from this development org.
Observable: An administrator deploying later to a separate org must verify that org’s credential, allowed destination, model entitlement, and user access in that target before enabling chat there.
Source: choice: readiness evidence must apply to the environment that will send the requests

### C-72: Installing the bot preserves existing Salesforce business records.
Observable: A user comparing business records before installation and after chat, verification, suspension, and rollback sees no bot-created, edited, or deleted business records.
Source: implied: U-12 adds a bot without requesting a change to the org’s business data

### C-73: Installing the bot preserves existing business automation.
Observable: Existing triggers, flows, validation rules, and scheduled business automation keep their prior behavior for ordinary Salesforce work. Chat activity does not invoke them on business records.
Source: implied: U-12 adds a separate experience without asking to automate existing work

### C-74: Installing the bot preserves existing access to unrelated Salesforce features.
Observable: A user who gains or loses Grok access keeps the same access to existing records, fields, applications, and navigation entries outside the bot.
Source: implied: U-12 adds a bot-specific entitlement

### C-75: Grok has no authority to act on the user’s behalf in Salesforce.
Observable: A prompt or Grok reply that asks to query or change org data, send a message, execute code, or invoke a tool produces no such action through the bot.
Source: choice: provide text assistance without a Salesforce agent or enabled inference tools

### C-76: Returned Grok text cannot execute in the Salesforce page.
Observable: When a response contains markup, script-like content, or instructions, opening the reply does not execute code, submit a request, or automatically navigate or load remote content.
Source: choice: provider-generated text is untrusted display content

### C-77: The inference credential is inaccessible from the chat client.
Observable: Inspection of the chat UI, its network requests and responses to Salesforce, application-visible diagnostics, and exported deployment materials reveals no xAI credential value.
Source: implied: U-5 and U-8 require the configured credential to stay private

### C-78: Chat content has no durable copy in Salesforce or in the bot’s browser storage.
Observable: After a chat ends, the user or an operator cannot recover prompts, drafts, replies, or error text through bot history, Salesforce records, application logs, or browser storage written by the bot.
Source: choice: temporary chat should not become a hidden transcript. Provider retention is governed separately by C-64

### C-79: Chat diagnostics cannot disclose another user’s conversation.
Observable: An ordinary user who supplies another attempt’s reference or varies it cannot see that user’s prompt, reply, or diagnostic details.
Source: implied: U-5 and U-10 separate operator lookup from private chat

### C-80: Failure messages exclude raw diagnostic details.
Observable: When an inference or setup action fails, the chat or setup view shows a safe category and next action where applicable. It never displays the raw provider body, request headers, credential, or platform stack trace.
Source: choice: provider and platform errors can include sensitive details

### C-81: Every send is subject to the same admission rules.
Observable: Direct invocation cannot bypass the restrictions for Salesforce authentication, bot entitlement, suspension, input, pending sends, conversation capacity, admission expiry, or diagnostic availability.
Source: choice: a saved page or direct call must honor the same limits as the visible controls

### C-82: A whitespace-only prompt is treated as empty.
Observable: A value consisting entirely of Unicode White_Space code points receives the empty-prompt outcome.
Source: choice: whitespace alone has no useful question text

### C-83: A blank model identifier cannot be saved.
Observable: Saving an empty or whitespace-only model identifier is refused with an input-required indication.
Source: choice: an identifier is necessary to choose a Grok model

### C-84: An operator can browse admitted requests.
Observable: The operator can browse all admitted attempts within the lookup window, covering both request types and all four outcomes. Input and access refusals before admission create no entries.
Source: choice: offer a route to diagnose a problem when the reference was lost

### C-85: The caller receives a reference for an admitted attempt once admission is acknowledged.
Observable: An acknowledged send or verification shows an opaque reference unique to that attempt. A subsequent error in the same view keeps it available to report. If the view never receives acknowledgment, its error does not invent a reference.
Source: choice: match user reports to actual operator entries

### C-86: A verification check has a bounded waiting time.
Observable: A check with no live result by 60 seconds from initiation shows verification failed with a timeout or connection indication. A late result cannot change that verification status.
Source: choice: setup should recover from a stalled check without reopening an expired activation decision

### C-87: The bot admits only one live check of the current settings at a time.
Observable: Repeated requests to verify the same settings while a check is pending do not start a second inference or reset the existing check’s deadline.
Source: choice: verification should have one authoritative result at a time

### C-88: Live verification is available only while ordinary chat is disabled.
Observable: When the bot is enabled, a request to verify is refused until the administrator disables chat.
Source: choice: keep re-verification under the same activation gate as initial setup

### C-89: An expired submission cannot initiate a provider request.
Observable: A chat or verification submission that first reaches admission 60 seconds or more after its initiating action is refused as expired. A delayed replay of an earlier attempt cannot initiate inference after that attempt’s reference ages out.
Source: choice: prevent abandoned or replayed actions from unexpectedly starting billable work

### C-90: A late observable outcome may resolve an unknown diagnostic entry.
Observable: Within the lookup window, a terminal provider result can replace outcome unknown with succeeded or failed. The result never changes a chat or verification whose wait already ended.
Source: choice: improve the operator’s evidence without reopening a closed user action

### C-91: The bot distinguishes the supported reasons for an unsuccessful admitted attempt.
Observable: The caller sees the applicable safe category. The supported categories are configuration (missing or rejected credential, blocked outbound access, model or team access, or explicit billing refusal), rate limit (HTTP 429), context limit (explicit context overflow), timeout (deadline), connection failure (interrupted or unreachable service), unavailable (org or platform cannot complete the operation), access withdrawn (entitlement revoked), disabled (org-wide suspension), no usable answer (missing, empty, malformed, blocked, or unsupported reply), and other provider error (all remaining provider error responses). Operator diagnostics describe inference outcomes using these categories. An access or availability failure affecting only delivery does not replace a known inference outcome.
Source: choice: distinguish problems that call for retry, shorter context, or administrator action without leaking raw details

### C-92: The bot displays a text reply only when xAI returns usable answer text.
Observable: A completed response with nonblank assistant answer text yields one reply, including when the answer itself is a conversational refusal. Missing, empty, whitespace-only, malformed, or tool-only output and an explicit provider block produce the no-usable-answer outcome. Reasoning material is excluded from the displayed reply.
Source: choice: distinguish an assistant’s answer from provider metadata and execution errors

### C-93: The bot marks a usable reply cut short by the output-token budget.
Observable: If xAI explicitly reports the output limit and returns nonblank assistant text, the chat shows that text with an incompleteness indication. The pair counts as successful and only the actual answer text becomes context.
Source: choice: keep useful partial text while making the cutoff visible

### C-94: Salesforce Apex callout time limits can end an attempt before Grok replies.
Observable: If Apex performs the inference callout, a send cannot wait beyond Salesforce’s 120-second cumulative callout timeout per transaction. A callout with no timeout configured defaults to 10 seconds.
Source: implied: U-4 is subject to Salesforce’s Apex callout clock when Apex performs the callout. [Salesforce Apex limits](https://developer.salesforce.com/docs/platform/apex-dev/references/apex-dev/apex-gov-limits.html)

### C-95: A Salesforce Apex callout payload over the platform ceiling cannot yield a normal reply.
Observable: If Apex performs the inference callout, Salesforce caps each request or response at 6 MB in synchronous Apex or 12 MB in asynchronous Apex. These bytes count against the respective 6 MB or 12 MB heap, so an attempt can also fail below the payload ceiling.
Source: implied: U-4 is subject to Salesforce’s callout size and heap limits when Apex performs the callout. [Salesforce Apex limits](https://developer.salesforce.com/docs/platform/apex-dev/references/apex-dev/apex-gov-limits.html)

### C-96: A successful configuration change requires a fresh conversation for further sends.
Observable: When chat is enabled again, a send from a view opened on the old configuration is refused with a prompt to start a fresh chat. No prior prompt, reply, or draft is sent under the new configuration automatically, even if the previous model identifier has been restored.
Source: choice: users can decide what to submit after the destination team or model may have changed

### C-97: Opening the chat alone does not run inference.
Observable: An authorized user can open, read the disclosures, enter a draft, and leave without an xAI call. Ordinary inference starts only on explicit submission.
Source: choice: keep data transfer and possible charges tied to a deliberate action

### C-98: One failed inference does not disable the bot by itself.
Observable: After a provider timeout, rate limit, or other unsuccessful inference, the administrator still sees the prior enable setting. A subsequent explicit send can succeed when the service recovers.
Source: choice: the suspension control is an operator decision

### C-99: The administrator can identify the last working model configuration for rollback.
Observable: After verifying a replacement, the administrator can still determine the prior live-verified model identifier, or see that no prior verified configuration exists. No prior secret can be retrieved through rollback.
Source: choice: allow restoration even after diagnostic entries have expired

### C-100: The administrator can identify the last working release for rollback.
Observable: An administrator can identify and recover the prior release that completed a live pilot chat, or determine that it is the first release and no prior one exists.
Source: choice: make C-42 executable without guessing which deployed revision worked

### C-101: Rollback preserves diagnostics within the lookup window.
Observable: After restoring a prior release or configuration, the operator can still look up pre-rollback attempts until their original 7-day window ends.
Source: choice: keep evidence of the failure that prompted rollback

### C-102: The bot sends inference credentials only to the authorized xAI inference host.
Observable: If the service redirects to a different host, the bot does not follow it with the credential or chat text. The attempted inference ends with a safe provider error.
Source: choice: service responses cannot choose where the bot sends the secret or user data

### C-103: The installation is accepted only after an entitled pilot user obtains a live reply in the target org.
Observable: An administrator can open the bot in the authorized target as a pilot user and get a live Grok reply through the ordinary chat entry. If target access, deployment privileges, or xAI provisioning is unavailable, delivery is identified as blocked until that prerequisite is supplied.
Source: choice: a successful operator check alone cannot establish that an ordinary user can use the installed bot

### C-104: Suspension prevents undispatched ordinary requests from reaching xAI.
Observable: If chat is disabled or the user loses entitlement after admission but before dispatch, the admitted attempt ends without an xAI call. An enabled state or entitlement restored in the meantime does not revive that attempt.
Source: choice: stopping new outbound work includes requests still waiting to leave Salesforce

### C-105: A superseded configuration cannot start an undispatched request.
Observable: If a model or credential change takes effect after admission but before dispatch, the ordinary or verification attempt ends with a configuration failure and no xAI request. A dispatched request keeps the settings under which it started.
Source: choice: do not start new provider work under obsolete credentials or silently change the request

### C-106: The send deadline also applies before dispatch.
Observable: An admitted chat or verification attempt still awaiting dispatch at 60 seconds from initiation ends with a timeout and no future provider call for that attempt.
Source: choice: enforce the same deadline across admission and dispatch delays

### C-107: An expired pending send no longer blocks a deliberate new send.
Observable: At 60 seconds from a send’s initiating action, a new send in an otherwise eligible conversation may proceed even if the prior inference outcome is still unknown. The expired prompt and any later reply are omitted from the follow-up context.
Source: choice: the user-facing wait must release the conversation without making late text part of it

### C-108: An acknowledged conversation reset prevents its undispatched send from reaching xAI.
Observable: If Salesforce receives a new-chat reset before the previous conversation’s pending request is dispatched, that request ends without an outbound call. Closing a browser or losing the connection can leave Salesforce unaware of abandonment until the request deadline.
Source: choice: honor a known local abandonment before any external work starts

### C-109: A signed-in user without bot entitlement cannot open an interactive conversation.
Observable: Directly opening the bot as an unassigned user shows an access refusal or the Salesforce access-denied screen. No prompt can be entered for submission in that view.
Source: choice: enforce the bot audience at entry as well as at send

### C-110: An entitled user opening disabled chat sees that chat is unavailable.
Observable: An entitled user who opens the bot while it is disabled is shown that it is unavailable and cannot submit a prompt.
Source: choice: make planned suspension distinct from an access grant problem

### C-111: Only authorized Salesforce operators can inspect bot diagnostics.
Observable: An administrator authorized to operate the bot can use the operator lookup. A signed-in user without that authority receives an access refusal, regardless of their chat entitlement.
Source: choice: the development org can use its bot administrator as the operator without creating a separate mandatory role

### C-112: A missing diagnostic reference produces a no-match result.
Observable: An authorized operator looking up a mistyped, unknown, or expired reference sees that no matching attempt is available.
Source: choice: the lookup must give a clear answer when a report cannot be correlated

