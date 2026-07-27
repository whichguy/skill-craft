# skill-interop checklist

## Classification

- [ ] Capability is prompt-only, script-backed, or mixed  
- [ ] Mixed: clear seam where prompts end and scripts begin  

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

## Host matrix

| Host | Prompt-only | Scripts | Install |
|------|-------------|---------|---------|
| Grok Build | | | |
| Claude Code | | | |
| Codex | | | |
| Hermes | | copy not abs-symlink to external checkout | |

## Anti-patterns absent

- [ ] No divergent prompt copies per host  
- [ ] No silent native↔measured mode switch  
- [ ] No unresolved `{{tokens}}` after render  
- [ ] No overclaim of validation/EVSI  
