# Current contact-review decision

## Accepted contract

Keep Contact and ReviewRequest remote-authoritative. Bypass the existing raw
shared cache until the runtime establishes current row and field authorization
and a tested invalidation, late-fill, and missed-change recovery contract. Until
then, a read passes through current policy enforcement or is denied; the raw
cache is never a fallback. The old partial metadata snapshot is not an absence
proof. Reconcile an additive
pending-review field against current metadata and retain Consent__c,
ComputedScore__c, Lifecycle__c, and unrelated automation.

ReviewRequest.status remains the durable status owner; preserve its
polling/re-read path. Notifications remain hints. The identity provider owns
login success/failure records. Add the missing application-owned review-state
audit event through the existing app.audit sink, not a second login logger.
Revalidate current metadata target, row/field authority, cache invalidation
evidence, and worker/status ownership immediately before any later change.
