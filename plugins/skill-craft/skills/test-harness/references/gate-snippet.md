## Local-change gate

`SKILL_ROOT` is the directory of the loaded test-harness `SKILL.md`; resolve it before pasting (never a guessed install path).

**Required** after edits (do not treat bare suite exit 0 as done):

```bash
bash "$SKILL_ROOT/scripts/run-harness.sh" \
  --repo "<WORK_ROOT portable>"
```

Require `PASS_CLEAN` or `PASS_CLEAN_SCOPED`. Paste `chat-card.md`.

| | |
|---|---|
| **Inner suite** | `<cmd harness discovers>` |
| **Residual** | live checks and evals — not RESULT |

See `references/local-change-gate.md` in the same skill.
