## Use cases

### U-1: A Salesforce user asks Grok a first question to get a reply inside Salesforce
Flow: Sign in to the development org, find Grok from org navigation, open it, enter a text prompt, submit it, and see the outcome in the same interface.
Source: request

### U-2: A Salesforce user follows up to continue the conversation
Flow: After a successful reply, submit a follow-up, see it paired with its reply, and start afresh by reopening Grok.
Source: implied: a bot is used repeatedly and a follow-up can refer to a prior reply

### U-3: A Salesforce user checks the input boundary to submit a valid prompt
Flow: Try missing text, whitespace-only text, the longest supported prompt, and text one character longer. See field feedback for invalid input and submit a corrected prompt.
Source: implied: U-1 accepts user-entered text

### U-4: A Salesforce user encounters a failed request and tries again
Flow: Submit valid text while Grok is unavailable, see that the attempt failed, keep the submitted text available, and explicitly submit again after correcting the problem or after service recovers.
Source: implied: U-1 depends on an external service

### U-5: A Salesforce user or guest attempts access to learn whether Grok is available to them
Flow: Try opening or invoking the bot without a Salesforce sign-in or without access to the bot. See sign-in or an access denial and receive no reply.
Source: implied: the bot runs inside a Salesforce development org

### U-6: A Salesforce administrator prepares the bot so intended users can use it
Flow: Identify the target development org, make the bot available there, configure xAI access and a Grok model, grant bot access to an intended user, and verify a live reply as a granted user. If setup is incomplete, identify the missing prerequisite.
Source: implied: a working Grok bot requires both Salesforce and provider setup

### U-7: A Salesforce administrator stops and restores bot availability to recover operation
Flow: Disable bot use or revoke a user's grant, verify that covered users cannot send new prompts, then restore availability or the grant when appropriate. Replace unusable provider credentials or model configuration when that is the failure.
Source: implied: U-6 provisions access to an external service

### U-8: A Salesforce administrator diagnoses a failed request to choose a recovery action
Flow: Observe the failed attempt's category, distinguish setup, access, capacity and provider failures, correct the applicable prerequisite where possible, and verify recovery with a new prompt.
Source: implied: U-4 and U-6 require visible failure and a way to verify recovery

### U-9: A Salesforce administrator adds, updates or backs out the bot while preserving existing org operation
Flow: Start with an org that already has Salesforce data. Install or update the bot, then verify ordinary org use. After an update, restore the preceding revision if needed. To back out the first installation, remove the bot. If the change fails, check which revision is active before trying again.
Source: implied: the request places the bot in an org that can already be in use

## Clauses

### C-1: The bot operates in a Salesforce development org.
Observable: A user opens the installed bot while signed in to the target Salesforce development org.
Source: request

### C-2: A successful response comes from Grok.
Observable: A valid submission with working setup results in a live reply attributable to xAI Grok.
Source: request

### C-3: The user can read the reply inside Salesforce.
Observable: Submit a prompt from the bot and read the returned reply in that Salesforce experience.
Source: implied: U-1 and the request's placement of the bot in Salesforce

### C-4: The bot accepts text prompts.
Observable: Submit a plain-text question such as `What is a sandbox?` and see a response attempt begin.
Source: implied: U-1 needs an input a user can give to the bot

### C-5: The bot refuses an empty prompt.
Observable: Attempt to submit a zero-length prompt and see that text is required.
Source: implied: U-3 and a bot must be given something to answer

### C-6: The bot refuses a whitespace-only prompt.
Observable: Try submitting a prompt consisting entirely of spaces, tabs or line breaks and see that text is required.
Source: implied: U-3 and whitespace alone gives the bot nothing to answer

### C-7: The bot reports when it fails to obtain a reply.
Observable: Cause the provider to be unreachable and see a failure outcome in place of a successful reply.
Source: implied: U-4

### C-8: The bot requires Salesforce sign-in.
Observable: Visit its entry point without a signed-in Salesforce session and see Salesforce request sign-in or deny access.
Source: implied: U-5 and the org is the access boundary

### C-9: An administrator can grant bot use to an eligible internal Salesforce user.
Observable: Grant bot use to an internal user in the target org and verify that the user can submit when the bot is ready and their Salesforce session is active.
Source: choice: the dev-org bot is for designated internal users

### C-10: An administrator can stop bot use org-wide.
Observable: Disable Grok in the target org and see that a previously authorized user cannot start a new request.
Source: choice: U-7 can stop development usage without removing the deployment

### C-11: An administrator can restore bot use org-wide.
Observable: Re-enable the ready bot and see a granted user start a new request.
Source: choice: U-7 can reverse a stop without repeating setup

### C-12: A failed attempt provides a diagnosis usable for recovery.
Observable: An administrator can distinguish insufficient Salesforce access, incomplete or invalid provider setup, service capacity, and temporary service failure from the outcomes available for a failed attempt.
Source: implied: U-8

### C-13: An administrator can restore the immediately preceding bot revision.
Observable: After a successful update, restore the bot revision that was active immediately before that update.
Source: implied: U-9

### C-14: Installing the bot preserves existing Salesforce business records.
Observable: Compare existing record counts, values and relationships before and after installing the bot with no other org changes.
Source: implied: U-9 and the request adds a bot

