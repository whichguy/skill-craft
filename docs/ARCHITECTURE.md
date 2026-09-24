# skill-craft architecture

Host-neutral portable skills monorepo. This document is the packaging contract for
`skills/<leaf>/`, multi-host install, and distribution.

## Learnings (replan)

These drove the final packaging model after advisors review and PR1–P4 landing:

1. **Append, do not renumber** Layer 0/1/2 (contract/prompts/scripts). Silent renumber collides with live checklists and other monorepo “L1/L2” uses.
2. **Hermes abs-symlink was a production bug**, not a docs gap — checklist already required copy; tests enshrined the wrong behavior.
3. **Copy without a lifecycle is a regression** — managed copies need a provenance marker + refresh/skip-foreign state machine.
4. **Frontmatter is the SoT** — optional `skill.manifest.yaml` is dual-SoT; enforce name/version/license/platforms/kind on every leaf first.
5. **`plugin.json` must derive from frontmatter** or version/description drift (and mid-sentence truncation) is inevitable.
6. **Enumerate plugin sync from `skills/`**, not `plugins/` — otherwise new leaves never get Claude views and `--check` stays green.
7. **Discovery ≠ execution** for engines — a four-host skill-dir install is not multi-host runtime.
8. **Foreign real destinations** (e.g. live Hermes `devloop` engine) must classify as `foreign` and never clobber; the `devloop` card skips Hermes install so dest does not collide with the engine leaf.
9. **Extend `install.sh`**, do not invent `skillctl` as a second install CLI.
10. **CI is required** — hermetic green alone coexists with broken host binding if nothing runs `--check` / install tests automatically.

## Status labels

| Label | Meaning |
|-------|---------|
| **implemented** | True of the repo today; tests or live code enforce it |
| **partial** | Some of the contract is live; remainder is proposed |
| **proposed** | Documented intent; not yet enforced |
| **optional** | May never ship |

## Package concerns (normative names)

Do **not** renumber legacy Layer 0–2. Skill-interop reviews and checklists already use them.

| Concern | Legacy id | Status |
|---------|-----------|--------|
| Contract | **Layer 0** | **implemented** |
| Prompts | **Layer 1** | **implemented** |
| Scripts / CLI | **Layer 2** | **implemented** |
| Skill card (`SKILL.md` router) | review step (not a Layer 1 rename) | **implemented** |
| Runtime binding | append (**SC-L3**) | **implemented** for Hermes materialize + installed `devloop` resolution; explicit operator setup is outside packages; Grok/Hermes engine transports, no native Claude/Codex transport |
| Host adapters + distribution | append (**SC-L4 / SC-L5**) | **implemented** (skill-dir install, shared plugin views, Grok/Cursor indexes, Claude/Codex pins) |
| Provenance (managed installs) | append | **implemented** — schema-2 marker + append-only `receipts.jsonl` + `--status` / `--uninstall` |
| Operator / CI | control plane (not a runtime layer) | **implemented** — hermetic suite + GitHub Actions |

Optional numbered aliases: `SC-L0`… only when disambiguating from unrelated monorepo “L1/L2” tiers (e.g. question-bench).

### Layer 0 — contract (**implemented**)

Inputs/outputs, artifacts, success vs failure (including empty/no-op), honest product labels.

### Layer 1 — prompts (**implemented**)

Host-agnostic prompt bodies; placeholders only; no model pins; no host-only sole procedure.

### Layer 2 — scripts (**implemented**)

One CLI family per skill; injectable seams; scripts do not re-author planning policy.

### Skill card (**implemented**)

`SKILL.md` is the discovery/router surface. Engines that are CLI-first load this as documentation for chat models, not as the engine’s system prompt.

### Runtime binding — SC-L3 (**implemented** for Hermes materialize + installed `devloop` resolution)

Binding surfaces are **distinct** (do not collapse into one env var).

**Product default:** bare **DevLoop / devloop** = engine via **`skills/devloop`**
(shim only). Harnesses must not reimplement the loop. Optional offline freeze/prove/stop
is **`evidence-gates`** (demoted; not default). See
`skills/devloop/references/product-default.md`. Host overlay compose
(before / during / after) and the practice list:
[LOOP-ENGINEERING.md](LOOP-ENGINEERING.md).

