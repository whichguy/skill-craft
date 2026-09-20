# Synthetic case: remote-backed customer workspace

Design the first-part discovery and implementation handoff for this increment.
Use the supplied facts as a synthetic environment, not as a live Salesforce claim.

Request: add a customer review panel, filter by review status, and request a
background risk assessment. Keep remote customer records authoritative and avoid
a replicated customer database. List values may be 30 seconds old. Access revoked
by an administrator must not remain available through subsequent application reads.
Reopening the panel must recover an accepted assessment even after a worker restart.

Observed facts:
- The developer MCP catalog exposes describe_objects, query_records, retrieve_metadata,
  deploy_metadata, and deployment_status. The connected developer role successfully
  describes a sandbox object. Metadata-write authority has not been tested.
- The app currently uses CustomerService -> an existing remote REST adapter under
  a broad integration identity. It does not use MCP at runtime. The per-user
  authorization enforcement point has not been documented.
- Prior accepted local model has Customer__c(Name, Region__c). Current local XML
  matches it. Scoped remote metadata now also has Consent__c and an independent
  automation reading that field. The incoming feature needs ReviewStatus__c.
  An existing remote RiskRequest__c object stores owner, status, request ID and
  result, but restart/retry/concurrency behavior has not been inspected.
- The current service cache is keyed by tenant + serialized query, with a 5-minute
  TTL, filled by the integration identity. Browser cache survives account switching.
  There is a customer-data change feed; whether it reports sharing, field-permission,
  and policy changes is unknown. No event-gap or stale-fill behavior is documented.
- An in-flight slow query started before a write can finish after invalidation.
  A permission change can occur without any customer record being edited.
- Metadata deploy returns a job ID; a saved success receipt must come from the
  status endpoint. The risk worker may complete after the initiating tab closes.
  A notification channel exists but delivers only to connected subscribers, may
  duplicate notifications, and carries record ID + request ID, not a durable result.
- No latency or quota baseline has been measured. Native platform cache and
  authorization facilities are possible research leads, not established choices.

Return a grounded architecture decision, highest-value discovery reads/probes,
critical unresolved questions, and an ordered handoff naming example file roles
(paths may be proposed, not claimed to exist), acceptance checks and revalidation.
No remote execution or product edits. Maximum 1100 words.

Independent local control: an unrelated requested edit changes a pure string
formatter's title capitalization in one file, with existing unit tests and no
remote data. State what discovery/service work that edit needs in one sentence.
