## Use cases

### U-1: An org administrator brings Grok into a Salesforce development org
Flow: Verify the target org ID, install the bot, provision its xAI credential, select an available Grok text model, grant a pilot user access, then enable the bot and send a sample prompt to see a live Grok answer. If the org ID is wrong, stop before changing that org. If setup is incomplete, finish setup before enabling.
Source: request

### U-2: An authorized org user asks Grok a question to get an answer
Flow: Open Grok inside the signed-in org, type a text prompt, submit it, see that it is pending, then read Grok’s answer. Ask a follow-up that refers to the answer or start a fresh conversation.
Source: implied: the request calls for an interactive Grok bot inside a Salesforce development org

### U-3: An org user checks access and availability before sending
Flow: Open Grok as an assigned user, an unassigned user, or after sign-out. An assigned user can use it when enabled. Others are denied. When disabled or awaiting setup, an assigned user sees why they cannot send.
Source: implied: U-1 and U-2 require controlled access to the org’s connection

### U-4: An authorized org user corrects input to send a valid prompt
Flow: Try empty text, whitespace, a prompt exactly at the supported maximum, and a prompt above it. The maximum is accepted and invalid text can be corrected in place.
Source: implied: U-2 requires an input boundary

### U-5: An authorized org user handles a failed send to continue the conversation
Flow: Send when access is rejected by xAI, the model is unavailable, a quota is reached, the network fails, the response times out, or a response has no usable answer. See the outcome, keep the draft, and decide whether to send again after correction or recovery.
Source: implied: U-2 depends on an external service

### U-6: An org administrator observes and restores service
Flow: Inspect a failed smoke prompt, identify whether local setup, provider access, the model, capacity, or connectivity needs attention, correct configuration or replace the key, then send a fresh sample prompt and see an answer.
Source: implied: U-1 establishes an integration that can subsequently fail

### U-7: An org administrator pauses, resumes, upgrades, or rolls back Grok
Flow: Pause new sends, update the bot, or restore the preceding working release when one exists. If replacement is interrupted, finish or restore a complete release before resuming. On first-install rollback, remove the bot experience. After release recovery, use existing Salesforce records and workflows as before.
Source: implied: U-1 adds a feature to an existing org

### U-8: An authorized org user submits from overlapping sessions or navigates away
Flow: Double-submit one prompt while pending, open a separate conversation in another tab, or leave while waiting. See one answer at most for the pending turn and keep each view’s conversation separate.
Source: implied: U-2 runs in a browser where actions and views can overlap

## Clauses

### C-1: Grok is available inside a Salesforce development org.
Observable: In the designated Salesforce development org, open the Grok bot from within Salesforce.
Source: request

### C-2: The bot returns a Grok answer to a submitted question.
Observable: Submit a supported prompt with the connection ready and Grok responsive. The bot presents the text answer returned by Grok.
Source: request

### C-3: The administrator verifies readiness with a live smoke prompt.
Observable: After enabling the configured bot, use an assigned Salesforce account without bot administration privileges to send a benign test prompt. An answer from the configured Grok service verifies the pilot user’s path.
Source: choice: A smoke check with administrator privileges could miss a permission required by a pilot user

### C-4: The bot shows when a send is pending.
Observable: After an admitted send, the user sees that a reply is pending until the turn succeeds, fails, or the conversation view is lost.
Source: choice: A pending state distinguishes a slow answer from a missed submit

### C-5: An open conversation supplies recent successful turns as follow-up context.
Observable: After a successful turn, a further send in the same view supplies up to the 5 most recent successful prompt-and-answer pairs in their original order, followed by the new prompt.
Source: choice: A small rolling context supports ordinary follow-ups within a bounded cost

### C-6: A user can start an empty conversation.
Observable: Use the new-conversation action when idle. The draft and visible turns clear, and the next send has zero prior turns in its context.
Source: choice: A user needs a way to change subjects or clear sensitive text from view

### C-7: The bot refuses empty prompts.
Observable: Submit an empty string or text composed solely of Unicode White_Space characters. The user sees an input correction and the bot makes no provider request.
Source: choice: Empty text has no question and needlessly consumes capacity

### C-8: A prompt may contain up to 4,000 Unicode code points.
Observable: A nonblank prompt of 1–4,000 Unicode code points, inclusive, passes the length check. A prompt of 4,001 or more Unicode code points fails that check before contacting Grok.
Source: choice: A bounded prompt is enough for a development-org text demo and avoids sending unbounded pasted input

### C-9: Successful replies are rendered as text.
Observable: The returned answer is readable in the conversation. Any embedded markup is inert, including strings that resemble links, scripts, commands or Salesforce actions.
Source: choice: Text is adequate for a chat and generated content is untrusted

### C-10: A failed send preserves the editable prompt in its current view.
Observable: If the view remains open, a send that fails leaves its prompt available for correction or another explicit send.
Source: choice: Avoids retyping and lets the user reconsider what will be sent

### C-11: A failed turn ends with a visible failure outcome.
Observable: When an admitted send fails in an open view, the view ends its pending state with a user-safe failure outcome.
Source: implied: U-5

### C-12: The administrator can pause admission of new sends.
Observable: With the bot paused, an assigned user attempting a new send sees that it is paused and no new provider call is made.
Source: choice: A reversible stop is useful for maintenance or provider spend control

### C-13: The administrator can resume admission of new sends.
Observable: After the administrator resumes a configured, working bot, an assigned user can send again without opening a replacement org.
Source: choice: A pause must be reversible

### C-14: The administrator can replace the provider credential.
Observable: Replace the credential for the development org and send a new smoke prompt. When the replacement has valid model access and capacity, the new prompt receives a live answer.
Source: choice: A development connection must recover from credential revocation or expiration

