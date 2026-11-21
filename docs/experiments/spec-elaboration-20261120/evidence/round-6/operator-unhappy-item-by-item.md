# Q-shiploop-spec-lenses against P-shiploop-spec, round-6, item by item (operator, unhappy items)

## sonnet-high, judge claude-opus-5-5: 8 covered by Q-shiploop-spec-lenses and not by P-shiploop-spec; 2 the other way
+ grokbot-salesforce N-16 [unhappy] P-shiploop-spec: partial; P-shiploop-spec in round-5: covered; Q-shiploop-spec-lenses: covered
    item: A partial or truncated answer, and what the user sees when an answer never arrives.
    P-shiploop-spec (R-7, R-8.4): INVALID_RESPONSE | HTTP 200 with `{"choices":[]}`, with an empty content string ... A pending state never persists past the service's return
    Q-shiploop-spec-lenses (R-2 B1; R-6): Reply with `finish_reason` meaning length-truncated: the reply is shown and marked "(reply was cut off)".
+ grokbot-salesforce N-22 [operator] P-shiploop-spec: partial; P-shiploop-spec in round-5: partial; Q-shiploop-spec-lenses: covered
    item: An administrator can turn the bot off, change the model, and see failed requests.
    P-shiploop-spec (R-9, NFR-8): model ID, system prompt, maximum prompt characters, remembered exchanges, callout timeout and optional maximum output tokens are administrator-editable configuration
    Q-shiploop-spec-lenses (R-8; R-12): `Enabled__c` (checkbox, default true), `Model__c` ... (c) Each failed request writes one log line (R-9 fields) retrievable in Setup debug logs
+ gym-waitlist N-9 [unhappy] P-shiploop-spec: partial; P-shiploop-spec in round-5: covered; Q-shiploop-spec-lenses: covered
    item: Payment for a promoted booking: when it is taken and what happens when it fails.
    P-shiploop-spec (R-10, D-4): Exclusions: payments, credits ... Any existing rule of these kinds still applies at promotion (D-4); the waitlist adds none of its own.
    Q-shiploop-spec-lenses (Service boundaries): Booking service ↔ payments/credits (G-3, if present): authority is the payment/credit system, checked at promotion time (not cached from join time)
