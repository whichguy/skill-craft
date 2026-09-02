# Ledger contract (copied, not imported)

Copied from review-coverage public grammar. Do not import
`skills/review-coverage/scripts/review-coverage` private `_` helpers.
Do not author STATIC / halt sentences here.

## Status line (REVIEW_CONVERGE.md)

```
(?im)\bStatus\b[^\n]*(?P<state>stopped\s*\([^\n)]*\)|complete\b|active\b)
```

## Plan binding (ledger header)

```
(?im)^\*\*Plan contract:\*\*\s*`?(?P<path>[^`\n]+?)`?\s*$
(?im)^\*\*Plan hash:\*\*\s*`?(?P<hash>[0-9a-fA-F]{64})`?
```

## Landed latest log

Latest `### Round` / `### Round N` section must contain:

- `(?im)^\*\*Committed:\*\*\s*yes\b`
- `(?im)(?:review-converge|grok-review-converge):\s*round\s+\d+\s*—`

`Committed: no` is not landed. `stopped (...)` is halt, not `done`.
Landed also holds when read-only `git log --grep` finds that latest-round
subject; the latest round must still say `Committed: yes`.

## Waiver (bound plan file only)

Unfenced inside H2 `## Review Coverage` only:

```
(?im)^[ \t]*None\s*[—–-]\s*residual\s+loop\s+waived\s*:\s*(?P<reason>\S.+?)\s*$
```

Placeholder reasons (`<reason>`, `tbd`, `todo`) are not waivers.
Ledger-local “waiver” prose is not a waiver.