### C-15: An earlier working bot release can be restored.
Observable: Roll back a bot upgrade to the immediately preceding working release if one exists. After restoring the connection prerequisites, the earlier bot release again answers a live smoke prompt.
Source: choice: One working predecessor is enough to cover the requested rollback exercise

### C-16: Rolling back the first installation removes the bot experience.
Observable: With no prior bot release, undo the first rollout. The bot entry disappears from Salesforce navigation.
Source: choice: An org with no predecessor should return to having no Grok bot

### C-17: Bot work preserves existing Salesforce record data.
Observable: Compare existing records before and after setting up, using, pausing, upgrading or rolling back the bot. Their data stays unchanged as a result of those bot actions.
Source: choice: The request calls for a bot and supplies no CRM record task

### C-18: One pending turn is admitted per conversation view.
Observable: While the view shows a pending turn, submitting again in that view cannot start another turn.
Source: choice: Avoids accidental duplicate requests and preserves an intelligible turn order

### C-19: Two views have separate conversations.
Observable: Open the bot in two views, including two tabs signed in as the same user. Each receives only its own draft, transcript and pending outcome.
Source: choice: Browser views are independent workspaces and require no shared conversation store

### C-20: One development org is the rollout target.
Observable: Before setup, the deploying administrator verifies the Salesforce org ID against the designated ID. The rollout proceeds only on a match. A Developer Edition org, development sandbox, or scratch org qualifies if designated for this work.
Source: choice: No org ID or particular development-org type was supplied

### C-21: The bot has a discoverable Salesforce entry.
Observable: A permitted user can identify and open Grok through signed-in Salesforce Lightning navigation without a separate website, a copied URL, or a separate xAI login.
Source: choice: A single internal entry is enough for the development rollout

### C-22: Bot access requires a current Salesforce session.
Observable: A signed-out visitor opening a saved bot URL or attempting a send cannot obtain a bot conversation or invoke Grok. Salesforce sign-in is required.
Source: implied: U-2 takes place inside the user’s Salesforce org

### C-23: A bot-use grant is required on every send.
Observable: A signed-in Salesforce user is refused before any Grok request if the operator has never granted bot use or has revoked the grant. The same result holds from a stale page or a direct invocation of the send action.
Source: choice: Membership in the org alone does not authorize use of its provider account

### C-24: The operator can grant bot use to individual org users.
Observable: Grant bot use to one active Salesforce user. That user can send if the bot is otherwise ready, while another otherwise equivalent unassigned user is refused.
Source: choice: Individual assignment supports a development pilot

### C-25: The operator can revoke bot use from an individual org user.
Observable: Remove a user’s bot-use grant. Their next attempted send is denied even from an already-open view.
Source: choice: The pilot must be reversible for each participant

### C-26: Bot administration requires a separate administrative grant.
Observable: A signed-in user without administrative authority cannot change model selection, provision or replace a credential, pause or resume the bot, change bot-use assignments, view operator diagnostics, or deploy or roll back the bot. Bot-use access alone confers none of these operations.
Source: choice: The provider connection and deployment controls belong to the administrator

### C-27: A fresh install starts paused.
Observable: Open the bot after first installation. No user can send until the administrator resumes it after setup.
Source: choice: A new deployment should start with explicit operator control over live traffic

### C-28: Resuming requires complete local provider setup.
Observable: If either the credential has not been provisioned or the text-model selection is missing, the resume attempt leaves the bot paused. The administrator can identify which of those two prerequisites is missing. Presence alone does not prove remote access or capacity.
Source: choice: An administrator can fix incomplete setup before exposing it to users

### C-29: The operator can choose one xAI Grok text model for the org.
Observable: Supply one exact model identifier for an xAI Grok text model. The administrator can select a different identifier to replace the current selection.
Source: choice: No specific Grok model was requested and availability depends on the provider account

### C-30: The operator can see local service readiness.
Observable: The administrator can distinguish unconfigured (credential or model missing), paused (both supplied and sends disabled), and enabled (both supplied and sends allowed subject to access and live service availability).
Source: choice: Local configuration state and current provider health are different observations

### C-31: The initial conversation is empty.
Observable: On first open, a permitted user sees an empty transcript and empty text composer.
Source: choice: A minimal text conversation supports the requested bot

### C-32: The composer accepts plain text only.
Observable: A user can type or paste text, including newlines and non-ASCII characters. The bot offers no submission of files, images, audio, or video, because the requested bot has no multimodal requirement.
Source: choice: Text is sufficient for the development rollout

### C-33: An admitted prompt retains its text.
Observable: Submit a valid prompt containing leading or trailing spaces, line breaks, or non-ASCII text. The prompt shown on success and the text received by Grok preserve those characters.
Source: choice: Code, quotations and multilingual text may depend on formatting

### C-34: The visible transcript holds up to five successful turns.
Observable: Complete six successful turns without leaving the view. The transcript contains successful turns 2–6 in order, each consisting of the submitted user text followed by the answer text. The pending prompt or retained failed draft does not occupy a successful-turn slot.
Source: choice: A visible history equal to the context window makes follow-up behavior predictable

### C-35: A successful turn clears the composer.
Observable: Receive a successful answer while the view is open. The composer is empty for the next prompt.
Source: choice: A completed prompt has already moved into the transcript

### C-36: A conversation is available only during the lifetime of its open view.
Observable: Reload, close or leave the bot view, then return. The draft, transcript and any pending outcome from the previous view cannot be recovered in the new view. The bot has no saved transcripts or cross-device history.
Source: choice: A development pilot needs no durable chat archive

### C-37: The bot sends inference requests only to the official xAI API.
Observable: Ask the bot to redirect the prompt or provider credential elsewhere. Inference traffic goes only to the official xAI HTTPS API for the configured Grok model. There is no user-supplied destination.
Source: choice: Restricts the integration to the requested provider

