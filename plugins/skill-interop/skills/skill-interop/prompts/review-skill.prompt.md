# Review a skill for multi-host interop

You review an agent **skill package** for portability across Grok Build, Claude Code, Codex, and Hermes.

## Input

Goals / user intent:
{{GOALS}}

Skill tree (paths + key file excerpts):
{{SKILL_TREE}}

## Task

1. Classify: prompt-only vs script-backed vs mixed.  
2. Check Layer 0 contract, Layer 1 prompts, Layer 2 scripts (if any).  
3. Fill a host matrix for Grok / Claude Code / Codex / Hermes.  
4. List **material** vs **minor** findings.  
5. Propose smallest migration steps (prompt extraction first).  

Reject: host-only instructions as sole procedure, divergent host prompt copies, silent mode fallback, unresolved `{{TOKENS}}`, overclaim of validation/EVSI, silent empty success.

## Output

Markdown with sections: Classification · Contract · Prompts · Scripts · Host matrix · Findings · Migration steps.
