# Composable design, state lifecycle and layered runtimes: experiments

September 26, 2026. Prompt experiments on whether ShipLoop's stage guidance makes
a model (1) evaluate composing existing parts before building new ones, (2) plan
the interaction, state and information lifecycle against what the runtime offers,
and (3) find and follow the conventions a project has layered on its runtime,
such as the mcp-gas-deploy module system or an org's Apex framework.

Harness, fixtures, judge prompts and every verdict:
[experiments/shiploop-composition-state-20260926](experiments/shiploop-composition-state-20260926/README.md).
No ShipLoop source was changed by this work.

## Decisions this evidence supports

| # | Change | Evidence |
| --- | --- | --- |
| 1 | Code craft: reword rules 1 and 5 and add *compose before you build*, with its one-meaning guard | E0: full composition 0/4 → 4/4; no false merges (8/8 kept separate) |
| 2 | Intake: add the interaction-and-state question paragraph | E3: persistence questions 3/9 → 9/9, hidden information 0/9 → 7/9, no more questions asked |
| 3 | Interaction-design block: add the *state and information lifecycle* paragraph (v2 wording) | E4/E5: end of life, quotas, personal data, retention and invite expiry rise from 0–3/9 to 7–8/9 |
| 4 | Planning review: add a platform-claim bullet requiring a source or a probe | E6b: errors the plan stage wrote itself caught 0/15 → 10/15 |
| 5 | Platform cards: record project layers and their trust properties (starting with mcp-gas-deploy) | E7: layer conventions already followed 21/21; the layer's eval bridge caught 0/15 by wording, 3/3 by a card entry |

Not supported: rebalancing the guides' restraint wording (no effect), and
putting a shared composition block in seven packets (plan-level choices did not
change; it reprints unchanged rules).

## Method

- Model: Sonnet (`claude -p --model sonnet`), three trials per cell unless noted.
  Code-level results were scored by an AST script. Plan-level results were scored
  by a blind Sonnet judge that saw one output at a time, without its variant, and
  graded what the plan *adopts*, not what it mentions.
- The keyword scorer (`score_regex.py`) was abandoned after it missed phrasings
  such as "imperative Apex calls"; it is kept only for reference.
- Prompts are condensed stage packets built from the real text in
  `shiploop_navigator_v3_prompts.py`, not full ShipLoop runs.
- Limits: small samples, one model family both producing and judging, and made-up
  scenarios. A judge without web access mislabels correct but unfamiliar platform
  facts (see E6b). Treat the numbers as directions.

## E0: composable design

**Code level.** An existing CSV export must also produce TSV (extending is
right), and sales tax is added beside a shipping function (extending is wrong).
Current Code craft against the proposed wording, four trials each.

| Case | Current Code craft | Proposed wording |
| --- | --- | --- |
| TSV export | 1/4 full copy, 3/4 shared validation but copied writer setup | 4/4 one core function with a delimiter argument |
| Sales tax | 4/4 separate function | 4/4 separate function |

The current rules 1 ("no option without a present need") and 5 (YAGNI limits
abstractions) are what produced the copy: that run explicitly rejected adding a
parameter.

**Plan level.** An Apps Script project (OrgMail library, `getRows_`, `groupBy_`,
`installTriggers`) and a Salesforce DX project (trigger framework,
`DiscountService`, discount custom metadata, approval flow). With the inventory
provided, both wordings reused every part in all 12 plans. The new wording
changed the recorded reasoning, not the choice.

## E1: architecture across runtimes (72 trials)

Battleship, solo against the computer and multiplayer with sign-in, on Google
Apps Script, Salesforce DX and Cloudflare Workers. Variants: no guidance,
current guides linked (with file access), current guides inline, inline plus a
rebalancing sentence, and new lifecycle wording (v1).

- An explicit multiplayer request already produces server-held state, runtime
  storage, runtime identity (custom auth on Cloudflare), server endpoints and a
  notification path in every variant, including no guidance: 15/15 per variant.
- Lifecycle wording added what defaults miss: finished or abandoned games' end
  of life 7/9 against 0–3/9, quotas 5/9 against 0–2/9, and the hidden fleet on
  Apps Script 3/3 against 1/3.
- Linked guides were opened in every run (three or four per run) and scored like
  the control. Rebalancing the restraint wording changed nothing.
- Solo requests: all variants chose a browser-only game with an explicit reason.
- 5 of 72 plans made false platform claims, for example `google.script.run`
  described as synchronous, field-level security used for per-record access, a
  composite unique constraint on a custom object, and scrypt in Workers' Web Crypto.

## E2: discovery on existing code (12 trials)

Browser-only Battleship fixtures on Apps Script (`ANYONE_ANONYMOUS`,
`localStorage`, no server calls) and Salesforce (LWC only, App Page), with the
request "make it multiplayer". Both the current wording and the lifecycle wording
found anonymous access, browser-only state, missing server endpoints, custom
objects, sharing and push in all runs. Only locking differed: Apps Script
`LockService` 0/3 against 2/3, Salesforce 1/3 against 2/3.

## E3: intake on a vague request (18 trials)

"Build a Battleship game." Current intake duty against the same duty plus:

> For a product people interact with, record the open questions of its
> interaction and state model: who the actors are and how the runtime identifies
> them; whether state is shared across people, devices or sessions; how long it
> must live and what ends it; what information must stay hidden from whom; and
> what the runtime already provides for each. Answer from the request where it
> says so; otherwise ask, naming the default you would take and what it rules out.

