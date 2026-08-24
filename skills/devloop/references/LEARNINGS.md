# DevLoop shim + multi-transport — learnings

Recorded after advisors panel `20260809T142914Z-bd9c` and implementation of
host-affinity + Grok `chat_raw` (2026-08-09).

## What went wrong earlier

1. **Two products, one name.** `devloop-native` (now `evidence-gates`) looked
   like DevLoop but only ran host freeze/prove/stop. Agents (and Grok) routed
   “devloop” there and never touched the engine.
2. **Resolve hijack.** On dual-install laptops, empty host-local selected the
   live Hermes leaf; “zero Hermes” was never exercised while still looking green.
3. **Transport hard-wire.** Engine `chat_raw` only built `hermes chat …`. Card
   bootstrap alone cannot produce Grok parity.
4. **False COMPLETE.** Acceptance that allowed “or fail-closed error” could pass
   with zero successful loops.

## What we shipped (card + engine leaf)

| Layer | Change |
|-------|--------|
| Card `devloop-run` 0.4.1 | Default product; `DEVLOOP_HOST`; skip Hermes seed on Grok; nesting refuse; capability preflight; atomic swap |
| Card `devloop` 0.5.0 | Source leaf is `skills/devloop`; dest = leaf; Hermes card install skipped |
| `evidence-gates` (was `devloop-native`) | Renamed so it cannot steal DevLoop discovery |
| Engine transport | `resolve_transport`, `build_grok_cmd`, multi-transport `chat_raw`; `engine-capabilities.json` with `transports: [hermes, grok]` |
| Write-safe | `DEVLOOP_WRITE_SAFE_ROOT` + XDG state default when `/opt/data` unusable |

## Residual risks (still improve)

1. **Child skill isolation (shipped).** Grok workers use `grok_worker_home()`
   (`$XDG_STATE_HOME/devloop/grok-worker` or `DEVLOOP_GROK_HOME`) so child `HOME`
   does not inherit `~/.grok/skills`. Auth stays on `XAI_API_KEY`. Override:
   `DEVLOOP_GROK_INHERIT_HOME=1` (unsupported).
2. **Distinct models (honest, not silent 5×).** On Grok transport, skip
   `assert_distinct_models` and record `model_identity: {policy: grok-host-single,
   distinct: false, model: grok-4.6}`. Do not claim five roles ran.
3. **Pin 0.2.0 published.** GitHub Release `devloop-engine-v0.2.0` is live
   (`https://github.com/whichguy/skill-craft/releases/tag/devloop-engine-v0.2.0`).
   `--host grok --setup` bootstraps from the pin URL+sha256
   (`62ec01f3969ed48def0abfe9bd08bf67ed0f50ba1fb5a0a8981fa48a6fc95c57`).
   Local `file://` URL remains valid for offline/air-gapped machines.
4. **Judge stdout (shipped predicates).** `_is_yes` strips Grok banners
   (`You are using XAI_API_KEY.`, `Default model:`, `Available models:`). Ambiguity
   still fail-closes.
5. **Optional components (shipped).** Receipts include `optional_components`
   (`nbq` / `scout` status: ran vs skipped_*). Silent skip must not look like parity.

## Operator recipe (Grok, no Hermes required for dispatch)

Happy path is **host-local** (`~/.local/share/devloop` after `--setup`), never
`DEVLOOP_HOME` pointed at the live Hermes leaf (that is the dual-install hijack).

```sh
# once on a fresh machine
bash ~/.grok/skills/devloop/scripts/devloop-run --setup

# interactive or headless — prompt, not flag soup
grok -p '/devloop new repo. Create result.txt containing exactly one line: devloop-ok. verify_cmd exactly ["bash", "-c", "test \"$(cat result.txt)\" = devloop-ok"]' --always-approve
```

Without a Grok-capable engine tree, the card exits **2** and must not fall back
to `evidence-gates`. `DEVLOOP_ALLOW_HERMES_SEED=1` is an unsupported escape hatch,
not the Grok happy path.

## Interpolation, not shim prose-scraping (0.4.5)

