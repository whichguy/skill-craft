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
8. **Foreign real destinations** (e.g. live Hermes `devloop` engine) must classify as `foreign` and never clobber; thin cards use non-colliding leaves (`devloop-run`).
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
| Runtime binding | append (**SC-L3**) | **implemented** for Hermes materialize + probe resolve (`devloop-run`); full multi-transport matrix remains optional |
| Host adapters + distribution | append (**SC-L4 / SC-L5**) | **implemented** (skill-dir install, Claude plugin views, market pins) |
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

### Runtime binding — SC-L3 (**implemented** for Hermes materialize + `devloop-run` resolve)

Binding surfaces are **distinct** (do not collapse into one env var). Full multi-transport
matrix beyond Hermes/`DEVLOOP_HOME` remains **optional**.

| Surface | Role |
|---------|------|
| Package root | Directory containing `SKILL.md` |
| Runtime home | e.g. Hermes hub / container data root |
| Write-safe root | Where engines may create workspaces/traces |
| Transport / launcher bins | Overridable (`HERMES_BIN`, `CLAUDE_BIN`, …) |
| Target repository | Effectful git work for engines |

**Hermes skill-dir install (implemented):** materialize a **managed copy** under
`~/.hermes/skills/software-development/<leaf>` with provenance at
`…/software-development/.skill-craft/<leaf>.json`. Do **not** abs-symlink an external
host checkout into a tree that is bind-mounted into the container as `/opt/data`.

### Delivery — SC-L4/L5 (**implemented** / **proposed**)

| Track | Status |
|-------|--------|
| Skill-dir symlink (Claude, Grok, Codex) | **implemented** |
| Skill-dir materialized copy (Hermes default) | **implemented** |
| Claude plugin view `plugins/<leaf>/` via `sync-plugin-views.sh` | **implemented** |
| `plugin.json` name/version/description/license derived from `SKILL.md` | **implemented** (`scripts/skill-frontmatter-to-plugin-json.js`; sync enumerates from `skills/`) |
| skill-craft-market pins (catalog only; no skill bodies) | **implemented** |
| `install.sh --status` / `--uninstall` (owned only) | **implemented** |
| skillctl | **optional / not planned** (use `install.sh`) |
| Engine probe card `skills/devloop-run` | **implemented** (discovery all hosts; execution if engine resolves) |

### Operator / CI (**implemented**)

- Hermetic suite: `bash test/run-all.sh` (**implemented**)
- Plugin view drift: `bash scripts/sync-plugin-views.sh --check` (**implemented**)
- CI: `.github/workflows/ci.yml` (**implemented**)

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
skill-craft/skills/<leaf>/     # SoT (all hosts skill-dir; Grok/Codex/Hermes docs)
        │
        ├── install.sh ──► ~/.claude|grok|codex/skills/<leaf>   (symlink)
        │              ──► ~/.hermes/skills/software-development/<leaf>  (copy)
        │
        └── plugins/<leaf>/    # Claude marketplace view (materialised copy)
                 ▲
                 └── skill-craft-market pins path: plugins/<leaf>
```

## Out of scope (product repos)

claude-craft product suites (wiki, gas, async, …) stay host-native. Portable leaves port here; suite hooks/agents may remain in claude-craft.

## Phase completion

| Phase | Content | Status |
|-------|---------|--------|
| PR1 | ARCHITECTURE + Hermes copy lifecycle + CI + honesty | **done** |
| P1 | Frontmatter contract + kinds | **done** |
| P2 | Derive `plugin.json` from `SKILL.md` | **done** |
| P3 | `--status` / `--uninstall` | **done** |
| P4 | `skills/devloop-run` probe card | **done** |
| Market pins | skill-craft-market → tagged `ref: v0.3.0` for released leaves; new leaves may pin `main` until tagged | **done** |

### Package-internal symlinks (**implemented**)

Package trees may contain **package-internal** symlinks (targets resolve under the package root).
Both **Hermes materialization** (`install.sh`) and **Claude plugin-view sync**
(`scripts/sync-plugin-views.sh`) **validate** then **dereference** them into real files
(`rsync -aL` / `cp -R -L`). Symlinks that **escape** the package root are **refused**
(fail closed; no partial write). Post-sync / post-materialize trees must contain **no**
residual symlinks (Claude git-subdir cannot follow them under `plugins/`).

**skill-craft-market** Claude catalog pins skill-craft `plugins/<leaf>` at a git **`ref`**
(currently **`v0.3.0`** for the tagged catalog, or **`main`** for leaves not yet on that
tag — e.g. `lennox-s40`). After a packaging release, retarget catalog refs/tags so
marketplace consumers pick up derived `plugin.json` versions.


## Related files

- Install: `install.sh`, `skills/skill-interop/references/host-paths.md`
- Interop review: `skills/skill-interop/references/checklist.md`, `anti-patterns.md`
- Engine probe: `skills/devloop-run/`
- Ports inventory: `docs/PORT.md`
