# GCP Web App Platform Fact Sheet

## 1. Identity and sign-in
- Firebase Authentication / Identity Platform issues a signed Firebase ID token (JWT) after client sign-in; the client sends it to your backend (e.g., `Authorization: Bearer`). [Admin Auth API intro](https://firebase.google.com/docs/auth/admin)
- Server verifies with Admin SDK `verifyIdToken()` (checks signature, format, expiry); this does **not** check revocation unless you explicitly request revocation-checking. [Verify ID Tokens](https://firebase.google.com/docs/auth/admin/verify-id-tokens)
- For org/employee-perimeter access, Identity-Aware Proxy authenticates via Google identity at the load balancer and forwards a signed `x-goog-iap-jwt-assertion` header; the backend must independently verify the signature against IAP's JWKS and audience claim. [Securing your app with signed headers](https://cloud.google.com/iap/docs/signed-headers-howto)

## 2. Authorization patterns
- Firestore Security Rules evaluate `request.auth` for direct **client SDK** access (mobile/web) only. [Get started with Security Rules](https://firebase.google.com/docs/firestore/security/get-started)
- Server/Admin SDK and REST/RPC calls **bypass Security Rules entirely** and authenticate via IAM/Application Default Credentials — you must implement access control in server code. [Get started with Security Rules](https://firebase.google.com/docs/firestore/security/get-started)
- Custom claims (Admin SDK) are a common RBAC mechanism, checked either in rules or server logic.

## 3. State and storage
- **Firestore**: document DB; realtime listeners guarantee strong ordering ("changelog structure guarantees strong consistency"). [Real-time queries at scale](https://docs.cloud.google.com/firestore/native/docs/real-time_queries_at_scale). Transactions retry on read/write conflicts (data contention); Standard edition uses pessimistic, Enterprise edition optimistic concurrency. [Transaction serializability](https://firebase.google.com/docs/firestore/transaction-data-contention)
- **Cloud SQL** (Postgres/MySQL/SQL Server): standard relational ACID transactions; connect via Cloud SQL Auth Proxy, which does **not** pool connections itself. [About the Auth Proxy](https://docs.cloud.google.com/sql/docs/postgres/sql-proxy)
- Firestore/Cloud SQL are the two durable stores; Memorystore (below) is in-memory/non-durable by design.

## 4. Concurrency control
- Firestore: optimistic — a transaction fails/retries if a read document changed underneath it. [Transaction contention](https://firebase.google.com/docs/firestore/transaction-data-contention)
- Cloud SQL: engine-native locking/MVCC (Postgres/MySQL), unrelated to GCP-specific behavior.
- Cloud Run instances are stateless with **no guaranteed in-memory persistence between requests**; cross-request coordination needs Firestore/Cloud SQL transactions or an external lock (e.g., Memorystore). [Cloud Run FAQ](https://github.com/ahmetb/cloud-run-faq)

## 5. Connectivity channels
- **Request/response**: native HTTP(S)/gRPC unary on Cloud Run.
- **Polling**: supported via standard REST calls; no special platform feature.
- **Streaming/SSE**: Cloud Run supports chunked-transfer streaming and `text/event-stream` SSE with no extra config, subject to the request timeout. [Invoke with HTTPS](https://docs.cloud.google.com/run/docs/triggering/https-request)
- **WebSockets**: supported as long-lived HTTP requests, bounded by request timeout (default 5 min, max 60 min); session affinity is **best-effort only** and breaks on instance termination/max concurrency. [Using WebSockets](https://docs.cloud.google.com/run/docs/triggering/websockets), [Session affinity](https://docs.cloud.google.com/run/docs/configuring/session-affinity), [Request timeout](https://docs.cloud.google.com/run/docs/configuring/request-timeout)
- **Platform push**: Firestore realtime listeners push ordered changes to clients. [Listen doc](https://firebase.google.com/docs/firestore/query-data/listen). Pub/Sub push subscriptions deliver via HTTPS POST, at-least-once. [Dead-letter topics](https://docs.cloud.google.com/pubsub/docs/dead-letter-topics)

## 6. Caching and staleness
- Cloud Storage: public objects with no `Cache-Control` metadata get `public, max-age=3600` by default; fully configurable per-object. [Object metadata](https://docs.cloud.google.com/storage/docs/metadata)
- Cloud CDN: origin can set `stale-while-revalidate`; clients can request `max-stale` to bound freshness. [Serving stale content](https://docs.cloud.google.com/cdn/docs/serving-stale-content)
- Firestore client SDKs cache locally for offline use; freshness/ordering guarantees apply once reconnected via listeners (unverified: exact staleness bound while offline).

## 7. Secrets custody
- Secret Manager stores immutable, versioned secret values; access requires `roles/secretmanager.secretAccessor`. [Access control](https://docs.cloud.google.com/secret-manager/docs/access-control)
- Cloud Run can mount secrets as env vars (resolved at instance startup — pin a version, not "latest") or as mounted volumes. [Configure secrets for services](https://docs.cloud.google.com/run/docs/configuring/services/secrets)

## 8. Scheduling, queues, background work
- **Cloud Tasks**: exponential-backoff retry per queue/task (min/max interval, max doublings); Cloud Tasks has **no native dead-letter queue** — build one by writing failed payloads elsewhere after the final attempt. [Configure queues](https://cloud.google.com/tasks/docs/configuring-queues), [Set retry parameters](https://docs.cloud.google.com/tasks/docs/configure-retry-task)
- **Pub/Sub**: at-least-once by default (design consumers idempotently); optional dead-letter topic after N delivery attempts; separate exactly-once delivery mode exists but **only for pull subscriptions**, not push/export. [Dead-letter topics](https://docs.cloud.google.com/pubsub/docs/dead-letter-topics), [Exactly-once delivery](https://docs.cloud.google.com/pubsub/docs/exactly-once-delivery)
- **Cloud Run jobs**: per-task timeout (default 10 min, up to 168h; GPU jobs capped lower), default 3 retries per task. [Task timeout](https://docs.cloud.google.com/run/docs/configuring/task-timeout), [Max retries](https://docs.cloud.google.com/run/docs/configuring/max-retries)

## 9. Limits to check
- [Cloud Run quotas](https://docs.cloud.google.com/run/quotas) · [Firestore quotas](https://docs.cloud.google.com/firestore/quotas) · [Pub/Sub quotas](https://docs.cloud.google.com/pubsub/quotas) · [Cloud Tasks quotas](https://docs.cloud.google.com/tasks/docs/quotas) · [Secret Manager quotas](https://docs.cloud.google.com/secret-manager/quotas) · [Cloud SQL quotas](https://docs.cloud.google.com/sql/docs/quotas)

## 10. Deployment and verification surface
- Firebase Emulator Suite does **not enforce all production limits** (e.g., may allow oversized transactions), doesn't track compound indexes (runs queries that would fail in prod for missing an index), and transaction-contention locks can take up to 30s to release — unlike prod behavior. [Firestore emulator](https://docs.cloud.google.com/firestore/native/docs/emulator)
- Cloud Storage emulator lacks bucket-level config and Pub/Sub-based object-change notifications. [Emulator Suite](https://firebase.google.com/docs/emulator-suite/connect_storage)
- None of the above prove real IAM enforcement, quota/throttling behavior, Cloud Run autoscaling/cold-start timing, or VPC/Memorystore network latency — those require testing against real deployed resources.

## 11. Common false claims
- "Cloud Run keeps reliable in-memory state/cache across requests." **False** — instances are stateless with no persistence guarantee between invocations; CPU is throttled outside request processing unless always-on CPU is set. [Cloud Run FAQ](https://github.com/ahmetb/cloud-run-faq)
- "IAP is sufficient application authorization; the backend can trust the header blindly." **False** — the app must independently verify the JWT signature/audience; IAP only gates network access. [Signed headers](https://cloud.google.com/iap/docs/signed-headers-howto)
- "Firestore Security Rules protect data accessed via the Admin SDK/server." **False** — server client libraries bypass rules entirely; use IAM instead. [Get started with Security Rules](https://firebase.google.com/docs/firestore/security/get-started)
- "Pub/Sub guarantees exactly-once delivery by default." **False** — default is at-least-once; exactly-once mode exists only for pull subscriptions. [Exactly-once delivery](https://docs.cloud.google.com/pubsub/docs/exactly-once-delivery)
- "Cloud Tasks has a built-in dead-letter queue like Pub/Sub." **False** — you must build your own DLQ pattern. [Configure queues](https://cloud.google.com/tasks/docs/configuring-queues)
- "Passing tests against the Firebase Emulator Suite proves production limits/index requirements are respected." **False** — the emulator doesn't enforce all production limits or index checks. [Firestore emulator](https://docs.cloud.google.com/firestore/native/docs/emulator)

**As of:** 2026-09-26, checked against `docs.cloud.google.com` / `firebase.google.com` pages listed above (Cloud Run request-timeout, WebSockets, session-affinity, task-timeout, max-retries docs; Firestore real-time-queries, transaction-data-contention, security/get-started, quotas, emulator docs; Firebase Auth admin/verify-id-tokens; IAP signed-headers-howto; Cloud SQL sql-proxy; Pub/Sub dead-letter-topics, subscription-retry-policy, exactly-once-delivery, quotas; Cloud Tasks configuring-queues, configure-retry-task, quotas; Secret Manager access-control, quotas; Cloud Storage metadata; Cloud CDN serving-stale-content).
