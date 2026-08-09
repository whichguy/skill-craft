# DevLoop shim + multi-transport — learnings

Recorded after advisors panel `20260809T142914Z-bd9c` and implementation of
host-affinity + Grok `chat_raw` (2026-08-09).

## What went wrong earlier

1. **Two products, one name.** `devloop-native` looked like DevLoop but only ran
   host freeze/prove/stop. Agents (and Grok) routed “devloop” there and never
   touched the engine.
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
| `devloop-native` | Demoted triggers; installed Hermes copy refreshed |
| Engine transport | `resolve_transport`, `build_grok_cmd`, multi-transport `chat_raw`; `engine-capabilities.json` with `transports: [hermes, grok]` |
| Write-safe | `DEVLOOP_WRITE_SAFE_ROOT` + XDG state default when `/opt/data` unusable |

## Residual risks (still improve)

1. **Child skill inheritance.** `grok -p` may still load global skills/instructions;
   argv isolation is partial until a verified Skills(0) profile exists. Defense:
   `DEVLOOP_DEPTH` at the card + role prompts as workers only.
2. **Distinct models.** One Grok model vs `assert_distinct_models` — product default
   is Hermes-free multi-transport (per-role second backend), not silent 5× alias.
3. **Pin lag.** Host-local pin 0.1.1 may lack Grok transport; operators need
   `DEVLOOP_HOME` to a capable tree or a new pin after package/release.
4. **Judge stdout.** Grok noise may still break Hermes-shaped `_is_yes` — capture
   real transcripts next and scope noise predicates (advisors M4).
5. **Hermes optional components** (NBQ/Scout) still skip silently — parity
   `optional_components` receipt block not yet implemented.

## Operator recipe (Grok, no Hermes required for dispatch)

```sh
export DEVLOOP_HOST=grok
export DEVLOOP_TRANSPORT=grok
export GROK_BIN="$(command -v grok)"
export DEVLOOP_HOME="$HOME/.hermes/skills/software-development/devloop"  # or host-local with capabilities
# optional: DEVLOOP_WRITE_SAFE_ROOT=$HOME/.local/state/devloop
bash ~/.grok/skills/devloop-run/scripts/devloop-run -- \
  --repo /abs/repo --lang command \
  'Create result.txt containing exactly: devloop-ok\n'
```

Without a Grok-capable engine tree, the card exits **2** and must not fall back
to `devloop-native`.

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
- **Proof:** integration `verify_cmd` must be a real CLI/HTTP check (e.g. `clasp push`,
  `scripts/gas-verify`), not only offline tests.
- **MCP:** fine for operators and for implementing verify_cmd; engine does not speak MCP.
- **Anti-pattern:** host silently pushes after COMPLETE to “finish” DevLoop delivery.