| Surface | Role |
|---------|------|
| Package root | Directory containing `SKILL.md` |
| Runtime home | e.g. Hermes hub / container data root |
| Write-safe root | Where engines may create workspaces/traces |
| Host-local engine | `~/.local/share/devloop` (explicit operator setup; marker-owned) |
| Transport / launcher bins | Overridable (`HERMES_BIN`, `GROK_BIN`, `DEVLOOP_TRANSPORT`, …) |
| Target repository | Effectful git work for engines |

**Transport honesty:** Hermes host uses Hermes chat transport. Grok uses an installed
engine with Grok capability and `GROK_BIN`, without requiring a Hermes runtime.
Claude/Codex/Cursor require an explicitly selected supported external transport;
the card does not claim those hosts have native engine transports. Missing engines
or unsupported capabilities fail closed, without host-agent loop improvisation.

**devloop clean-laptop path:** the card installs on Grok/Claude/Codex/Cursor, but
never downloads or installs an engine at invocation time. An operator separately
runs `bash scripts/devloop-setup.sh --host grok` from a trusted source checkout.
That repository-only command owns `scripts/devloop-engine-pin.json`, SHA-256
verification, safe extraction, locking and atomic replacement. Before activation,
it checks `pytest` and the engine CLI using the same interpreter selection as the
runtime. Dependencies must already be installed; neither setup nor the packaged
launcher installs them. The card never clobbers the Hermes engine leaf (card install skipped
on Hermes). Missing prerequisites exit 2 with operator guidance.

**Hermes skill-dir install (implemented):** materialize a **managed copy** under
`~/.hermes/skills/software-development/<leaf>` with provenance at
`…/software-development/.skill-craft/<leaf>.json`. Do **not** abs-symlink an external
host checkout into a tree that is bind-mounted into the container as `/opt/data`.

### Delivery — SC-L4/L5 (**implemented** / **proposed**)