| Intake asks about | Current | With paragraph |
| --- | --- | --- |
| Solo, hotseat or separate devices | 9/9 | 9/9 |
| Persistence or resuming | 3/9 | 9/9 |
| Hidden fleet or cheating | 0/9 | 7/9 |
| Sign-in | 0/9 | 3/9 |
| Question count | 3–5 | 2–5 |

The earlier browser-only game repositories came from hotseat requests; keeping
them in the browser matched the request. The gap is that no stage asked.

## E4 and E5: lifecycle wording v2 (63 trials)

v2 ([life2.txt](experiments/shiploop-composition-state-20260926/battleship/life2.txt))
asks the model to *decide and state* each state's owner, readers, concurrency,
end of life, quotas and personal-data handling, and to carry open identity,
sharing or persistence choices to the user instead of building them.

Invite-by-email request (pooled over three runtimes):

| Plans that define | Current | v1 | v2 |
| --- | --- | --- | --- |
| Hidden fleet kept from the other client | 6/9 | 9/9 | 9/9 |
| Concurrency mechanism | 4/9 | 9/9 | 9/9 |
| End of life for games | 2/9 | 5/9 | 7/9 |
| Quotas | 3/9 | 3/9 | 7/9 |
| Email addresses as personal data | 0/9 | 7/9 | 7/9 |
| Retention | 0/9 | 5/9 | 7/9 |
| Deletion path | 0/9 | 1/9 | 2/9 |
| Personal data kept out of logs | 0/9 | 5/9 | 5/9 |
| Invite link expiry | 6/9 | 6/9 | 8/9 |

Solo request: v2 adopted platform sign-in in 2/9 plans against 5/9 for v1.
Moving solo state to the server stayed at 5/9 for both, mostly on Cloudflare,
where it keeps the computer's fleet away from the player. Unrequested features
were noisy (current 11, v1 7, v2 5 across nine plans each); this does not show an
overbuild effect. Multiplayer with v2 kept the E1 gains (end of life 8/9, quotas
8/9). A deletion path remains weak in every variant.

## E6 and E6b: platform claims

**Research stage, seeded claims (27 trials).** A draft plan per runtime held two
false claims and two true decoys. Every variant (no web access, web access, web
access plus a "verify each claim" paragraph) flagged all 18 false claims. The
four decoy flags (one, one and two per variant) were refinements, such as `FOR UPDATE` waiting 10 seconds
and then throwing `UNABLE_TO_LOCK_ROW` rather than queuing.

**Planning review, real errors (30 trials).** The five E1 plans with real errors
went through the current planning review focus, and through the focus plus:

> a claim about what the runtime, platform or a library can do that a decision
> depends on, with no primary-documentation source or probe result: check it,
> and correct the plan where it is wrong

The current focus caught 0/15; with the bullet, 10/15. The judge also reported ten
new errors in those reviews. On inspection about three are real (for example
`DmlException` where Salesforce throws `QueryException`); others are the judge
lacking web access, such as the documented rule that ORDER BY cannot be used in
a locking query. Errors enter at the plan stage, after research, so the review
that follows the plan is where to check them.

## E7: conventions a project layers on its runtime

Fixtures: a real mcp-gas-deploy project (tic-tac-toe; source
`whichguy/gas-tic-tac-toe` at `7d56d8e`, private, so it is not copied here) and
a synthetic Salesforce project with an in-house layer
([fixtures/sf-layered](experiments/shiploop-composition-state-20260926/battleship/fixtures/sf-layered)).
Request: make the game multiplayer. Discovery plus step plan with read-only tools.

The mcp-gas-deploy layer: modules as `_main(module, exports)` with
`__defineModule__` and `require('common-js/…')`; routing through
`module.exports.__events__`; pages calling `srv.<module>.<fn>()` from
`gas_client`; configuration through `ConfigManager`. The Salesforce layer:
`BaseSelector`, `ServiceResult`, `Logger`, `TriggerHandler`, a `c/apex`
wrapper and `TestDataFactory`.

- **Following the layer is already the default.** No guidance, current wording
  and a layered-conventions paragraph all followed every Salesforce convention
  (21/21 each). On Apps Script no plan adopted raw `google.script.run` or a global
  `doGet`. The apparent routing gap was plans that did not need a new route.
- **Judging whether the layer suits the new requirement is not.** The `srv`
  proxy sends client-built code to `apiExec`, which runs it with `new Function`,
  so any player can read the opponent's hidden fleet from stored state.

| Variant | Plans that identified the eval bridge |
| --- | --- |
| No guidance, current wording, layered paragraph | 0/9 |
| Layered paragraph plus "record what each layer guarantees and exposes" | 0/3 |
| Planning review, current focus (with repo access) | 0/3 |
| Planning review plus "trace one request through every layer" | 1/3 |
| Current wording with an mcp-gas-deploy section in the linked Apps Script card | 3/3 identified, 0/3 closed it |

General wording does not surface a deep property of a layer. A specific
platform-card entry does, because the models read the linked card. It still did
not produce a fix: the plans recorded the gap as open instead of planning an
allowlisted entry point. The requirement that hidden information stay hidden
has to be tied to the layer's property for the plan to act on it. The candidate
card text is in
[candidate-apps-script-card.md](experiments/shiploop-composition-state-20260926/battleship/candidate-apps-script-card.md).

## Open experiments

- Deletion path for personal data: weak (at most 2/9) under every wording tried.
- Closing a layer's trust gap once identified: tie the hidden-information
  requirement to the card entry and test whether plans plan the allowlisted
  entry point.
- A layer inventory in discovery for Salesforce managed packages and unlocked
  packages the repository does not contain (only the org does).
- One full ShipLoop run from "Build a Battleship game" on Apps Script, to confirm
  the intake question reaches the plan and work items.
