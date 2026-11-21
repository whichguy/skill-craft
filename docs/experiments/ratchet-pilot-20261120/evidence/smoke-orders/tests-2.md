## Failing now

none

## Discoveries

- The parser preserves negative zero when ID or price underflows during conversion. | Observable: Parse `id=-2e-324;qty=1;price=-2e-324;status=open;shipped_at=` and check `Object.is(order.id, -0)` and `Object.is(order.price, -0)`. Both are true. | Why: The price passes the minimum check at zero, and the returned fields retain the sign produced by conversion.
- The running sum follows the input array order. | Observable: With quantity `1` on every order, prices `[9007199254740992, 1, 1]` total to `9007199254740992`, while `[1, 1, 9007199254740992]` total to `9007199254740994`. | Why: Each one-cent addition rounds away when the large amount comes first, and the two cents survive when they are added together first.
- After the ID passes validation, the parser checks status, then the shipping date format, then whether the status and date agree. | Observable: With valid numeric fields, `status=pending;shipped_at=bad` reports a status error, `status=open;shipped_at=bad` reports a date format error, and `status=open;shipped_at=2026-10-01` reports that the date must be empty. | Why: Probes for diagnostic precedence showed which error wins when the status or date has multiple problems.
