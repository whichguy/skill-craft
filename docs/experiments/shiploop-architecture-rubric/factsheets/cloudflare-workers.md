# Cloudflare Workers Platform Fact Sheet

## 1. Identity and sign-in for end users
- Cloudflare Access can be enabled per-Worker or account-wide, enforcing an identity policy (SSO/IdP, device posture) at the edge before code runs, covering custom domains, routes, workers.dev and previews. ([changelog](https://developers.cloudflare.com/changelog/post/2026-08-14-workers-access/))
- Access injects `ctx.access`; call `await ctx.access.getIdentity()` for email/name/groups/IdP/device posture — no manual JWT parsing needed. ([docs](https://developers.cloudflare.com/workers/configuration/cloudflare-access/))
- Server-side, the signed `Cf-Access-Jwt-Assertion` JWT should still be validated (signature/audience) if the origin is reachable other than through Access. ([API Shield](https://developers.cloudflare.com/api-shield/security/jwt-validation/jwt-worker/))
- Workers has no built-in consumer identity provider; non-Zero-Trust apps implement OAuth/OIDC themselves. Turnstile is bot mitigation, not identity. ([Turnstile](https://developers.cloudflare.com/turnstile/))

## 2. Authorization patterns
- Access policies (identity/group/device posture/service token) gate Zero Trust apps at the edge. ([docs](https://developers.cloudflare.com/cloudflare-one/access-controls/applications/http-apps/authorization-cookie/application-token/))
- Service bindings let one Worker call another (RPC or fetch) without a public URL; auth is implicit via account membership. ([docs](https://developers.cloudflare.com/workers/runtime-apis/bindings/service-bindings/))
- Service Tokens (`CF-Access-Client-Id/Secret`) authenticate machine callers through an Access app. ([docs](https://developers.cloudflare.com/cloudflare-one/access-controls/service-credentials/service-tokens/))
- mTLS certificate bindings let a Worker present a client cert to an mTLS-secured origin. ([docs](https://developers.cloudflare.com/workers/runtime-apis/bindings/mtls/))

## 3. State and storage
- Durable Objects storage is private, transactional, strongly consistent per object; SQLite-backed DOs expose full SQL; transactions roll back on throw. ([docs](https://developers.cloudflare.com/durable-objects/api/sqlite-storage-api/))
- Workers KV is an eventually-consistent global cache; writes propagate to other locations with delay; concurrent writes to a key are last-write-wins. ([docs](https://developers.cloudflare.com/kv/concepts/how-kv-works/))
- D1 gives snapshot isolation on its primary; the Sessions API adds sequential consistency across read replicas; only one `db.transaction()` runs at a time per database. ([blog](https://blog.cloudflare.com/d1-read-replication-beta/))
- R2 is strongly consistent: read-after-write, metadata, delete, and list all reflect the latest state immediately, globally. ([docs](https://developers.cloudflare.com/r2/reference/consistency))

## 4. Concurrency control
- DOs are single-threaded per instance; input gates pause new event delivery during storage ops (opt out with `allowConcurrency: true`); output gates delay externally-visible confirmation until prior writes commit. ([blog](https://blog.cloudflare.com/durable-objects-easy-fast-correct-choose-three/))
- Scale-out is per object ID, not within one object — shard across IDs. ([docs](https://developers.cloudflare.com/durable-objects/concepts/what-are-durable-objects/))
- KV has no locking/CAS; for correctness-sensitive counters/locks use a Durable Object or D1 transaction instead. ([docs](https://developers.cloudflare.com/kv/concepts/how-kv-works/))

## 5. Connectivity channels
- Request/response via `fetch` handler — native and fully supported.
- Polling — no special primitive; implemented as repeated `fetch` calls.
- Streaming/SSE — supported via `ReadableStream`/`TransformStream` response bodies; no dedicated SSE API, but `text/event-stream` works over a stream. ([docs](https://developers.cloudflare.com/workers/runtime-apis/streams/))
- WebSockets — supported as server (`WebSocketPair`) or outbound client (`fetch` with `Upgrade: websocket`). ([docs](https://developers.cloudflare.com/workers/runtime-apis/websockets/))
- DO Hibernation API lets sockets stay connected while the object is evicted from memory, avoiding duration billing; docs cite up to 32,768 connections per DO. ([docs](https://developers.cloudflare.com/durable-objects/best-practices/websockets/))
- Platform push (APNs/FCM-style) has no built-in primitive; call the provider's API via `fetch`. Unverified beyond this.

## 6. Caching and staleness
- Cache API follows RFC 9111 (heuristic freshness, respects `Cache-Control`). ([docs](https://developers.cloudflare.com/workers/reference/how-the-cache-works/))
- `stale-while-revalidate`/`stale-if-error` are **not** honored by `cache.put`/`match`. ([docs](https://developers.cloudflare.com/workers/runtime-apis/cache/))
- Responses with `Set-Cookie` are never cached. ([docs](https://developers.cloudflare.com/workers/runtime-apis/cache/))

## 7. Secrets custody
- Per-Worker secrets (`wrangler secret put`) are encrypted, exposed only via `env` bindings, unreadable after creation. ([docs](https://developers.cloudflare.com/workers/configuration/secrets/))
- Secrets Store holds account-level secrets shared across Workers via store ID + name bindings. ([docs](https://developers.cloudflare.com/secrets-store/integrations/workers/))
- mTLS bindings store client certs/keys as a managed resource, not inline code. ([docs](https://developers.cloudflare.com/workers/runtime-apis/bindings/mtls/))

## 8. Scheduling, queues, background work
- Cron Triggers call `scheduled()` on a schedule defined in Wrangler config; test locally with `--test-scheduled`. ([docs](https://developers.cloudflare.com/workers/configuration/cron-triggers/))
- Queues are **at-least-once**, not exactly-once — build idempotent consumers. ([docs](https://developers.cloudflare.com/queues/reference/delivery-guarantees/))
- `max_retries` defaults to 3; exhausted messages go to a configured `dead_letter_queue` or are discarded; batch failures retry the whole batch unless acked individually. ([docs](https://developers.cloudflare.com/queues/configuration/dead-letter-queues/))
- Workflows give step-based durable execution (`step.do`/`sleep`/`waitForEvent`); each step retries/memoizes independently; billed only while executing. ([blog](https://blog.cloudflare.com/workflows-ga-production-ready-durable-execution/))

## 9. Limits to check
- Workers runtime/plan limits: https://developers.cloudflare.com/workers/platform/limits/
- Durable Objects limits: https://developers.cloudflare.com/durable-objects/platform/limits/
- KV limits: https://developers.cloudflare.com/kv/platform/limits/
- D1 limits: https://developers.cloudflare.com/d1/platform/limits/
- R2 limits: https://developers.cloudflare.com/r2/platform/limits/
- Queues limits: https://developers.cloudflare.com/queues/platform/limits/
- Workflows limits: https://developers.cloudflare.com/workflows/reference/limits/

## 10. Deployment and verification surface
- `wrangler dev` (Miniflare) emulates KV/D1/DO/Queues/R2 locally; `--remote`/remote bindings cover behavior hard to simulate. ([docs](https://developers.cloudflare.com/workers/local-development/))
- Miniflare does not enforce real CPU-time limits — reported timing includes I/O wait, so a local pass doesn't prove you're under the production CPU cap (community-sourced, unverified against a primary doc).
- Local dev does not reproduce real cross-datacenter KV propagation, R2's actual replication path, DO jurisdiction placement, or Access's true edge enforcement — validate those via `--remote` or staging.
- `access.dev` config in Wrangler simulates `ctx.access` locally; it proves handler logic, not real Access policy enforcement. ([docs](https://developers.cloudflare.com/workers/configuration/cloudflare-access/))

## 11. Common false claims
- False: DOs process one object's requests across multiple threads for more throughput. Correction: single-threaded per object; scale by sharding IDs. ([docs](https://developers.cloudflare.com/durable-objects/concepts/what-are-durable-objects/))
- False: KV is strongly consistent everywhere. Correction: it's an eventually-consistent cache with propagation delay. ([docs](https://developers.cloudflare.com/kv/concepts/how-kv-works/))
- False: R2 has S3-style eventual consistency. Correction: R2 is documented strongly consistent for reads, metadata, deletes, and listing. ([docs](https://developers.cloudflare.com/r2/reference/consistency))
- False: Queues guarantee exactly-once delivery. Correction: at-least-once; dedupe in the consumer. ([docs](https://developers.cloudflare.com/queues/reference/delivery-guarantees/))
- False: Cache API honors `stale-while-revalidate`. Correction: explicitly unsupported by `cache.put`/`match`. ([docs](https://developers.cloudflare.com/workers/runtime-apis/cache/))
- False: hibernating DO WebSockets keep accruing duration billing. Correction: hibernation exists precisely so duration doesn't accrue while evicted. ([docs](https://developers.cloudflare.com/durable-objects/best-practices/websockets/))
- False: local `wrangler dev` proves you're under the production CPU-time limit. Correction: local timing includes I/O wait and doesn't enforce the real cap; only a deployed/`--remote` run does (partly unverified/community-sourced nuance).

**As of:** 2026-09-26, checked against developers.cloudflare.com pages for Workers, Durable Objects, KV, D1, R2, Queues, Workflows, Secrets Store, Cache, Web Crypto, Turnstile, and Cloudflare Access (including the 2026-08-14 Workers+Access changelog). Wrangler/workerd version not independently confirmed — check `wrangler --version` before relying on exact CLI/emulation behavior.
