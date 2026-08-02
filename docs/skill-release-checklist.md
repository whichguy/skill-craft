# Skill release checklist (skill-craft → skill-craft-market)

After shipping a skill package change to `main`:

1. **Green suite** for that skill (`bash test/<skill>.test.sh` or `bash test/run-all.sh`).
2. **Plugin view in sync:** `bash scripts/sync-plugin-views.sh <skill>` (or full sync).
3. **Tag** skill-craft at the ship tip, e.g. `git tag -a v0.3.2 -m "…" && git push origin v0.3.2`.
4. **Market pin:** in skill-craft-market `.claude-plugin/marketplace.json` (+ `faces/claude/…`):
   - `source.path` = `plugins/<skill>` (not bare `skills/`)
   - `source.ref` = the new tag
   - `version` = SKILL.md `version:` field
5. **Push market** and operators run: `claude plugin marketplace update skill-craft-market`.
6. skill-dir users: `./install.sh --skill <skill>` (tracks checkout; no tag required).

Pin lag after ship is a bug: marketplace install must not serve pre-ship wording.
