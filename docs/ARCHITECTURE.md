# skill-craft architecture

Host-neutral portable skills monorepo. This document is the packaging contract for
`skills/<leaf>/`, multi-host install, and distribution. Status labels:

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
| Runtime binding | append (**SC-L3**) | **partial** — Hermes materialize + copy lifecycle **implemented**; multi-binding resolver **proposed** |
| Host adapters + distribution | append (**SC-L4 / SC-L5**) | **implemented** (skill-dir install, Claude plugin views, market pins) |
| Provenance (managed installs) | append | **partial** — Hermes `.skill-craft/<leaf>.json` marker **implemented**; full receipts **proposed** |
| Operator / CI | control plane (not a runtime layer) | **partial** — hermetic `test/run-all.sh` **implemented**; GitHub Actions workflow **implemented** |

Optional numbered aliases: `SC-L0`… only when disambiguating from unrelated monorepo “L1/L2” tiers (e.g. question-bench).

### Layer 0 — contract (**implemented**)

Inputs/outputs, artifacts, success vs failure (including empty/no-op), honest product labels.

### Layer 1 — prompts (**implemented**)

Host-agnostic prompt bodies; placeholders only; no model pins; no host-only sole procedure.

### Layer 2 — scripts (**implemented**)

One CLI family per skill; injectable seams; scripts do not re-author planning policy.

### Skill card (**implemented**)

`SKILL.md` is the discovery/router surface. Engines that are CLI-first load this as documentation for chat models, not as the engine’s system prompt.

### Runtime binding — SC-L3 (**partial**)

Binding surfaces are **distinct** (do not collapse into one env var):

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
| skill-craft-market pins (catalog only; no skill bodies) | **implemented** |
| skillctl / full receipts / uninstall | **proposed** |

### Operator / CI (**partial**)

- Hermetic suite: `bash test/run-all.sh` (**implemented**)
- Plugin view drift: `bash scripts/sync-plugin-views.sh --check` (**implemented**)
- CI: `.github/workflows/ci.yml` (**implemented**)

## Materialization policy (Hermes)

- A Hermes leaf is a **local materialization** of a skill-craft package, not content owned by the hermes home git repo.
- Source of truth remains `skill-craft/skills/<leaf>/` (or `--from` path).
- Re-run `./install.sh` to refresh a **managed** copy (marker present). Foreign real trees (no marker) are never clobbered.
- Copy mode is keyed on **host** (Hermes default), not on source path.
- Copied packages must be **self-contained** (no symlinks in the source tree); install refuses otherwise.
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

## Later phases (**proposed**)

| Phase | Content |
|-------|---------|
| P1 | Frontmatter contract for all skills; kind metadata; no dual manifest |
| P2 | Derive `plugin.json` metadata from `SKILL.md`; enumerate views from `skills/` |
| P3 | Full receipts, `--status`, safe uninstall on top of the Hermes marker |
| P4 | Engine probe canary (non-colliding leaf, refusal codes, Hermes-only runtime) |
| P5 | Package-internal symlink support if ever required |

## Related files

- Install: `install.sh`, `skills/skill-interop/references/host-paths.md`
- Interop review: `skills/skill-interop/references/checklist.md`, `anti-patterns.md`
- Ports inventory: `docs/PORT.md`