### C-15: The bot is discoverable from the target org's signed-in navigation.
Observable: A granted user can find a navigation entry identifiable as Grok without already knowing its address.
Source: implied: U-1 starts from within Salesforce

### C-16: The installation targets one administrator-designated development org at a time.
Observable: With two development orgs available, select one and verify that the installation changes only the selected org.
Source: choice: the request names a single development org and gives no org identifier

### C-17: Salesforce Developer Edition is a supported development target.
Observable: An administrator can enable a working bot in a Salesforce Developer Edition org.
Source: choice: the request names a development org without specifying its edition

### C-18: Production orgs are outside the deployment scope.
Observable: During installation, update and rollback for this request, Salesforce production orgs receive zero bot deployments.
Source: implied: the request specifies a development org

### C-19: An eligible user must have a bot-use grant.
Observable: A signed-in target-org user without the grant tries both navigation and a direct invocation and can start zero Grok requests.
Source: choice: an explicit grant lets the administrator control use of an external, metered service

### C-20: An administrator can revoke one user's bot-use grant.
Observable: Remove a user's grant and verify that their next submission is refused while another granted user's access still works.
Source: choice: the explicit individual grant is reversible independently of the org-wide stop

### C-21: The administrator can configure the xAI credential for this org.
Observable: From the authorized setup path, supply or replace the org's xAI inference credential and use it to obtain a live reply.
Source: implied: U-6 and U-7 depend on authenticated access to Grok

### C-22: The administrator can select the Grok model for this org.
Observable: Select an available xAI Grok text-generation model and confirm that a new request uses that selection. The exact model ID depends on the target xAI team's current access and is unconfirmed.
Source: choice: the available models vary by provider account and the request names no version

### C-23: A bot-use grant alone confers no control over org-wide bot settings.
Observable: Using a granted nonadministrator account, try to change the enabled state, user grants, xAI credential or selected model. Each change is refused.
Source: implied: U-6 and U-7 assign provisioning to the administrator

### C-24: A fresh bot installation starts disabled.
Observable: After first installation and before explicit enablement, a granted user cannot start a request.
Source: choice: the administrator must control when submissions start leaving the dev org

### C-25: The administrator can tell whether the bot is configured locally.
Observable: As the administrator, distinguish these local readiness blockers when present: bot disabled, credential missing and model missing. Completing local setup alone gives no live verification outcome.
Source: choice: U-6 needs setup feedback without requiring a provider probe for each view or edit

### C-26: A prompt may contain up to 4,000 Unicode code points.
Observable: A prompt with 4,000 code points passes length validation when otherwise valid. A prompt with 4,001 is refused with the 4,000 limit indicated. A supplementary-plane character counts as one code point.
Source: choice: a single predictable bound supports normal questions while keeping conversation payloads small