### C-38: The bot discloses that conversation text is sent externally before the first send.
Observable: Before first submission in a fresh view, the user can see that the new prompt and up to five recent successful turns go to xAI.
Source: choice: The user needs to know what leaves Salesforce before submitting

### C-39: The bot uses a shared development connection.
Observable: An authorized user can send without supplying an xAI key. The administrator provisions one development-org credential for its current provider configuration.
Source: choice: One administrator-managed connection is sufficient for one pilot org

### C-40: Grok answers appear only once complete.
Observable: Receive an answer in parts from the provider. No part appears in the transcript until the complete answer is available.
Source: choice: Complete text replies are adequate for the pilot

### C-41: A request for unrelated bot capabilities stays a text exchange.
Observable: A submit has one possible external action, text inference at xAI. Requests for CRM reads or writes, web search, code execution, messaging, or scheduled work can receive a text answer without carrying out those actions.
Source: choice: This bot answers questions through Grok using supplied conversation text

### C-42: A returned answer must contain usable text.
Observable: Provider results with empty text, text composed solely of Unicode White_Space characters, missing answer text, unreadable structure, or a provider-declared incomplete answer produce a failed turn. A complete refusal written as answer text is a valid answer and is displayed as returned.
Source: choice: An upstream success status alone does not provide a readable answer

### C-43: An answer may contain up to 12,000 Unicode code points.
Observable: An otherwise usable response at 12,000 code points is displayed intact. If it exceeds 12,000, the turn fails with an answer-size outcome and no partial answer.
Source: choice: A bounded answer keeps five context turns practical without silently changing the model’s answer

### C-44: An admitted turn uses the configuration in effect at admission.
Observable: Admit a send, then change the configured model or credential. That send uses the admitted settings, or fails under them if xAI rejects them. The next admitted send uses the new settings.
Source: choice: One turn should never straddle two provider configurations

### C-45: Pausing allows previously admitted turns to settle.
Observable: Pause the bot while a turn is pending. An already-admitted turn may finish under the original settings, subject to its deadline and continued user authorization.
Source: choice: Pause stops new spend without promising cancellation of requests already in progress

### C-46: A revoked user cannot receive a pending answer.
Observable: Make a user’s access revocation effective, or expire their Salesforce session, before the answer is released to the view. The answer is withheld. The view exits pending when it learns that access has ended or reaches its send deadline.
Source: choice: Continued permission is required when releasing an answer

### C-47: The draft cannot change while its send is pending.
Observable: While one send is pending in a view, the submitted draft is read-only.
Source: choice: Locks the draft to the turn the user is waiting for

### C-48: Starting a new conversation is unavailable while a send is pending.
Observable: Try the new-conversation action while pending. It cannot reset the open conversation until the turn finishes or the view is left.
Source: choice: The minimal interface has no in-view cancellation

### C-49: An admitted turn makes at most one provider inference attempt.
Observable: Double-submit the same action or replay its invocation during its lifetime. Observe at most one inference attempt for that action, including when a browser or intermediating transport repeats delivery.
Source: choice: Avoids repeated requests and spend from a single user action

### C-50: An explicit subsequent send is a distinct turn attempt.
Observable: After a failure or success, explicitly submit even the same text again in an idle view. It is eligible for a new attempt under current conditions.
Source: choice: Text equality must not suppress an intentional repeat or retry

### C-51: A failed turn does not enter the follow-up context.
Observable: Fail a turn between two successful sends. The later provider call contains the previous successful turns and its own new prompt, with no failed prompt or error included from the intervening attempt.
Source: choice: A user may revise or abandon a failed message

### C-52: A send has a 30-second user-facing deadline.
Observable: If no terminal outcome is available within 30 seconds of submission, the open, responsive view exits pending and shows a timeout. If the browser suspends the view, an elapsed deadline is reflected when the view becomes responsive again.
Source: choice: Bounds how long a development user waits for a single non-streamed answer

### C-53: Late outcomes cannot change a closed turn.
Observable: Deliver a result after its turn succeeds, fails, or times out, including after a new send has begun. No extra answer, updated error or change to the new turn appears.
Source: choice: The first terminal outcome owns the turn

### C-54: Leaving a view discards its pending answer locally.
Observable: Leave, reload or close the view before an answer arrives. Returning presents an empty conversation and the prior result does not appear there. An admitted provider attempt can still complete upstream.
Source: choice: Leaving the chat releases the local session without promising remote cancellation

### C-55: One view does not lock another view’s composer.
Observable: With one open view pending, submit a valid prompt from a second authorized view. The second send may proceed independently subject to shared org and provider capacity.
Source: choice: The pending limit governs conversation ordering per view

### C-56: A failed send never starts an automatic second inference attempt.
Observable: Cause a provider rejection, transport interruption, deadline expiry, unusable reply or Salesforce failure. Observe no second provider inference call unless the user explicitly submits again.
Source: choice: The first request may already have consumed provider capacity

### C-57: An uncertain send outcome warns of possible provider processing.
Observable: When the bot cannot confirm whether an admitted request was processed, such as after a deadline or lost connection, its failure feedback makes clear that resending may send the same text again.
Source: choice: Local failure cannot prove that remote processing stopped

### C-58: The open view distinguishes the actions a user can take after refusal or failure.
Observable: A signed-out user is directed to sign in. An unassigned user is refused and can seek access. For pause the user can wait for resume. For incomplete setup the user can seek administrator help. For blank or oversized input the user can correct the text. For an already-pending send the pending state tells the user to wait. For a stale release the user can reopen the bot. For a capacity or account refusal the user can retry later or seek administrator help. For a timeout, transport, Salesforce runtime or other provider failure the user can explicitly resend or seek help. For an unusable, incomplete or oversized answer the user can revise the prompt, resend, or seek help. Exact UI wording is open.
Source: choice: Feedback should guide recovery using a finite set of actionable outcomes

