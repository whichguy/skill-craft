## Use cases

### U-1: A development-org user opens the bot to ask Grok a question
Flow: The user signs in to the target Salesforce development org, opens the bot, enters a question, submits it, and sees Grok's reply in Salesforce. On the first visit the prompt is empty. The user can ask another question after the first finishes.
Source: implied: “Create a Grok bot in a Salesforce development org.”

### U-2: A user submits a boundary-case prompt to learn whether it can be answered
Flow: The user tries an empty prompt, a whitespace-only prompt, a prompt of exactly 4,000 Unicode code points, then a prompt of 4,001. Empty, whitespace-only, and over-limit inputs receive feedback without reaching Grok. The 4,000-code-point prompt can be sent. A caller trying to submit a value other than text receives input feedback.
Source: implied: a bot accepting user-entered questions

### U-3: A user encounters a failed request and decides whether to retry
Flow: The user submits a valid question. If Salesforce or Grok refuses the request, the connection fails, or the answer misses its deadline, the user sees the failure category and can retry the same text when service is available again.
Source: implied: a Salesforce bot depends on access to an external model

### U-4: An operator configures bot access to make it available
Flow: The operator confirms the target development org, configures a Grok account credential and model, grants access to a verification user, enables submissions, verifies a reply from a real request, then grants access to the intended audience. An unauthorized user who tries to open or use the bot is refused.
Source: implied: a bot in a Salesforce development org must be usable by its intended audience

### U-5: An operator suspends or recovers the bot to control availability
Flow: The operator checks whether the bot is enabled and whether a sample question can be answered. The operator can disable the bot, fix or replace its Grok settings, re-enable it, and verify service with a permitted account. Users denied service see feedback.
Source: implied: a development-org operator needs to diagnose and stop an integration that makes external requests

### U-6: An operator activates or rolls back the bot in an existing org to preserve org use
Flow: The operator starts with an org that may already have users, records, and other features. Activation enables the new bot for the authorized audience. An unrelated feature that conflicts with installation stays available while the operator addresses the conflict. Rollback of the initial activation removes the bot from use. If rollback fails, the operator can see that removal is incomplete.
Source: implied: the request places a new bot in a Salesforce development org that may already be in use

### U-7: A user checks where a question goes before sharing it
Flow: Before the first submission, the bot makes clear that the question goes to xAI. The user types a question or pastes text, then reads the reply in the same view. Opening a fresh view does not recover either the draft or the reply.
Source: implied: U-1 sends text from Salesforce to an outside service

### U-8: An operator investigates a rejected or unsuccessful attempt to restore service
Flow: The operator checks enablement, model selection, credential presence, and user grants. A configured credential still needs live verification. The operator tries a harmless question using a permitted Salesforce account. The resulting failure category directs the operator to check org access, configuration, provider limits, or availability, as applicable.
Source: implied: U-3 and U-5 require recoverable operation

### U-9: Users submit overlapping questions to get their own answers
Flow: One user activates submit twice while the first question is pending. Another user submits a question in a different view. The first view has one attempt, and each view receives only its own result. If a result arrives after its attempt timed out or its view ended, it does not appear in another attempt or view.
Source: implied: U-1 and U-3 can occur concurrently in the same org

### U-10: An operator changes availability while a question is processing to control future requests
Flow: The operator disables the bot, revokes access, or replaces provider settings while a request is outstanding. The existing request may finish under the conditions it was sent with. Subsequent requests use the now-effective state.
Source: implied: U-4 and U-5 can overlap an ordinary submission

## Clauses

### C-1: A Grok bot is available in the designated Salesforce development org.
Observable: The operator can sign in to the designated Salesforce development org as a permitted user and open the installed bot.
Source: request

### C-2: A successful bot reply comes from Grok.
Observable: When Grok returns a successful answer to a submitted question, the answer shown in Salesforce is the answer supplied by Grok.
Source: request

### C-3: The bot presents its reply inside the Salesforce org.
Observable: After a successful submission the user reads the answer without leaving Salesforce.
Source: choice: one in-org surface is enough for the requested bot.

### C-4: The bot opens with an empty prompt.
Observable: A newly opened bot view has no draft text.
Source: choice: a new view starts ready for a new question.

### C-5: A user can submit another prompt after a successful reply.
Observable: After the first answer appears, the user can submit a second valid question.
Source: implied: U-1 calls for ordinary repeated use of the bot.

### C-6: A zero-code-point prompt is refused before it reaches Grok.
Observable: Submitting an empty prompt results in feedback and no Grok request.
Source: implied: U-2 has no question for the bot to answer.

