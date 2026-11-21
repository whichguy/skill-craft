## Use cases

### U-1: A Salesforce administrator brings the Grok bot into service in a development org
Flow: The administrator selects the Salesforce development org, makes the bot available in that org, configures xAI access for a Grok text model, and authorizes a user. The administrator verifies readiness by getting a Grok reply from inside the org.
Source: request

### U-2: An authorized Salesforce user asks Grok a question for the first time
Flow: The user signs in to the development org, opens the bot from inside Salesforce, and sees a place to enter a prompt. The user enters text, submits it, and reads Grok's reply in Salesforce.
Source: request

### U-3: A returning Salesforce user asks another question
Flow: The user submits another prompt after a request finishes. Each submission is independent. If the user closes and reopens the bot, there is no saved conversation to resume.
Source: implied: the bot can be used repeatedly after the first question

### U-4: A Salesforce user corrects empty input to submit a question
Flow: The user attempts to submit an empty or whitespace-only prompt. The bot indicates that prompt text is required. The user enters text and submits it.
Source: implied: U-2 requires something for Grok to answer

### U-5: A Salesforce user checks the prompt boundary to send the largest supported input
Flow: The user submits an otherwise valid prompt of 4,000 Unicode code points and the bot accepts it. The user attempts to submit 4,001 and is told the maximum is 4,000. The user shortens the prompt and submits again.
Source: implied: U-2 accepts user-entered text of variable length

### U-6: A Salesforce user checks a pending request and avoids an accidental second submission
Flow: The user submits a prompt and can tell a reply is pending. A second submission in the same open bot view while the first is pending does not start another request. When the request settles, the user can submit again.
Source: implied: a Grok reply to U-2 can take time to arrive

### U-7: A caller without bot access attempts to use it
Flow: A signed-out caller or a signed-in user without bot access tries the bot entry point or attempts to submit directly. The attempt is denied before any prompt reaches Grok.
Source: implied: U-1 and U-2 take place inside a Salesforce org with controlled access

### U-8: A Salesforce user receives a refusal from Grok
Flow: The user submits a valid prompt. If Grok replies that it will not answer, the user sees that reply and can submit a different question.
Source: implied: an answer from Grok in U-2 can be a refusal

### U-9: A Salesforce user hits a usage or capacity limit and tries again later
Flow: The user submits a valid prompt while the provider or org is at a usage limit. The bot identifies a limit as the reason where the service reports one. The user can try the same prompt after capacity or entitlement returns.
Source: implied: U-2 depends on limited Salesforce and xAI capacity

### U-10: A Salesforce user recovers from a failed or incomplete request
Flow: The user submits a valid prompt. The bot indicates whether the request failed, timed out, or returned only part of a reply. If the request failed, the user's prompt is available to correct or resubmit. The user can start another request after the failure.
Source: implied: U-2 depends on an external service that can fail or return an incomplete result

### U-11: An administrator corrects a setup problem or changes bot access
Flow: The administrator learns whether a failed request needs setup attention, updates missing or rejected xAI credentials or selects an available Grok text model, then verifies with a fresh prompt. The administrator can grant or revoke a user's bot access.
Source: implied: the configuration and authorization needed in U-1 can change

### U-12: An administrator restores normal use after an interruption
Flow: After a temporary interruption, the administrator restores the affected service or corrects its configuration. A user opens the bot and submits a fresh prompt using the existing bot access and working configuration.
Source: implied: U-1 needs to remain usable after interruption

### U-13: Existing Salesforce users continue their work while the bot is in use
Flow: Users continue to use existing records, apps, and automations. An authorized bot user may type a question about a Salesforce record, but the bot acts on the submitted text alone. Grok's reply stays in the bot and does not act on the org.
Source: implied: U-1 adds a bot to an org that may already have data and behavior

### U-14: An administrator backs out a bot release
Flow: The administrator reverses the release in the development org. If this was the first release, the bot becomes unavailable. If it replaced a working version, the administrator can restore that version for its existing users. Existing Salesforce work can continue during and after the backout.
Source: implied: U-1 introduces a change to a potentially populated org

## Clauses

### C-1: The Grok bot is available in a Salesforce development org.
Observable: An authorized user opens the bot while signed in to the designated Salesforce development org.
Source: request

### C-2: The bot uses Grok to answer submitted prompts.
Observable: Submit a distinctive prompt and verify that the reply for that request was generated by an xAI Grok model.
Source: request

### C-3: The user can submit a prompt from inside Salesforce.
Observable: Open the bot in the development org, enter a prompt, and submit it from Salesforce.
Source: implied: U-2 places the interaction with the bot in the Salesforce org

