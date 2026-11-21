# Architecture decisions

How the product is built. What it must do lives in `spec.md`; nothing here restates a requirement.
Decisions are `AD-<n>`. No repository, stack or environment evidence existed when these were written, so
every entry is **proposed**, names no technology, and must be revalidated against the real system once
spec gap G-1 is closed.

## Decisions

### AD-1 Reminder processing runs as background work with its own authority
- **Status:** proposed. **Serves:** R-4, R-9, R-10, NFR-2.
- **Decision:** the daily evaluation and the sending are done by background work in the deployed runtime, triggered by a time-based trigger per account time zone, acting under the account's service authority. No screen, browser session or developer workstation takes part. The runtime and trigger facility are not chosen (G-1).
- **Alternatives:** triggering from the UI or from a user's session (rejected: the spec requires reminders with no session active).
- **Revalidate when:** the runtime is known; its trigger facility's limits (frequency, duration, overlap behaviour) must be read from its primary documentation before commitment.

### AD-2 Step records are the claim, the history and the duplicate guard
- **Status:** proposed. **Serves:** R-4, R-5, R-7, R-8, R-9, NFR-2.
- **Decision:** one durable record per (invoice, offset) with a uniqueness guarantee. Creating it is the atomic claim; its state field holds the final outcomes; the same records feed the history view. A claim with no result after a recovery threshold becomes unknown-outcome. Threshold value: **unresolved**, to be set in planning above the longest provider call.
- **Alternatives:** a separate queue or outbox (not justified: no dispatch gap demonstrated); an in-memory lock (rejected: does not protect overlapping instances).
- **Revalidate when:** the data store is known and its conditional-write or uniqueness support is confirmed in its documentation.

### AD-3 Mail sending sits behind one port with a test double
- **Status:** proposed. **Serves:** R-6, R-7, NFR-5.
- **Decision:** a single outbound-mail interface returns accepted, transient failure or permanent rejection. The production adapter is chosen after G-2; the test adapter captures messages and can fail on cue. Provider credentials come from the platform's secret facility.
- **Revalidate when:** a provider is selected.

### AD-4 Invoice data is read through an adapter, uncached
- **Status:** proposed. **Serves:** R-3, R-5, R-10.
- **Decision:** the feature reads invoice, customer contact, time zone and account data through one adapter onto the host data, at evaluation and again immediately before each send. No copy is kept beyond the step record's recipient field.
- **Revalidate when:** G-1 is closed; if the host exposes no usable read path, this decision is reopened.

### AD-5 Time comes from an injectable clock
- **Status:** proposed. **Serves:** R-4, NFR-5.
- **Decision:** all "today" and 09:00 decisions use a clock and the account time zone supplied from outside, so the acceptance cases can set both.

### AD-6 UI treatment (conditional)
- **Status:** unresolved until G-7. If a graphical surface is built, the concrete treatment (tokens, typefaces from local fonts, signature element, component set) is chosen in planning from `spec.md` NFR-6 and recorded here; an established host identity takes precedence.