### C-7: A prompt consisting exclusively of Unicode whitespace is refused before it reaches Grok.
Observable: A nonempty prompt made only from U+0009–U+000D, U+0020, U+0085, U+00A0, U+1680, U+2000–U+200A, U+2028, U+2029, U+202F, U+205F, or U+3000 yields blank-input feedback without a provider request.
Source: choice: use the [Unicode White_Space set](https://www.unicode.org/charts/collation/chart_Whitespace.html) to make blank detection consistent.

### C-8: The bot admits nonblank prompts up to 4,000 Unicode code points inclusive.
Observable: Nonblank submitted text from 1 through 4,000 code points passes length validation. A supplementary-plane character such as 😀 counts as 1, as does each individual code point in a combining sequence. All whitespace in the submitted text counts toward this boundary.
Source: choice: a finite input boundary supports useful questions and can be checked consistently.

### C-9: The bot refuses prompts above 4,000 Unicode code points before sending them to Grok.
Observable: A 4,001-code-point prompt yields length feedback without sending a shortened prompt or making a Grok request.
Source: choice: users should know when the full question exceeds the chosen input boundary.

### C-10: A failed submission is reported as a failure.
Observable: When the submission ends without a usable reply, the current attempt shows a failure instead of answer text.
Source: implied: U-3 requires the user to distinguish a failure from a Grok answer.

### C-11: A failed submission leaves its text available for a deliberate retry in the same open view.
Observable: After a failed request becomes terminal, the user can resubmit the same text from that view without retyping it when the bot permits submissions again.
Source: choice: keeping the draft avoids needless re-entry.

### C-12: Only Salesforce users granted bot access can use it.
Observable: In the designated org, a signed-in user without the grant is refused when trying to submit a question.
Source: choice: the operator controls who can spend Grok capacity.

### C-13: The operator can set the Grok account credential.
Observable: After the operator sets a valid credential, an otherwise ready bot can use the corresponding Grok account to answer a question.
Source: implied: U-4 needs an authenticated Grok request.

### C-14: The operator can choose a Grok model supported for text answers by the configured account.
Observable: With a supported model selected, a successful request uses that model as seen at the Grok service boundary.
Source: choice: the request gives no model name and account availability can vary.

### C-15: The operator can turn off new bot submissions.
Observable: After disablement takes effect, a valid prompt is refused before a new Grok request is made.
Source: choice: U-5 requires a way to suspend external use.

### C-16: The operator can resume new bot submissions.
Observable: After enablement takes effect, an authorized user with a valid prompt and working Grok settings can submit it.
Source: choice: U-5 requires recovery after a suspension.

### C-17: The operator can see whether the bot is enabled.
Observable: The operator can tell whether the bot is administratively enabled or disabled without sending a prompt. Enablement alone does not establish service health.
Source: choice: administrative availability is distinct from service health.

### C-18: The operator can return the bot to its pre-activation user-facing availability.
Observable: After rollback of the initial activation, users can neither open nor submit through the new bot.
Source: choice: the first rollback restores the pre-bot state.

### C-19: Initial installation targets one explicitly designated Salesforce development org.
Observable: Before activation the operator can match the selected target to its Salesforce org ID. With no confirmed org ID, activation remains pending.
Source: choice: the request supplies no org identifier, so the requester or authorized operator designates a single target.

### C-20: The bot is discoverable through Salesforce navigation for authorized users.
Observable: An authorized user can find the Grok bot from the org's navigation without having to know a direct link.
Source: choice: one discoverable entry point suffices. The navigation location and label are left open because the request supplies neither.

### C-21: A person without a valid Salesforce session cannot submit a question.
Observable: A signed-out visitor or a user with an expired or invalid session cannot cause a Grok request.
Source: choice: the bot serves an internal development-org audience.

### C-22: A signed-in user without bot access is denied the bot surface.
Observable: Opening the bot directly with a Salesforce account lacking the bot-use grant does not reveal the prompt or any answer.
Source: choice: a direct link is an entry point, so access applies there too.

### C-23: The operator can grant bot use to a named Salesforce user.
Observable: After the grant takes effect, the designated user can open the bot.
Source: choice: individual grants suffice to establish the permitted audience.

### C-24: The operator can revoke a user's bot-use grant.
Observable: After revocation takes effect, a new submission by that user does not reach Grok.
Source: choice: U-4 requires a way to remove access that was granted.

### C-25: A bot-use grant alone provides no bot administration privileges.
Observable: With only the bot-use grant, a user cannot change enablement, model selection, credentials, or bot access grants.
Source: choice: the ability to ask questions does not require control of the four bot settings.

### C-26: The operator can inspect bot configuration.
Observable: The operator can determine the selected model or its absence, whether a credential is configured, and which users have bot use. Enablement is independently visible as in C-17. The lists cover the bot's administrative state and exclude unrelated Salesforce settings.
Source: choice: these are the settings needed to diagnose U-8.

### C-27: A fresh installation starts with external submissions disabled.
Observable: A valid prompt cannot reach Grok immediately after installation and before an operator enables submissions.
Source: choice: verification users and the provider account must be chosen before external use.

### C-28: A fresh installation starts with zero bot-use grants for ordinary users.
Observable: Before the operator assigns a grant, an ordinary signed-in Salesforce user cannot open the bot.
Source: choice: the request names no audience.

### C-29: A missing required setting prevents dispatch.
Observable: With the bot enabled, omitting the credential, model selection, outbound destination authorization, or Salesforce authorization to use the configured credential results in a setup failure with no Grok request.
Source: implied: U-4 requires a usable provider configuration and authorized access to it.

### C-30: The operator can replace the configured credential.
Observable: After replacement, a new request uses the replacement credential's provider access.
Source: choice: a revoked, expired, or deliberately rotated credential must be recoverable.

### C-31: The operator can see the outcome of a live verification question.
Observable: Acting as, or observing, a Salesforce user with the bot-use grant, the operator can see the Grok reply or the failure feedback for a valid sample prompt submitted through the ordinary bot entry point.
Source: implied: U-4 verifies that the installed integration actually answers.

### C-32: Each Grok request contains the submitted question as a single user turn.
Observable: At the provider boundary, the submitted text arrives intact, including leading or trailing whitespace on nonblank text. Earlier questions and replies are absent.
Source: choice: a question-and-answer bot serves the request without carrying history forward.

### C-33: The bot accepts questions as plain text.
Observable: The prompt can contain letters, numbers, punctuation, emoji, and line breaks within the input boundary. Uploads, audio, and images are outside scope because the bot only needs written questions.
Source: choice: text provides a minimal input channel.

### C-34: The bot presents the answer as readable text.
Observable: The user can read the model's answer, including multi-line text and non-ASCII characters, in the bot view.
Source: choice: text is sufficient for a reply. Formatting and styling are left open.

### C-35: The bot discloses the external recipient before sending a question.
Observable: Before submitting a prompt, a user can see that the prompt is sent to xAI for Grok processing.
Source: choice: users need to know where their text will go before they supply it.

### C-36: The bot adds no Salesforce record contents to the request.
Observable: The provider receives the user-entered question without extra text from account, contact, lead, opportunity, case, or other Salesforce records. Text the user enters themselves is part of the question.
Source: choice: the request asks for a bot in Salesforce and specifies no CRM data integration.

### C-37: The bot does not retain prompts after the current view ends.
Observable: Closing, refreshing, or navigating away from the view leaves no draft or submitted question retrievable through the bot on reopening.
Source: choice: short-lived questions suffice for the requested development bot.

### C-38: The bot does not retain replies after the current view ends.
Observable: Closing, refreshing, or navigating away from the view leaves no answer retrievable through the bot on reopening.
Source: choice: a persistent transcript is outside scope because the requested bot can answer in the current view.

### C-39: The user sees whether an admitted submission is still pending.
Observable: While the bot awaits the terminal result of a submission, the user sees an in-progress state.
Source: implied: U-3 requires the user to know whether the attempt is finished.

### C-40: A terminal failure identifies an actionable failure category.
Observable: Feedback distinguishes Salesforce access denied, bot disabled, input invalid, setup or provider authorization rejected, provider usage limited, timeout, service or connection failure, and unusable provider reply. Invalid input feedback distinguishes empty or blank text, excessive length, and a missing or invalid text value. A provider rejection for insufficient account capacity or a model context limit falls under provider usage limited. When multiple independent conditions prevent dispatch, reporting any applicable refusal suffices. Service or connection failure includes Salesforce execution failure, browser connection failure, xAI transport failure, and provider outage. Exact wording is left open.
Source: choice: these categories tell the user whether to edit the prompt, retry later, or contact an operator.

### C-41: The bot refuses a provider result that has no usable answer.
Observable: A missing answer, an empty or whitespace-only answer, a malformed provider response, a provider-reported failed or incomplete response, or a reply composed solely of non-answer output such as reasoning metadata or action requests yields feedback rather than an apparent successful blank or partial answer.
Source: choice: the user needs a completed, readable result for the question.

### C-42: The current attempt has a 30-second response deadline.
Observable: In a continuously active view, the response window starts when the view accepts the submission and enters the pending state, including time spent reaching Salesforce. If no answer or earlier terminal failure arrives before 30 seconds have elapsed, the visible terminal result is a timeout.
Source: choice: a short development interaction needs a bounded wait. Suspension of the browser itself can delay display until it runs again.

### C-43: The bot requests a provider output ceiling of 2,048 tokens for each answer.
Observable: At the provider boundary each question requests a 2,048-token output ceiling using a model and operation that accept this limit. The provider may count reasoning or other non-answer tokens toward that ceiling under its own rules.
Source: choice: cap generated answer text to keep the reply suitable for a development interaction.

### C-44: A request sent to Grok uses the configured account for the org.
Observable: Two authorized users can get answers via that provider account without each furnishing a personal API key.
Source: choice: one development-org provider account suffices and makes credential recovery possible for the operator.

### C-45: Bot-use authorization does not confer access to unrelated Salesforce features.
Observable: Granting the bot to a user who lacks access to a Salesforce record or app leaves that record or app unavailable to that user.
Source: implied: U-4 grants use of the bot only.

### C-46: Each open bot view allows at most one pending submission.
Observable: With one question pending, further submit activations in that view do not create another attempt until the first has ended.
Source: choice: one pending question is sufficient for the single-turn view.

### C-47: Separate open views have independent pending states.
Observable: A question waiting in one view does not by itself block submitting from a separate view, including a second tab of the same user's session. Org and provider limits can still apply.
Source: choice: sharing an org or sign-in is insufficient reason to serialize separate views.

### C-48: An admitted attempt causes at most one Grok request.
Observable: During a deliberately repeated click, repeated keyboard activation, or duplicate delivery of the original attempt while its 30-second window is valid, the provider sees at most one request for that attempt.
Source: choice: duplicate handling avoids accidental external charges within the attempt window.

### C-49: The bot does not dispatch an attempt whose 30-second window has expired.
Observable: An original or duplicate request for an attempt received after that attempt's response deadline results in no new request to Grok.
Source: choice: replay after the validity window must not restart work the view has already treated as finished.

### C-50: The bot never automatically resubmits a failed attempt.
Observable: After a local failure, network failure, provider rejection, or timeout, no second provider request for the question originates from the bot without a new deliberate submission.
Source: choice: a retry can incur another charge even if the first result was lost.

### C-51: A deliberate retry is a new attempt.
Observable: After a terminal failure, the user's deliberate retry with identical text is eligible for another provider request subject to the current access, availability, setup, and input rules.
Source: choice: duplicate suppression must preserve intentional retries.

### C-52: The result appears only in the view that originated its attempt.
Observable: Submit distinguishable questions from two tabs or two accounts. Each visible result belongs to its own question even when the results return in reverse order.
Source: implied: U-9 requires a user to get their own reply.

### C-53: A late result cannot change a terminal attempt.
Observable: After a timeout, success, or other failure has become visible for an attempt, subsequent responses for that attempt leave that result untouched, including after a deliberate retry starts.
Source: choice: once an attempt is terminal, later delivery cannot redefine its result.

### C-54: Ending the originating view abandons delivery to the user.
Observable: Close, refresh, or leave the view before a reply arrives. The old result does not appear in a new view. An already-sent request may continue at Grok.
Source: choice: a transient view cannot recover background answers.

### C-55: Each submission is evaluated against the effective bot-use grant at dispatch.
Observable: If revocation takes effect before a question leaves Salesforce, the question does not reach Grok even if the user opened the view earlier.
Source: choice: an open tab cannot extend a revoked grant.

### C-56: Each submission is evaluated against the effective enable state at dispatch.
Observable: A question that has yet to leave Salesforce when disablement takes effect does not reach Grok.
Source: choice: suspension prevents new external work whether or not the view has updated.

### C-57: Changes to bot settings do not recall requests already sent to Grok.
Observable: Disabling, revoking bot use, changing the model, replacing the credential, or rolling back after dispatch does not cancel that request. A result already in progress may appear only in its still-active originating view before the deadline with a valid Salesforce session.
Source: choice: settings control future dispatch, and an external request has already left the org.

### C-58: A newly dispatched question uses the model effective at dispatch.
Observable: Changing the model while an earlier request is in flight causes the next dispatched question to use the new model without changing which model was requested for the earlier question.
Source: choice: the operator's model change applies prospectively.

### C-59: A newly dispatched question uses the credential effective at dispatch.
Observable: Changing the credential while an earlier request is in flight causes the next dispatched question to use the new credential without resending the earlier question.
Source: choice: the operator's credential change applies prospectively.

### C-60: An admitted submission is tied to the text present when it was submitted.
Observable: At the provider boundary the question matches the original submitted text even if the draft later changes. Whether editing is possible while pending is left open because it does not affect submission semantics.
Source: implied: U-1 asks Grok the question the user submitted.

### C-61: Starting a new admitted attempt clears the preceding displayed outcome in that view.
Observable: When a new attempt becomes pending, the previous answer or terminal failure no longer serves as the current result.
Source: choice: a single result area suffices and avoids mistaking an old reply for the new one.

### C-62: A validation refusal does not remove the last successful reply.
Observable: After seeing an answer, the user tries an empty, blank, or over-limit question. The answer remains available alongside the new validation feedback.
Source: choice: refusing bad input has no reason to discard a usable result.

### C-63: A failed activation stays unavailable to the intended audience.
Observable: If installation, configuration, verification-user setup, or live verification fails during U-4, the operator withholds general access. Once verification succeeds, intended users gain access only when their own grants take effect.
Source: choice: partial setup cannot be announced as a working rollout.

### C-64: Repeated activation does not create a second bot entry.
Observable: After completing activation twice for the same org, users still find one bot through navigation.
Source: choice: repeating setup when recovering from partial completion must not create indistinguishable entries.

### C-65: The latest effective operator change to a setting determines that setting for future requests.
Observable: With two successive successful changes to the same setting, new requests use the enable state, model, credential, or per-user grant from the later effective change as applicable.
Source: choice: a delayed save must have an observable resolution. Simultaneous edits require no user-visible ordering guarantee before either takes effect.

### C-66: Salesforce must permit the outbound destination before a question can reach it.
Observable: If the target org has no authorization for outbound access to xAI, a question fails with setup feedback and does not reach the provider.
Source: implied: U-4 is bound by Salesforce's [authorization of authenticated callout destinations](https://developer.salesforce.com/docs/platform/named-credentials/guide/get-started.html).

### C-67: xAI inference requires provider authentication.
Observable: At xAI's inference boundary, a request with a missing or invalid bearer credential cannot yield an answer. A provider authentication denial surfaces as setup or provider authorization feedback.
Source: implied: U-4 is bound by the [xAI inference authentication rule](https://docs.x.ai/developers/rest-api-reference/inference).

### C-68: xAI rejects requests the credential is not permitted to make.
Observable: A key restricted away from the selected Grok model or the inference operation cannot obtain an answer. The user sees setup or provider authorization feedback.
Source: implied: U-8 is bound by [xAI key permissions for endpoints and models](https://docs.x.ai/developers/rest-api-reference/management/auth).

### C-69: The effective xAI usage limits are those of the selected account and model.
Observable: Exceeding either the account and model's request-rate ceiling in requests per second or its throughput ceiling in tokens per minute produces HTTP 429 at the provider and a usage-limit outcome in the bot. The two exact ceilings are unconfirmed until an account and model are selected. The operator can find the values in the xAI Console.
Source: implied: U-3 is bound by [xAI's account-tier and model rate limits](https://docs.x.ai/developers/rate-limits).

### C-70: Apex-backed calls cannot wait beyond Salesforce's callout timeout.
Observable: Where Apex makes the Grok request, a provider that outlasts the configured callout timeout produces timeout feedback. Salesforce defaults to 10 seconds and permits 1 millisecond through 120,000 milliseconds for a single callout. The bot still owes the user the 30-second view deadline in C-42.
Source: implied: U-3 is bound by the [Salesforce per-callout timeout rule](https://developer.salesforce.com/docs/platform/apex-dev/references/apex-dev/apex-callouts-timeouts.html).

### C-71: An Apex transaction out of callout slots cannot start a Grok request.
Observable: If the transaction executing the bot's callout has exhausted its 100 callouts, Salesforce refuses the next callout and the bot attempt cannot report success.
Source: implied: U-3 is bound by the [Salesforce per-transaction callout count](https://developer.salesforce.com/docs/platform/apex-dev/references/apex-dev/apex-gov-limits.html).

### C-72: An Apex transaction out of its cumulative callout time cannot finish a Grok call past that budget.
Observable: If an applicable Apex transaction reaches its 120-second cumulative callout timeout before the bot result is available, Salesforce cannot supply that answer. The bot shows a terminal failure if it was still waiting.
Source: implied: U-3 is bound by the [Salesforce cumulative callout timeout](https://developer.salesforce.com/docs/platform/apex-dev/references/apex-dev/apex-callouts-timeouts.html).

### C-73: A Developer Edition org can refuse bot requests when its concurrent external callouts are full.
Observable: If the target is Developer Edition and 20 callouts to endpoints outside the org's domain are already active, another such Apex callout cannot run concurrently. A refused submission yields feedback under C-40.
Source: implied: U-9 is bound by the [Developer Edition concurrent callout rule](https://developer.salesforce.com/docs/platform/apex-dev/references/apex-dev/apex-callouts-timeouts.html).

### C-74: A Salesforce synchronous Apex concurrency refusal cannot become a successful bot reply.
Observable: If Salesforce denies the Apex transaction because the org is at its long-running synchronous transaction ceiling, the user sees a service failure. The ceiling is one concurrent transaction per 100 applicable licenses, with a floor of 10 and a cap of 50. Only requests past 5 seconds count toward this limit, excluding time spent waiting for HTTP callouts. The exact target ceiling is unconfirmed until the org is identified.
Source: implied: U-9 is bound by [Salesforce's org-level synchronous Apex concurrency limit](https://developer.salesforce.com/docs/platform/apex-dev/references/apex-dev/apex-gov-limits.html).

### C-75: Over-limit Apex callout payloads cannot yield bot success.
Observable: For a Grok request or response beyond 6 MB in synchronous Apex or 12 MB in asynchronous Apex, Salesforce rejects the payload and the user sees failure feedback. These are transport ceilings, separate from C-8 and C-43.
Source: implied: U-2 and U-3 are bound by [Salesforce's Apex callout request and response size ceilings](https://developer.salesforce.com/docs/platform/apex-dev/references/apex-dev/apex-gov-limits.html).

### C-76: A Grok callout cannot start while its Apex transaction has pending Salesforce operations.
Observable: If an Apex transaction already has uncommitted record changes, queued asynchronous work, scheduled work, or a pending email send, then the same transaction cannot send a live Grok request while those operations are pending.
Source: implied: U-1 is bound by the [Salesforce pending-operation callout prohibition](https://developer.salesforce.com/docs/platform/apex-dev/references/apex-dev/apex-callouts-timeouts.html).

### C-77: Salesforce entry-point authorization remains a prerequisite to invoking the bot.
Observable: If Salesforce denies access to the underlying callable entry point, a user with the bot-use grant cannot bypass that denial. In particular, an Apex entry point requiring class access rejects a user whose Salesforce profile and permission sets lack access to that class.
Source: implied: U-4 is bound by [Salesforce entry-point class security when Apex is exposed to users](https://developer.salesforce.com/docs/platform/apex-dev/references/apex-dev/apex-classes-security.html).

### C-78: Salesforce can refuse the installation to an operator without deployment authority.
Observable: The bot cannot be made available by a deployment Salesforce rejects for missing deployment privileges. For a Metadata API deployment the operator needs Modify Metadata Through Metadata API Functions or Modify All Data.
Source: implied: U-4 is bound by [Salesforce Metadata API deployment permissions](https://developer.salesforce.com/docs/platform/api-metadata/references/file-based-calls/meta-deploy.html).

### C-79: An accepted deployment request does not establish availability before Salesforce completes it.
Observable: A queued or in-progress Metadata API deployment cannot be treated as an installed bot. The operator can tell whether Salesforce has completed the deployment successfully.
Source: implied: U-4 is bound by the [asynchronous Salesforce Metadata API deployment lifecycle](https://developer.salesforce.com/docs/platform/api-metadata/references/file-based-calls/meta-deploy.html).

### C-80: Packaging a Salesforce external credential does not authorize the bot in a fresh target org.
Observable: If the bot's external credential is moved through a Salesforce package, installing the package alone provides no working xAI secret. The target org must have a usable credential populated separately.
Source: implied: U-4 is bound by [Salesforce's exclusion of sensitive credential values from packaging](https://developer.salesforce.com/docs/platform/named-credentials/guide/nc-packaging-dev-guide.html).

### C-81: If later shipped with Apex, the bot must pass Salesforce's applicable production test run before production activation.
Observable: A Salesforce production deployment of the bot with failed required Apex tests is rejected and cannot make that deployment active.
Source: implied: the development-org scope in U-4 is subject to [Salesforce's production Apex deployment test requirement](https://developer.salesforce.com/docs/platform/apex-dev/references/apex-dev/apex-testing-best-practices.html) if the bot later moves to production.

### C-82: If later shipped with Apex, the bot must meet Salesforce's applicable production coverage gate.
Observable: Salesforce refuses a production Apex deployment below the coverage gate. For all-org or local test levels the gate is at least 75% overall coverage with coverage of each trigger. For specified or relevant test levels the gate is at least 75% for each deployed Apex class and trigger.
Source: implied: later production deployment is bound by the [Salesforce coverage and test-level rules](https://developer.salesforce.com/docs/platform/api-metadata/references/file-based-calls/meta-deploy.html) and [trigger coverage requirement](https://developer.salesforce.com/docs/platform/api-metadata/references/file-based-calls/meta-deployrecentvalidation.html).

### C-83: A future managed-package listing requires Salesforce security review.
Observable: If a later release is offered as a managed package through Salesforce's marketplace, it cannot be listed before Salesforce approves the required security review.
Source: implied: expansion beyond U-4 into a public listing is subject to [Salesforce marketplace security review](https://developer.salesforce.com/docs/platform/isvforce/guide/security-review-check-listing-readiness.html).

### C-84: Closing a Salesforce view does not erase data held by xAI.
Observable: The provider may retain an already-submitted prompt or response after the Salesforce view closes. The documented default audit retention is 30 days. Teams with Zero Data Retention enabled have no provider disk retention of prompts or responses. The applicable mode is unconfirmed until the account is selected.
Source: implied: U-7 sends content under [xAI's provider retention rules](https://docs.x.ai/developers/faq/security), independently of Salesforce view lifetime.

### C-85: Provider acceptance alone does not constitute a successful answer.
Observable: If the provider reports it has accepted a request for processing but supplies no completed answer yet, the bot does not show success from acceptance alone. In the xAI deferred completion API this distinction is signaled by HTTP 202.
Source: implied: U-1 relies on the [xAI distinction between queued acceptance and a finished inference result](https://docs.x.ai/developers/debugging).

### C-86: Bot lifecycle operations leave pre-existing business records intact.
Observable: Compare existing accounts, contacts, leads, opportunities, cases, and other standard or custom business records before and after installation, use, failure, suspension, and rollback. The bot creates no business records and changes or deletes none of the existing records.
Source: implied: U-6 adds a bot to an org that may already have business data.

### C-87: Unrelated org features keep their pre-existing access settings.
Observable: Before and after bot installation, granting use, suspension, and rollback, the same unrelated apps, records, automations, and administrative functions are available to the same users according to their existing grants.
Source: implied: U-6 adds access to the bot without changing existing access.

### C-88: The bot leaves unrelated org configuration intact.
Observable: Compare unrelated apps and their existing navigation entries, object definitions, page layouts, flows, credentials, and integration definitions across installation, use, suspension, and rollback. The bot introduces its own entry and settings without replacing or removing unrelated configuration.
Source: implied: U-6 preserves existing org features when introducing the bot.

### C-89: Activation does not overwrite an unrelated feature that conflicts with the bot.
Observable: If an existing feature prevents installing the intended bot entry or settings without replacing that feature, activation reports the conflict while leaving the feature usable.
Source: choice: preserving an existing feature takes priority over automatic conflict resolution.

### C-90: Initial rollback removes the bot-specific grants from the failed or rolled-back installation.
Observable: After returning to the pre-bot state, former bot users have no bot-use grant from that installation. In a fresh activation they need a new grant.
Source: choice: rollout authorization should not silently survive rollback of the rollout.

### C-91: Initial rollback clears this installation's provider configuration from the bot.
Observable: A subsequent fresh activation starts with no preselected model or usable xAI credential from that bot installation. A provider credential used by unrelated integrations is not removed or revoked by bot rollback.
Source: choice: new activation requires explicit provider setup while existing integrations retain control of shared resources.

### C-92: The bot applies the same admission rules to direct and in-view submissions.
Observable: Running a submission through the ordinary surface or calling the same exposed entry point directly yields the same eligibility decision for session validity, bot-use authorization, enabled state, required settings, prompt validity, attempt expiry, and replay of the same attempt.
Source: implied: U-2, U-4, U-5, and U-9 apply regardless of how the caller reaches the bot.

### C-93: The bot sends the configured API key only to the authenticated xAI inference endpoint.
Observable: During bot use, no browser response, page source, browser storage, or browser request exposes the configured key. This check excludes the operator entering the key in authorized credential setup. At the external service boundary the configured key is present only as provider authentication.
Source: choice: a bot user needs the answer without gaining the ability to use the shared credential elsewhere.

### C-94: Bot diagnostics omit the configured API key.
Observable: With tracing enabled, bot-generated logs and failure feedback omit the configured key, even when xAI rejects that key or echoes it in a raw error body.
Source: choice: diagnosis does not require disclosure of the secret.

### C-95: Bot diagnostics do not retain question or answer bodies.
Observable: Routine bot logs, audit entries it creates, and error diagnostics contain no question or answer body, including on a failed attempt. This does not govern provider-side retention described in C-84.
Source: choice: troubleshooting requires outcomes without creating a second transcript.

### C-96: Model output is inert in Salesforce.
Observable: A reply containing executable markup, scripts, or instructions to alter Salesforce data is displayed as answer text without executing that content or granting it Salesforce access.
Source: choice: Grok supplies answers, and the request gives it no authority to act.

### C-97: Leaving the bot does not replay the previous submission.
Observable: After a dispatch, refresh the page, go back through browser navigation, or reopen the bot. No new provider request occurs without a new deliberate submission.
Source: choice: view restoration must not silently repeat external work.

### C-98: Sign-out ends bot access in the existing view.
Observable: Signing out or losing the Salesforce session before viewing a pending result does not expose that result after session loss.
Source: implied: U-4 limits use to authenticated Salesforce users.

### C-99: The requested installation provides bot access only in the designated Salesforce development org.
Observable: Activating the bot in the designated org creates no bot entry in any other Salesforce org, including production. Availability in another org would require its own authorized installation.
Source: request

### C-100: A missing or invalid text value is refused before dispatch.
Observable: If a callable submission is missing its prompt, contains null, provides a number, boolean, array, or object instead of text, or contains an unpaired surrogate, the caller receives input feedback without sending a coerced question to Grok.
Source: choice: a direct caller must submit the same plain-text question supported by the view.

### C-101: Model refusal text remains a readable provider answer when xAI returns it as a completed answer.
Observable: If Grok completes a response whose answer text declines the user's question, the bot displays that text. A failed or incomplete provider result remains subject to C-41.
Source: choice: the model's answer can be a refusal, and the completion outcome distinguishes that reply from an integration failure.

### C-102: The bot uses no fallback model for a rejected model selection.
Observable: If the configured model is unknown, retired, or inaccessible to the key, the bot reports a setup or provider authorization failure. The provider receives no automatic request to an alternative model.
Source: choice: the model selected by the operator governs account capability and cost.

### C-103: The bot supplies no direct Salesforce user identifiers to xAI as question context.
Observable: Provider requests contain no automatically added Salesforce user ID, username, email, session credential, org ID, or record ID. Values typed into the prompt by the user are part of the question. Provider-required authentication, model selection, generation controls, and opaque technical metadata may accompany the question.
Source: choice: Salesforce identity is needed for local access control. Identifying Salesforce details serve no purpose in a single-turn answer.

### C-104: A request rejected for exceeding the selected model's context cannot succeed.
Observable: If xAI refuses the request for exceeding the selected model's context window, the bot reports a usage-limit failure without resending a shorter question. The window in tokens is unconfirmed until the model is selected.
Source: implied: U-2 is bound by the [model-specific context window documented by xAI](https://docs.x.ai/developers/models).

### C-105: The operator can tell if initial rollback is incomplete.
Observable: If Salesforce rejects or fails an operation needed to withdraw bot access, the operator sees the failure. The installation counts as rolled back only when C-18, C-90, and C-91 hold.
Source: choice: a failed removal must not be mistaken for recovery to the pre-bot state.

### C-106: The bot displays only user-facing answer content from a completed provider response.
Observable: A completed result containing both an answer and provider metadata displays the model's answer. Provider reasoning, internal identifiers, token counts, raw protocol fields, and action payloads are excluded from the answer because they are not part of the user-facing reply.
Source: choice: U-1 requires the answer and has no use for the provider's execution details.

### C-107: The bot makes no external tool actions on behalf of a question.
Observable: Submitting a question asking for web or X search, code execution, CRM retrieval, a record change, or another tool action causes no action beyond the single text inference request.
Source: choice: external tool execution is outside the authorized scope of a text question.

### C-108: A fresh installation starts without an active Grok model selection.
Observable: Before the operator configures the model, its status shows no selection and enablement alone cannot send a question.
Source: choice: the request gives no model, so the operator chooses a model available to the account.

### C-109: A fresh installation starts without a usable xAI credential.
Observable: Until the operator configures a credential, its status shows that setup is incomplete and enablement alone cannot send a question.
Source: choice: the operator selects the provider account for this org.

### C-110: Configured credential status reports presence independently of provider validity.
Observable: A credential that has been saved but has expired or lost model access can show as configured. An operator verifies current validity by the outcome of C-31.
Source: choice: inspecting settings must not silently perform inference or suggest that a saved value has passed live verification.

### C-111: User-facing failure feedback omits the raw provider error.
Observable: When xAI sends an error body containing diagnostics, request data, or provider stack details, the user sees the appropriate failure category from C-40 without the raw body.
Source: choice: category feedback is enough to recover without passing through provider internals.

### C-112: A completed answer spanning multiple text parts preserves the provider's answer sequence.
Observable: If Grok supplies multiple parts of a single answer, the displayed answer presents those parts in their provider-defined sequence. The visual separator is left open because the user relies on reading the answer in sequence.
Source: implied: U-1 presents the answer Grok supplied, including when the service sends it in parts.

### C-113: A prior installation's unshipped attempts cannot dispatch after initial rollback.
Observable: Hold a submission before it reaches xAI, finish rollback, and activate the bot again. Delivery of the held attempt does not reach xAI even if the user's new grant and the old attempt's 30-second window are both active.
Source: choice: new activation begins a fresh operational lifecycle and cannot resume work from a removed installation.

### C-114: The bot sends prompts to xAI over authenticated HTTPS.
Observable: A provider connection with failed certificate or host authentication yields a service or connection failure. No prompt or credential is sent on an untrusted connection.
Source: choice: the [xAI inference endpoint uses HTTPS](https://docs.x.ai/developers/rest-api-reference/inference), and the question and shared credential must only reach the intended provider.