### C-59: Operator diagnostics classify the latest smoke outcome.
Observable: Attempt an operator smoke prompt in an open view. Its latest outcome identifies one of success, local access refusal, paused, incomplete local setup with the absent prerequisites listed, invalid local input, stale release, Salesforce runtime refusal, provider authentication or permission rejection, unknown model or inference route, provider throttling, provider account or billing refusal when specifically identified, invalid provider request, upstream service error, transport failure, deadline expiry, unusable reply, answer above the limit, or unclassified provider failure. A duplicate submit while pending leaves the current smoke attempt in place.
Source: choice: A basic smoke diagnosis supports recovery without a persistent monitoring system

### C-60: Operator smoke diagnostics expire with the smoke view.
Observable: Leave or refresh the smoke view after a completed attempt. Its diagnostic outcome disappears from the bot and cannot be restored there.
Source: choice: A live smoke prompt is sufficient for development-org operation

### C-61: Changing an available model does not erase an open conversation.
Observable: Change the selected Grok model between successful turns without replacing the bot release. The next turn uses the existing conversation context with the new model.
Source: choice: Simple connection maintenance need not erase a user’s working context

### C-62: An upgrade or rollback occurs with new sends paused.
Observable: Begin bot release replacement while enabled. The administrator first pauses new sends and keeps them paused during replacement and setup verification. Resuming follows the same local setup rule as first install.
Source: choice: A maintenance boundary prevents traffic against a mixed release

### C-63: Replacing the release invalidates views served by the previous release.
Observable: After activation of the replacement release, try to send from an earlier release’s still-open view. It cannot admit a new turn and tells the user to reopen the bot, or Salesforce serves its unavailable response if the bot has been removed.
Source: choice: Existing pages cannot send against an incompatible replaced release

### C-64: A replaced release cannot publish an outstanding answer into a stale view.
Observable: If a turn is still pending when its release is replaced or removed, its late result does not appear. The old open view shows that the bot must be reopened or is unavailable when it detects replacement, or ends with its deadline if it cannot reconnect.
Source: choice: A release change ends ownership of older pending turns

### C-65: An incomplete rollout keeps new sends paused.
Observable: Interrupt deployment, upgrade or rollback after pausing and before replacement is verified ready for resumption. Ordinary sends remain blocked until an administrator restores a complete release and explicitly resumes it.
Source: choice: Partial completion never exposes an uncertain release to ordinary users

### C-66: Rolling back the bot release does not reinstate a previous secret.
Observable: Replace the provider credential, then restore the preceding bot release. That release may use the currently provisioned key or another valid key the administrator supplies. The replaced key is never recovered implicitly.
Source: choice: Rotated or revoked credentials must not become active through release rollback

