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

Load and follow the **skill-interop** skill selected by the host for this plugin
or skill-dir installation. Use the selected card's absolute path (expanding its
host alias when needed), not a path relative to the user's project. If the host
cannot identify the selected card, report that prerequisite instead of choosing
an ambient same-named skill. Do not re-author the full procedure here.

- Review / create / install modes: skill card.
- Scaffold: bind and run the selected card's absolute `SCAFFOLD` helper.
- Checklist and anti-patterns: skill `references/`.
- Optional source-checkout install: use an explicitly selected trusted checkout's
  installer with `--skill skill-interop --agents`. That repository installer is
  not part of this installed plugin; marketplace operations use the card's
  bundled `MARKETPLACE_RUN` helper.