### C-4: The bot displays Grok's reply inside Salesforce.
Observable: After a successful request, read the corresponding reply in the bot.
Source: implied: U-2 is complete when the Salesforce user can read the answer

### C-5: The bot accepts text prompts.
Observable: Submit an ordinary written question as text.
Source: choice: text alone delivers the interaction in U-2

### C-6: Each request uses the current prompt independently of other prompts.
Observable: Submit a follow-up containing a reference to an earlier prompt without restating it. The earlier exchange is absent from the context supplied by the bot for the follow-up.
Source: choice: independent requests support repeated use in U-3 without requiring conversation management

### C-7: The bot does not provide saved conversations.
Observable: Close the bot after a completed exchange, then reopen it. The previous exchange is not available to resume in the bot.
Source: choice: U-3 requires the ability to ask again and can be served without a conversation archive

### C-8: Opening the bot does not start a Grok request.
Observable: Open the bot and take no submission action. No prompt is sent to xAI.
Source: implied: U-2 begins with a user choosing what to ask

### C-9: The bot rejects a prompt containing zero non-whitespace characters before inference.
Observable: Attempt to submit the empty string or a prompt made only of spaces, tabs, or line breaks. The bot indicates that text is required and no inference request is issued.
Source: implied: U-4 has no question for Grok to answer

### C-10: The bot enforces a prompt length limit of 4,000 Unicode code points.
Observable: With access and service available, an otherwise valid prompt of exactly 4,000 Unicode code points passes length validation. A prompt of 4,001 is rejected before inference. Whitespace counts toward length.
Source: choice: a finite bound gives U-5 a predictable maximum while allowing a multi-paragraph question

### C-11: The bot tells the user the allowed maximum when rejecting an overlength prompt.
Observable: Attempt to submit a prompt over the limit. The rejection identifies the allowed maximum.
Source: implied: U-5 requires the user to know how far to shorten the prompt

### C-12: The bot indicates when a request is pending.
Observable: Delay the Grok reply and observe a pending state before the result is available.
Source: implied: U-6 needs a way to distinguish waiting from a settled request

### C-13: Each open bot view allows at most 1 pending submission at a time.
Observable: While a submission is pending, attempt a second submission in the same view. Only the first is sent.
Source: choice: one pending submission per view avoids duplicate sends without requiring a queue in U-6

### C-14: The user can submit a new prompt after a request settles.
Observable: After a reply, refusal, or failure, submit another valid prompt from the same open bot view.
Source: implied: U-3, U-8, and U-10 require repeated use

### C-15: The org administrator can grant bot access to a Salesforce user.
Observable: Grant a signed-in Salesforce user bot access, then verify that user can submit a prompt when the service is ready.
Source: implied: U-1 requires authorization for the bot to be used

### C-16: The org administrator can revoke a Salesforce user's bot access.
Observable: Revoke the user's bot access. The user's next attempt to submit is denied.
Source: implied: U-11 requires administrators to withdraw bot access when it is no longer appropriate