The card's `/devloop` procedure now interpolates `--repo` / `--lang` /
`verify_cmd exactly [...]` from plain English **host-side**, prints the
interpolation, then execs the shim with explicit argv. The shim itself no
longer auto-prepends `--lang command` from a raw `verify_cmd exactly [` in
argv — that was a second, silent profile selector. The shim only labels
whatever actually reached the CLI (`STATE lang=<value> reason=explicit` or
`STATE lang=none reason=none`). `STATE target=` is the `--repo` flag only
(`explicit` / `repo_flag` vs `scratch` / `default`) — designation phrases
live on the card interpolate table, not in bash. Do not invoke Grok `/goal`
or `/loop` from this card or its alias; goal-engineering shape lives in the
`/devloop` prompt text itself.

## Process learnings

- Commit pathspecs only; never broad `git add` in multi-session trees.
- Hermetic tests for affinity/nesting/capability (D22–D25) caught `set -e` +
  nonzero function return aborting preflight as exit 1 — fix with `set +e` around
  capability probe.
- Advisors “Open Unknowns: None” was itself a plan bug; keep load-bearing U-list.

## Remote delivery surfaces (2026-08-09)

Local unit/`unittest` COMPLETE is **not** product-on-host when the request names a
hosted runtime, deploy/publish/push, or live web app URL.

- **Engine (general):** charter/refine/advisor prompts + `remote_delivery_named` /
  `require_remote_delivery_integration` admission (twin of external CLI check).
- **Proof:** integration `verify_cmd` must be a real CLI/HTTP check that
  observes the hosted surface, not only offline tests. Instance bindings
  (how one dest claims inbound work) live in `destination-instances.md`.
- **MCP:** host inventories session MCP **before the engine plans**
  (read-capable bar; not product-specific) and prints `mcp-considered`.
  Engine does not speak MCP. COMPLETE stays `AFTER exec exit=0`. If a
  pre-existing MCP-backed CLI exists, that is `verify_cmd`; otherwise
  fold a *concrete* constraint (`do not write new operator tooling`) —
  do not invent a new committed harness or a second host COMPLETE gate.
- **Anti-pattern:** host silently pushes after COMPLETE to “finish” DevLoop delivery.

## Destination contract (2026-08-16)

Hosted asks need a **destination contract** before DEFINE/BUILD: identity,
claim hook, reserved surface, success shape, live **misread**. Print
`env-discovered` with those five slots. Discover from user text, session MCP,
and the provisioned tree — do not hardcode one vendor’s hook into the skill.

**Instance (mcp-gas-deploy):** HEAD JSON `No doGet handler claimed the
request` with `totalHandlers>0` / `failedCount=0` is missing **claimer**
(handlers yielded), not platform down. Bindings:
[destination-instances.md](destination-instances.md).

## No auto-Hermes on invoke-host (2026-08-23)

Cursor/Claude/Codex (and `auto` + a full engine) must not fall through to
`hermes chat` when `DEVLOOP_TRANSPORT` is unset. The engine’s
`resolve_transport` still defaults to Hermes; the shim fail-closes first
unless the operator sets `DEVLOOP_TRANSPORT=grok` or `=hermes`. `auto` no
longer allows Hermes seed. `DEVLOOP_HOME` pointed at the live Hermes leaf
is still an explicit package override (warn only).

## Overlay compose (2026-08-22)

Card 0.5.2 names the compose graph and thins the handshake:

- **Before** `/devloop`: validate the spec
  ([validate-spec.md](validate-spec.md); optional `define-done` /
  `backchain`) when done is not machine-checkable. Not `c-plan`, not
  c-thru `/cplan`. Handshake step 0, then MCP → dest → interpolate.
- **During:** engine only. Still do not invoke Grok `/goal` or `/loop`.
- **After** COMPLETE: `/review-coverage` under `/goal` for residual×2.

MCP consider and destination-contract procedures live in
[mcp-consider.md](mcp-consider.md) and
[destination-contract.md](destination-contract.md). Portable practices:
[loop-engineering.md](loop-engineering.md). Maintain the card with
`prompt-align` against `test/devloop-run.test.sh` (D37–D48); do not add
SKILL.md greps for prose that already lives in a reference.

## Foreground + prompt on HUMAN_REVIEW (2026-08-17)

A host that backgrounds `devloop-run` hides `[devloop]` status and turns
exit 2 into a late postmortem. The operator never sees `NEEDS YOUR INPUT`
in time to answer. Card 0.5.1: do **not** background the shim; on the
first `HUMAN_REVIEW` / `NEEDS YOUR INPUT` / `AFTER exec exit=2`, **prompt
the user** with the engine reason and `— ANSWERS:`. Do not wait out
further automatic attempts in silence.

