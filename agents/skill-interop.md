---
name: skill-interop
description: >-
  Use when authoring or reviewing a portable multi-host agent skill (Grok,
  Claude Code, Codex, Hermes): scaffold a prompt-only skill, make a skill
  host-agnostic, create skill layout, review skill for interop, or install
  across hosts.
model: inherit
---

# skill-interop

Load and follow the **skill-interop** skill (`skills/skill-interop/SKILL.md` or the
installed `skill-interop` skill). Do not re-author the full review/create procedure here.

- Review / create / install modes: skill card.
- Scaffold: `skills/skill-interop/scripts/scaffold-skill.sh`.
- Checklist and anti-patterns: skill `references/`.
- Install skills + this card: `./install.sh --skill skill-interop --agents`.