+ gym-waitlist N-17 [operator] P-shiploop-spec: partial; P-shiploop-spec in round-5: partial; Q-shiploop-spec-lenses: covered
    item: Staff can see the waitlist, promote or remove someone by hand, and see who was promoted when.
    P-shiploop-spec (R-9 Exclusions, NFR-6): Exclusions ... staff view of the waitlist, waitlist counts, and any waitlist-specific permissions for staff.
    Q-shiploop-spec-lenses (R-9; R-12): a roster showing the ordered queue (member name, join time, position), the count, and a Remove action ... every waitlist event is recorded with timestamp ... actor ... event (join, leave, promote
+ gym-waitlist N-18 [operator] P-shiploop-spec: absent; P-shiploop-spec in round-5: absent; Q-shiploop-spec-lenses: covered
    item: The feature can be turned off, or enabled per class or class type.
    P-shiploop-spec (None): None
    Q-shiploop-spec-lenses (R-11): A **global** waitlist switch and a **per-class** override (on/off/inherit) exist.
+ invoice-reminders N-13 [unhappy] P-shiploop-spec: partial; P-shiploop-spec in round-5: partial; Q-shiploop-spec-lenses: covered
    item: More than one billing contact, and which of them is written to.
    P-shiploop-spec (G-4): Whether a customer can have several billing emails. | Folded into G-1. | One recipient address per invoice.
    Q-shiploop-spec-lenses (Basis and baseline): Out of scope ... several recipient addresses per invoice (A-1)
+ csv-user-import N-18 [operator] P-shiploop-spec: partial; P-shiploop-spec in round-5: partial; Q-shiploop-spec-lenses: covered
    item: Cancelling an import that is running, and retrying only the rows that failed.
    P-shiploop-spec (R-6.3, D-3): the client aborts the connection ... store read-back is S-0 or S-0 plus all three users, never one or two; if all three exist, a resubmit gives the R-6.2 result.
    Q-shiploop-spec-lenses (R-14 / A-4): Not cancellable in this version. ... Makes retry after correction safe and removes the half-imported state.
+ csv-user-import N-21 [unhappy] P-shiploop-spec: partial; P-shiploop-spec in round-5: partial; Q-shiploop-spec-lenses: covered
    item: Hostile content in the file: a value that becomes a formula when the result is opened in a spreadsheet, or a field far longer than any column allows.
    P-shiploop-spec (R-9, R-3): A name starting with =, +, - or @ is stored verbatim; neutralizing it for spreadsheet export is excluded ... Open gap G-6 (prerequisite): a maximum name length (code would be NAME_TOO_LONG)
    Q-shiploop-spec-lenses (R-15 / R-4): No CSV result export exists in this version, so formula-injection is `n/a`; if one is added, cells starting with `=`, `+`, `-` or `@` must be neutralized. ... name ... 1 to 100 characters
- grokbot-salesforce N-24 [operator] P-shiploop-spec: covered; P-shiploop-spec in round-5: partial; Q-shiploop-spec-lenses: partial
    item: A development org is not production: how the configuration and credential differ per environment, and how the work is deployed (scratch org or sandbox, metadata deployment, the production code-coverage requirement).
    P-shiploop-spec (PD-2, R-1.3, AD-2, AD-10): A production org identity makes the deploy step refuse. ... a production deploy would also need the Apex coverage gate, a development org deploy does not by itself
    Q-shiploop-spec-lenses (R-13; P-8): The bot deploys only to the user-authorised development org alias ... Deploys to production-type orgs require Apex test coverage (75% org-wide, per-deploy rule)
- gym-waitlist N-8 [unhappy] P-shiploop-spec: covered; P-shiploop-spec in round-5: covered; Q-shiploop-spec-lenses: partial
    item: A waitlisted person booking directly at the same moment a promotion is offered to them.
    P-shiploop-spec (T-2, AC-2.3, R-8): Member already has a live entry | Member joins again, or tries to book | Nothing | WAITLISTED(current position); no new entry, position unchanged
    Q-shiploop-spec-lenses (R-6): a direct "Book" request from a person not at the head fails (class remains full) whether it arrives before, during or after the freeing operation

## sonnet-high, judge gpt-6.2-astra: 5 covered by Q-shiploop-spec-lenses and not by P-shiploop-spec; 0 the other way
  +grokbot-salesforce N-16, +grokbot-salesforce N-22, +gym-waitlist N-18, +invoice-reminders N-17, +csv-user-import N-21 | 

## sol-medium, judge claude-opus-5-5: 5 covered by Q-shiploop-spec-lenses and not by P-shiploop-spec; 0 the other way
+ grokbot-salesforce N-22 [operator] P-shiploop-spec: partial; P-shiploop-spec in round-5: partial; Q-shiploop-spec-lenses: covered
    item: An administrator can turn the bot off, change the model, and see failed requests.
    P-shiploop-spec (R-4 Affected state; AD-2; NFR Security): At decommissioning revoke the upstream key and remove its bot-specific org credential and access assignments. ... with a configured `model` ... Diagnose by status category
    Q-shiploop-spec-lenses (R-4.a / R-4.b / R-4.c): the org operator sets the permitted endpoint/model binding ... operator can stop the bot for all users ... an authorized operator can tie a failed or completed request to its safe outcome.
+ gym-waitlist N-8 [unhappy] P-shiploop-spec: partial; P-shiploop-spec in round-5: covered; Q-shiploop-spec-lenses: covered
    item: A waitlisted person booking directly at the same moment a promotion is offered to them.
    P-shiploop-spec (R-2 Domain rules): A direct booking request for a seat held for allocation receives updated availability and the applicable waitlist action.
    Q-shiploop-spec-lenses (R-3.b; Non-functional booking integrity; R-1 State and data): Competing mutations resolve at the booking authority ... preserve one active entry and one confirmed booking at most per booking identity and occurrence ... A booked member has no active entry for the same occurrence
+ gym-waitlist N-18 [operator] P-shiploop-spec: absent; P-shiploop-spec in round-5: partial; Q-shiploop-spec-lenses: covered
    item: The feature can be turned off, or enabled per class or class type.
    P-shiploop-spec (None): None
    Q-shiploop-spec-lenses (R-6.a): Authorized operators can enable or pause waitlisting globally and pause or enable it for a single occurrence through an approved operations surface.
+ csv-user-import N-8 [unhappy] P-shiploop-spec: partial; P-shiploop-spec in round-5: covered; Q-shiploop-spec-lenses: covered
    item: A row failing after side effects have already happened for earlier rows (invitations already sent).
    P-shiploop-spec (R-3): settle default role/status plus provisioning, invitation, or notification effects and their failure contract... If the normal lifecycle has effects that cannot honor the draft failure contract, settle that conflict before enabling writes.
    Q-shiploop-spec-lenses (R-3 A / R-3 Resources): If the authoritative create operation definitively fails for a row, report that row as failed and preserve already committed rows. ... automatic rollback ... outside the upload contract.
+ csv-user-import N-21 [unhappy] P-shiploop-spec: absent; P-shiploop-spec in round-5: partial; Q-shiploop-spec-lenses: covered
    item: Hostile content in the file: a value that becomes a formula when the result is opened in a spreadsheet, or a field far longer than any column allows.
    P-shiploop-spec (None): None
    Q-shiploop-spec-lenses (R-6 A / R-2 C): Raw CSV, raw field values ... are absent from receipt payloads and import logs. ... Text from the upload is never executed or rendered as active content. / A file above the ... decoded field-size cap is rejected

## sol-medium, judge gpt-6.2-astra: 6 covered by Q-shiploop-spec-lenses and not by P-shiploop-spec; 0 the other way
  +grokbot-salesforce N-14, +grokbot-salesforce N-22, +gym-waitlist N-8, +gym-waitlist N-18, +csv-user-import N-8, +csv-user-import N-21 | 

