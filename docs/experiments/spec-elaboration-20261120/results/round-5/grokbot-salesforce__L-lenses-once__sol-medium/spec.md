## Use cases

### U-1: A Salesforce administrator makes a Grok bot available in a development org so an intended user can try it
Flow: The administrator identifies the target org, installs the bot there, supplies authorized Grok API access, selects one available Grok text model, grants an intended Salesforce user access, and enables the bot. The intended user opens it in Salesforce and obtains a live Grok answer using a sample prompt. If the org is unavailable or the setup fails, the administrator sees which prerequisite to address before treating the bot as verified.
Source: implied: creating a working bot in a Salesforce development org requires a target, setup, access, and a live interaction.

### U-2: An authorized Salesforce user asks Grok a question to get a reply inside Salesforce
Flow: The user signs in, finds the bot, and sees where submitted text goes before entering a prompt. They submit a question, see that it is pending, then read the Grok reply in the same view. If the service cannot answer, they see an outcome other than success.
Source: implied: a Grok bot must accept an interaction and return a Grok answer where the user meets the bot.

### U-3: An authorized Salesforce user checks what input the bot accepts to submit a valid prompt
Flow: The user opens the empty view, tries an empty or all-whitespace prompt, and sees that nothing was sent. They can send nonblank text of 1 through 4,000 Unicode code points, including multiline and non-ASCII text. At 4,001 code points they see the limit and can edit the text before sending.
Source: implied: accepting a prompt entails handling empty, invalid, and boundary input.

### U-4: An authorized Salesforce user asks again to obtain a separate answer
Flow: After an attempt ends, the user submits a new prompt, which can contain the same text as before. Grok receives the new prompt on its own. If the earlier attempt failed, the user can correct or deliberately resend its text. Refreshing or reopening starts an empty view.
Source: implied: the bot can be used more than once, including after a failed attempt.

### U-5: Salesforce users submit overlapping prompts to get their own replies
Flow: A user repeats the send action while a prompt is pending and sees only one attempt for that action. A second user, or a separate view for the same user, can submit a separate prompt subject to available capacity. Replies can finish in either order and appear only in their originating views. If one attempt times out, its late reply does not replace another result.
Source: implied: repeated delivery and overlapping requests can occur when people use the bot.

### U-6: A person without current bot access tries to open or use it to see whether access is allowed
Flow: A guest, a signed-in user without the bot grant, or a user with an expired session attempts to use the bot, including from an already open view or a direct link. The person receives a sign-in requirement or an access denial as applicable and cannot obtain a Grok answer. A user whose access was removed receives no reply that was still pending when the removal took effect.
Source: implied: the bot runs inside an org with authenticated users and permissions that can change.

### U-7: An authorized Salesforce user encounters a dependency failure and resubmits when appropriate to get an answer
Flow: The user sends valid text when Salesforce or xAI rejects the attempt, runs out of capacity, times out, or returns an unusable result. The user sees the kind of failure and what they can do next. The prompt remains available in the open view. After the failure clears, the user explicitly submits again.
Source: implied: a working bot depends on Salesforce, a connection, and an external Grok service.

### U-8: An authorized Salesforce user leaves while waiting to end their interaction
Flow: The user refreshes, closes the view, navigates away, or signs out during a pending request. When they open the bot again with access, they see the empty starting view. A reply from the earlier view does not appear in the new one, even if xAI completes the earlier request.
Source: implied: a caller can leave before a reply arrives.

### U-9: A Salesforce administrator changes Grok setup to restore or maintain the integration
Flow: The administrator checks the enablement state, model selection, credential presence, and access assignment. They replace a credential or change the model, then verify a fresh request. If the save is rejected, the prior settings remain effective. If a saved value fails during verification, the administrator sees the failure and can restore a known working setup.
Source: implied: Grok access and model availability can change after initial setup.

### U-10: A Salesforce administrator suspends or resumes the bot to control when it can send prompts
Flow: The administrator disables the bot while another user has it open. New attempts are refused and pending replies are withheld. The administrator enables it after confirming setup, then verifies that a fresh explicit submission works. If setup is missing, the administrator can see what needs attention.
Source: implied: the operator must be able to stop and start a development integration.

### U-11: A Salesforce administrator diagnoses a failed or unverified installation to restore service
Flow: The administrator checks local setup, then uses the ordinary bot interaction with a non-sensitive test prompt. They distinguish local access or configuration problems from provider authentication, model access, account capacity, and service or transport problems without needing to inspect user prompts or secrets. An unresolved failure leaves the installation unverified.
Source: implied: the operator must be able to observe failures and verify recovery.

### U-12: A Salesforce administrator adds or rolls back the bot in an occupied org to preserve existing work
Flow: The administrator deploys into an org that already has records, users, permissions, automations, and other integrations. Those continue to work under their existing rules. If a change cannot go live or a rollback fails, the administrator can leave the bot disabled. For the initial release, rollback returns the org to its prior state without the bot. A subsequent rollback can restore the prior working bot version.
Source: implied: the request can apply to an existing development org and the administrator must be able to undo the change.

### U-13: An authorized Salesforce user checks the bot's data boundary to avoid exposing unintended information
Flow: The user opens the bot from Salesforce, submits sample text, and receives text back. The bot does not attach the current record, other org data, or past prompts. A prompt or reply containing markup or a request to act on records remains text. A different user or a new view cannot retrieve the interaction through the bot.
Source: implied: the bot crosses the Salesforce-to-Grok boundary without an instruction to expose org data or perform org actions.

