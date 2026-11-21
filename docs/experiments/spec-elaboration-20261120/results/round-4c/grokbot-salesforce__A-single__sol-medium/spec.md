## Use cases

### U-1: A deployment operator puts the Grok bot in the Salesforce development org for evaluation
Flow: The operator identifies the intended Salesforce development org. After installation, they verify that the bot is available in that org. If the destination is missing, ambiguous, or a production business org, deployment stops before changes are made.
Source: request

### U-2: A Salesforce user opens the bot for the first time to ask Grok a question
Flow: The user signs in to the development org, opens its bot entry point, enters a text prompt, and submits it. They see that the prompt is pending if the answer is still being generated. When Grok answers, they read its reply within Salesforce.
Source: request

### U-3: A returning user submits more prompts to keep using the bot
Flow: The user submits a different prompt after an answer, then deliberately submits the same prompt again. Each submission can receive its own result. If the user activates submit twice while the same send is pending, the extra activation does not generate another send. If two users send prompts at the same time, each sees the result for their own submission.
Source: implied: repeated and concurrent use of the bot requested in U-2

### U-4: A user corrects an empty or invalid submission to send a question
Flow: The user tries to submit an empty field, whitespace alone, or an unsupported input instead of text. The bot indicates that it needs a text prompt. The user supplies valid text and can send it.
Source: implied: U-2 requires a prompt that Grok can answer

### U-5: A user sends a prompt at the length boundary to learn what the bot accepts
Flow: The user finds the active prompt limit, submits valid text exactly at that limit, then tries a prompt one unit longer. The first is eligible for processing. The second is rejected with the limit available to the user. If Grok itself rejects an input for exceeding the model context limit, the user is told to shorten it.
Source: implied: U-2 is bounded by the amounts the deployed bot and Grok can process

### U-6: A user without current Salesforce access attempts to use the bot
Flow: A signed-out user opens the entry point. A signed-in user without bot access tries to submit. A previously authorized user submits from a page whose Salesforce session has expired. The attempts are blocked until the corresponding access requirement is met.
Source: implied: the bot in U-2 is used inside a Salesforce org

### U-7: A user receives a Grok refusal and submits a different question
Flow: The user sends a prompt that Grok refuses to answer. The user can tell Grok declined the request, then sends a different prompt from the bot.
Source: implied: the response in U-2 may be a provider refusal

### U-8: A user hits an active service limit and resumes when service permits
Flow: The user sends a valid prompt while the applicable xAI request or token rate limit is exhausted, or while the provider account cannot run inference because its allowance is exhausted. The user sees the relevant problem. They can submit again after capacity returns or the operator restores the allowance.
Source: implied: the provider used in U-2 applies account and model limits

### U-9: A user encounters an interrupted or incomplete response and recovers
Flow: The user sends a prompt during a connection failure, provider outage, or excessively slow response. They see that the request did not complete and can reuse the submitted text. An unexpected provider rejection or a response with no usable reply is reported as unsuccessful. If Grok returns a reply marked incomplete, any portion shown is identifiable as incomplete. Once service is available, the user can submit again. A late reply from a timed-out request does not replace the result of the newer request.
Source: implied: the external service used in U-2 may fail to return a complete result

### U-10: An operator configures access to start the bot
Flow: The operator locates the setup instructions, supplies an authorized Grok credential, confirms the enabled model and applicable limits, and grants a Salesforce user access. The user verifies readiness by submitting a prompt from the org. A missing credential, a rejected credential, or an unavailable model gives the operator enough information to correct the setup without showing the secret to users.
Source: implied: the bot in U-1 needs authorized Salesforce and Grok access to serve U-2

### U-11: An operator restores service after a configuration problem or interruption
Flow: The operator corrects the applicable configuration or replaces a revoked credential. After an ordinary service interruption, the bot can resume with its existing valid setup. After recovery, the user reopens the bot if needed and submits a fresh prompt using the current configuration. A prior interrupted request is not silently resent.
Source: implied: the setup in U-10 must remain usable after interruption or credential changes

