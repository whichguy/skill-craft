# Product default — DevLoop

## Rule

**Default DevLoop** = the **engine** via the multi-host card `devloop-run`
(`scripts/devloop-run` → `scripts/devloop_cli.py`).

Harnesses (Grok, Claude, Codex, Hermes chat) are **shims only**: resolve,
bootstrap if needed, exec the engine, report exit codes and receipts.
They must **not** reimplement DEFINE / PROVE / BUILD / DELIVER+LEARN.

## Package leaves

| Leaf | Role |
|------|------|
| `devloop-run` | **Default** portable card for bare “devloop” / DevLoop / machine-verifiable build goals |
| `devloop` | **Reserved** Hermes skillhub engine path — never a skill-craft `skills/devloop` package |
| `devloop-native` | **Demoted** optional offline evidence gates (freeze/prove/stop). Not DevLoop default |

## Grok parity (target)

Grok completion of a real loop must work with:

- Host-local engine (`~/.local/share/devloop` or `DEVLOOP_HOME`)
- Grok model transport (`DEVLOOP_TRANSPORT=grok` / host affinity)
- **No** `HERMES_BIN` and **no** `~/.hermes/.../devloop` required at runtime

**Host affinity (shipped in card):** `DEVLOOP_HOST=grok` (or `--host grok`) never
selects the live Hermes leaf unless `DEVLOOP_ALLOW_HERMES_SEED=1`. Nested invoke
(`DEVLOOP_DEPTH`≠0) exits 2. Full engines without a declared `grok` transport
capability fail closed at invoke (override: `DEVLOOP_ALLOW_LEGACY_ENGINE=1`).

Pin 0.2.0 declares `transports: ["hermes","grok"]`. Until a matching host-local
engine is bootstrapped, the card must fail closed with exit **2** and next steps —
not fall back to host-agent improvisation or `devloop-native`.

**Write-safe:** prefer `DEVLOOP_WRITE_SAFE_ROOT`; host-local default under
`$XDG_STATE_HOME/devloop` (not `/opt/data` unless that path is a writable container root).

## Agent procedure (card)

1. Banner: `DevLoop — mode=engine host=<host> engine=<path-or-pending>`
2. `SKILL_ROOT` = directory containing the installed `SKILL.md` (logical skill-dir path)
3. Grok: `bash "$SKILL_ROOT/scripts/devloop-run" --host grok --setup`
4. Grok: `bash "$SKILL_ROOT/scripts/devloop-run" --host grok -- [engine args…] "<goal>"`
5. Report engine stdout/JSON + exit code only. COMPLETE only on engine exit 0
   (and matching `--json` delivery/terminal). Exit 2 is not success.

**Forbidden:** host-written charters as the acceptance path; host BUILD;
suggesting `devloop-native` as “DevLoop.”
