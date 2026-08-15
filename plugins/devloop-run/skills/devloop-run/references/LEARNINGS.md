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

1. **Child skill isolation (shipped).** Grok workers use `grok_worker_home()`
   (`$XDG_STATE_HOME/devloop/grok-worker` or `DEVLOOP_GROK_HOME`) so child `HOME`
   does not inherit `~/.grok/skills`. Auth stays on `XAI_API_KEY`. Override:
   `DEVLOOP_GROK_INHERIT_HOME=1` (unsupported).
2. **Distinct models (honest, not silent 5×).** On Grok transport, skip
   `assert_distinct_models` and record `model_identity: {policy: grok-host-single,
   distinct: false, model: grok-4.6}`. Do not claim five roles ran.
3. **Pin lag.** Pin 0.2.0 declares `transports: ["hermes","grok"]`. GitHub Release
   `devloop-engine-v0.2.0` still needs operator `gh` publish; until then bootstrap with
   `DEVLOOP_ENGINE_URL=file:///abs/path/devloop-engine-0.2.0.tar.gz` matching the pin sha256
   (`62ec01f3969ed48def0abfe9bd08bf67ed0f50ba1fb5a0a8981fa48a6fc95c57` for the 0.2.0 tarball
   in skill-craft `dist/`).
4. **Judge stdout (shipped predicates).** `_is_yes` strips Grok banners
   (`You are using XAI_API_KEY.`, `Default model:`, `Available models:`). Ambiguity
   still fail-closes.
5. **Optional components (shipped).** Receipts include `optional_components`
   (`nbq` / `scout` status: ran vs skipped_*). Silent skip must not look like parity.

## Operator recipe (Grok, no Hermes required for dispatch)

Happy path is **host-local** (`~/.local/share/devloop` after `--setup`), never
`DEVLOOP_HOME` pointed at the live Hermes leaf (that is the dual-install hijack).

```sh
export DEVLOOP_HOST=grok
export DEVLOOP_TRANSPORT=grok
export GROK_BIN="$(command -v grok)"
# optional: DEVLOOP_WRITE_SAFE_ROOT=$HOME/.local/state/devloop
# optional: DEVLOOP_HOME=$HOME/.local/share/devloop   # only if already bootstrapped
bash ~/.grok/skills/devloop-run/scripts/devloop-run --host grok --setup
bash ~/.grok/skills/devloop-run/scripts/devloop-run --host grok -- \
  --repo /abs/repo --lang command \
  'Create result.txt containing exactly: devloop-ok\n'
```

Without a Grok-capable engine tree, the card exits **2** and must not fall back
to `devloop-native`. `DEVLOOP_ALLOW_HERMES_SEED=1` is an unsupported escape hatch,
not the Grok happy path.

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