### U-14: A Salesforce administrator recovers after losing the development org to resume the demo
Flow: The administrator attempts to open the designated org. If a scratch org has expired or an org has been permanently deleted, the old bot is unavailable there. The administrator designates an accessible development org, installs the bot, provisions authorized xAI access there, and verifies a new interaction.
Source: implied: the requested bot depends on access to the development org throughout its lifetime.

### U-15: A Salesforce release operator checks future release eligibility to keep development acceptance separate from promotion
Flow: The operator sees that the bot works in the development org. If asked later to promote it, they validate in the destination and address applicable Salesforce deployment, credentials, and publication gates. A failed validation or missing destination credential cannot be treated as a working release there.
Source: implied: the request names a development environment, where successful operation does not establish eligibility for a wider release.

## Clauses

### C-1: A Grok bot is installed in a Salesforce development org.
Observable: Opening the designated non-production org shows an installed bot available through an in-org entry point to an authorized user.
Source: request

### C-2: A successful bot reply comes from xAI Grok.
Observable: Submit a new prompt in the target org with live access enabled. The visible answer corresponds to a completed inference from the configured Grok model, verifiable against the provider exchange using a non-sensitive sample prompt.
Source: implied: U-2 and the request's designation of Grok.

### C-3: Acceptance is demonstrated in one designated development org.
Observable: The administrator can identify the target by its Salesforce org identity. A Salesforce org already designated for the task is used if suitable. Otherwise an authorized administrator designates one accessible development org, with Developer Edition as the default when provisioning a new org is necessary.
Source: choice: the request supplies no org identity or edition and needs only one working target.

### C-4: This delivery stops at the development org.
Observable: The delivery outcome shows operation in the designated development org. No production org, public listing, or external end-user channel is provisioned by this delivery.
Source: implied: the request specifies a Salesforce development org as its destination.

### C-5: The bot's user interaction is an in-org text exchange.
Observable: In Salesforce, the user can submit text and read a text reply. Voice, images, file attachments, external chat channels, scheduled jobs, and delegated tasks are outside this interaction.
Source: choice: a text exchange is the smallest in-org interpretation of a Grok bot, and the request supplies no workflow or other channel.

### C-6: An authorized user can find the bot through Salesforce navigation.
Observable: A signed-in user with access can locate a Salesforce entry point whose visible description identifies Grok. A private setup link or direct knowledge of a URL is unnecessary.
Source: implied: U-2 requires the intended user to find the bot.

### C-7: Initial availability is off.
Observable: Immediately after setup is installed, before an administrator enables use, an attempted prompt produces no Grok inference.
Source: choice: a development installation can be provisioned before exposing a billable service.

### C-8: Bot access requires a current Salesforce login.
Observable: A signed-out visitor or user whose session has expired cannot submit a prompt through any bot entry point. Salesforce requests sign-in or returns an authentication denial.
Source: implied: U-6 and Salesforce session authentication.

### C-9: An internal Salesforce user needs an explicit bot grant.
Observable: A signed-in internal user with the grant can use the enabled bot. An internal user without it cannot submit, even from a direct link or an already open view.
Source: choice: access to the development org alone need not include access to external inference.

### C-10: External and guest users cannot invoke the bot.
Observable: A guest or Experience Cloud external user attempting to send through any entry point gets no Grok inference.
Source: choice: the request supplies no external audience.

### C-11: Bot administration requires authorized Salesforce setup access.
Observable: An ordinary bot user cannot change the model, credential, enablement, or user grants. A Salesforce administrator with the relevant setup rights can administer the bot using Salesforce controls.
Source: implied: U-1, U-9, and U-10 distinguish bot use from control over shared setup.