### U-12: An existing Salesforce user keeps working with records and workflows during bot use
Flow: The user opens their existing records or automations before and after using the bot. Records, access, and unrelated behavior remain as before. Having a record open does not add its data to a prompt. Asking Grok to carry out a Salesforce change leaves the record untouched.
Source: implied: the bot in U-1 is added to an org that may already contain data and workflows

### U-13: An operator backs out the bot deployment to restore the previous org behavior
Flow: The operator follows the rollback procedure. After a first-install rollback, users can no longer use the new bot. After a rollback of an update, users can use the prior version with its prior behavior when its dependencies are valid. Existing Salesforce data, unrelated automation, and work performed outside the bot are retained.
Source: implied: the operator may need to reverse the org change in U-1

## Clauses

### C-1: The Grok bot is deployed in the designated Salesforce development org.
Observable: The operator signs in to the designated Salesforce development org and verifies that it contains the deployed bot.
Source: request

### C-2: Deployment requires an unambiguous development-org destination.
Observable: If the operator cannot identify a specific development org, deployment stops before any org is modified.
Source: implied: U-1 and the request's confinement to a Salesforce development org

### C-3: Deployment leaves production business orgs untouched.
Observable: A deployment attempt aimed at a production business org makes no changes there.
Source: implied: U-1 specifies a development org as the destination. [Salesforce org development model](https://developer.salesforce.com/docs/platform/sfvscode-extensions/guide/orgdev.html)

### C-4: An authorized user can open the bot from inside Salesforce.
Observable: The user finds an entry point in the designated org that opens the bot.
Source: implied: U-2 takes place in the Salesforce development org

### C-5: The bot accepts user-entered text prompts.
Observable: The user can enter and submit an eligible text prompt from the bot.
Source: choice: a text prompt is sufficient for the unspecified interaction in U-2

### C-6: The bot uses Grok to generate the answer.
Observable: The operator can verify that a successful bot submission is answered by an xAI Grok model.
Source: request

### C-7: The bot presents Grok's reply within Salesforce.
Observable: The user reads the reply to their successful submission without leaving the Salesforce bot.
Source: implied: U-2 must deliver the result of the requested bot interaction

### C-8: The user can recognize a pending submission.
Observable: While an accepted submission is awaiting its result, the user can tell that processing is in progress.
Source: implied: U-2 can include a wait for Grok

### C-9: The bot accepts another eligible prompt after a completed request.
Observable: After seeing a result, the user can submit a subsequent eligible prompt, including text identical to the previous prompt.
Source: implied: U-3 includes repeated use

### C-10: A repeated activation of the same pending send does not duplicate it.
Observable: Activating submit twice for the same pending send produces one Grok submission for that send.
Source: choice: an extra activation during a pending send is treated as accidental to avoid duplicate inference usage in U-3

### C-11: Each result is delivered to the user who submitted the corresponding prompt.
Observable: When two users submit concurrently, each sees only their own result, including if the results arrive in reverse order.
Source: implied: U-3 shares one org across users

### C-12: A prompt containing zero non-whitespace characters is rejected before inference.
Observable: A submission containing zero characters or only whitespace receives input feedback and generates zero Grok requests.
Source: implied: U-4 needs text for Grok to process

### C-13: Unsupported input is rejected before inference.
Observable: If non-text input is attempted, the bot indicates that it accepts text and generates zero Grok requests for that input.
Source: choice: U-4 relies on text as the supported input so the bot needs no other input modes

### C-14: The active prompt length limit is discoverable before submission.
Observable: The user can find the exact maximum as a positive integer with its counting unit in the deployed bot or its accompanying usage instructions.
Source: choice: U-5 needs a verifiable boundary, whose value can follow the active model and org

### C-15: Prompt length alone does not exclude valid text exactly at the active limit.
Observable: A valid prompt measured at the exact published maximum proceeds past the bot's length validation.
Source: choice: an inclusive boundary makes the published maximum in U-5 usable

### C-16: The bot rejects prompts beyond its active length limit before inference.
Observable: A prompt one counting unit above the published maximum produces a length error with zero Grok requests.
Source: choice: rejecting text beyond the published maximum lets the user shorten it without losing submitted text to silent truncation in U-5

### C-17: The bot communicates a Grok rejection caused by the model context limit.
Observable: When Grok rejects the request for excessive input length, the user sees that the prompt needs to be shortened.
Source: implied: U-5 encounters the configured Grok model's context window rule. [xAI model documentation](https://docs.x.ai/developers/grok-4-7)

### C-18: Bot submission requires a valid Salesforce session.
Observable: A signed-out user cannot send a prompt to Grok through the Salesforce bot.
Source: implied: U-6 is subject to the Salesforce org login requirement. [Salesforce login rules](https://help.salesforce.com/s/articleView?id=000212767&language=en_US&type=1)

### C-19: The bot honors the Salesforce session expiration in effect for the user.
Observable: When the applicable org or profile session expires, the user cannot submit another prompt until Salesforce restores an authenticated session.
Source: implied: U-6 is subject to Salesforce session timeout rules. [Salesforce session settings](https://help.salesforce.com/s/articleView?id=sf.admin_sessions.htm&language=en_US)

### C-20: Bot submission requires authorization in the Salesforce org.
Observable: A signed-in user without bot authorization cannot invoke Grok through the bot, including through a directly opened bot entry point.
Source: implied: U-6 must respect permissions in the shared org

### C-21: Users are told when Grok declines their request.
Observable: When Grok returns a refusal, the user sees an outcome identifying the request as declined.
Source: implied: U-7 must surface Grok's response to the submission

### C-22: The bot reports when xAI throttles inference.
Observable: An xAI rate-limit response with status 429 results in a user-visible rate-limit outcome.
Source: implied: U-8 is subject to the xAI rule that exceeding the applicable request or token rate cap returns 429. [xAI rate limits](https://docs.x.ai/developers/rate-limits)

### C-23: The operator can determine the provider rate caps that apply to the bot.
Observable: Given the configured model and xAI account, the operator can obtain the exact active requests-per-second and tokens-per-minute caps from the provider's account settings.
Source: implied: U-8 is subject to model- and account-tier-specific xAI caps. [xAI rate limits](https://docs.x.ai/developers/rate-limits)

### C-24: The bot reports when the provider identifies an exhausted inference allowance.
Observable: When xAI explicitly reports insufficient credits or an exhausted spending allowance, the bot identifies that the provider allowance prevented the submission from completing.
Source: implied: U-8 requires the provider allowance problem to be identifiable before service can be restored. [xAI API quickstart](https://docs.x.ai/developers/quickstart)

### C-25: A connection failure produces an unsuccessful outcome.
Observable: If the connection fails before a reply arrives, the user sees that the request failed.
Source: implied: U-9 needs a recognizable outcome when the provider cannot be reached

### C-26: A provider service failure produces an unsuccessful outcome.
Observable: When xAI responds with a server error in the 500–599 range, the user sees a service failure for the submission.
Source: implied: U-9 needs a recognizable outcome when the provider is unavailable

### C-27: The operator can determine the active request deadline.
Observable: The deployed bot or its operating instructions give the exact positive deadline in seconds, measured from acceptance of the submission.
Source: choice: U-9 needs a finite deadline, whose duration can follow the org's interactive needs

### C-28: A request without a terminal result by its deadline ends in a timeout.
Observable: If no terminal result arrives by the active deadline, the user sees that the submission timed out.
Source: implied: the request deadline in U-9 bounds how long the user waits

### C-29: A provider response without a usable answer or refusal produces an unsuccessful outcome.
Observable: If a malformed response or a response with zero usable reply characters contains neither a refusal nor an answer, the user sees a failure.
Source: implied: U-9 requires a recognizable outcome when no usable reply is returned

### C-30: Shown text from a reply that Grok marks incomplete is identifiable as incomplete.
Observable: If the bot displays text from an incomplete response, the user can tell the displayed reply is incomplete.
Source: implied: U-9 must distinguish a partial reply from a complete one. [xAI text response guidance](https://docs.x.ai/developers/model-capabilities/text/best-practices)

### C-31: The user can reuse their submitted text after a failed request in the open bot.
Observable: Following a failed request, the user can reuse the submitted text without retyping it while the bot remains open.
Source: choice: retaining the current text is enough to support recovery in U-9 without requiring saved conversations

### C-32: A failed or declined request permits a new submission once its cause is resolved.
Observable: After correcting the input, restoring access, or waiting for service to recover as applicable, the user can send an eligible prompt from the bot.
Source: implied: U-4, U-6, U-7, U-8, and U-9 include recovery

### C-33: An operator can locate the steps required to enable the bot.
Observable: The operator can find setup instructions covering the bot's Salesforce entry point, access, and Grok prerequisites.
Source: implied: U-10 must be possible for an operator starting with the deployed bot

### C-34: Grok inference requires valid provider authentication.
Observable: A request lacking a credential valid for the selected Grok model cannot obtain a Grok reply.
Source: implied: U-10 is subject to xAI inference authentication rules. [xAI inference authentication](https://docs.x.ai/developers/rest-api-reference/inference)

### C-35: The operator can supply the Grok credential for the org.
Observable: An operator with the applicable setup authority can install a valid credential for bot inference without asking each Salesforce user for a provider credential.
Source: choice: supplying the credential at the org level is sufficient for the shared bot in U-10

### C-36: The installed Grok credential is kept out of user-visible surfaces.
Observable: Inspecting the bot page, its browser requests, and its user-visible errors does not expose the configured credential.
Source: implied: U-10 uses an xAI secret that must remain confidential. [xAI API security guidance](https://docs.x.ai/developers/faq/security)

### C-37: The operator can identify the Grok model used for inference.
Observable: The operator can determine the exact model identifier in use for the development org.
Source: choice: U-10 needs an identifiable supported Grok model, with the particular identifier left open

### C-38: The operator can grant bot access to an eligible Salesforce user.
Observable: After the operator grants bot access, the user can invoke it with a valid Salesforce session.
Source: implied: U-10 must make the deployed bot usable by an authorized user

### C-39: The operator can revoke a user's bot access.
Observable: After the operator revokes bot access, the user cannot start another Grok request, even from an already open page.
Source: implied: the operator controls access in U-10

### C-40: Missing provider configuration produces a setup outcome.
Observable: If the required Grok credential has never been configured, the user sees that setup is required when attempting to submit.
Source: implied: U-10 can start with an unconfigured installation

### C-41: Rejected provider authorization is diagnosable by the operator.
Observable: When xAI reports missing or invalid authorization with status 401 or forbidden access with status 403, the operator can identify the provider access problem.
Source: implied: U-10 is subject to xAI's authentication and authorization error rules. [xAI API error reference](https://docs.x.ai/developers/debugging)

### C-42: A provider-reported unknown or unavailable model is diagnosable by the operator.
Observable: When xAI identifies the configured model as unknown or unavailable, the operator can identify that the model is the problem.
Source: implied: U-10 requires an available Grok model. [xAI API error reference](https://docs.x.ai/developers/debugging)

### C-43: The operator can replace a rejected or revoked Grok credential.
Observable: After the operator replaces a rejected or revoked credential with a valid one, a fresh eligible prompt can receive a Grok response.
Source: implied: U-11 requires recovery from credential rejection or revocation

### C-44: An interrupted submission is not automatically replayed when the bot reopens.
Observable: After interruption, reopening the bot generates zero new Grok requests for the interrupted submission by itself.
Source: choice: a fresh user submission after recovery avoids duplicate usage when the original outcome is unknown in U-11

### C-45: The bot does not automatically include Salesforce record data in Grok input.
Observable: With an existing record open in Salesforce, submitting text that omits the record's data sends none of that record's fields or attachments to Grok.
Source: choice: user-supplied prompt text is sufficient for U-2, which does not require CRM grounding in U-12

### C-46: A bot interaction does not mutate Salesforce business records.
Observable: A user asks for an existing record to be edited and sees that the record has not changed as a result of the bot interaction.
Source: choice: the requested bot supplies responses, and Salesforce business actions are outside the interaction chosen for U-12

### C-47: Installing the bot preserves existing Salesforce records.
Observable: Comparing business records before and after installation shows that deployment has not created, altered, or deleted those records.
Source: implied: U-12 requires the existing org data to remain usable

### C-48: Bot setup preserves access to unrelated Salesforce functionality.
Observable: For each affected user, access to existing objects, fields, records, and unrelated apps is the same after bot setup as before it.
Source: implied: U-12 must preserve existing Salesforce access rules

### C-49: The bot preserves the behavior of unrelated Salesforce automation.
Observable: An existing workflow or automation outside the bot still produces its prior observable result for the same triggering inputs after the bot is installed or used.
Source: implied: U-12 adds bot behavior alongside existing automation

### C-50: First use does not require a Salesforce data migration.
Observable: A Salesforce development org with zero business records or an org already populated with records can use the bot after its own setup, with no prerequisite record migration.
Source: implied: U-2 and U-12 use text prompts independently of the amount of CRM data present

### C-51: The bot does not create saved Salesforce conversation history.
Observable: After a user closes the bot and opens it again, the earlier interaction is not available as a saved transcript in Salesforce.
Source: choice: U-2 and U-3 require prompt and reply interaction, with no need to introduce durable Salesforce conversation data

### C-52: The operator can locate a bot rollback procedure.
Observable: The operator can find instructions for reversing the bot deployment, including the first-install case.
Source: implied: the operator in U-13 needs a way to restore the prior org behavior

### C-53: Rolling back the first installation removes the new bot from use.
Observable: After the operator reverses the first deployment, the newly installed bot cannot be opened or invoked in the org.
Source: implied: U-13 restores the behavior that existed before the initial installation

### C-54: Rolling back a bot update restores the prior bot behavior.
Observable: When an earlier bot deployment existed, reversing the update restores that version's observable behavior using its valid dependencies.
Source: implied: U-13 must allow return to the version before the change

### C-55: Rollback preserves Salesforce business data present when rollback begins.
Observable: Existing business records, including independent work performed after deployment, retain their values after rollback.
Source: implied: U-13 reverses the bot deployment without undoing existing Salesforce work

### C-56: Rollback preserves unrelated Salesforce configuration present when rollback begins.
Observable: Unrelated apps, access settings, and workflows still behave as configured immediately before rollback.
Source: implied: U-13 reverses the bot's changes without reverting unrelated org work

### C-57: An otherwise unclassified provider rejection produces an unsuccessful outcome.
Observable: When xAI rejects an eligible submission with an error the bot does not recognize, the user sees that their request failed.
Source: implied: U-9 requires a recognizable outcome even when xAI rejects the request for an unexpected reason

### C-58: A late result from a timed-out request does not replace a subsequent result.
Observable: After a timeout, the user submits a new prompt and receives its own result even if the timed-out request's reply reaches the bot later.
Source: implied: U-9 permits a new submission after the attempted request timed out

### C-59: Bot service can resume after an interruption using its existing valid setup.
Observable: When service returns after an interruption, an authorized user can submit a fresh prompt without the operator having to repeat setup.
Source: implied: U-11 must recover from an interruption that did not invalidate setup

### C-60: A valid prompt reaches Grok with its text intact.
Observable: For a valid prompt containing punctuation, line breaks, or non-ASCII characters, the text Grok receives preserves those characters.
Source: implied: U-2 expects Grok to answer the question the user submits
