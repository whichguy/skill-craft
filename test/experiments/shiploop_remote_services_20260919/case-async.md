# Synthetic case: remote catalog with background recalculation

Design first-part discovery and implementation handoff for this increment.
All facts below are a supplied hypothetical, not live observations.

Request: multiple business services must cooperate to recalculate a catalog quote.
The UI may see progress up to 15 seconds late and must recover completed work on
reopen. A stale completion must never replace a newer submitted quote. Sensitive
prices must not be readable after the user's entitlement is revoked. Avoid copying
the catalog into an application database unless evidence proves it necessary.

Observed facts:
- A vendor MCP exposes list_models, describe_model, query_records, update_record
  and get_operation. It has no observed schema-management tool. Its developer
  account has read access. A documented vendor schema API is a lead with unknown
  account authority. Successful query access has been verified only for developers.
- The application already has a server-side query facade. It reads the remote
  catalog and delegates recalculation to an existing worker. The worker is allowed
  to update durable operation records without a browser being present.
- The service already provides atomic conditional record updates on revision,
  documented same-intent idempotency within the operation's lifetime, and bounded
  filtered queries. These facilities are available for reuse. Rate/latency
  measurements for polling under the expected population remain unknown.
- A durable operation record stores tenant, requester, operation ID, input revision,
  status, result locator, revision and timestamps. get_operation reads it. Work
  acceptance is recorded before the response, but its atomic relationship to
  dispatch and the worker's abandoned-work recovery have not been inspected.
- No event bus, webhook subscription, or websocket endpoint is installed. There
  is no requirement for an instant push notification. Current UI polls every 10
  seconds while open and stops polling on close.
- A cache has tenant/user/query keys and 60-second TTL. Permission changes are
  not a documented invalidation source. An old authorized response can arrive
  after account switching or revocation. On an authorization-service outage the
  existing handler currently returns its last cached result.
- Local schema v3 expects numeric QuoteTotal. Remote metadata now marks it as a
  computed field and contains a separate manually maintained SpecialTerms field.
  Prior intent expected QuoteTotal to be writable. The change request requires
  calculation behavior, not permission to overwrite vendor schema.

Return a grounded architecture decision, highest-value discovery reads/probes,
critical unresolved questions, and an ordered handoff naming example file roles
(paths may be proposed, not claimed to exist), acceptance checks and revalidation.
No remote execution or product edits. Maximum 1100 words.

Independent local control: an unrelated requested edit changes a pure string
formatter's title capitalization in one file, with existing unit tests and no
remote data. State what discovery/service work that edit needs in one sentence.