### C-27: Blank-input validation uses the Unicode White_Space property.
Observable: Input consisting only of characters in Unicode White_Space is refused, including input containing only U+00A0. The members are U+0009–U+000D, U+0020, U+0085, U+00A0, U+1680, U+2000–U+200A, U+2028, U+2029, U+202F, U+205F and U+3000.
Source: choice: blank text should be treated consistently beyond ASCII spaces, tabs and line breaks, using the [Unicode White_Space definition](https://www.unicode.org/faq/unsup_char.html)

### C-28: The length check counts the submitted text before trimming.
Observable: A leading space followed by 4,000 non-whitespace code points fails length validation.
Source: choice: the character bound is predictable from the complete submitted input

### C-29: Valid text is passed through without changing its content.
Observable: A provider-bound submission of valid text preserves its characters, including leading and trailing whitespace and line breaks present in the submitted value.
Source: implied: U-1 asks Grok the user's question

### C-30: Invalid input consumes zero provider requests.
Observable: Compare outbound activity when trying missing, empty, whitespace-only and over-limit text. Each yields zero xAI inference requests.
Source: implied: U-3 refuses invalid submissions

### C-31: A reply is associated with the prompt that produced it.
Observable: Submit two different prompts in sequence and identify which displayed reply belongs to each one.
Source: implied: U-2 requires the user to distinguish successive exchanges

### C-32: Follow-ups use recent successful exchanges from the current bot view.
Observable: On a follow-up, the provider receives the current prompt plus all complete prompt-reply pairs still visible in that view up to the four most recent, in chronological order with the current prompt last. With no complete pairs only the current prompt is sent. With three, all three are included. With five, the oldest pair is omitted. Pending, failed and partial exchanges are excluded.
Source: choice: bounded context supports follow-ups within a visit without requiring history storage

### C-33: The bot view begins with an empty conversation.
Observable: Open Grok as a fresh view, including by fully reloading it, and see zero prior messages and a blank input.
Source: choice: a visit is the conversation boundary, with no saved conversation library

### C-34: The bot supports text as its only user message input.
Observable: Use the bot with text. There is no submission action for file, image, audio or video attachments.
Source: choice: text is sufficient for the requested development bot

### C-35: An attempt in progress is visible.
Observable: Hold a reply open at the provider and see a pending state associated with the submitted prompt.
Source: implied: U-1 and U-4 involve waiting for an external response

### C-36: The bot tells the user when prompt text leaves Salesforce.
Observable: Before a first submission, the user can see that submitted text and any conversation context included with it are sent to xAI.
Source: choice: dev-org users can decide what to enter before making the external call

### C-37: A bot view admits at most one pending attempt.
Observable: While one prompt is pending in a view, try to submit a second prompt or activate Send twice. The view admits only the first attempt.
Source: choice: serial submissions keep the context and reply order clear within each view

### C-38: A pending attempt keeps its submitted prompt visible.
Observable: While waiting, see the exact text that was submitted for the pending attempt.
Source: implied: U-1 shows what is awaiting a reply

### C-39: The prompt input is read-only while its attempt is pending.
Observable: Try to edit the input while a response is pending. The edit does not change the submitted input.
Source: choice: one input field suffices for both submitting and recovering the prompt

### C-40: A complete reply clears the prompt input.
Observable: After the reply appears, the input is blank and ready for another message.
Source: choice: a successful submission leaves the input ready for U-2

### C-41: A failed or partial attempt leaves the submitted text editable.
Observable: After a timeout, failure or marked partial reply in a still-authorized view, recover the exact submitted text in the input and edit it.
Source: choice: U-4 can repeat or revise the attempt without retyping

### C-42: The bot sends no automatic repeat for an admitted attempt.
Observable: Cause a timeout, dropped connection, throttling or provider error. Observe at most one inference request initiated by the bot for that admitted attempt, including after reconnection.
Source: choice: an unknown provider outcome can already have consumed quota

### C-43: An explicit resubmission after a terminal attempt can start a new attempt.
Observable: When access is available, submit the same text after a success, partial reply or failure. A valid resubmission starts a new request.
Source: implied: U-2 and U-4 allow intentional repeated use

### C-44: An admitted attempt produces at most one visible terminal outcome.
Observable: Deliver a duplicate outcome or deliver a reply after that attempt has timed out. The prior terminal result stays as shown and no second result appears.
Source: choice: late and duplicate outcomes must not change what the user can safely retry

### C-45: Independent bot views have independent conversation context.
Observable: Open two views as the same user or as different users. Submissions from both can proceed independently when capacity is available, with neither receiving the other's prompts, context or replies.
Source: choice: a visit is the conversation boundary

### C-46: Closing or leaving the bot view ends that conversation.
Observable: Navigate away, close the tab, or reload the view while a reply is pending. A later opening starts empty and shows none of the departed conversation's replies.
Source: choice: the bot provides no background conversation or reattachment to an earlier view

### C-47: The bot checks current access before accepting a prompt.
Observable: Keep a view open after sign-out or session expiry, removal of the user's grant, or org-wide disablement. A new send after that change is refused.
Source: implied: U-5 and U-7 apply to already-open views

### C-48: Org-wide disablement alone does not suppress results from already accepted requests.
Observable: Disable the bot after an authorized request has started. A user whose session, grant and view remain current sees that attempt's result.
Source: choice: the stop governs admission and lets existing provider work settle

### C-49: The bot withholds an in-flight reply after the user's Salesforce authorization ends.
Observable: Let an attempt start, then expire the Salesforce session or revoke the user's bot grant before delivery. The original view receives no reply content from that attempt.
Source: choice: delivery should respect the Salesforce user's current authorization

### C-50: Corrected provider configuration applies to the next accepted attempt.
Observable: Change the credential or selected model, then submit again. The next accepted attempt uses the new value.
Source: implied: U-7 recovers by fixing provider setup

### C-51: Configuration edits do not reroute an attempt that has already been sent.
Observable: Change the model or credential after a provider request has left. That attempt settles with its own result or failure and causes zero sends under the replacement settings.
Source: choice: one attempt has one provider outcome even during a rotation

### C-52: Failure to finish installing, updating or rolling back leaves the previously active revision in service.
Observable: Cause a deployment change to fail before it becomes active. The admin can still identify and use the previously active revision if there was one, or see the bot remain absent on failed first install.
Source: choice: an incomplete lifecycle change must have a defined active state

### C-53: The active bot revision is identifiable by the administrator.
Observable: After a successful install, update, rollback or failed change, the administrator can tell which revision is active or that the bot is absent.
Source: implied: U-9 requires verification of the lifecycle outcome

### C-54: Grok inference requires valid xAI API authentication.
Observable: A request sent to xAI carries its required bearer authentication. A missing or invalid key cannot produce a live reply.
Source: implied: U-6 is bound by the [xAI inference authentication rule](https://docs.x.ai/developers/rest-api-reference/inference)

### C-55: Salesforce must permit the outbound connection before a prompt can reach Grok.
Observable: Remove the applicable Salesforce outbound authorization and observe that the provider does not receive the prompt.
Source: implied: U-6 is bound by [Salesforce's callout endpoint authorization rules](https://developer.salesforce.com/docs/platform/apex-dev/references/apex-dev/apex-callouts-named-credentials.html)

### C-56: A callable Apex entry point requires Salesforce class access whenever the bot uses one.
Observable: Remove Salesforce access to the bot's top-level Apex entry point and attempt to invoke it directly. Salesforce refuses the invocation.
Source: implied: U-5 is bound by [Salesforce Apex class security](https://developer.salesforce.com/docs/platform/apex-dev/references/apex-dev/apex-classes-security.html)

### C-57: When Salesforce external credential principal access applies, a user lacking it cannot use that principal for Grok.
Observable: Remove principal access from a bot user whose callout requires it. The prompt does not reach xAI under that principal and the user sees a setup or access failure.
Source: implied: U-6 is bound by [Salesforce external credential principal authorization](https://developer.salesforce.com/docs/platform/api-metadata/references/meta-types/metadata-permissionset.html)

### C-58: A packaged Salesforce external credential requires target-org secret provisioning.
Observable: If the bot is deployed with a packaged external credential, install it into a fresh org. It can authenticate to xAI only after an administrator provisions the target-org secret.
Source: implied: U-6 is bound by [Salesforce's rule excluding credential tokens and certificates from packages](https://developer.salesforce.com/docs/platform/named-credentials/guide/nc-package-credentials.html)

### C-59: Apex callout concurrency in Developer Edition cannot exceed 20 simultaneous callouts to destinations outside the org domain.
Observable: With all 20 applicable callout slots occupied, an additional bot callout cannot proceed at the same time. A Salesforce refusal surfaces as unavailable capacity.
Source: implied: U-4 is bound by [Salesforce Developer Edition Apex callout concurrency](https://developer.salesforce.com/docs/platform/apex-dev/references/apex-dev/apex-callouts-timeouts.html)

### C-60: Any Apex transaction used for bot callouts is subject to the 100-callout transaction ceiling.
Observable: With the applicable Apex callout allowance exhausted by 100 prior callouts, a further callout in that transaction cannot produce a reply. The bot attempt terminates as a Salesforce failure if the runtime rejects it.
Source: implied: U-4 is bound by [Salesforce Apex callout count limits](https://developer.salesforce.com/docs/platform/apex-dev/references/apex-dev/apex-callouts-timeouts.html)

### C-61: An individual Apex callout cannot wait beyond the Salesforce callout timer.
Observable: For an Apex callout made without a custom timer, a provider that stays silent reaches the 10-second callout timeout. A configured timer is within 1 to 120,000 milliseconds inclusive.
Source: implied: U-4 is bound by [Salesforce per-callout timeout rules](https://developer.salesforce.com/docs/platform/apex-dev/references/apex-dev/apex-callouts-timeouts.html)

### C-62: Apex callouts cannot use more than 120 seconds of cumulative timeout per transaction.
Observable: In an Apex bot transaction that also encounters other callouts, a callout that would exceed the remaining cumulative allowance cannot keep waiting beyond that allowance.
Source: implied: U-4 is bound by [Salesforce's cumulative Apex callout timeout](https://developer.salesforce.com/docs/platform/apex-dev/references/apex-dev/apex-callouts-timeouts.html)

### C-63: An Apex callout message cannot exceed Salesforce's size allowance.
Observable: If an Apex request or response exceeds 6 MB in synchronous Apex or 12 MB in asynchronous Apex, the attempt cannot succeed through that callout and surfaces as a Salesforce failure.
Source: implied: U-4 is bound by [Salesforce Apex callout message size limits](https://developer.salesforce.com/docs/platform/apex-dev/references/apex-dev/apex-gov-limits.html)

### C-64: The bot cannot dispatch an Apex callout from a transaction with prohibited pending operations.
Observable: If the transaction still holds pending record writes, asynchronous Apex work, scheduled Apex work or email, the provider receives no callout from that transaction.
Source: implied: U-4 is bound by [Salesforce's Apex uncommitted-work restriction](https://developer.salesforce.com/docs/platform/apex-dev/references/apex-dev/apex-callouts-timeouts.html)

### C-65: If Apex exhausts its transaction CPU budget while serving the bot, the attempt fails.
Observable: Force Apex processing past 10,000 milliseconds of synchronous CPU or 60,000 milliseconds of asynchronous CPU. The attempt yields a Salesforce failure. Time spent waiting on the external callout does not consume this CPU allowance.
Source: implied: U-4 is bound by [Salesforce Apex CPU governors](https://developer.salesforce.com/docs/platform/apex-dev/references/apex-dev/apex-gov-limits.html)

### C-66: If Apex exhausts its transaction heap budget while serving the bot, the attempt fails.
Observable: Exceed the applicable Apex heap allowance during the bot operation and see a Salesforce failure. The current published allowances are 10 MB synchronous and 25 MB asynchronous, including callout messages.
Source: implied: U-4 is bound by [Salesforce Apex heap governors](https://developer.salesforce.com/docs/platform/apex-dev/references/apex-dev/apex-gov-limits.html)

### C-67: The chosen model's xAI context limit constrains each request.
Observable: When the provider rejects the request for exceeding the selected model's context window, the user sees a size-related failure with the option to shorten the prompt or open a fresh view. The exact token limit is unconfirmed until the model is selected.
Source: implied: U-2 and U-3 are bound by the [xAI per-model context window](https://docs.x.ai/developers/rest-api-reference/inference/models)

### C-68: xAI throttling ends the affected attempt as a capacity failure.
Observable: An xAI HTTP 429 results in a capacity failure the user can explicitly retry later. The applicable requests-per-second and tokens-per-minute figures are unconfirmed until the model and xAI team are known.
Source: implied: U-4 is bound by [xAI per-team and per-model rate limits](https://docs.x.ai/developers/rate-limits)

### C-69: A provider-account spending restriction can prevent an inference reply.
Observable: If xAI explicitly refuses an inference because available credit or a spending allowance is exhausted, the administrator can identify an account capacity problem. The actual balance or spending limit is unconfirmed and belongs to the configured xAI team.
Source: implied: U-6 depends on provider account capacity under the [xAI billing rules](https://docs.x.ai/console/billing)

### C-70: A future production deployment containing Apex requires passing Salesforce validation tests.
Observable: On a future authorized production deployment containing Apex, a failure in any test required for that deployment prevents release.
Source: implied: a release beyond U-9's development scope would be bound by [Salesforce production Apex deployment validation](https://developer.salesforce.com/docs/platform/api-metadata/references/file-based-calls/meta-deploy.html)

### C-71: A future production Apex deployment using all local or all org tests requires at least 75% overall Apex coverage.
Observable: In that production validation mode, Salesforce refuses deployment with overall coverage below 75%.
Source: implied: a release beyond U-9's development scope would be bound by [Salesforce overall production Apex coverage](https://developer.salesforce.com/docs/platform/api-metadata/references/file-based-calls/meta-deployrecentvalidation.html)

### C-72: A future production Apex deployment using all local or all org tests requires some coverage for each trigger.
Observable: In that production validation mode, Salesforce refuses deployment with a trigger at 0% coverage.
Source: implied: a release beyond U-9's development scope would be bound by [Salesforce production trigger coverage](https://developer.salesforce.com/docs/platform/api-metadata/references/file-based-calls/meta-deployrecentvalidation.html)

### C-73: A future production Apex deployment using specified tests requires at least 75% coverage per deployed Apex class or trigger.
Observable: Under `RunSpecifiedTests`, Salesforce refuses release when a deployed class or trigger has less than 75% coverage from those tests.
Source: implied: a release beyond U-9's development scope would be bound by [Salesforce specified-test coverage](https://developer.salesforce.com/docs/platform/api-metadata/guide/meta-deploy-run-specific-tests.html)

### C-74: Bot instructions describe the provider's separate audit retention accurately.
Observable: The information available with the first-use disclosure states that xAI documents a default audit retention of 30 days for API inputs and outputs, subject to the xAI team's retention terms. The target team's actual retention is unconfirmed.
Source: implied: U-1 sends text to xAI under the provider's [API security and audit-retention rules](https://docs.x.ai/developers/faq/security)

### C-75: Bot lifecycle changes preserve existing Salesforce business records.
Observable: Compare preexisting record counts, values and relationships before and after updating, rolling back or removing the bot with no other org changes.
Source: implied: U-9 changes the bot independently of existing data

### C-76: Bot lifecycle changes preserve existing Salesforce business-record access.
Observable: For the same existing users, compare object access, field access and record sharing before and after install, update, rollback or removal. Bot grants confer zero changes to that access.
Source: implied: U-9 adds a bot alongside existing users and access rules

### C-77: Bot lifecycle changes preserve existing Salesforce sign-in policy.
Observable: Existing sign-in requirements, including whatever session, MFA and login restrictions the target org already enforces, apply identically after bot installation, update, rollback and removal.
Source: implied: U-5 and U-9 use the target org's existing identity boundary

### C-78: Bot lifecycle changes preserve unrelated Salesforce automation.
Observable: Existing flows, triggers, validation rules and scheduled jobs outside the bot have the same configuration and results for the same inputs before and after bot installation, update, rollback and removal.
Source: implied: U-9 leaves ordinary org operation in place

### C-79: Bot lifecycle changes preserve unrelated Salesforce navigation.
Observable: The target org's preexisting app, tab and page entries remain accessible to the same users after bot installation, update, rollback and removal.
Source: implied: U-9 adds a discoverable bot alongside existing navigation

### C-80: Bot lifecycle changes preserve unrelated Salesforce integrations.
Observable: Existing outbound destinations, authorization and behavior for unrelated integrations remain the same after bot installation, update, rollback and removal.
Source: implied: U-9 changes only the bot's integration

### C-81: A bot conversation does not modify Salesforce business records.
Observable: Submit prompts requesting record creation, updates, deletion or restoration. Record counts, values and relationships remain the same after each attempt.
Source: implied: the request asks for a Grok bot and specifies no Salesforce record actions

### C-82: The bot attaches zero Salesforce business records to the Grok request.
Observable: From orgs with different business records, submit the same message in fresh views with the same model. The bot supplies no automatically fetched Salesforce object data, field values or relationships to xAI.
Source: implied: the request supplies no record lookup or Salesforce-data grounding capability

### C-83: The bot attaches zero Salesforce user identity or session data to the Grok request.
Observable: In provider-bound data for the same prompt submitted by different users, there is no Salesforce user ID, username, email, org ID or session credential automatically supplied by the bot.
Source: choice: inference requires conversational text and provider authentication, so Salesforce identity stays inside Salesforce

### C-84: The xAI secret remains within authorized server-side credential handling.
Observable: After provisioning a known key, ordinary bot interaction, org settings readback, deployed bot artifacts, browser traffic, diagnostics and logs expose no copy of that key. The authorized write operation and server-to-provider authentication are the paths that handle the supplied value.
Source: implied: U-6 requires a credential whose disclosure would bypass the controlled bot access in U-5

### C-85: The bot sends conversational text only to xAI's official HTTPS inference service.
Observable: Replace the provider response with a redirect to a different origin or put a different address in prompt text. Neither causes the bot to send the conversation to that address.
Source: implied: C-2 identifies xAI Grok as the provider

### C-86: The bot displays reply text as inert content.
Observable: Return text containing HTML, a script, executable links or a form. Viewing it cannot run provider-supplied code, open a new destination automatically or submit a form.
Source: implied: U-1 asks to read the reply within a Salesforce session

### C-87: Grok output cannot invoke tools on behalf of the user.
Observable: A provider response requesting execution of a tool, including a Salesforce action, search, file access or a request to another service, produces zero bot-executed tool actions.
Source: choice: the development bot answers with text and needs no external or Salesforce actions

### C-88: The bot keeps no durable conversation history of its own.
Observable: After a view closes, later use and administrator inspection recover no bot-stored transcript, prompt draft or prior response from Salesforce, browser persistence, logs or analytics.
Source: choice: current-view context serves follow-ups without lasting conversation records

### C-89: The bot does not ask xAI to save a retrievable conversation.
Observable: Outbound interaction does not request provider-managed conversation storage or refer to a saved prior response identifier.
Source: choice: all conversation context comes from the current view, with provider audit retention governed separately

### C-90: Bot diagnostics expose no raw provider response.
Observable: Cause a provider error containing internal details, prompt text or credential material. User and administrator diagnosis omits the raw response, raw headers and stack trace.
Source: choice: recovery needs a cause category without copying provider payloads into Salesforce diagnostics

### C-91: No provider request starts without an explicit user submission.
Observable: Installation, opening a view, editing text, changing setup, enabling, signing in, automatic reconnect and scheduled org activity each initiate zero inference requests by themselves.
Source: choice: metered provider activity follows a deliberate action by a granted user

### C-92: Every available bot invocation route enforces the same admission checks.
Observable: Try direct invocation using the same session, grant, enabled state and invalid payload that were refused in the interface. No refusal can be bypassed by skipping the visible interface.
Source: implied: U-3, U-5 and U-7 define whether the bot can accept a submission

### C-93: The interactive attempt has a 60-second deadline.
Observable: Starting from a valid Send that enters pending, allow 60 seconds to elapse without a terminal outcome. A still-open view reports timeout at the deadline while responsive, or when it next becomes responsive. A reply received at or after that deadline does not replace the timeout.
Source: choice: external requests need a predictable end even when no response comes back to Salesforce or the browser

### C-94: The bot shows at most 20 terminal attempts in one view.
Observable: On the 21st terminal attempt, the oldest of the prior 20 entries drops out. The retained entries are ordered by submission. Complete replies, partial replies and failed admitted attempts each count as one entry. A separately pending attempt and input validation feedback occupy no terminal entry.
Source: choice: a short development conversation stays bounded even across failures and repeated prompts

### C-95: A displayed reply contains at most 16,000 Unicode code points of Grok text.
Observable: A complete valid reply of 16,000 code points is shown in full. At 16,001 code points, only the first 16,000 are shown as reply text and the attempt is marked partial.
Source: choice: a bounded text answer keeps the interface and follow-up payload manageable

### C-96: Nonblank text from a provider-declared length truncation is marked partial.
Observable: Return a reply xAI explicitly marks incomplete for its length limit. Inspect the available text with an indication that it is incomplete.
Source: implied: U-1 must distinguish incomplete Grok output from a completed reply under [xAI's output limits](https://docs.x.ai/developers/model-capabilities/text/best-practices)

### C-97: An unusable provider reply produces a reply failure.
Observable: Return malformed data, missing text, empty text, whitespace-only text, only a tool request, or an unsupported incomplete result. Each unusable terminal response yields an invalid-reply failure.
Source: implied: U-1 and U-4 need a visible result when the provider supplies no displayable answer

### C-98: A readable final text refusal from Grok is a reply.
Observable: When Grok returns a final text message declining the question, the user reads the message as Grok's answer.
Source: implied: U-1 shows what Grok actually answered

### C-99: A locally unavailable bot explains why a submission cannot start.
Observable: With an otherwise eligible signed-in user, try to send while disabled, missing local provider setup or blocked by Salesforce callout authorization. The result distinguishes disabled, setup needed and Salesforce access or outbound failure.
Source: choice: the visible category tells the user whether to try again or contact their administrator

### C-100: An explicit xAI credential rejection is identified as a provider setup failure.
Observable: An xAI HTTP 401, HTTP 403 or another provider error explicitly identifying an invalid key or insufficient provider permissions is distinguished from a Salesforce sign-in or grant failure.
Source: implied: U-8 is bound by [xAI authentication and authorization error meanings](https://docs.x.ai/developers/debugging)

### C-101: An unavailable or unsupported selected Grok model is identified as a provider model setup failure.
Observable: Select a model that gets retired, becomes inaccessible or does not support text input and output. When that reason is known, the administrator can identify the model setup problem and correct it.
Source: implied: U-7 and U-8 depend on xAI's [current model availability](https://docs.x.ai/developers/rest-api-reference/inference/models)

### C-102: Transient connection and provider service errors are shown as temporary failures.
Observable: Cause DNS or TLS failure, a dropped connection between the bot and xAI, or an xAI HTTP 5xx. In the absence of a more specific known cause, see a temporary connectivity or service failure.
Source: implied: U-4 and U-8 cover a provider dependency that can fail

### C-103: An unclassified provider rejection is shown as a provider request failure.
Observable: Return a non-successful provider response with no cause matching another specified failure, such as an unclassified HTTP 400, 404, 405, 415 or 422, or a redirect. The attempt ends with a provider request failure the user can report.
Source: choice: U-8 needs an actionable fallback without guessing that an unclassified rejection is a credential, prompt or model fault

### C-104: A value that cannot represent Unicode text is refused at the submission boundary.
Observable: Invoke the available submission route with an absent or null prompt, non-text values such as a number, Boolean, object or array, or a string containing an unpaired surrogate. The submission gets input feedback and starts no xAI inference.
Source: implied: U-3 and C-4 accept only valid text regardless of invocation route

### C-105: The bot reports a text-required error before a length error when both apply.
Observable: Submit 4,001 spaces. The feedback identifies the need for non-whitespace text.
Source: choice: the user has to enter substantive text regardless of the length

### C-106: A refused submission keeps the user's draft in the current authorized view.
Observable: Try submitting 4,001 code points or sending while the bot is disabled. The text remains available to edit once the refusal is shown.
Source: choice: correcting input or setup should not force the user to retype

### C-107: A valid onboarding verification reaches the live provider.
Observable: After setup, a granted user submits a normal text question and observes a completed Grok reply. An installation success indicator, locally ready state or sample response cannot serve as that verification.
Source: implied: U-6 verifies that the configured bot can actually reach Grok

### C-108: Recovery instructions cover the available actions for each failure category.
Observable: A user or administrator can identify the applicable action: sign in again for a missing session, ask the org administrator for missing access or disabled state, correct input for validation, shorten input or reopen for context size, repair the configured credential or model for provider setup, correct Salesforce outbound access for Salesforce authorization, wait for capacity after throttling or platform saturation, check the xAI account for a billing restriction, try again after timeout, lost connection or temporary failure, or report a repeated reply, request or Salesforce runtime failure.
Source: choice: support a development deployment without a separate support console or new durable diagnostics

### C-109: An administrator can remove the bot after its first installation.
Observable: Back out a first installation. Bot navigation and submission become unavailable, with no earlier bot revision to restore.
Source: implied: U-9 defines a backout even when there is no preceding bot revision

### C-110: Returning to an earlier bot revision preserves the current access policy for the bot.
Observable: Revoke a user grant or disable the bot, then restore the immediately preceding revision. The restored revision still honors the revocation or disabled state.
Source: choice: rolling back bot behavior does not undo the administrator's subsequent access decisions

### C-111: Returning to an earlier bot revision preserves the current provider setup for the bot.
Observable: Rotate the key or change the model, then restore an earlier bot revision. The restored revision uses the currently configured values. If that setup is incompatible, the administrator sees a setup failure.
Source: choice: restoring the bot revision must not restore an old secret or silently change the configured provider model

### C-112: Removal ends the bot's use of its Salesforce-side settings.
Observable: Remove the bot and perform a fresh installation. The new installation starts with no prior bot-use grants, xAI credential or model. Unrelated Salesforce settings and the external xAI account remain independent.
Source: choice: removal restores the prior absence of this bot

### C-113: An obsolete bot view cannot continue after its revision is replaced or removed.
Observable: Leave a view open while its revision is replaced by an update, restored revision or removal. Further sends through that view are refused with an indication to reopen if the bot is still installed.
Source: choice: revisiting the bot gives the user the active revision and avoids ambiguous cross-version behavior

### C-114: Revoking the user's Salesforce authorization ends access to the conversation in the bot view.
Observable: On the first bot interaction or pending delivery that detects loss of the session or grant, the view ceases to show the conversation and draft. Reopening after access is restored starts empty.
Source: choice: the conversation belongs to one authorized visit, including when a different user next signs in on the same browser

### C-115: The bot displays no Grok reply text until an attempt becomes terminal.
Observable: With a held provider response, the pending prompt and any earlier entries remain visible, with no new Grok text displayed before the attempt becomes terminal.
Source: choice: each attempt yields one readable result without requiring streamed output or adding a background workflow

### C-116: Loss of the browser connection has a visible outcome in a view that stays open.
Observable: Disconnect the browser after Send. A reported client-to-Salesforce connection failure shows a recoverable connection failure. When the connection yields no outcome, the still-open view reaches the 60-second timeout under C-93.
Source: implied: U-4 also covers loss of communication between the browser and Salesforce

### C-117: Admission refusals appear as feedback without creating conversation entries.
Observable: Submit invalid text, use a stale revision, or attempt to send with missing session, missing grant, disabled bot or missing local setup. The attempt is refused before inference and adds no terminal conversation entry.
Source: choice: the transcript tracks admitted prompt attempts, with admission refusals shown separately from provider outcomes

### C-118: Authorization failure takes precedence over input feedback.
Observable: Submit empty or malformed text after the session or bot grant has observably ended. The bot responds with sign-in or access denial feedback as appropriate.
Source: choice: a caller must have access before the bot behaves as an available input validator

### C-119: There is no separate public bot channel.
Observable: The only supplied end-user entry is the signed-in Salesforce experience. No guest page, external messaging channel or supported public integration API is supplied.
Source: implied: the request places the bot in a Salesforce development org and names no other channel

### C-120: The bot has no automatic fallback model.
Observable: Make the selected Grok model unavailable and observe that the attempt does not obtain a reply from a different model.
Source: choice: the administrator chooses the model that consumes the team's quota

### C-121: An in-flight attempt from an obsolete bot view cannot append a reply to that view.
Observable: Hold a response, replace or remove the view's revision, then release the response. The old view does not display that reply.
Source: choice: replacing or removing the revision ends the view's ability to receive replies

### C-122: Bot output has a single visible terminal classification per admitted attempt.
Observable: An admitted attempt resolves to exactly one of complete reply, partial reply or failure while its view is open, responsive, on the active revision and still authorized by Salesforce session and bot grant. A failure has one primary cause category. Closing the view, a revision change or loss of authorization can end the visit without displaying a terminal classification.
Source: choice: an attempt has a clear completion state even when several failure symptoms occur

### C-123: Follow-up context is taken from the retained conversation when the new submission starts.
Observable: In a view already showing 20 terminal entries, send a follow-up. Its context is drawn from the entries shown at Send, before the new attempt's eventual terminal entry can evict any of them.
Source: choice: the reply should use the conversation visible when the user asked

### C-124: Submitted conversational content distinguishes the user from Grok.
Observable: In the text supplied to Grok on a follow-up, prior prompts and the current prompt are identified as user contributions and prior replies are identified as Grok contributions.
Source: implied: U-2 depends on Grok distinguishing its previous answers from the user's questions

### C-125: No fixed bot-specific request quota is added beyond the pending-attempt limit per view.
Observable: Continue submitting sequential valid prompts in the same view or from multiple authorized views while Salesforce and xAI have capacity. No additional bot quota stops use after a count per user, view or day.
Source: choice: the development bot uses the platform and provider capacity limits instead of adding its own quota system

### C-126: The administrator can inspect the bot's active nonsecret settings.
Observable: In the target org, an authorized administrator can see the enabled or disabled state, which users hold bot-use grants, whether a key is configured and the selected model or its absence.
Source: implied: U-6 through U-8 require the administrator to distinguish current configuration from the intended one

### C-127: A rejected administrative change leaves the existing value effective.
Observable: Attempt a settings write that Salesforce or the bot rejects. The previous enabled state, grant, key or model affected by that write remains in effect.
Source: choice: a failed change must not silently break existing bot access or provider setup

### C-128: Concurrent local admission blockers produce feedback about an actual blocker.
Observable: As an authorized user, submit with several blockers present among an obsolete view, disabled bot, missing local setup and invalid input. The refusal names at least one present blocker. If both the credential and model are missing, the local readiness inspection identifies both.
Source: choice: one applicable reason suffices for user feedback, while the administrator needs to see every missing local setting

### C-129: A future production Apex deployment using Salesforce's relevant-tests mode, where available, requires at least 75% coverage per deployed Apex class or trigger.
Observable: Under `RunRelevantTests`, Salesforce refuses production deployment when a deployed class or trigger is covered below 75% by the relevant tests Salesforce ran.
Source: implied: a release beyond U-9's development scope would be bound by [Salesforce relevant-test coverage](https://developer.salesforce.com/docs/platform/api-metadata/references/file-based-calls/meta-deploy.html)

### C-130: A request contains at most 84,000 Unicode code points of conversational text.
Observable: With four retained complete pairs each consisting of a 4,000-code-point prompt and a 16,000-code-point reply, submit a 4,000-code-point follow-up. The combined conversational text is 84,000 code points. This bound excludes provider protocol overhead.
Source: implied: C-26, C-32 and C-95 bound the five user prompts and four reply texts

### C-131: A successful bot update retains the current bot access policy.
Observable: Disable the bot or revoke a user, update the revision successfully, and verify that the disabled state or revocation still applies.
Source: choice: updating bot behavior does not reset authorization decisions

### C-132: A successful bot update retains the current provider setup.
Observable: Set a supported model and credential, update the bot successfully and verify that its next accepted attempt uses those values. If the setup no longer works, the configured values remain in place for the administrator to correct.
Source: choice: updating the bot does not silently rotate a credential or pick a model

### C-133: Restoring a revision does not reactivate previously invalidated views.
Observable: Open a view, replace its revision, then restore the original revision without reopening the view. The original view still cannot send or receive replies.
Source: choice: a change of active revision ends each affected visit permanently

### C-134: Redelivery of the same submission does not start another inference.
Observable: Deliver the same submission twice to Salesforce, including replaying it after the original attempt becomes terminal in the same view. At most one Grok inference begins for that submission. A fresh explicit Send of the same text is a separate submission.
Source: choice: duplicate delivery is different from the intentional repeated use in U-2 and U-4