### C-67: Salesforce can refuse an unauthorized outbound Apex callout.
Observable: If Apex supplies the Salesforce-to-xAI connection, omit its outbound authorization. The smoke attempt fails before reaching xAI. Salesforce requires an approved remote site or an applicable Named Credential for the destination.
Source: implied: U-1 under [Salesforce outbound site authorization](https://developer.salesforce.com/docs/platform/apex-dev/references/apex-dev/apex-callouts-remote-site-settings.html)

### C-68: Salesforce can refuse invocation of an Apex-backed Lightning send entry.
Observable: If the send entry calls an Apex class, remove the Salesforce profile or permission-set access to that entry class. The user cannot execute that send through Lightning.
Source: implied: U-3 under [Salesforce Apex entry-point class security](https://developer.salesforce.com/docs/platform/apex-dev/references/apex-dev/apex-classes-security.html)

### C-69: Salesforce can refuse use of an unmapped external credential principal.
Observable: If the bot uses an external credential principal, a user lacking the required mapping cannot make its authenticated callout, even if they can open the bot.
Source: implied: U-3 under [Salesforce external credential principal access](https://developer.salesforce.com/docs/platform/named-credentials/references/named-credentials-reference/nc-glossary.html)

### C-70: A managed package installation does not supply a live external-credential secret.
Observable: If the bot is delivered as a managed package with external credentials, a fresh installation cannot make the authenticated callout solely with packaged metadata. The target org requires separate credential provisioning.
Source: implied: U-1 under [Salesforce packaging rules for credential secrets](https://developer.salesforce.com/docs/platform/named-credentials/guide/nc-populate-external-credentials.html)

### C-71: An Apex-backed send can be refused at the per-transaction callout ceiling.
Observable: If another callout in the bot’s Apex transaction would exceed 100 callouts, Salesforce will not execute it and that turn cannot yield a Grok answer from it.
Source: implied: U-5 under [Salesforce Apex callout limits](https://developer.salesforce.com/docs/platform/apex-dev/references/apex-dev/apex-callouts-timeouts.html)

### C-72: Developer Edition can refuse concurrent outbound Apex calls when its org capacity is full.
Observable: If Apex is used in Developer Edition and the org already has 20 concurrent external callouts, a new bot callout can fail without an answer. Other outbound Apex activity in that org counts against the same capacity.
Source: implied: U-5 under the [Developer Edition concurrent callout limit](https://developer.salesforce.com/docs/platform/apex-dev/references/apex-dev/apex-callouts-timeouts.html)

### C-73: An Apex-backed send cannot wait past its callout timeout for xAI.
Observable: When xAI does not answer before the configured Apex timeout, the turn cannot succeed on that callout. Salesforce defaults to 10 seconds, accepts 1–120,000 milliseconds for a custom timeout, and caps cumulative callout waiting per transaction at 120 seconds. C-52 independently bounds the user’s wait.
Source: implied: U-5 under [Salesforce Apex callout timeout limits](https://developer.salesforce.com/docs/platform/apex-dev/references/apex-dev/apex-callouts-timeouts.html)

### C-74: Apex callout size can limit delivery of a Grok answer.
Observable: If Apex is used, an HTTP request or response above 6 MB in synchronous Apex or 12 MB in asynchronous Apex cannot yield a successful turn. Size includes the complete upstream envelope, not only displayed answer text.
Source: implied: U-5 under [Salesforce Apex HTTP payload limits](https://developer.salesforce.com/docs/atlas.en-us.apexcode.meta/connectapi/apex_gov_limits.htm)

### C-75: Exhausting the Apex heap can prevent an answer from reaching the user.
Observable: If an Apex-backed turn exceeds 6 MB in synchronous Apex or 12 MB in asynchronous Apex heap, Salesforce can terminate the transaction before it returns an answer. Callout request and response data count towards heap.
Source: implied: U-5 under [Salesforce Apex heap limits](https://developer.salesforce.com/docs/atlas.en-us.apexcode.meta/connectapi/apex_gov_limits.htm)

### C-76: Exhausting Apex CPU time can prevent a turn from succeeding.
Observable: If the bot’s Apex execution exceeds its Salesforce CPU allowance, the transaction can terminate without an answer. The allowance is 10,000 ms for synchronous Apex or 60,000 ms for asynchronous Apex. Remote HTTP waiting does not consume the CPU allowance.
Source: implied: U-5 under [Salesforce Apex CPU limits](https://developer.salesforce.com/docs/atlas.en-us.apexcode.meta/connectapi/apex_gov_limits.htm)

### C-77: Pending Apex operations can block a callout to Grok.
Observable: If a proposed Apex callout encounters uncommitted DML, pending asynchronous Apex, scheduled Apex, pending email or an active savepoint, the callout cannot go ahead in that state. A user sees a failed turn if the restriction blocks the integration.
Source: implied: U-5 under [Salesforce callout transaction restrictions](https://developer.salesforce.com/docs/platform/apex-dev/references/apex-dev/apex-callouts-timeouts.html) and [savepoint rules](https://developer.salesforce.com/docs/platform/apex-dev/references/apex-dev/langcon-apex-transaction-control.html)

### C-78: A Salesforce record trigger cannot synchronously wait for Grok.
Observable: A synchronous record-trigger transaction cannot obtain a Grok answer by making an Apex callout inline. This applies even when a user can get an answer through the bot’s interactive path.
Source: implied: U-2 under the [Salesforce trigger callout rule](https://developer.salesforce.com/docs/platform/apex-dev/references/apex-dev/apex-triggers.html)

### C-79: An expired scratch org can no longer host this bot.
Observable: If the selected target is a scratch org, its lifespan is selectable from 1 to 30 days and defaults to 7 days. After expiry, the old org and its bot are unavailable and the org cannot be restored.
Source: implied: U-1 under [Salesforce scratch-org expiration](https://developer.salesforce.com/docs/atlas.en-us.sfdx_dev.meta/sfdx_dev/sfdx_dev_scratch_orgs.htm)

### C-80: A live request requires valid xAI inference authorization.
Observable: Use `https://api.x.ai` with a valid xAI API bearer key whose account allows the inference endpoint and selected text model. Missing or invalid authorization or a disallowed endpoint or model produces a refusal instead of an answer.
Source: implied: U-1 under the [xAI inference authentication contract](https://docs.x.ai/developers/rest-api-reference/inference) and [key permissions](https://docs.x.ai/developers/rest-api-reference/management/auth)

### C-81: xAI can throttle sends against team-level per-model inference limits.
Observable: Drive requests above the selected model’s requests-per-second or tokens-per-minute ceiling. xAI returns HTTP 429, which appears as a capacity failure. The exact RPS and TPM figures for this rollout are unconfirmed until the actual model and xAI team tier are known. The operator can look up both in the team’s xAI Console.
Source: implied: U-5 under [xAI inference rate limits](https://docs.x.ai/developers/rate-limits)

### C-82: xAI can reject a request that exceeds the selected model’s context window.
Observable: If the combined input exceeds the selected model’s token window, the turn fails on that request. The window in tokens for this rollout is unconfirmed until model selection. The operator can inspect the selected model’s published context length.
Source: implied: U-5 under [xAI model context metadata](https://docs.x.ai/developers/rest-api-reference/inference/models)

### C-83: An xAI team without sufficient billing capacity can no longer produce an answer.
Observable: When the xAI team exhausts its prepaid credits and reaches its postpaid spending limit, xAI refuses further inference. Existing spend capacity and the team’s USD limit are unconfirmed until the team is designated. The operator can verify them in the xAI Console.
Source: implied: U-5 under [xAI team billing limits](https://docs.x.ai/developers/rest-api-reference/management/billing)

### C-84: Clearing a local conversation does not control xAI audit retention.
Observable: After clearing the view, content already submitted remains subject to the xAI team’s policy. xAI documents a 30-day default audit retention period and a Zero Data Retention option. The actual team setting is unconfirmed until setup.
Source: implied: U-2 under [xAI API data retention](https://docs.x.ai/developers/faq/security)

### C-85: A future production Apex deployment must pass Salesforce’s required test run.
Observable: If a separately authorized production deployment includes Apex and a test required for that deployment fails, Salesforce refuses that deployment.
Source: implied: U-7 under [Salesforce production Apex deployment test rules](https://developer.salesforce.com/docs/platform/api-metadata/guide/meta-deploy-running-tests.html)

### C-86: A future production Apex deployment must meet Salesforce’s coverage threshold.
Observable: If separately promoting Apex under `RunLocalTests` or `RunAllTestsInOrg`, Salesforce requires at least 75% aggregate Apex coverage. With `RunSpecifiedTests` or `RunRelevantTests` where available, it requires at least 75% for each deployed class and trigger.
Source: implied: U-7 under [Salesforce deployment coverage rules](https://developer.salesforce.com/docs/platform/api-metadata/guide/meta-rest-deploy.html)

### C-87: A future aggregate-coverage production deployment requires coverage of every Apex trigger.
Observable: For a separately authorized production Apex deployment using aggregate coverage, Salesforce refuses deployment if any Apex trigger has zero coverage even when the aggregate reaches 75%.
Source: implied: U-7 under [Salesforce trigger coverage rules](https://developer.salesforce.com/docs/platform/apex-dev/references/apex-dev/apex-testing-best-practices.html)

### C-88: A future public managed-package listing requires Salesforce security review approval.
Observable: If separately distributed as a managed package through Salesforce’s marketplace, the listing cannot go live until the package passes security review.
Source: implied: U-7 under [Salesforce marketplace security review](https://developer.salesforce.com/docs/platform/isvforce/guide/security-review-how-it-works.html)

### C-89: The rollout confines its Salesforce changes to the designated development org.
Observable: Inspect the environments involved after a rollout, upgrade, rollback or retry. Bot work makes no changes in any other Salesforce org, including a production org or a Dev Hub hosting a designated scratch org.
Source: choice: The request authorizes a development-org rollout only

### C-90: The bot preserves unrelated org configuration.
Observable: Compare existing navigation entries, metadata, permissions and external connections unrelated to the bot through installation, use, upgrade and rollback. Their definitions and assignments stay unchanged by bot work.
Source: choice: The addition is limited to Grok and its own access and connection

### C-91: Existing Salesforce workflows do not acquire a dependency on Grok.
Observable: Run an existing record operation, automation, integration or unrelated Lightning workflow while the bot is paused, unconfigured, or experiencing an xAI outage. It does not invoke Grok or require a Grok response.
Source: choice: No existing workflow was identified for integration

### C-92: An unrecognized existing Grok entry blocks installation over that entry.
Observable: If the target org already has a Grok entry that the administrator has not identified as this bot’s predecessor, setup reports the conflict before replacing or deleting the entry.
Source: choice: An installation must preserve unrelated or unverified existing work

### C-93: A bot upgrade preserves existing bot-use assignments.
Observable: Upgrade a recognized installed release. Once the replacement is enabled, prior bot-use grants and revocations still apply unless the operator explicitly changes them.
Source: choice: An upgrade must preserve the pilot’s access boundary

### C-94: A bot rollback preserves the current bot-use assignments.
Observable: Restore the preceding release after granting or revoking bot use. The then-current access decisions apply in the restored release.
Source: choice: Restoring a release must not undo more recent access decisions

### C-95: Removing the first rollout clears its dedicated Salesforce connection.
Observable: After first-install rollback, inspect the target org. The credential configured solely for this bot is no longer available for bot use. Credentials shared with unrelated features are outside first-install cleanup.
Source: choice: Removing the integration must not leave a usable bot credential or disable unrelated features

### C-96: Removing the first rollout clears its bot-specific access assignments.
Observable: After first-install rollback, existing users no longer have grants dedicated to this installation. Independent Salesforce grants and assignments remain effective.
Source: choice: Rollback removes this installation’s authority

### C-97: Chat activity does not expose the configured provider secret.
Observable: After credential provisioning, inspect the bot page, chat browser traffic, user feedback, operator diagnostics, app logs and deployment artifacts. None receives the configured key from the bot. Operator provisioning is the only browser interaction that can carry the key entered by the administrator.
Source: choice: An org credential must not be retrievable through the bot or its artifacts

### C-98: The bot does not automatically include Salesforce data in an inference request.
Observable: Open the bot after browsing a Salesforce record, then inspect the inference request for a prompt entered in the bot. The conversation content consists of the submitted text and the bounded prior user and assistant text. It does not include Salesforce record fields, IDs, page context, user identity, permission data or Salesforce session material drawn from the org. The user can still type or paste text manually.
Source: choice: The request supplies no authorization or business need for automatic CRM disclosure

### C-99: The bot does not retain chat content outside the current view for later retrieval.
Observable: After a view ends, there is no bot-provided way for a user or administrator to retrieve its draft, prompts, answers or pending outcomes. Bot-created Salesforce records, stored browser history for the app, and bot-generated diagnostic or analytics logs contain none of that chat content.
Source: choice: Session-local chat needs no archive or telemetry containing conversation text

### C-100: Raw errors are not disclosed to bot users.
Observable: Trigger a Salesforce or xAI error containing a credential, stack trace, request body or provider response body. User feedback and operator diagnostics show safe categories without exposing raw errors, headers, stack traces or payloads.
Source: choice: Diagnostic feedback needs no sensitive transport details

### C-101: A Salesforce identity change starts with a clean view.
Observable: Switch Salesforce account or org in the browser, including by signing out and back in as another user. Once the bot observes the identity change, the new account or org cannot see the old draft, transcript or pending result.
Source: choice: Browser reuse cannot transfer chat content between Salesforce identities

### C-102: A send cannot override access by modifying caller-supplied fields.
Observable: Invoke the send with altered values claiming another Salesforce user, org, model, credential or view. The request either fails or uses only the actual authorized org, user, view and administrator configuration, with no access to another view’s content.
Source: choice: Client-supplied assertions must not broaden authority

### C-103: A development deployment cannot rely on mock or canned answers for acceptance.
Observable: During rollout verification, the smoke answer must correspond to a successful inference request under the designated xAI connection. A local mock, cached answer or fixed bot reply alone does not satisfy readiness.
Source: implied: U-1 and U-2 ask for Grok itself

### C-104: The bot does not request a provider-side conversation archive.
Observable: Inspect provider requests. The bot declines any optional provider feature for storing the chat for later retrieval or continuation. Provider processing and retention remain subject to C-84.
Source: choice: View-local history needs no retrievable provider conversation archive

### C-105: Unassigned Salesforce users cannot open a bot conversation.
Observable: As a signed-in user without a bot-use grant, try to open Grok from both navigation and a saved direct link. No conversation is accessible. A direct link yields an access refusal or Salesforce’s unavailable response.
Source: choice: An access restriction must cover discovery and bookmarked entry

### C-106: The bot tells an assigned user when chat cannot accept a prompt.
Observable: Open the bot when unconfigured or paused. The view identifies the applicable state. If both apply, incomplete setup takes precedence in its explanation. A change after opening is reflected at the next attempted send.
Source: choice: A user needs an explanation even before attempting a prompt

### C-107: A configured model failure never selects another model.
Observable: Configure one Grok model, then cause xAI to reject inference for it. The turn fails and no attempt goes to a different model.
Source: choice: Model selection controls the expected capability and billing

### C-108: The bot provides the controls needed for one text conversation.
Observable: The required end-user controls in desktop Lightning are a text composer, send, and new conversation. Attachment, voice, saved-history, model-selection, and cancel controls are outside this pilot’s scope.
Source: choice: These three controls are enough for the requested interaction

### C-109: A fresh view advises users to use non-sensitive development text.
Observable: An assigned user sees that guidance before their first prompt is submitted from the view.
Source: choice: Once the user sends text, Salesforce cannot withdraw it from xAI

### C-110: The full credential cannot be read back in bot administration.
Observable: After provisioning, reopen the bot’s credential settings as administrator. You can tell whether the credential is present without viewing its value.
Source: choice: Operators need to verify provisioning without exposing the key

### C-111: A turn has at most one successful transcript entry.
Observable: Complete a turn, then deliver the same answer again. The transcript has one entry for that turn, containing its submitted prompt and one answer.
Source: choice: Repeated responses cannot create repeated conversation turns

### C-112: An expired send invocation cannot start new inference.
Observable: Replay an old send invocation after its 30-second turn deadline or after its view or release has been invalidated. It cannot cause a fresh inference request even if the bot is otherwise ready.
Source: choice: Replay protection must outlive the turn without requiring permanent conversation history

### C-113: The bot cannot first dispatch inference after the turn deadline.
Observable: Delay the bot’s initial dispatch until 30 seconds after submission or later. The bot does not start an inference attempt for that turn. A call dispatched earlier can still reach or finish at xAI after the deadline.
Source: choice: An expired queued action should not start new provider spend

### C-114: Reinstating access does not revive a turn invalidated by revocation.
Observable: Revoke bot use or end the Salesforce session while a turn awaits delivery, then grant access again or sign in again. The previously invalidated turn still cannot publish its answer.
Source: choice: Renewed access authorizes fresh sends only

### C-115: A known loss of access clears the affected view.
Observable: When the view learns its session or bot-use grant has ended, its draft, transcript and pending text are no longer offered through that view. Failure recovery that preserves the draft applies while the user still has access.
Source: choice: An already-open view must enforce the same ongoing access boundary as a new one

### C-116: The maximum conversation text submitted as context is 84,000 Unicode code points.
Observable: Submit a 4,000-code-point prompt with five prior turns of 4,000-code-point prompts and 12,000-code-point replies. The combined user and assistant text is 84,000 code points, before any provider message framing or fixed bot instructions. This passes the bot’s length rules and remains subject to the provider context window in C-82.
Source: choice: The largest context is the sum of the chosen prompt, reply, and history bounds

### C-117: Provider messages preserve the two conversation roles.
Observable: Inspect the request after a successful turn. Earlier user prompts remain user text and earlier Grok replies remain assistant text. The current user prompt is the last conversation message. A fixed bot instruction, if supplied, is independent of user-entered text and does not count as a turn.
Source: choice: Follow-ups depend on who said what

### C-118: The operator can tell which provider configuration a smoke outcome reflects.
Observable: Change the configured model or replace the credential after a smoke prompt succeeds. The previous result is identifiable as belonging to the earlier settings rather than evidence that the current settings work.
Source: choice: A stale smoke success must not certify a changed connection

### C-119: A no-op repeat of rollout does not create a second bot.
Observable: Repeat setup for the same recognized release in the same target org. Users still have one navigation entry for that bot.
Source: choice: Repeating a setup after an interruption must not duplicate the pilot

### C-120: Replacing a bot release preserves the currently selected Grok model.
Observable: Upgrade or restore a whole release without making a provider setup change. The selected model remains the same after replacement. If the replacement cannot use it, stay paused until the administrator chooses a supported selection.
Source: choice: A release change must not silently change the model or spend profile

### C-121: The administrator can verify the active release before reopening the bot.
Observable: After an upgrade or rollback, the administrator can distinguish which of the attempted replacement, preceding working release, or no installed release is present. An incomplete replacement is visibly incomplete and remains paused.
Source: choice: An operator recovering from an interrupted promotion needs to know what will resume

### C-122: The smoke path requires the same send authorization as ordinary chat.
Observable: An administrator with no bot-use grant, or whose org is paused, may inspect local setup but cannot use a smoke prompt to bypass the send gate. When the bot is ready, an administrator with bot-use access can exercise the ordinary send path for diagnosis.
Source: choice: A separate smoke bypass would leave the user path unverified

### C-123: The bot has no independent inference quota or spend cap.
Observable: Attempt another valid send after any number of earlier turns while the user is otherwise eligible. The bot imposes no per-user, per-day, or dollar budget beyond admission and content bounds in this spec. Salesforce limits and xAI team capacity still apply.
Source: choice: A single development pilot can use the provider account’s configured capacity

### C-124: Operator diagnosis is initiated by a smoke attempt.
Observable: During ordinary chat or inactivity, the bot does not poll the provider or send alerts. A diagnosis in the bot begins when an administrator attempts a smoke send.
Source: choice: No always-on monitoring is needed for the development rollout

### C-125: The org owner designates the target before installation begins.
Observable: The operator can obtain the development org’s Salesforce ID from its owner. With no verified designation or no administrator authorized for that org, installation does not begin.
Source: choice: No org or deployment authorization was supplied with the request

### C-126: The administrator can inspect the current bot-use grants.
Observable: Use the bot’s access-management path or Salesforce Setup to tell which active org users are currently assigned bot use, including the result after a grant or revocation.
Source: choice: The operator must be able to verify access changes without impersonating users

### C-127: The same prompt validation applies at the send entry.
Observable: Bypass the composer and attempt a send with missing text, non-text input, a blank string or 4,001 or more Unicode code points. Each is refused before xAI is called.
Source: choice: A direct invocation must not evade the same input constraints as the UI

### C-128: Local send refusals do not enter the conversation.
Observable: Submit a prompt that is blocked before admission due to access, stale view, an already-pending turn, incomplete setup, pause or invalid input. It creates no transcript entry and is not included as later context.
Source: choice: Only successful exchanges belong in the conversation

### C-129: Provider HTTP outcomes support the operator’s smoke classification.
Observable: When xAI supplies no more specific recognized reason, HTTP 401 or 403 is authentication or permission rejection, 404 is unknown model or inference route, 429 is throttling, 400, 405, 415 or 422 is invalid provider request, and 500–599 is upstream service error. A specifically identified account or billing block takes its own category. Other unrecognized errors use the generic provider category. [xAI status code reference](https://docs.x.ai/developers/debugging)
Source: choice: Use the provider’s documented distinctions with a fallback for cases the bot cannot diagnose reliably

### C-130: An interrupted credential update cannot leave a partially saved credential active.
Observable: Interrupt replacement before the credential change is confirmed saved. If the save did not commit, the previous credential stays active. If it committed before confirmation was lost, the complete replacement is active. No newly admitted send uses a partially provisioned local credential.
Source: choice: An administrator must be able to recover from an ambiguous setup outcome

### C-131: A smoke failure is not reported as a successful rollout.
Observable: Enable the configured bot and run the live smoke. If the prompt does not receive a complete answer, the rollout remains unverified until a later smoke succeeds. The administrator can pause the bot while investigating.
Source: choice: Dashboards and setup success cannot stand in for an end-to-end check

### C-132: An incomplete xAI generation cannot satisfy a send.
Observable: If the provider reports that generation reached an output ceiling before finishing, the turn fails without exposing a fragment as an answer. The xAI ceiling in tokens is unconfirmed for the selected model and inference mode.
Source: implied: U-5 under [xAI generation limits](https://docs.x.ai/developers/model-capabilities/text/best-practices)

### C-133: A synchronous Apex bot request can be refused under the long-running concurrency governor.
Observable: If Apex is used, Salesforce can terminate requests when the org’s concurrent synchronous request limit for execution lasting over 5 seconds is exhausted. Salesforce calculates the limit at one per 100 applicable licenses, with a floor of 10 and ceiling of 50. HTTP callout waiting is excluded. The designated org’s count is unconfirmed until its license allocation is known.
Source: implied: U-5 under [Salesforce Apex concurrency limits](https://developer.salesforce.com/docs/platform/apex-dev/references/apex-dev/apex-gov-limits.html) and [Lightning callout timing](https://developer.salesforce.com/docs/platform/lwc/guide/apex-continuations.html)

### C-134: An expired Developer Edition org can no longer host this bot.
Observable: If the designated target is Developer Edition, the bot becomes unavailable when the org is deleted for inactivity. Salesforce lists inactivity thresholds of 45 days for Developer Edition and 180 days for Developer Edition Legacy. The target’s deletion date is unconfirmed until its edition and Salesforce’s applicable expiration notice are known.
Source: implied: U-1 under [Salesforce Developer Edition expiration](https://help.salesforce.com/s/articleView?id=sf.admin_de_org_expiration.htm&language=en_US&type=5)

### C-135: Only one release replacement can be in progress in the target org.
Observable: Start an upgrade or rollback, then attempt another replacement before the first succeeds, fails, or is abandoned by the operator. The second cannot change the rollout while the first is in progress.
Source: choice: Competing release operations would make the active version and recovery target ambiguous

### C-136: A resume request cannot open admission during a release replacement.
Observable: Attempt to resume from a second administration session while an upgrade or rollback is in progress. New sends stay paused until a complete release is present and a subsequent resume succeeds.
Source: choice: Simultaneous maintenance and activation must preserve the maintenance boundary

### C-137: Concurrent edits to one operator setting have a single effective result.
Observable: Make overlapping changes to the same model selection, credential, pause state, or named user’s bot-use assignment. Inspect the setting after both finish. The last successfully applied change is effective, subject to the normal prerequisites. A failed change leaves the last successfully applied value in effect.
Source: choice: Ordinary Salesforce administration can resolve simultaneous edits without an additional collaboration workflow

### C-138: Changing one provider setting does not revert another.
Observable: Submit overlapping updates from different admin views that change different settings, such as the model in one and the credential in another. If both succeed, the next admitted send uses both updated values.
Source: choice: An operator changing the model should not restore an older key from a stale view

### C-139: The bot can be recovered in a replacement development org after the old org is gone.
Observable: If the original org expires or is deleted, the administrator can roll out the bot to a newly designated development org using a fresh setup and smoke check. Bot grants and keys must be provisioned there before verified use.
Source: choice: Recovery uses a new target when Salesforce cannot restore the old target
