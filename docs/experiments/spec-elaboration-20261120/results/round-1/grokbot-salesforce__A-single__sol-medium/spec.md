## Use cases

### U-1: A Salesforce user opens the bot for the first time to get a Grok reply
Flow: The user signs in to the development org, opens the bot, sees where submitted text goes, enters a prompt and submits it. The user sees that the request is pending until a reply appears or the bot reports an outcome.
Source: request

### U-2: A returning user submits another prompt to get a new reply
Flow: The user submits another prompt after a reply, including the option to submit the same text deliberately. The bot returns the reply for the new submission. The user can also reopen the bot later and submit a prompt from a fresh view.
Source: implied: A bot must remain usable after its first interaction.

### U-3: A user corrects invalid input to ask a question
Flow: The user tries to submit an empty prompt, whitespace alone or a non-text item. The bot indicates what input it accepts. The user supplies valid text and can submit it.
Source: implied: A new prompt starts empty, and a user can attempt to submit unsupported input.

### U-4: A user checks the prompt boundary to send as much text as the bot accepts
Flow: The user finds the active prompt limit, submits valid text exactly at the limit and sees it accepted. The user tries a prompt one unit beyond the limit and sees that it must be shortened.
Source: implied: A text prompt can exceed the capacity of the configured service or org.

### U-5: A user handles a refused or incomplete reply to decide what to ask next
Flow: The user submits a prompt. When Grok refuses, the user sees the refusal. When Grok reports that it shortened a reply, the user sees that the available text is incomplete.
Source: implied: A valid submission can produce a service refusal or a reply that ends at a limit.

### U-6: A user recovers from a failed request to finish asking a question
Flow: A submission encounters a rate limit, exhausted usage allowance, unavailable service, invalid reply or timeout. The bot reports the applicable outcome. The user can submit again when the cause is resolved.
Source: implied: The bot depends on an external service that can reject a request or fail to return a usable reply.

### U-7: A user repeats a submit gesture while waiting to avoid sending the same request twice
Flow: The user activates the submit action again before the first request finishes. The bot continues to show the outcome of the original submission.
Source: implied: A slow reply can prompt a user to activate Submit again.

### U-8: Two authorized users submit prompts at the same time to get their own replies
Flow: Two users submit different prompts from their Salesforce sessions. Each sees the reply or failure for their own prompt.
Source: implied: More than one person can use the same development org.

### U-9: A person without bot access attempts to open or invoke it
Flow: A signed-out visitor or signed-in user without bot access attempts to use the bot. Salesforce requires a valid session, or the bot denies access when the signed-in user lacks permission.
Source: implied: An org bot may spend shared service allowance and is subject to the org's access rules.

### U-10: A user reopens the bot after an interruption to resume using it
Flow: The user reloads after an interruption or signs back in after session expiry, opens the bot and submits a prompt. Any result shown for the new submission belongs to that submission.
Source: implied: Users can leave, lose their session or reload while a submission is pending.

### U-11: An org administrator starts the bot to make it available in a development org
Flow: The administrator identifies the target org, uses the setup instructions to configure the Grok connection, grants bot access and verifies readiness with a real prompt. Setup works in an org with zero CRM records. If setup stops partway, the administrator can correct the issue and complete setup.
Source: implied: Creating a bot in a Salesforce development org requires installation, service access and a way to verify that it runs.

### U-12: A service operator provisions or replaces Grok access to keep the connection working
Flow: The Grok account owner supplies an authorized credential and identifies an available Grok text model. If Grok rejects the credential or model, the org administrator can identify the failing prerequisite, correct the setup and verify it with a new submission.
Source: implied: Grok access depends on a valid credential and an available model, both of which can change.

### U-13: An org administrator changes bot access to control who can use it
Flow: The administrator grants access to an existing user and later removes it. Attempts after each change follow the user's effective bot access. A user with bot access alone cannot modify the service connection.
Source: implied: An administrator must be able to restrict use of an org feature that calls a shared external service.