### C-17: Bot use requires an authenticated Salesforce session in the designated development org.
Observable: Attempt to open or invoke the bot without such a session. The caller must authenticate to use it, and the attempt produces no xAI inference request.
Source: implied: U-7 follows the [Salesforce session authentication rule](https://developer.salesforce.com/docs/platform/api/guide/sforce-api-concepts-security.html) for access within the org

### C-18: An authenticated user without bot access is denied inference.
Observable: Attempt to submit as a signed-in user lacking bot access, including via a direct invocation. The caller is denied and no xAI inference request is issued.
Source: implied: U-7 follows the [Salesforce feature access rule](https://developer.salesforce.com/docs/platform/api/guide/sforce-api-concepts-security.html) that access is subject to the user's permissions

### C-19: An ordinary bot user cannot change the bot's integration settings.
Observable: Attempt to change xAI access or model settings using only bot user access. The change is denied.
Source: implied: U-11 requires configuration changes to be restricted to authorized operators

### C-20: The administrator can configure the bot's xAI credential for the development org.
Observable: In an unconfigured deployment, supply an xAI credential with access to inference for the selected model. Subsequent valid submissions can authenticate to xAI.
Source: implied: U-1 depends on the [xAI API authorization rule](https://docs.x.ai/developers/rest-api-reference/management/auth) requiring a valid key with the applicable permissions

### C-21: The administrator can select an available Grok text model.
Observable: Configure a different supported Grok text model available to the credential. A subsequent inference uses that model.
Source: choice: U-11 can recover from changes to model availability by selecting a supported model without replacing the bot

### C-22: The administrator can replace the xAI credential.
Observable: Replace an expired, revoked, or otherwise rejected credential with a valid one. The next new request uses the replacement.
Source: implied: U-11 must recover when the original xAI credential stops working

### C-23: Bot users can submit prompts without handling the xAI credential.
Observable: As an authorized bot user, send a prompt using only Salesforce sign-in and bot access.
Source: choice: org-managed xAI access gives U-2 a single sign-in path

### C-24: The bot keeps the xAI credential out of user-visible output.
Observable: Inspect the bot view, browser traffic, replies, and error messages during successful and failed requests. None exposes the xAI credential.
Source: implied: U-1 supplies a provider credential whose disclosure would let another caller use the integration's xAI access

### C-25: Missing bot configuration is reported as a setup problem.
Observable: Try to use a deployment with an unset required integration setting. The user sees that the bot needs setup, and no purported Grok reply appears.
Source: implied: U-11 must distinguish unfinished setup from a prompt failure

### C-26: The operator can distinguish xAI authorization failure from a rejected prompt.
Observable: Use an invalid or unauthorized credential. When xAI reports HTTP 401 or 403, the operator can determine that provider access needs attention.
Source: implied: U-11 follows the [xAI API authorization error rules](https://docs.x.ai/developers/debugging)

### C-27: The operator can identify an unavailable configured model when xAI reports it.
Observable: Configure a model that is no longer available to the integration. When xAI reports that model as missing, the operator can identify model availability as the problem.
Source: implied: U-11 follows the [xAI API error rule](https://docs.x.ai/developers/debugging) under which HTTP 404 can identify a missing model

### C-28: The bot displays a refusal that Grok returns as a valid reply.
Observable: When Grok returns a readable refusal, the user can read it in the bot without it being replaced by a service error.
Source: implied: U-8 requires the user to receive Grok's actual answer

### C-29: The bot reports xAI throttling as a usage limit.
Observable: When xAI returns HTTP 429, the user sees that a usage limit was reached and can try again later.
Source: implied: U-9 follows the [xAI rate-limit rule](https://docs.x.ai/developers/rate-limits) that HTTP 429 signals a provider limit

### C-30: Bot inference is subject to the active xAI rate limits for the configured model and credential.
Observable: Use the numerical request and token limits shown in the xAI team and API-key configuration for the deployed integration. If a request exceeds an active limit, xAI can reject that request.
Source: implied: U-9 inherits the [xAI rate limits](https://docs.x.ai/developers/rate-limits) and [xAI API-key limits](https://docs.x.ai/developers/rest-api-reference/management/auth), whose numeric values vary by configuration

### C-31: The bot identifies a reported capacity or spending restriction that prevents a reply.
Observable: Submit a prompt while Salesforce or xAI denies processing with a reported capacity or spending restriction, such as exhausted xAI spending allowance. The bot reports the restriction as the reason the request could not complete.
Source: implied: U-9 requires users to distinguish a reached limit from a bad prompt

### C-32: The bot tells the user when the service rejects the prompt itself.
Observable: Submit a prompt that passes local validation but is explicitly rejected as input by the service. The bot indicates that the prompt was rejected.
Source: implied: U-10 needs to distinguish an input the user can revise from an outage

### C-33: The bot reports a service failure when it cannot obtain a usable reply.
Observable: Make the service unreachable, return an HTTP 5xx error, or return an empty or unrecognizable result. The user sees a failure instead of a purported Grok answer.
Source: implied: U-10 requires a clear outcome when the dependency cannot answer

### C-34: The bot resolves a request as timed out if no completed outcome is available within 120 seconds of submission.
Observable: Leave a request unresolved through the 120-second boundary. The bot reports a timeout by that boundary.
Source: choice: U-10 needs a finite wait, with a ceiling that allows a slow inference

### C-35: A reply arriving after the bot reports a timeout does not replace the outcome of a later request.
Observable: Time out a request, submit a different prompt, and then let the first reply arrive. The later request remains associated with its own outcome.
Source: implied: U-10 requires safe resubmission after an unresolved request

### C-36: The bot identifies a partial reply when the provider reports that generation was cut short.
Observable: Return partial text accompanied by a provider truncation indication. The bot identifies the reply as incomplete.
Source: implied: U-10 follows the [xAI incomplete-generation rule](https://docs.x.ai/developers/model-capabilities/text/best-practices) so the user can recognize a reply cut short by a provider limit

### C-37: A failed submission leaves the prompt available for correction or resubmission in the open bot view.
Observable: Trigger a request failure and recover the submitted text in the same view without retyping it.
Source: choice: U-10 needs a retry path that avoids losing the user's work

### C-38: A failed submission is not automatically resubmitted by the bot.
Observable: Cause a request to fail, including with HTTP 429 or a timeout. Observe that no further inference attempt is made for it until the user submits again.
Source: choice: user-initiated retries avoid unexpected repeat usage or charges in U-9 and U-10

### C-39: The bot communicates the transfer of submitted text to xAI before the user submits.
Observable: Open the bot for the first time and find that prompt text will be sent to xAI before sending a prompt.
Source: choice: U-2 crosses an org boundary, so users need to know who will receive what they submit

### C-40: A bot request does not retrieve Salesforce business records.
Observable: Ask about a record using an identifier without supplying its field values. The bot does not look up that record to answer.
Source: choice: U-13 requires a prompt-and-reply bot without requiring Salesforce record integration

### C-41: The bot does not automatically transfer Salesforce business data to xAI.
Observable: Submit a prompt while viewing a Salesforce record. The record, its fields, and other business data are absent from the outbound request unless the user supplied them in the prompt.
Source: implied: U-13 relies on the user controlling the business content shared for inference

### C-42: Bot use does not change Salesforce business records.
Observable: Submit a prompt requesting a record change, then check the affected record. The bot has made no change.
Source: implied: U-13 adds a reply feature without authorizing Salesforce record actions

### C-43: Provider replies do not execute instructions in the user's Salesforce session.
Observable: Have the model return text containing executable markup or instructions to act. Reading the reply does not execute it.
Source: implied: U-13 requires Grok's output to be shown as a reply without acting on the org

### C-44: One Salesforce user cannot read another user's prompts or replies through the bot.
Observable: Submit as one user. As another user, open the bot or attempt to retrieve that exchange and receive none of its contents.
Source: implied: U-2 and U-13 use an authenticated org without granting access to other users' interactions

### C-45: Bot deployment leaves pre-existing Salesforce business data intact.
Observable: Compare existing business records before and after deployment. The same records retain their pre-existing values.
Source: implied: U-13 must continue with the data already in the org

### C-46: Bot deployment preserves pre-existing access to unrelated Salesforce features and data.
Observable: Compare what existing users can see and do in unrelated features before and after the bot is introduced. Their effective access is unchanged.
Source: implied: U-13 retains the [Salesforce object, field, and record access rules](https://developer.salesforce.com/docs/platform/salesforce-record-access-under-the-hood/guide/uth-intro.html) already in force

### C-47: Bot deployment preserves existing unrelated Salesforce automations.
Observable: Run an existing Salesforce workflow before and after bringing the bot into service. Its configured triggers and outcomes stay the same.
Source: implied: U-13 adds the bot alongside existing workflows

### C-48: Bot deployment preserves the availability of unrelated Salesforce apps.
Observable: Open an existing unrelated app before and after introducing the bot. It remains available to its existing users.
Source: implied: U-13 adds the bot alongside existing apps

### C-49: The bot resumes accepting fresh requests after service is restored.
Observable: Interrupt the integration temporarily, restore its dependencies, and submit a new prompt from an authorized account. The new request can complete using the existing valid bot configuration and user access.
Source: implied: U-12 requires recovery on the installed release

### C-50: A bot release can be backed out in the development org.
Observable: Apply the operator's backout procedure. For a first release, the bot no longer accepts prompts. For a replacement release, the previously working bot behavior can be restored to existing authorized users.
Source: implied: U-14 must restore the preceding availability of the bot

### C-51: Backout preserves Salesforce business records created or changed independently of the bot.
Observable: Create or update an unrelated record after the bot release, then back out the release. The record retains the independent changes.
Source: implied: U-14 must restore the bot release without rolling back ongoing Salesforce work

### C-52: Introducing the bot does not change a production Salesforce org.
Observable: Bring the bot into service in the designated development org. No production org receives bot-related changes.
Source: implied: the request scopes the bot to a Salesforce development org

### C-53: The chosen Grok model's context limit applies to bot inference.
Observable: Consult the configured model's published context limit in tokens. If xAI reports that an otherwise valid request exceeds that limit, the bot identifies the input as too large for the model.
Source: implied: U-5 and U-9 inherit the [xAI model context limit](https://docs.x.ai/developers/advanced-api-usage/context-compaction), whose numerical value depends on the selected model

### C-54: The bot does not silently shorten the prompt submitted for inference.
Observable: Submit a valid prompt with distinctive text at the end. Inspect the request received by xAI and confirm that it includes the end of the submitted prompt.
Source: implied: U-5 asks Grok to answer the submitted question in full
