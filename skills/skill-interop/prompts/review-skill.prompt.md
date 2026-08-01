# Review a skill for multi-host interop

You review an agent **skill package** for portability across Grok Build, Claude Code, Codex, and Hermes.

## Input

Goals / user intent:
{{GOALS}}

Skill tree (paths + key file excerpts):
{{SKILL_TREE}}

## Task

1. Classify: prompt-only vs script-backed vs mixed. Treat **engine** as an honesty/runtime claim (orthogonal), not a silent replacement for `mixed`.  
2. Check **Layer 0** contract, **Layer 1** prompts, **Layer 2** scripts (if any). Do not renumber these layers.  
3. Check skill card honesty and **runtime binding** (package root; separate write-safe / transport; Hermes = materialize-copy not abs-symlink to external checkout).  
4. Fill a host matrix for Grok / Claude Code / Codex / Hermes. For engines: discovery ≠ execution.  
5. List **material** vs **minor** findings.  
6. Propose smallest migration steps (prompt extraction first).  

Reject: host-only instructions as sole procedure, divergent host prompt copies, silent mode fallback, unresolved `{{TOKENS}}`, overclaim of validation/EVSI, silent empty success, abs external Hermes symlink into bind-mounted skill home, engine multi-host claims without transport, unprovenanced “installed” trees.

## Output

Markdown with sections: Classification · Contract · Prompts · Scripts · Binding · Host matrix · Findings · Migration steps.