### C-12: Any Salesforce platform permission needed to invoke the bot applies at invocation.
Observable: Withhold the relevant entry-point permission or, if Salesforce External Credentials are used, access to the selected principal. A direct invocation fails without inference even if navigation is visible. Salesforce requires permission for exposed Apex entry points and maps external credential principal access to an authorized profile or permission assignment. [Apex class access](https://developer.salesforce.com/docs/platform/lwc/guide/apex-security), [External credential principals](https://developer.salesforce.com/docs/platform/named-credentials/references/named-credentials-reference/nc-glossary.html)
Source: implied: U-6 and Salesforce entry-point and credential permission rules.

### C-13: The administrator can grant bot use to a specific internal user.
Observable: Grant a selected user access. Their next authorized attempt can proceed without granting access to another user.
Source: implied: U-1 requires making the bot available to its intended user.

### C-14: A revoked bot grant blocks new attempts from that user.
Observable: After revocation is effective in Salesforce, an attempt from the user's already open view is refused without a Grok request.
Source: implied: U-6 and the requirement for a current grant in U-1.

### C-15: A lost authorization prevents delivery of a pending reply.
Observable: Revoke the relevant grant, remove a required platform permission, or end the user's Salesforce session after sending but before reply delivery. The originating view receives no answer from that pending attempt, including after access is restored.
Source: choice: ongoing authorization protects an undelivered reply while allowing access restoration for fresh attempts.

### C-16: A new bot view starts empty.
Observable: On opening a new view, refreshing, or returning after leaving, the prompt is empty and no earlier pending state, answer, or error is displayed.
Source: choice: one fresh text interaction needs no restored session contents.

### C-17: Only an explicit submission starts inference.
Observable: Opening the view, typing, editing, leaving, signing in, changing a Salesforce record, changing bot settings, or enabling the bot does not submit a user prompt.
Source: choice: the request describes no proactive activity or background workload.

### C-18: A submission accepts one text prompt.
Observable: The user can enter one text value, including line breaks, Unicode letters, combining marks, emoji, and punctuation. Submission accepts no separate attachment, image, audio, or record selector.
Source: choice: a single text value is sufficient to ask Grok a question.

### C-19: Nonblank text of 1 through 4,000 Unicode code points is within the bot input limit.
Observable: With setup and service available, prompts of 1 and 4,000 Unicode code points pass local length validation. Spaces and line breaks count toward the limit, an emoji outside the Basic Multilingual Plane counts as one code point, and a combining mark counts separately.
Source: choice: a character bound makes a development interaction predictable without requiring the user to count model tokens.

### C-20: Blank prompts are refused before inference.
Observable: A missing text value, a zero-length string, or a string consisting entirely of Unicode White_Space characters yields a prompt-required outcome and zero Grok inference requests.
Source: implied: U-3 requires an actual input to ask Grok a question.

### C-21: Over-limit text is refused before inference.
Observable: A 4,001-code-point nonblank prompt yields a 4,000-code-point limit notice and zero Grok inference requests. The user can reduce the text without re-entering it.
Source: implied: U-3 applies the chosen upper bound without silent clipping.

### C-22: A malformed submission is refused before inference.
Observable: An attempt with a non-text value, invalid text encoding, or a submitted file or other unsupported input instead of a single text value yields input rejection and no inference request. This also holds if the normal entry point is invoked directly.
Source: implied: U-3 requires the same input boundary regardless of how submission reaches the bot.

### C-23: Valid prompt content reaches Grok without silent rewriting.
Observable: Compare the text presented for submission with the decoded prompt received by xAI. The content matches, including leading and trailing whitespace, line breaks, punctuation, and non-ASCII characters.
Source: implied: U-2 requires Grok to answer what the user actually sent.

### C-24: The user sees that a submission is pending.
Observable: Delay the response after a valid send. The originating view shows that the attempt is in progress until it reaches a final outcome.
Source: implied: U-2 requires distinguishing work still in progress from an unanswered or completed attempt.

### C-25: A successful attempt displays one complete Grok text reply.
Observable: Receive a completed response with nonblank answer text. The originating view shows the user-facing text, preserving its readable content and line breaks. Provider envelopes, token accounting, reasoning traces, and tool payloads are absent from the reply.
Source: implied: U-2 calls for a Grok answer in Salesforce.

### C-26: The bot delivers replies as a single completed result.
Observable: While Grok is generating, the view shows pending status. When the answer is complete, it becomes visible together. The bot exposes no incremental stream.
Source: choice: a single result serves the request without introducing streaming controls or partial-message state.

### C-27: A reply is confined to its originating view.
Observable: Two users or two views for one user submit distinguishable prompts and receive responses in reverse order. Each answer appears only beside its own interaction.
Source: implied: U-5 and U-13 require isolation and correct response association.

### C-28: A later submission uses only its current prompt as user context.
Observable: Send a prompt containing a unique marker, then ask a second question without that marker. The second provider exchange includes neither the earlier text nor the earlier response nor a reference that retrieves them.
Source: choice: independent turns provide repeat use without assuming conversation memory.

### C-29: A final outcome makes the open view available for a new submission.
Observable: After a reply, refusal, validation error, dependency failure, or timeout, a user with valid access can make a fresh explicit submission when the bot is enabled. A previous attempt's pending indication does not block it.
Source: implied: U-4 and U-7 require continued use after an attempt ends.

### C-30: A rejected or failed attempt leaves its text available for correction in the open view.
Observable: After invalid input, a busy rejection, or a failed request, the affected draft can be edited or deliberately resubmitted in its originating view while the user retains access.
Source: implied: U-3 and U-7 require a usable path to correct or repeat the submission.

### C-31: An intentional later send of identical text is a new attempt.
Observable: After an attempt ends, explicitly submit the same prompt again. The second send creates its own inference attempt rather than displaying a cached bot answer.
Source: implied: U-4 distinguishes an intentional repeat from duplicate delivery of one action.

### C-32: A single open view permits at most one unresolved accepted submission at a time.
Observable: While 1 attempt is pending, a second send from that view cannot start or queue a second attempt. A separately delivered second action is treated as busy until the user can explicitly send again.
Source: choice: one pending slot per view avoids ambiguity without blocking separate users or views.

### C-33: Duplicate delivery of one submission does not multiply inference.
Observable: Deliver the same send action twice while it is pending or replay it after it finishes. Observe at most 1 inference request and at most 1 displayed final result for that action. Closing or refreshing its view does not make that same action eligible to submit again.
Source: implied: U-5 must distinguish duplication from a new intentional send.

### C-34: Different views can proceed independently.
Observable: With Salesforce and xAI capacity available, accept valid sends from 2 users or 2 independently open views for the same authorized user before either reply returns.
Source: choice: the per-view pending limit should not serialize unrelated interactions.

### C-35: A pending view has a 45-second interaction deadline.
Observable: In an active view, if a final result has not reached the view 45 seconds after it indicated pending, the view ends the attempt with a timeout outcome. This includes browser-to-org and org-to-provider delays.
Source: choice: the development user needs a bounded wait even if one dependency never sends a completion.

### C-36: An attempt has at most one terminal outcome.
Observable: A submission ends as one of these outcomes: local rejection, complete reply, Grok refusal, incomplete reply, dependency failure, timeout, or abandonment. Closing, replacing, or losing the authorized view can abandon delivery. A later result or error cannot replace a terminal outcome or appear as the answer to a different attempt.
Source: implied: U-5, U-6, U-7, and U-8 require a stable end to each attempt.

### C-37: The bot performs zero automatic retries of user inference.
Observable: Induce an error before dispatch, a lost response after dispatch, or a timeout. No second inference is sent without another explicit action, even if the provider becomes available again.
Source: choice: an uncertain first attempt may already have reached xAI or incurred usage.

### C-38: A live attempt is abandoned when its originating view ends.
Observable: While a request is pending, refresh, navigate away from the bot, close the view, or sign out. The replacement view never displays the old result. An already transmitted request can still complete at xAI.
Source: choice: this bot has no background inbox or resume operation.

### C-39: Troubleshooting feedback tells the user the next available action.
Observable: For each refusal or failure, the view gives the applicable next step: sign in again, request access, wait for an in-progress attempt, correct input, contact the administrator for disabled or misconfigured service, revise a refused or oversized request, or deliberately try again for capacity, timeout, connectivity, or service failure. Unclassified failures direct the user to the administrator.
Source: implied: U-3, U-6, U-7, and U-10 require recovery a user can act on.

### C-40: Missing local setup prevents new inference.
Observable: With the bot enabled but its model selection absent, its credential absent, or required Salesforce outbound authorization disabled, a new send returns a setup problem. An intentionally unfilled prerequisite sends zero inference requests.
Source: implied: U-1 and U-11 require usable setup before the bot can run.

### C-41: A Salesforce request-capacity refusal appears as a failed attempt.
Observable: Exhaust Salesforce capacity needed for the request. The originating user gets a Salesforce capacity or availability outcome, including a Salesforce-provided refusal where the platform blocks entry before the bot can respond.
Source: implied: U-5 and U-7 must account for Salesforce's shared runtime refusing work.

### C-42: A provider authentication rejection is visible as an integration problem.
Observable: Run with an invalid, expired, or revoked key. An authentication rejection, including HTTP 401, yields a provider credential failure. The administrator can identify the need to repair xAI authorization without reading the key in the result. [xAI error reference](https://docs.x.ai/developers/debugging)
Source: implied: U-7, U-9, and the xAI API authentication rule.

### C-43: A provider permission or model rejection is visible as an integration problem.
Observable: A blocked team, a key lacking permission, a retired or inaccessible model, an invalid model identifier, or a provider endpoint rejection yields a provider access or setup failure. HTTP 403 and 404 are handled according to the provider's reported cause when it distinguishes these cases. [xAI error reference](https://docs.x.ai/developers/debugging)
Source: implied: U-7, U-9, and xAI's endpoint and model access rules.

### C-44: A provider-reported account funding or quota problem is visible as an account-capacity failure.
Observable: Cause xAI to reject an otherwise valid request for lack of available credits or exhausted account quota. The administrator sees the account-capacity category when the provider identifies it. The bot does not automatically add credits, change plans, or change accounts. The exact budget and credit threshold for the target account are unconfirmed. [xAI quickstart](https://docs.x.ai/developers/quickstart)
Source: implied: U-7, U-11, and the xAI account funding prerequisite.

### C-45: xAI rate limiting appears as a capacity failure.
Observable: At a provider HTTP 429 rate-limit response, the view indicates that capacity is temporarily unavailable. The limits are requests per second and tokens per minute for the selected model and team. Both exact figures are unconfirmed until the team and model are selected, as xAI sets them per team tier and model. [xAI rate limits](https://docs.x.ai/developers/rate-limits)
Source: implied: U-7 and the xAI team/model rate-limit rule.

### C-46: An xAI-reported text limit refusal appears as a size failure.
Observable: Cause the selected Grok model to reject a request for exceeding its text budget. The attempt reports a provider size refusal even if the local prompt passes 4,000 code points. The provider input/context and output token ceilings are unconfirmed until the Grok model and endpoint are selected. [xAI model reference](https://docs.x.ai/developers/rest-api-reference/inference/models)
Source: implied: U-3 and U-7 and xAI's model-specific token limits.

### C-47: An xAI-reported policy refusal is visible as a refused request.
Observable: If the provider signals a moderation or policy refusal, the user sees a refusal for that attempt. A completed ordinary Grok text answer that declines to answer is shown as returned.
Source: implied: U-7 must account for Grok declining to answer without substituting bot-generated success text.

### C-48: An xAI-reported incomplete result is identified as incomplete.
Observable: Have xAI report that a response ended early, including because it reached an output limit. The attempt indicates that there is no complete reply. Any displayed excerpt is identified as incomplete.
Source: implied: U-7 and the xAI completion status distinguish limited output from a finished answer. [xAI text model best practices](https://docs.x.ai/developers/model-capabilities/text/best-practices)

### C-49: A malformed or unusable provider result yields a failure.
Observable: Return an invalid response body, an empty or whitespace-only answer with no policy-refusal result, an unexpected nonfinal response, or a result containing only non-text or tool content. The user sees that no usable reply was received.
Source: implied: U-2 and U-7 require a usable Grok reply for success.

### C-50: A rejected provider request with no more specific category yields a request failure.
Observable: Return a provider client error for an invalid request argument, method, media type, or field format, such as HTTP 400, 405, 415, or 422. If it has no more specific identified cause, the user sees a request failure with an administrator recovery path. [xAI error reference](https://docs.x.ai/developers/debugging)
Source: implied: U-7 and xAI's rules for valid API requests.

### C-51: Provider service failure is visible as service unavailability.
Observable: Return HTTP 5xx or a provider outage response without a more specific recognized outcome. The user sees that Grok service is unavailable for the attempt.
Source: implied: U-7 requires an observable outcome when the external service fails.

### C-52: A connection failure is visible as a transport or availability failure.
Observable: Interrupt the browser-to-Salesforce connection, or cause DNS resolution, TLS validation, connection establishment, or response transfer to Salesforce to fail. While the view is still available, it reports a connection or availability problem, with the timeout outcome applying if the failed path supplies no earlier result.
Source: implied: U-7 requires distinguishing absence of a reply from successful inference.

### C-53: A provider callout timeout ends the attempt as a timeout.
Observable: Cause the Salesforce callout to reach its timeout before a usable final result. The originating view reports timeout. The Salesforce Apex callout default is 10 seconds when no override is set, and Salesforce permits a per-call override from 1 through 120,000 milliseconds. The bot's separate 45-second view deadline still applies. [Salesforce callout timeout rules](https://developer.salesforce.com/docs/platform/apex-dev/references/apex-dev/apex-callouts-timeouts.html)
Source: implied: U-7 and the Salesforce Apex per-call timeout rule.

### C-54: A service failure never appears as a fabricated Grok answer.
Observable: Block the provider, remove authorization, or supply an unusable result. The view shows the failure outcome without a substitute model's answer, canned response presented as a live reply, or silent reuse of an earlier reply.
Source: implied: the request names Grok as the bot and U-2 calls for a genuine answer.

### C-55: Only the configured xAI service receives bot inference traffic.
Observable: A submitted URL, model instruction, redirect, or untrusted reply does not cause Salesforce to send the prompt or authorization to a different host. The legitimate destination is the authorized xAI HTTPS inference service for the configured org.
Source: implied: U-2, U-9, and U-13 limit the external exchange to Grok.

### C-56: The bot identifies xAI as the recipient before submission.
Observable: Before entering or sending text, a user can see that text they submit will leave Salesforce and be processed by xAI.
Source: implied: U-2 and U-13 involve a user's intentional transfer across a service boundary.

### C-57: The external exchange sends no hidden org or user content.
Observable: Inspect the provider request for a non-sensitive sample. Its application data consists of the current submitted text and the selected Grok model, with authentication and any fields required to request text inference. No Salesforce records, record context, Salesforce user identifiers, session tokens, conversation history, or browser state are included. Ordinary protocol metadata is outside this restriction.
Source: choice: the request does not authorize Salesforce data enrichment or linking a Grok request to an identifiable Salesforce user.

### C-58: The bot has no bot-managed conversation or result history.
Observable: After refresh, navigation away, close, logout, or reopening in another view, past drafts, prompts, replies, and errors are unavailable through the bot. They cannot be retrieved by an administrator via a bot-owned record, transcript, or export. This applies to bot-managed storage, with provider retention governed separately.
Source: choice: transient prompt-and-reply use needs no saved history or retention controls.

### C-59: xAI retention is governed by the configured provider account.
Observable: The operator can verify that the development team's default provider audit retention is 30 days unless the team is configured for Zero Data Retention. Clearing the Salesforce view does not promise erasure at the provider. [xAI API security and retention](https://docs.x.ai/developers/faq/security)
Source: implied: U-13 and xAI's retention rule for API traffic.

### C-60: The bot exposes provider output as inert content.
Observable: A prompt or reply containing HTML, script, an instruction to run code, or a tool invocation cannot execute in the Salesforce page or initiate an outbound action. The user can read the reply as text.
Source: implied: U-13 and the Salesforce Lightning rule that untrusted content may not be injected as executable markup. [Salesforce Lightning security](https://developer.salesforce.com/docs/platform/secure-coding/guide/secure-coding-lightning-security.html)

### C-61: Bot use never retrieves Salesforce business records.
Observable: Open the bot from a record context or ask for stored Accounts, Contacts, or any other org data without supplying it in the prompt. The operation does not read a business record for the answer, even if the user has Salesforce record access.
Source: choice: the request supplies no record-backed workflow or search scope.

### C-62: Bot use never mutates Salesforce business records.
Observable: Ask to create, update, delete, or otherwise act on a Salesforce record. Observe that Salesforce records and their fields have the same values and existence before and after the interaction.
Source: choice: the request gives Grok no authority to take actions on Salesforce data.

### C-63: The bot offers no model-driven action or tool invocation.
Observable: Ask the bot to look up the web, execute code, send a message, or trigger an automation. No such operation is invoked through the bot, even if the reply contains action-shaped content.
Source: choice: text inference meets the request without delegating actions to the model.

### C-64: The administrator can supply Grok API authorization without asking end users for a key.
Observable: An authorized administrator provisions the org's Grok API access. A user with the bot grant can send a prompt without entering an API key or signing in to xAI. Missing or invalid API authorization fails because xAI requires an authorized API credential for inference. [xAI API quickstart](https://docs.x.ai/developers/quickstart)
Source: choice: one org-level integration lets authorized development users work entirely within Salesforce.

### C-65: A configured Grok key is secret outside authorized credential provisioning.
Observable: Inspect the bot UI, subsequent configuration views, exported bot metadata, client assets, browser request traffic, errors, and bot-emitted diagnostics after provisioning. None reveals the key, Salesforce auth tokens, or credential-bearing headers. The Grok key is used only for authentication to the authorized provider.
Source: implied: U-6, U-9, and U-13 require authorization without disclosing access secrets.

### C-66: Salesforce outbound authorization is a prerequisite for an Apex callout.
Observable: In an Apex-backed bot, remove or disable Salesforce's authorization for the xAI destination. Salesforce prevents the external send until the destination is authorized again. Salesforce requires a usable Named Credential for that destination or the applicable Remote Site Setting for a direct Apex callout. [Salesforce named credential rules](https://developer.salesforce.com/docs/platform/apex-dev/references/apex-dev/apex-callouts-named-credentials.html)
Source: implied: U-1 and the Salesforce Apex outbound destination authorization rule.

### C-67: The administrator selects one effective Grok text model at a time.
Observable: The administrator sees the current model selection, can replace it with a text model available to the authorized API key, and can observe the selection used for a fresh inference. There is no end-user model picker or automatic substitution. [xAI model availability](https://docs.x.ai/developers/rest-api-reference/inference/models)
Source: choice: one active configurable model supports a demo and subsequent model retirement without fixing a release-specific model name.

### C-68: The administrator can replace the development credential.
Observable: Replace the existing bot credential with another authorized xAI key and send a fresh sample prompt. New requests use the replacement after the change takes effect. The bot does not need to reveal the old key to make the change.
Source: implied: U-9 requires recovery from an invalid or revoked key.

### C-69: Credential changes are confined to the bot's integration.
Observable: Rotate, clear, or remove the bot's credential binding. Unrelated Salesforce integrations continue to use their existing credentials. The operation does not revoke external keys in the xAI account.
Source: choice: bot recovery and rollback must be possible without altering unrelated integrations or provider account state.

### C-70: A rejected setup change leaves the previous saved setting effective.
Observable: Cause Salesforce to reject a proposed change to enablement, model, credential binding, or a user's bot grant. The administrator sees the rejection and the affected setting remains at its previous saved value.
Source: implied: U-9 and U-10 require knowing which settings took effect.

### C-71: Concurrent setup operations do not produce a partially applied effective configuration.
Observable: Overlap credential or model changes with a submission. The request uses the coherent saved settings in effect when it starts its outbound call. If an overlapping operation is rejected, the request cannot use values from that rejected operation. Separately saved settings can require verification as a new combination.
Source: choice: observable application follows successful saves without requiring a particular configuration screen or a multi-setting transaction.

### C-72: Credential or model changes do not cause a dispatched attempt to be sent again.
Observable: Change the model or replace the key after xAI receives a request. The pending attempt can finish using the existing provider outcome while access and enablement remain valid. It does not issue a new request with the replacement settings.
Source: choice: preserve an already dispatched interaction without extra usage or mixed answers.

### C-73: The administrator can disable new inference without removing the bot.
Observable: Disable the bot using available Salesforce controls. A send attempted after the change is effective yields an unavailable outcome with zero xAI requests, even in a pre-opened view.
Source: implied: U-10 requires an operational stop.

### C-74: Disablement withholds pending replies.
Observable: Disable the bot after dispatch but before delivery. The still-open view withholds the reply and ends the attempt as unavailable. Re-enabling does not revive it. Work already accepted at xAI can still finish there.
Source: choice: stop applies to undelivered bot results without claiming to recall external traffic.

### C-75: Re-enablement permits fresh requests with current valid setup.
Observable: After disabling, enable the bot with usable org access and Grok setup. A fresh explicit submission can produce a Grok reply without reinstalling the bot.
Source: implied: U-10 requires resuming ordinary use after a stop.

### C-76: Local setup status is inspectable by the administrator.
Observable: Salesforce controls show whether the bot is enabled or disabled, the selected model or its absence, whether credential setup is present, and whether a given user has the necessary bot grant. Presence of local configuration does not claim the provider is reachable or that a key is valid.
Source: implied: U-1, U-9, and U-11 require troubleshooting the setup the administrator controls.

### C-77: Live verification uses the ordinary authorized user path.
Observable: Use a sample prompt in the designated org as a user with the intended access. The deployment is verified only after a genuine Grok text reply appears through that entry point. Installed metadata alone, a mock, or a failed or incomplete result is insufficient.
Source: implied: U-1 and U-11 require evidence that the created bot operates end to end.

### C-78: An administrator can diagnose a sample request without exposing conversational content.
Observable: For a fresh sample attempt, the administrator can distinguish success, local access denial, disabled or missing setup, Salesforce failure or capacity, provider authentication, provider model or permission, provider account capacity, provider rate limit, provider request or size refusal, provider policy refusal, incomplete or invalid result, timeout, transport failure, and unclassified provider failure, where the platform or provider supplies the distinction. Lookups or live checks suffice. A historical diagnostics dashboard is outside scope.
Source: choice: coarse outcomes plus existing setup surfaces suffice to identify recoverable demo failures without adding a telemetry product.

### C-79: Diagnostics do not disclose user content or credentials.
Observable: Exercise success and failure with unique strings in a prompt, reply, key, authorization header, and raw upstream error body. Bot-emitted logs and diagnostic or error output contain no raw prompt, raw reply, credential value, credential-bearing header, raw upstream error body, or raw stack trace. The user-facing answer and editable prompt in the originating view are outside diagnostic output.
Source: implied: U-11 and U-13 require safe observation without widening access.

### C-80: Salesforce's Apex transaction callout count constrains bot inference when Apex makes the request.
Observable: An Apex transaction that has used its 100 available callouts receives no 101st bot callout. The user sees a failure rather than a success fabricated from the blocked callout. [Salesforce callout limits](https://developer.salesforce.com/docs/platform/apex-dev/references/apex-dev/apex-callouts-timeouts.html)
Source: implied: U-7 and the Salesforce Apex maximum of 100 callouts per transaction for ordinary org code.

### C-81: Salesforce's cumulative callout allowance constrains an Apex-backed attempt.
Observable: When Salesforce exhausts the shared 120-second callout allowance in a transaction, the attempt cannot obtain a successful reply through that transaction after the allowance is exhausted. [Salesforce callout limits](https://developer.salesforce.com/docs/platform/apex-dev/references/apex-dev/apex-callouts-timeouts.html)
Source: implied: U-7 and the Salesforce Apex 120-second cumulative callout rule.

### C-82: Developer Edition Apex external concurrency can refuse bot attempts.
Observable: In Developer Edition, hold 20 Apex callouts to hosts outside the org domain open. A further attempt that exceeds Salesforce's org-wide external callout capacity is refused or fails pending capacity returning. The 20-callout rule is specific to Developer Edition. [Salesforce callout concurrency](https://developer.salesforce.com/docs/platform/apex-dev/references/apex-dev/apex-callouts-timeouts.html)
Source: implied: U-5 and the Salesforce Developer Edition external callout concurrency cap.

### C-83: Salesforce's Apex callout payload ceiling constrains request and response handling.
Observable: For an Apex callout, a request or response exceeding Salesforce's ceiling fails rather than becoming a complete bot answer. The ceiling for each HTTP message is 6 MB in synchronous Apex and 12 MB in asynchronous Apex. [Salesforce Apex limits](https://developer.salesforce.com/docs/platform/apex-dev/references/apex-dev/apex-gov-limits.html)
Source: implied: U-3 and U-7 and the Salesforce per-callout message-size rule.

### C-84: Apex heap exhaustion cannot produce a successful bot reply.
Observable: If handling an Apex response exhausts Salesforce's applicable transaction heap, the attempt ends without a reply and the user sees a failure or the bounded timeout. Salesforce's published heap limits are 10 MB synchronous and 25 MB asynchronous, with the request and response counting toward heap. [Salesforce Apex limits](https://developer.salesforce.com/docs/platform/apex-dev/references/apex-dev/apex-gov-limits.html)
Source: implied: U-7 and the Salesforce Apex transaction heap rule.

### C-85: Apex CPU exhaustion cannot produce a successful bot reply.
Observable: If the transaction exceeds its Salesforce CPU allowance while processing the attempt, no complete reply is reported from that transaction. The Salesforce Apex limits are 10,000 ms synchronous and 60,000 ms asynchronous. Waiting for callouts is excluded from CPU accounting. [Salesforce Apex limits](https://developer.salesforce.com/docs/platform/apex-dev/references/apex-dev/apex-gov-limits.html)
Source: implied: U-7 and the Salesforce Apex CPU governor.

### C-86: Salesforce's long-running Apex capacity can refuse a new synchronous attempt.
Observable: If the org has exhausted its allowed concurrent synchronous Apex work lasting more than 5 seconds, the bot cannot deliver a reply through a transaction refused by Salesforce. The allowance is 1 transaction per 100 applicable licenses, with a floor of 10 and a ceiling of 50. The exact org allowance is unconfirmed, and HTTP callout wait time is excluded. [Salesforce Apex limits](https://developer.salesforce.com/docs/platform/apex-dev/references/apex-dev/apex-gov-limits.html)
Source: implied: U-5 and the Salesforce long-running synchronous transaction governor.

### C-87: An Apex request blocked by uncommitted work cannot dispatch to Grok in that transaction.
Observable: In an Apex-backed integration, try to send from a transaction with pending record changes, queued asynchronous work, scheduled work, or email sends. Salesforce refuses the external callout while those pending operations remain. The attempted interaction cannot report a Grok success using that blocked callout. [Salesforce callout limitations](https://developer.salesforce.com/docs/platform/apex-dev/references/apex-dev/apex-callouts-timeouts.html)
Source: implied: U-7 and the Salesforce rule preventing Apex callouts with uncommitted work.

### C-88: A record save never waits for a synchronous Grok callout.
Observable: Save a record or run an automation that saves a record. The save does not start a bot interaction or wait for Grok. Salesforce also forbids synchronous Apex callouts from record triggers. [Salesforce Apex trigger rules](https://developer.salesforce.com/docs/platform/apex-dev/references/apex-dev/apex-triggers.html)
Source: implied: U-12 preserves the existing record workflow and Salesforce's record-trigger callout restriction.

### C-89: Async Apex capacity can refuse an attempt when the chosen route uses it.
Observable: If the bot uses asynchronous Apex and the org has exhausted its standard licensed quota, an attempt that cannot run within the interaction deadline shows failure or timeout. Salesforce's standard rolling 24-hour limit is the greater of 250,000 executions or 200 times applicable user licenses. The target allowance and any enabled elastic entitlement are unconfirmed. [Salesforce Apex limits](https://developer.salesforce.com/docs/platform/apex-dev/references/apex-dev/apex-gov-limits.html)
Source: implied: U-7 and the Salesforce asynchronous Apex execution governor where applicable.

### C-90: Installation into the development org preserves pre-existing business data.
Observable: Existing Salesforce records and field values remain as before installation, including in an org with existing data. Installation requires no deletion, migration, seeding, or reclassification of those records.
Source: implied: U-12 and the request to add a bot give no authority to alter business data.

### C-91: Installation preserves pre-existing Salesforce access rights.
Observable: Existing user logins, object and field permissions, and record sharing work as before. The administrator can grant or revoke bot access independently of those rights.
Source: implied: U-12 requires adding bot access without changing existing org access.

### C-92: Installation preserves pre-existing automation.
Observable: Existing triggers, flows, validation rules, and scheduled behavior retain their prior conditions and effects after the bot is installed, enabled, or disabled.
Source: implied: U-12 and the additive request preserve existing automation.

### C-93: Installation preserves pre-existing navigation and integrations.
Observable: Existing Salesforce apps, tabs, and pages remain reachable to their existing audiences. Other integrations retain their destinations, credentials, and behavior. Bot setup adds only the visibility necessary to reach and operate this bot.
Source: implied: U-12 requires the existing org to continue working when the bot is added.

### C-94: Reinstalling the same bot release does not create another independently usable bot in the target org.
Observable: Install the same release twice into the designated org. The authorized user still reaches the same logical bot with one effective setup.
Source: choice: repeat deployment must be safe for the single-bot delivery without constraining the number of navigation links.

### C-95: A failed installation or update is not reported as verified.
Observable: Cause deployment to fail or leave local or provider setup incomplete. The administrator can identify that installation, setup, or verification is incomplete. Any incomplete release that cannot be verified stays unavailable to users, or the previously working release stays in use.
Source: implied: U-1 and U-12 require a working outcome even when setup spans more than one operation.

### C-96: The administrator can return the bot to the immediately preceding working release state.
Observable: After updating a working bot, roll back. The former behavior can be verified with a fresh sample after restoring the former bot settings with currently valid authorization. A revoked external key is not resurrected by rollback.
Source: implied: U-12 requires a realistic route back after a bad update.

### C-97: The administrator can undo the first release.
Observable: Return the org to its pre-bot release state. The bot has no usable entry point, no bot-specific user grants, and no active credential binding there.
Source: implied: U-12 requires first-release rollback even though there is no earlier bot version.

### C-98: A rollback affects only the bot's additions and its own setup.
Observable: Compare the org before and after rollback. Records, unrelated metadata, automations, other integrations, other permissions, and unrelated changes made since installation remain intact.
Source: implied: U-12 requires returning from the bot release without rolling back unrelated org work.

### C-99: A release rollback can be performed with inference disabled.
Observable: Start rollback with the bot disabled. A send during the rollback, including one from a stale view, yields no outbound inference. If rollback fails, the administrator can keep inference unavailable while repairing the installation.
Source: choice: a failed maintenance operation must have an available stopped state.

### C-100: A pending interaction does not migrate between releases.
Observable: Roll back or remove the bot while a request is pending. No reply from that attempt appears in a view of the restored release. A request already received by xAI may still have been processed.
Source: choice: releasing a new or previous version does not require persistence or replay of old interactions.

### C-101: An expired scratch org cannot continue serving the bot.
Observable: In a scratch org, the selected lifespan is 1 through 30 days, with 7 days by default. After Salesforce expires and deletes it, the administrator cannot open that instance or recover the bot there. [Salesforce scratch org lifecycle](https://developer.salesforce.com/docs/atlas.en-us.sfdx_dev.meta/sfdx_dev/sfdx_dev_scratch_orgs.htm)
Source: implied: U-14 and Salesforce scratch org expiration.

### C-102: Developer Edition inactivity can end the bot's availability.
Observable: If the target is Developer Edition and Salesforce permanently deletes it for inactivity, old access stops. The published idle thresholds are 45 days without login for Developer Edition and 180 days for Developer Edition Legacy, subject to Salesforce's edition-specific reactivation windows and exemption rules. The target's subtype, exemption status, and expiration date are unconfirmed. [Salesforce Developer Org Expiration](https://help.salesforce.com/s/articleView?id=sf.admin_de_org_expiration.htm&language=en_US&type=5)
Source: implied: U-14 and the Salesforce Developer Edition inactivity rule.

### C-103: Recovery in a replacement org requires verification in that org.
Observable: After the original org becomes inaccessible, install in an accessible designated development org and run a fresh authorized sample. The replacement is available only after its own access, setup, and live reply work. No previous interactions are brought over.
Source: implied: U-14 requires a working bot despite the previous environment being unavailable.

### C-104: A future Salesforce production deployment containing Apex is subject to Salesforce test execution rules.
Observable: Validate a future production deployment containing Apex. A failing required Apex test blocks deployment. The default production test level for a deployment containing Apex is RunLocalTests unless a valid different level is selected. [Salesforce deployment test levels](https://developer.salesforce.com/docs/platform/api-metadata/references/file-based-calls/meta-deploy.html)
Source: implied: U-15 and the Salesforce production Apex test gate.

### C-105: A future Salesforce production deployment containing Apex is subject to Salesforce coverage rules.
Observable: For ordinary local or all-org testing, Salesforce rejects inadequate org-wide Apex coverage below 75% or a trigger with zero coverage. If RunSpecifiedTests is selected, Salesforce instead requires at least 75% coverage for each deployed Apex class and trigger individually. [Salesforce testing rules](https://developer.salesforce.com/docs/platform/apex-dev/references/apex-dev/apex-testing-best-practices.html), [Salesforce selected-test coverage rule](https://developer.salesforce.com/docs/platform/api-metadata/guide/meta-deploy-run-specific-tests.html)
Source: implied: U-15 and the Salesforce production Apex coverage gate.

### C-106: Standard Apex unit-test execution cannot certify live Grok connectivity.
Observable: In an ordinary Apex unit-test run, external HTTP calls are blocked and substitutes supply their results. A passing unit-test deployment gate alone cannot yield the live reply required to verify the installation. [Salesforce Apex unit and integration testing rules](https://developer.salesforce.com/docs/platform/apex-dev/references/apex-dev/apex-testing-integration-testing.html)
Source: implied: U-1, U-15, and the Salesforce standard Apex unit-test callout rule.

### C-107: A destination org needs its own working credential setup before live use.
Observable: Deploy or package the bot for a future destination org. If a Salesforce packaged external credential is used, the installation does not carry its secret. The destination administrator supplies authorized credential material there before a live Grok request works. [Salesforce external credential provisioning rule](https://developer.salesforce.com/docs/platform/named-credentials/guide/nc-populate-external-credentials.html)
Source: implied: U-15 and Salesforce's exclusion of protected credential values from packaged metadata.

### C-108: A future public AppExchange release requires Salesforce security review.
Observable: A public AppExchange listing for the bot cannot be published with the linked solution still pending or failing security review. This gate applies only if public AppExchange distribution is later requested. [Salesforce AppExchange security review](https://partners.salesforce.com/s/education/appinnovators/Security_Review?language=en)
Source: implied: U-15 and the Salesforce AppExchange publication rule.