### U-14: An org administrator restores service after an outage to let users submit again
Flow: The administrator identifies the failure, corrects the connection if needed and verifies that a fresh submission can complete after recovery.
Source: implied: An interruption can occur after successful setup.

### U-15: An existing org user continues normal Salesforce work during bot use
Flow: The user opens existing records and uses existing org workflows under the same permissions after the bot is introduced. A user can ask a question from the bot without supplying any record context. Text directing the bot to act on records remains a prompt for a text reply.
Source: implied: Adding the bot to an existing org must coexist with its data, access rules and activity.

### U-16: An org administrator reverses a rollout to restore the previous state
Flow: The administrator follows the rollback instructions. For a first rollout, users return to the org without the bot. If a working bot version preceded the rollout, the administrator restores that version when it is available.
Source: implied: A development deployment may need to be undone.

## Clauses

### C-1: The Grok bot is available from inside the intended Salesforce development org.
Observable: An authorized user opens the working bot from the designated development org.
Source: request

### C-2: Successful answers come from Grok.
Observable: With a working service connection, a submitted prompt produces a reply traceable to a corresponding Grok inference.
Source: request

### C-3: The bot accepts plain-text prompts.
Observable: A user enters a plain-text question and can submit it.
Source: choice: Text supplies the basic prompt-and-reply interaction without requiring additional input modes.

### C-4: The bot displays the Grok text returned for the submitted prompt.
Observable: When Grok supplies answer text, the submitting user can read that text in Salesforce.
Source: implied: U-1 requires a person in the org to receive the answer.

### C-5: A pending submission has a visible pending state.
Observable: With the provider reply delayed, the user can tell that the submission is awaiting an outcome.
Source: implied: U-1 requires the user to distinguish waiting from a failed or missed submission.

### C-6: A completed submission leaves the bot available for another submission.
Observable: After one reply, the user can deliberately resubmit the same valid prompt and receive the outcome of a new request.
Source: implied: U-2 requires repeated use.

### C-7: Each prompt is independent of earlier bot exchanges.
Observable: An inspection of the Grok request for a follow-up finds zero earlier prompts or replies included as conversational context.
Source: choice: Independent exchanges provide repeat use without making conversational memory part of the bot.

### C-8: The bot provides no saved transcript.
Observable: After leaving the bot and opening it again, the user sees zero previous exchanges available to reopen in the bot.
Source: choice: A saved transcript adds a data-retention feature beyond the requested interaction.

### C-9: A prompt with zero non-whitespace characters is invalid.
Observable: Both a zero-character entry and a whitespace-only entry leave the user with an indication that prompt text is required.
Source: implied: U-3 needs a meaningful prompt to submit.

### C-10: Invalid input causes zero Grok inference requests.
Observable: Service activity shows zero requests from an attempt with invalid input.
Source: implied: U-3 and U-4 require invalid submissions to be corrected before consuming service capacity.

### C-11: The bot accepts prompts in text only.
Observable: A user trying to attach an image or file cannot submit that item as prompt input.
Source: choice: Attachments require additional handling beyond the text interaction.

