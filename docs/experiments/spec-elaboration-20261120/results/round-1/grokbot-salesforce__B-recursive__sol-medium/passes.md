## Pass 1 — The ground

Mapped the user and admin flows from first use through follow-up, empty and oversized input, denial, throttling, service failure, setup, recovery, and rollback. Wrote the initial 19 use cases and 32 clauses. The workspace contained no product baseline, named target org, or preselected bot surface. The request gave no prompt, model ID, or sizing values.

## Pass 2 — Prerequisites

Walked the request and the first-pass clauses from both actor perspectives. Added target identification, the Lightning entry point, an authenticated and authorized send boundary, initial readiness and recovery, user disclosure, transcript scope, input preservation, and the boundary between failed attempts and successful exchanges. Followed the added prerequisites through to Salesforce identity, org access, and the configured xAI account. Found no reason to require a second org, a separate end-user xAI login, or a fixed Grok version.

## Pass 3 — Interactions

Crossed page and user identity, access, enabled state, credentials, model selection, prompt, transcript, pending send, result, and rollback with Salesforce and xAI. Specified the effect of concurrent sends, configuration changes, stop and revocation, context overflow, uncertain delivery, delayed and duplicate results, and rollback during use. Found no shared record write, recurring job, or later-arriving import to reconcile.

## Pass 4 — Runtime rules

Checked Salesforce Developer Edition availability, endpoint and callout permissions, Apex timeout, count, payload and transaction constraints, and production Apex deployment gates against Salesforce documentation. Checked xAI authentication, rate, context and retention rules against xAI documentation. Kept Apex and credential packaging limits conditional on those paths being used. No target account, model, org variant, or quota was supplied, so the applicable figures are explicitly unconfirmed where they depend on selection. Found no product requirement for a job, trigger, or background workflow.

## Pass 5 — Preservation and invariants

Traced installation, use, and rollback against existing records, permissions, navigation, and unrelated changes. Traced untrusted prompts and Grok output across Salesforce, the provider, the browser, and diagnostics. Added explicit limits on CRM access, executable output, credential disclosure, cross-user visibility, and access bypass. Found no existing bot history or stored conversation schema to migrate.

## Pass 6 — Buildability review

Read the full spec as a builder, following each flow through its observables. Defined who needs the chat grant, the inclusive size boundary, coherent dispatch settings, the treatment of incomplete output, the finite wait, user-facing failure categories, diagnostic expiry and correlation, and partial setup recovery. Split the synchronous and asynchronous payload limits. Replaced overlapping requirements with distinct checks for browser persistence, effective model, and active chats during rollback. Found no user-provided copy, fixed deadline, fixed model, or format to impose.

## Pass 7 — Recovery and scope review

Rewalked each user and operator outcome across fresh and stale pages, settings changes, and service state. Added visible access and pause outcomes, pause-to-resume context continuity, model rejection, stale ceilings, draft disposal, a failed-rollback boundary, and the distinction between retrievable provider history and audit retention. Confirmed that the request provides no fixed product limits, public channel, CRM actions, or production rollout.

## Pass 8 — Authorization and rollback boundaries

Read the full document again from the install, dispatch, delivery, and restore boundaries. Made grant administration enforceable, anchored authorization to dispatch and delivery, and specified what rejected configuration writes and a first-install reversal leave behind. Defined that release rollback cannot regrant a revoked user. Confirmed that re-enabling after a pause without a release change does not need a new conversation.

## Pass 9 — Final state review

Checked the flow text against its clauses and revisited pending, denied, failed, and expired sends. Made the pending prompt identifiable, barred deferred sends caused by repeated gestures, gave replay eligibility a finite lifetime, and made incomplete setup actionable. Found no additional persistent user state that needs a migration, export, or restore policy.

## Pass 10 — Stop pass

Read from the request through every use case and clause. Checked who acts, what they observe at each outcome, which decisions are choices, where runtime conditions apply, and how pending work and stored state end. Rechecked the crossovers between authorization, controls, retries, context trimming, and rollback. Verified the exact record format, the 31 use cases and 151 clauses with gapless numbering, and all internal references. This pass found no behavior a builder would otherwise get wrong and made no further change to the specification.
