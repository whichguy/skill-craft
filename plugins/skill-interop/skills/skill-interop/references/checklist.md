# skill-interop checklist

See also [docs/ARCHITECTURE.md](../../../../docs/ARCHITECTURE.md) for packaging layers and status labels.

## Classification

- [ ] Capability is prompt-only, script-backed, or mixed  
- [ ] Mixed: clear seam where prompts end and scripts begin  
- [ ] Engine (if claimed): orthogonal to mixed/script-backed; host matrix states runtime honestly  

## Layer 0 — contract

- [ ] Inputs/outputs documented (JSON schema or fixed text envelope)  
- [ ] Artifact names listed  
- [ ] Success vs failure explicit (including empty/no-op)  
- [ ] Product labels honest (e.g. unvalidated vs packaged)  

## Layer 1 — prompts

- [ ] No model names, provider URLs, effort knobs  
- [ ] No host CLI / “run this script” as the only procedure  
- [ ] Placeholders `{{LIKE_THIS}}` only  
- [ ] Empty outcome is explicit (not silent success)  

## Layer 2 — scripts (if any)

- [ ] One CLI family for all hosts  
- [ ] Injectable side effects for tests  
- [ ] stdlib-first when possible  
- [ ] Documented when full checkout is required  
- [ ] Scripts do not re-encode planning policy (call prompts instead)  

## Skill card

- [ ] Short router: when to use / not for  
- [ ] Canonical invoke matches real CLI or honest discovery-only claim  

## Runtime binding (SC-L3)

- [ ] Package root = directory containing `SKILL.md`  
- [ ] Scripts resolve relative to package root (or documented `SKILL_ROOT`), not ambient cwd alone  
- [ ] Write-safe / runtime home / transport bins named separately (do not collapse into one env var)  
- [ ] Hermes skill-dir: materialization is a managed copy (not abs-symlink to external checkout)  

## Host adapters / distribution

- [ ] Skill-dir install path documented per host  
- [ ] Claude plugin view (if any) is derived from `skills/`, not a second SoT  
- [ ] Marketplace pins contain no skill bodies  

## Honesty

- [ ] Discovery ≠ execution for engine/runtime claims  
- [ ] Host matrix cells for engines mean runtime capability  
- [ ] Foreign real trees never claimed as managed installs  

## Operator / CI

- [ ] Hermetic tests cover install and contract surfaces used by this skill  
- [ ] Plugin view `--check` green when Claude view ships  

## Host matrix

| Host | Prompt-only | Scripts | Install |
|------|-------------|---------|---------|
| Grok Build | | | symlink skill-dir |
| Claude Code | | | symlink skill-dir and/or plugin view |
| Codex | | | symlink skill-dir |
| Hermes | | | **materialized copy** (not abs-symlink to external checkout); materialization ≠ synced content |

## Anti-patterns absent

- [ ] No divergent prompt copies per host  
- [ ] No silent native↔measured mode switch  
- [ ] No unresolved `{{tokens}}` after render  
- [ ] No overclaim of validation/EVSI  
- [ ] No silent empty success  
- [ ] No abs external symlink as sole Hermes install into bind-mounted skill home  
- [ ] No engine multi-host claim without transport/binding  
- [ ] No unprovenanced materialized tree claimed as managed  
