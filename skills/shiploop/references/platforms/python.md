# Python development

Return to the [guidance selector](../coding-guidance.md#select-guidance) when
the runtime or boundary changes. Use the supported interpreter and current
repository packaging, test, lint, and type-checking conventions. Define mutable
state ownership, iterator consumption, exception contracts, and resource
lifetime where callers can observe them. Use context managers or an appropriate
[cleanup stack](https://docs.python.org/3/library/contextlib.html#contextlib.ExitStack)
so partial setup releases acquired resources; avoid shared mutable defaults and
leaked test state.

Prefer argument-list subprocess APIs when a shell is unnecessary. Check status
and timeouts while preserving causal failure information. Async work must
preserve [cancellation](https://docs.python.org/3/library/asyncio-task.html#task-cancellation)
and bounded task ownership; cleanup must not silently turn failure into success.
Exercise representative malformed input, failure or cancellation paths, and
isolated temporary resources at the actual boundary.

Use parameterized or property/state-based tests when an invariant and independent
oracle justify them; do not mandate another framework for a few concrete cases.
Lint, types, and behavioral tests answer different questions. Review automated
fixes against the accepted contract, including empty inputs, error behavior, and
iterator side effects. An unsafe fix needs explicit review and relevant tests.
