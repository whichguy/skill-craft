---
name: prompt-on-change
description: >-
  Use when the user wants to watch a URL or page field and promote a prompt
  when it changes (price, status, HTTP, date/regex conditions).
model: inherit
---

# prompt-on-change

Load and follow the **prompt-on-change** skill (`skills/prompt-on-change/SKILL.md`
or the installed `prompt-on-change` skill). Do not re-author the procedure here.

- Native default: `prompts/author.prompt.md`, then same-turn
  `prompts/escalation.prompt.md` if the detect CLI prints `LLM_ESCALATION:`.
- Optional CLI: `scripts/prompt-on-change` (bootstrap / validate / run / claim).
- Install this card: `./install.sh --skill prompt-on-change --agents`.
