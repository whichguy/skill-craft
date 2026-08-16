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
3. Grok user form: `/devloop <plain English>` (headless:
   `grok -p '/devloop <plain English>' --always-approve`). Advertise `/devloop`
   only — never a second `skills/devloop`. Do not drive the loop with the
   host goal harness or `/loop`.
4. Host **parses the skill argument** (plain English; flags are optional
   overrides, never required). **Compile** `/goal`-shaped phase
   complete-whens into the request blob, then **interpolate** `--repo` /
   `--lang` / `verify_cmd exactly [...]` **values** from that parse (never
   invent a fourth *kind* of argv; typed `--setup-spec` is pass-through),
   then **print the interpolation** before exec. Fail-closed (stop and ask
   for what “done” looks like, not for flags) when the parsed argument
   still has no machine-checkable done — never invent `pytest`, a path, or
   a cwd.
5. Host exec: `bash "$SKILL_ROOT/scripts/devloop-run" -- --lang command "<goal + verify_cmd exactly [...]>"`
   (omit `--lang` / `--repo` when interpolation says so; pass through only
   flags the user typed plus what step 4 interpolated, including
   `--setup-spec`).
6. Report engine stdout/JSON + exit code only. **COMPLETE** only when engine
   exit is 0 **and** the shim printed `AFTER exec exit=0` (and matching
   `--json` delivery/terminal). Exit 2 is not success. Residual host
   campaigns only after that.

**Forbidden:** host-written charters as the acceptance path; host BUILD;
interpolating a fourth argv piece; invoking the host goal harness or `/loop`
to drive DevLoop; suggesting `devloop-native` as “DevLoop.”
