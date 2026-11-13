# Bounded reference workflow

Snapshot date: **2026-11-13 UTC (2026-11-12 America/Los_Angeles)**. This is a concise scenario interpretation of the supplied plan, exact Astra advice and official references. Freeze this file and relevant reference snapshots per attempt; later online changes must not silently amend frozen criteria. No screenshots or application implementation are supplied.

## Product reference and scenario choices

The official [Grok Bot design discussion](https://x.ai/news/designing-grok-bot) motivates durable agents and visible work. The supplied research and plan use it as design context, not as a source of Salesforce readiness or a promise of full parity.

[Bot management](https://docs.x.ai/grok-bot/bots) describes named bots with conversations and developing context, with lasting rules distinct from ordinary tasks. This scenario selects named bot persistence and explicit editable memory. It defines instruction-version snapshots and checkpoint consumption itself; these are scenario choices, not claims that the reference product uses this exact transaction model.

[Message and collaboration workflows](https://docs.x.ai/grok-bot/chat-and-collaboration) inform the roster/chat, follow-up and visible-progress experience. Sequenced steering, exact approval binding, Salesforce synthetic business tools and browser-away Apex evidence are explicit scenario requirements. Saved task prompts are reusable user inputs, never an authorization mechanism.

[xAI advanced tool usage](https://docs.x.ai/developers/tools/advanced-usage) is the provider-side reference for tool interactions. The scenario requires actual Apex tool dispatch and a subsequent provider request containing the result. It does not grant provider-hosted tools access to excluded execution surfaces.

The first version explicitly excludes voice, arbitrary cloud computer/shell/browser execution, bot-to-bot delegation, recurring routines, unsolicited initiative and enterprise integrations. It is a bounded Salesforce counterpart. The application owns orchestration in Apex; inference remains with xAI. The builder is ShipLoop, not the runtime agent service.

## Platform constraints, not live readiness

[Salesforce Queueable Apex](https://developer.salesforce.com/docs/platform/apex-dev/references/apex-dev/apex-queueing-jobs.html) provides background jobs, job IDs and chaining; resource availability can delay execution. The scenario therefore requires distinct worker transactions and committed progress before reopen, with queue-deadline expiry yielding UNKNOWN. Target API/queue capacity and actual worker observations remain unverified.

[Secure Apex classes](https://developer.salesforce.com/docs/platform/lwc/guide/apex-security.html) distinguishes API 67+ security defaults from API 66 and earlier and recommends explicit access/sharing declarations. Sharing, object permissions and field access must be evaluated deliberately. This scenario additionally requires effective async principal identification, permission rechecks after queueing, ownership isolation and protection before provider disclosure. Current target API version and credential principal behavior remain unknown.

[Callouts and uncommitted work](https://developer.salesforce.com/docs/platform/apex-dev/references/apex-dev/apex-classes-restful-http-testing-dml.html) documents callout constraints after DML and asynchronous enqueue operations. Production transaction ordering needs an actual target-compatible design; test-only start/stop mechanisms do not solve runtime ordering. The builder chooses its class/transaction structure.

[Named Credentials](https://developer.salesforce.com/docs/platform/named-credentials/guide/get-started.html) separates endpoint/credential configuration from application code. Operator-owned encrypted setup and grant ownership are scenario requirements. These references do not establish current auth, key, principal, supported model, configuration Save/readback or a real successful application connection.

## Retained evidence decisions

The plan and exact Astra response supplied for this preparation support a five-file packet, with no catalog integration needed now. Astra's material amendments are adopted: safety before every live launch; transaction-level approval/cancellation semantics; explicit asynchronous authority; versioned instructions/memory/steering; independent native evidence; four separate readiness states. No new advice was commissioned by this author. The subsequent full owner cleanup steering controls intake and lifecycle: this case is `run_kind=create`, with mandatory verified reset before every independent full-case builder attempt including the first, and cleanup after success/failure/interruption. This is not reset before each repeated test, Proof or Until Loop cycle. Those checks preserve the candidate and may reset only declared synthetic fixtures. Future unspecified scenarios ask clean-create versus feature/additive at outer intake; verified feature predecessors are preserved, and an existing app alone does not choose mode.

Canonical org/case/run inventory must discover prior declared TEST-OWNED resources across inventory-linked older prefixes. A new folder/prefix/browser cannot replace cleanup. Known empty targets require observed no-op cleanup receipts; unknown ownership, conflicting/active work, late deployments and incomplete cleanup block launch/reuse. Preserve unrelated apps/data/User accounts, other active work, existing owner credentials/keys and run/evidence history. New temporary provider resources need separate ownership evidence. Cleanup/admin/deployment/auth remain setup responsibilities outside runtime bot authority.

Pre-builder prerequisites are canonical target/user and deployment/setup authority, verified startup reset, job/deployment containment, the operator credential-reference/setup route and grants as appropriate, and actual observation capability/contract. They do not require a new product before its builder exists. Post-build SETUP-01 observes the real app Save, independent persisted configuration readback and app-initiated actual connection; dependent UI/provider acceptance cannot pass with blocked or unobserved provider outcomes, which remain UNKNOWN. Missing-setup UI remains a product obligation. Deployment still requires authority, reset and containment.

Future role launch controls are `gpt-6.1-sol` / `medium` for subject/builder, test author and routine execution, and separate fresh `gpt-6-astra` / `high` sessions for independent reviewer and judge. Apply actual controls at launch and retain requested-versus-served identity limits; app inference stays separately configured Grok/xAI. This changes no global defaults, installed packages or historical identities.

These are future requirements, not evidence of org access or cleanup in this preparation. The packet's INTAKE controls evaluate outer apparatus, separately from Apex app behavior.

Relevant full messages were read before the first edit:

| Commit | Decision carried into this packet |
|---|---|
| `f87061c07caa5901e0c35244dce62d52a83dfcf0` | Exploratory construction and mock/smoke success do not establish independent behavioral acceptance. |
| `cf211dab4409e0452235138a6b72dce6ac07655d` | Separate native, provider, browser, independent quality and cleanup evidence; field-only denial needs its own proof. |
| `a270e5bf0a3c12641ef27cfcfdb70d647837957a` | Recovered current acceptance preserves original failed trials and does not prove generic improvement. |
| `17f5e10f34c6af9ff5054a7842c09e56d81f750e` | Recovery inspection/preparation and scoped assessment are distinct; exact ownership/source matters. |
| `211fe61b0bc13b8fa5af43241a04400e1794fe85` | Step Proofs are rerun and must be safe to repeat; preserve the candidate within an attempt rather than interpreting startup reset as a per-check teardown. |
| `f0c244253e3ff050ef55409ea2e632d89de1a46f` | Verified cleanup gates target reuse; aliases are not canonical identity and shared-org cleanup is bounded. |
| `a8a168c4507ce11bac94aa07620f0cc69ff4429b` | Latest registered observation supersedes older credit, including a newer incomplete attempt. |

The historical design/source snapshot below is not the future installed selection. In the dated 2026-11-13 UTC preparation snapshot, the coordinator’s Git read observed canonical main at `7ceaecf441448c1c394340ec2c98f848cd685b27` (Skill Craft 2.36.6 / ShipLoop 1.33.10). This observation is preparation context, not a new owner version preference; preparation/reference `source_head` is not an installed subject binding. Resolve and verify current published bytes at future launch; do not pin historical 1.33.9 as latest. No pull/merge, release edit, frozen/live trial or model comparison occurs here.

At source HEAD `dcb7efcb4c6a79314aa4a23c37d296184b699c1d`, [SPEC resource lifecycle](../../SPEC.md#the-resource-lifecycle-added-2026-10-26) limits shared-org cleanup claims; [the full Grok guide](../../GROK_CHAT_FULL.md#run-and-attend-the-loop) uses synchronous browser/native joins. Their principles inform this packet; their existing evaluators and gym lifecycle do not qualify new background jobs or late deployments. All existing files remain outside this author's ownership.

Live readiness, evaluator calibration, actual product construction, source/deployment binding, provider/UI acceptance and complete owned cleanup are unresolved. Official documentation is platform context, never evidence that those steps occurred.