### C-12: The bot makes the effective prompt limit available before submission.
Observable: A user can find the exact numeric maximum for the active setup, with its unit and the counting basis needed to determine whether an entry fits.
Source: choice: A published limit gives users a predictable boundary while allowing the selected Grok model's capacity and the org's applicable request limits to determine that boundary. [Grok model capacities](https://docs.x.ai/developers/models)

### C-13: The effective prompt limit is inclusive.
Observable: An otherwise valid prompt exactly at the published maximum is accepted for submission.
Source: choice: A maximum that includes its stated endpoint has an unambiguous boundary.

### C-14: The bot rejects prompts above the effective prompt limit.
Observable: A prompt one stated unit above the maximum receives feedback that it must be shortened.
Source: implied: U-4 needs an actionable outcome for a prompt the current setup cannot accept.

### C-15: The bot submits the user's prompt without silently shortening it.
Observable: For valid multiline text at the maximum, the Grok request includes the full prompt, including its final line.
Source: implied: U-4 requires an accepted prompt to retain the text the user submitted.

### C-16: The bot conveys a refusal returned by Grok.
Observable: When Grok explicitly refuses a valid submission, the user sees that the prompt was refused.
Source: implied: U-5 requires the user to know whether Grok declined the request.

### C-17: The bot identifies text that Grok reports as truncated.
Observable: When the service returns answer text with a confirmed output-limit truncation, the user can tell that the visible answer is incomplete.
Source: implied: U-5 must distinguish a partial reply from a completed one. [Grok output limits](https://docs.x.ai/developers/model-capabilities/text/best-practices)

### C-18: The bot reports a Grok rate-limit rejection as temporary throttling.
Observable: On a Grok HTTP 429 rate-limit rejection, the user sees that the service is rate limited and can try again when capacity is available.
Source: implied: U-6 follows the Grok API rule that exceeding the applicable team and model rate limit returns HTTP 429. [Grok rate limits](https://docs.x.ai/developers/rate-limits)

### C-19: An administrator can find the active Grok rate limits.
Observable: The operator instructions point to the active team's limits for the selected model, where the administrator can read the exact current requests-per-second and tokens-per-minute values.
Source: implied: U-6 and U-14 depend on limits set by the Grok team and model, which vary with the service tier. [Grok rate limits](https://docs.x.ai/developers/rate-limits)

### C-20: The bot reports exhausted service allowance when Grok identifies that condition.
Observable: On a provider response explicitly indicating exhausted credits or usage allowance, the user sees that the service allowance must be restored before retrying.
Source: implied: U-6 requires an actionable outcome for an exhausted allowance that waiting alone cannot resolve.

### C-21: The bot reports a connection or service failure.
Observable: If the connection fails or Grok returns an HTTP 500–599 response, the user sees that Grok could not be reached or could not complete the request.
Source: implied: U-6 needs an outcome for transport or provider failures. [Grok error guidance](https://docs.x.ai/developers/model-capabilities/text/best-practices)

### C-22: A response without a usable answer or recognized outcome is reported as a failed reply.
Observable: A malformed response or a purported success with zero usable answer text produces an error indication.
Source: implied: U-6 requires the user to distinguish a failed reply from a completed answer.

### C-23: A submission can remain pending for at most 120 seconds.
Observable: With no final response from Grok, the bot leaves the pending state no later than 120 seconds after accepting the submission.
Source: choice: A finite two-minute wait bounds an interactive development-org request and fits within Salesforce's published cumulative timeout ceiling where an Apex callout is used. [Salesforce callout limits](https://developer.salesforce.com/docs/platform/apex-dev/references/apex-dev/apex-callouts-timeouts.html)

### C-24: The bot identifies an expired request as timed out.
Observable: When a request expires without a reply, the user sees a timeout outcome.
Source: implied: U-6 requires the user to recognize a timeout and decide whether to try again.

### C-25: A failed submission leaves the user able to submit again.
Observable: After the failure is shown, the user can submit a valid prompt from the bot once the blocking cause is resolved.
Source: implied: U-6 requires recovery from a failed request.

### C-26: The bot resends a failed prompt only after a new user submission.
Observable: After a request fails, service activity shows zero automatic resend attempts before the user submits again.
Source: choice: Explicit retry lets the user control spending when a failed response may have followed a completed inference.

### C-27: Repeated submit gestures for the same pending submission create only one inference request.
Observable: Rapidly activating Submit twice for the same pending entry produces one corresponding request at Grok.
Source: choice: One request per intended submission prevents the accidental duplicate usage in U-7.

### C-28: A user can see only outcomes belonging to their own submissions.
Observable: With two authorized users submitting distinct prompts at the same time, neither user sees the other user's reply or failure.
Source: implied: U-8 requires attribution and privacy between users.

### C-29: A valid Salesforce session is required to invoke the bot.
Observable: Direct invocation while signed out or after session expiry is denied until the person signs in.
Source: implied: U-9 and U-10 depend on the Salesforce rule that access within an authenticated org session requires a valid session.

### C-30: An authenticated user without effective bot access cannot invoke the bot.
Observable: A signed-in user lacking bot access is denied even when attempting a direct invocation.
Source: implied: U-9 requires authorization at the point of use.

### C-31: A denied invocation causes zero Grok inference requests.
Observable: Service activity shows zero corresponding requests when an attempt is denied for lack of a session or bot access.
Source: implied: U-9 requires denial before the unauthorized visitor can use the shared provider account.

### C-32: A result from an interrupted submission cannot appear as the outcome of a later submission.
Observable: The user reloads while one request is pending and makes a second submission. A delayed reply to the first request never appears as the reply to the second.
Source: implied: U-10 requires fresh use after interruption with correct result attribution.

### C-33: An administrator can identify the target Salesforce development org before applying setup changes.
Observable: The setup instructions let the administrator verify the identity of the target org before installation.
Source: implied: U-11 follows Salesforce's rule that org access is authorized for a specific org. [Salesforce org authorization](https://developer.salesforce.com/docs/platform/sfdx-dev/guide/sfdx-dev-auth.html)

### C-34: Bot setup is scoped to the designated development org.
Observable: The administrator can verify that the rollout applied bot changes only to the designated development org.
Source: implied: The request places the bot in a Salesforce development org.

### C-35: The bot can answer a prompt in an org containing zero CRM records.
Observable: In an otherwise ready development org with zero CRM records, a general text prompt receives a Grok reply.
Source: implied: U-11 requires a new development org to be usable without unrelated business data.

### C-36: The administrator has instructions for establishing initial bot readiness.
Observable: Starting from an authorized development org with available Grok access, the administrator can follow the instructions to the point where a real Grok reply verifies readiness.
Source: implied: U-11 requires a repeatable way to bring the bot into service.

### C-37: An authorized administrator can supply a valid Grok service credential.
Observable: An authorized administrator can set up the connection using a credential that the Grok account owner has authorized for inference.
Source: implied: U-11 and U-12 follow Grok's API authorization rule. [Grok authentication errors](https://docs.x.ai/developers/debugging)

### C-38: An authorized administrator can replace a Grok service credential.
Observable: After replacement and revocation of the old credential, a new submission can complete with the replacement credential.
Source: implied: U-12 requires recovery from a revoked or replaced credential.

### C-39: An authorized administrator can select an available Grok text model.
Observable: An administrator with access to two eligible Grok text models can change the selection and confirm that a new inference uses the newly selected model.
Source: choice: Letting the operator select a supported model avoids pinning a specific release or requiring a code change when availability changes.

### C-40: A missing or refused Grok credential is reported as a connection setup problem.
Observable: With no credential configured, or when Grok identifies a credential rejection or permission denial, the user's attempt indicates that the connection needs administrator attention.
Source: implied: U-12 follows the Grok API authorization rules, including HTTP 401 for missing or invalid authorization and HTTP 403 for insufficient provider access. [Grok error codes](https://docs.x.ai/developers/debugging)

### C-41: An unavailable configured model is reported as a connection setup problem.
Observable: When Grok identifies the selected model as missing or unavailable to the account, the administrator can distinguish the model problem from a user prompt error.
Source: implied: U-12 follows the Grok API model availability rule, which returns HTTP 404 when the specified model cannot be found. [Grok error codes](https://docs.x.ai/developers/debugging)

### C-42: Bot use does not expose the Grok credential.
Observable: A user inspecting the bot page, its browser traffic, replies and error details cannot recover the credential used by the bot.
Source: implied: U-9 and U-12 require the provider credential to remain restricted even when users can submit prompts.

### C-43: An administrator can grant bot access to an existing Salesforce user.
Observable: A user who previously lacked access can invoke the bot once the grant is effective.
Source: implied: U-13 requires access to be managed for existing users.

### C-44: An administrator can revoke bot access from an existing Salesforce user.
Observable: Once revocation is effective, a formerly authorized user's next invocation is denied.
Source: implied: U-13 requires removing access after it is granted.

### C-45: The operator can verify service recovery with a fresh request.
Observable: After restoring a failed connection, the operator can follow the recovery instructions and obtain a fresh Grok reply without reinstalling the bot.
Source: implied: U-14 requires a way to return the installed bot to use after a transient outage or a corrected connection problem.

### C-46: The bot identifies Grok as the recipient of submitted prompt text before submission.
Observable: Before sending a prompt for the first time, a user can tell that the text they submit will be sent to Grok outside Salesforce.
Source: implied: U-1 and U-15 require awareness of where entered text goes.

### C-47: The bot sends no Salesforce business-record data beyond what the user explicitly includes in the prompt.
Observable: A user opens a record containing a distinctive value, then submits a prompt that omits that value. Inspection of the outbound request shows that it contains no data drawn from the record.
Source: choice: A standalone question needs only the submitted prompt, so access to the bot does not become a route for automatic CRM disclosure.

### C-48: Bot interaction leaves Salesforce business records unchanged.
Observable: Before and after use, the org's business records have the same values and membership, even when a prompt asks the bot to create, update or delete a record.
Source: implied: U-15 adds a text bot to an existing org without authorizing it to act on that org's records.

### C-49: Existing Salesforce permissions outside the bot remain effective.
Observable: After setup, access changes and rollback, an existing user has the same access to unrelated records and features as before those bot operations.
Source: implied: U-13 and U-15 require bot access to coexist with existing permissions.

### C-50: Existing Salesforce workflows retain their behavior.
Observable: An existing workflow run with the same input before setup and after setup or rollback yields its usual result.
Source: implied: U-15 and U-16 require existing features to keep working through the bot's lifecycle.

### C-51: Bot setup preserves existing business records.
Observable: Records present before bot setup are still present with the same values after setup, apart from ordinary changes made independently of the bot.
Source: implied: U-15 requires an administrator to carry forward the org's existing data.

### C-52: An administrator can reverse the first bot rollout.
Observable: Following the rollback instructions after an initial rollout returns users to the pre-rollout state in which the bot is unavailable.
Source: implied: U-16 requires a path back when no earlier bot version exists.

### C-53: An administrator can restore a previously available working bot release.
Observable: When an earlier release is available, the administrator follows the rollback instructions and obtains a Grok reply from that release using valid service access.
Source: implied: U-16 requires a path back after replacing a working version.

### C-54: Only a user with bot administration access can change the Grok connection.
Observable: A user who can submit prompts but lacks administration access attempts to replace the credential or change the selected model. The configuration stays the same.
Source: implied: U-12 and U-13 distinguish setup authority from permission to use the bot.

### C-55: An administrator can resume setup after a failed attempt.
Observable: After an invalid setup value prevents readiness, the administrator can correct the value and complete setup in the same development org.
Source: implied: U-11 requires recovery from incomplete setup.

### C-56: The bot reports provider rejections that have no more specific user outcome.
Observable: When Grok rejects an inference with an invalid-argument HTTP 400 or invalid-format HTTP 422 response that does not identify a more specific condition, the user sees that the request failed.
Source: implied: U-6 requires a terminal outcome for unsuccessful provider responses. [Grok error codes](https://docs.x.ai/developers/debugging)

### C-57: Grok reply content cannot execute as part of the Salesforce page.
Observable: A reply containing browser script markup can be viewed without the script running.
Source: implied: U-1 displays content received from outside the Salesforce org.

### C-58: Bot rollback preserves existing business records.
Observable: Records present when rollback begins are still present with the same values after rollback, apart from ordinary changes made independently of the bot.
Source: implied: U-16 requires rollback to reverse the bot rollout while preserving ordinary org activity.

### C-59: The administrator can identify a Grok credential rejection.
Observable: After Grok rejects the configured credential, the administrator can distinguish the credential rejection from a missing model or an invalid prompt.
Source: implied: U-12 requires the administrator to identify which prerequisite needs correction.