| Track | Status |
|-------|--------|
| Skill-dir symlink (Claude, Grok, Codex, Cursor) | **implemented** |
| Skill-dir materialized copy (Hermes default) | **implemented** |
| Shared plugin view `plugins/<leaf>/` via `sync-plugin-views.sh` | **implemented** |
| Plugin bundle `bundles/<plugin>/` → one multi-skill view `plugins/<plugin>/` (vendored, provenance-verified; marketplace-only, never installed by `install.sh`) | **implemented** — `bundles/backchain`; `scripts/sync-vendored-bundles.py` |
| Grok/Cursor same-repository catalogs | **implemented** — generated from skill frontmatter; distribution and publication steps in [distribution.md](distribution.md) |
| `plugin.json` name/version/description/license derived from `SKILL.md` | **implemented** (`scripts/skill-frontmatter-to-plugin-json.js`; sync enumerates from `skills/`) |
| skill-craft-market pins (catalog only; no skill bodies) | **implemented** |
| `install.sh --status` / `--uninstall` (owned only) | **implemented** |
| skillctl | **optional / not planned** (use `install.sh`) |
| Default DevLoop card `skills/devloop` | **implemented** (discovery on Claude/Grok/Codex/Cursor; Hermes card skipped; installed-engine resolution only; separate operator provisioning) |
| Demoted evidence gates `skills/evidence-gates` | **implemented** (offline freeze/prove/stop; not DevLoop) |
| Grok engine transport (no Hermes) | **implemented** (card host affinity + pin `transports: [hermes, grok]`; [`devloop-engine-v0.2.0` was published on GitHub](https://github.com/whichguy/skill-craft/releases/tag/devloop-engine-v0.2.0) on 2026-08-15; publication does not establish host installation or execution) |

### Operator / CI (**implemented**)

- Hermetic suite: `bash test/run-all.sh` (**implemented**) remains the complete
  local aggregate. `--group smoke` runs core plus eight selected ShipLoop graph and
  boundary suites; it is partial evidence, never a full-regression claim.
  `test/shiploop.test.sh --smoke` selects those eight from the one canonical
  inventory, while no-argument/all and `--shard 1/3|2/3|3/3` preserve the full
  behavior. No installed AI host or engine is required; core's bundled mock also
  covers marketplace-style binding from an empty unrelated directory.
- Plugin view drift: `bash scripts/sync-plugin-views.sh --check` (**implemented**)
- CI: `.github/workflows/ci.yml` (**implemented**); pull requests and `main`
  pushes use the smoke tier. Manual dispatch defaults to smoke and can select
  `tier=full`, which runs core plus three deterministic ShipLoop shards for
  runtime/state/graph/callback changes and release qualification. The fail-closed
  `hermetic` status remains the aggregate gate. A full run only qualifies the
  matching final SHA/tree; it is not a substitute for the PR smoke gate.
  Each selected test job rejects staged or unstaged tracked changes after
  their suites, including failed suites; package parity runs with core or smoke.
- External integrations: explicitly selected via `bash test/run-integration.sh`;
  never pulled into the required CI aggregate. Live Grok E2E audits are also
  opt-in, use `xhigh` with a 7,200-second cap, and are distinct from hermetic
  graph checks. See [test runners](../test/README.md).

## Materialization policy (Hermes)

- A Hermes leaf is a **local materialization** of a skill-craft package, not content owned by the hermes home git repo.
- Source of truth remains `skill-craft/skills/<leaf>/` (or `--from` path).
- Re-run `./install.sh` to refresh a **managed** copy (marker present). Foreign real trees (no marker) are never clobbered.
- Copy mode is keyed on **host** (Hermes default), not on source path.
- Package trees may contain **package-internal** symlinks (targets resolve under the package root); install **dereferences** them into real files on materialize. Symlinks that escape the package root are **refused** (fail closed).
- When `~/.hermes` is a git work tree, install prints a gitignore hint. Operator applies ignore rules; install never writes `~/.hermes/.gitignore`.

## Package kinds

| Kind | Status |
|------|--------|
| `prompt-only` | **implemented** — `metadata.skill_craft.kind` on every `skills/*/SKILL.md` (enforced by `test/skill-frontmatter.test.js`) |
| `script-backed` | **implemented** (same) |
| `mixed` | **implemented** (vocabulary allowed; use when prompts + scripts are both material) |
| `engine` | **proposed** as orthogonal/subtype of script-backed (not a silent replacement for `mixed`) |

Minimum frontmatter contract (**implemented** for all leaves): `name` (= leaf), `description`, `version`, `license`, `platforms` (linux/macos), `metadata.skill_craft.kind`.  
skill-interop additionally requires Hermes-peer fields (`author`, `metadata.hermes.category`, Use-when description).

## Honesty rules

1. **Discovery ≠ execution.** Installing a skill card on four hosts does not prove multi-host runtime.
2. Host matrix cells for engines mean **runtime** capability (transport + binding), not skill-dir success.
3. Abs external symlink into a bind-mounted Hermes skill home is forbidden.
4. Unprovenanced real directories are **foreign** — never claimed as managed installs.
5. Do not overclaim validation/measurement without packaging or an eval backend.

## Dual-track distribution

```text
skill-craft/skills/<leaf>/     # SoT (all hosts skill-dir)
        │
        ├── install.sh ──► ~/.claude|grok|codex|cursor/skills/<leaf>   (symlink)
        │              ──► ~/.hermes/skills/software-development/<leaf>  (copy)
        │
        └── plugins/<leaf>/    # shared marketplace package (materialised copy)
                 ▲
                 ├── skill-craft Grok/Cursor indexes: ./plugins/<leaf>
                 └── skill-craft-market Claude/Codex pins: plugins/<leaf>

skill-craft/bundles/<plugin>/  # vendored multi-skill source (bundle.json + PROVENANCE.json)
        │                      # never enumerated by install.sh
        └── plugins/<plugin>/  # one plugin: skills/<member>/…, agents/…, host manifests
                 ▲
                 ├── skill-craft Grok/Cursor indexes: ./plugins/<plugin>
                 └── skill-craft-market Claude/Codex: plugins/<plugin>
```

### Plugin bundles (**implemented**)

A bundle packages several upstream skills as one plugin whose skills are
invoked as `<plugin>:<member>`. `bundles/<plugin>/bundle.json` declares the
member skills and agent cards; the member named like the bundle is the primary
card and supplies version, license, author and category. `PROVENANCE.json`
records the upstream commit and each copied file's sha256 and git blob id.
`scripts/sync-vendored-bundles.py --check` verifies those bytes offline (it runs
before every bundle view is written or checked) and applies a publication lint;
CI therefore proves consistency with the recorded provenance, not equality with
a private upstream. Only a local `--from` refresh or dry run compares against
upstream, and it reads committed blobs published on upstream `origin/main`.
A member name may never also be a `skills/<leaf>`. `install.sh` never
installs bundle members, and `install.sh --from` refuses bundle and
generated-view paths in a skill-craft checkout plus any copy whose plugin
manifest names the skill-craft repository (host plugin caches, git-subdir
clones), so the canonical skill-directory links are not duplicated or
repointed at a marketplace copy that still carries its generated manifests.

## Out of scope (product repos)

claude-craft product suites (wiki, gas, async, …) stay host-native. Portable leaves port here; suite hooks/agents may remain in claude-craft.

## Phase completion

| Phase | Content | Status |
|-------|---------|--------|
| PR1 | ARCHITECTURE + Hermes copy lifecycle + CI + honesty | **done** |
| P1 | Frontmatter contract + kinds | **done** |
| P2 | Derive `plugin.json` from `SKILL.md` | **done** |
| P3 | `--status` / `--uninstall` | **done** |
| P4 | `skills/devloop` probe card | **done** |
| Market pins | skill-craft-market → full commit `sha` for every leaf, with release tag or `main` as a reachability label | **done** |

### Package-internal symlinks (**implemented**)

Package trees may contain **package-internal** symlinks (targets resolve under the package root).
Both **Hermes materialization** (`install.sh`) and **Claude plugin-view sync**
(`scripts/sync-plugin-views.sh`) **validate** then **dereference** them into real files
(`rsync -aL` / `cp -R -L`). Symlinks that **escape** the package root are **refused**
(fail closed; no partial write). Post-sync / post-materialize trees must contain **no**
residual symlinks (Claude git-subdir cannot follow them under `plugins/`).

**skill-craft-market** Claude-compatible catalog (also read by Codex) pins skill-craft `plugins/<leaf>` at a full commit **`sha`**, optionally labeled with a git **`ref`**
(release tags such as **`v0.3.0`** / **`v0.3.3`** per leaf). External leaves (e.g.
**lennox-s40**) pin a **standalone** repo URL — this monorepo must not also ship
`skills/<same-name>/`. A private upstream (Backchain) is published instead as a
vendored plugin bundle, so its catalog entry selects `plugins/<plugin>` here. Advance a pin only when that leaf’s content or package version
changes at a released tag or verified published commit (no bulk retarget of
content-identical pins). Untagged published packages may use `ref: "main"` plus a
full commit `sha`; the SHA fixes package bytes. Catalog validation checks version
parity at that SHA and reachability from the declared ref.



## Exit codes (`install.sh`)

| Code | Meaning |
|------|---------|
| 0 | Success (no refusals) |
| 2 | Needs human / binding incomplete (reserved; used by engine cards) |
| 3 | **Foreign-refused** — install or uninstall hit an unowned path |
| 4 | **Absent** — uninstall found nothing owned |
| 8 | **Drift-blocked** (reserved for drift-aware uninstall) |
| 64 | Usage / flag error |

Foreign trees are never clobbered; refusals are **nonzero** so automation cannot treat a skip as success.

## Residual / quality review discipline

Hermetic residual×2 and similar loops should run in a **detached git worktree**
at a pinned SHA (not a dirty shared checkout). Use smoke for routine iteration;
use full regression for runtime/state/graph/callback changes and release
qualification. Capture the chosen suite status mechanically:

```bash
set -o pipefail
test_tier=smoke
bash test/run-all.sh --group "$test_tier" 2>&1 | tee run-all.log
echo "EXIT=${PIPESTATUS[0]}" | tee -a run-all.log
```

A smoke cycle may not claim full-regression coverage. Any cycle may not claim
PASS without a trailing `EXIT=0` line (or attributed non-packaging failures only).

## devloop bootstrap (host-local)

Portable card on Grok/Claude/Codex/Cursor. Engine materializes under
`~/.local/share/devloop` (or `$XDG_DATA_HOME/devloop`) via `--setup` / first run
when missing, without overwriting Hermes skillhub leaf `devloop`. See
`skills/devloop/references/bootstrap.md`.

## Reserved leaf names

| Leaf | Role |
|------|------|
| `devloop` | **Default DevLoop** portable card (`skills/devloop`). Dest = leaf on Claude/Grok/Codex/Cursor. Hermes card install is skipped — engine owns `software-development/devloop`. |
| `evidence-gates` | Demoted offline evidence gates; must not steal bare “devloop” discovery. |

## Related files

- Install: `install.sh`, `skills/skill-interop/references/host-paths.md`
- Interop review: `skills/skill-interop/references/checklist.md`, `anti-patterns.md`
- Engine probe: `skills/devloop/`
- Ports inventory: `docs/PORT.md`
