## On the starting project

- No existing clauses failed.
- No other clauses passed.
- All 115 commands printed their item ID. The 23 existing clauses and two existing use cases passed the portions observable through the shipped provider and fixtures. The 90 remaining items failed. C-100 ran the baseline's `npm test` and observed zero tests. The other 89 could not observe their requested application behavior because the baseline has no chat service.
- For existing clauses with application obligations, such as C-7, C-70 and C-76, the passing baseline check covers only the shipped fixture or provider contract. The corresponding HTTP and browser tests run when the service is delivered.

## Assumed

- The supplied computer's macOS WebKit and `swiftc` are available for real-browser checks. The local Node executable was v26.12.1. The baseline checks used that executable.
- A 540 CSS pixel viewport represents a narrow window for the responsive checks. The typography check uses 10 CSS pixels as a floor for visibly tiny transcript text.
- The browser's same-origin command transport uses `fetch` with JSON for addressed mutations. The adapter learns URLs, methods, and payloads from the actual UI. Where a replay needs the destination selection version, it substitutes version or revision fields recognized in the observed command.
- Closing and recreating a browser page with its session retained is the return event used for the task summary. The checks avoid specifying when activity becomes seen.
- The default-port check starts with `PORT` unset after the OS confirms port 3000 is free. If another process holds it throughout the bounded wait, the command reports the default observation as unavailable and exercises an OS-assigned port.
- The C-22 delivery check observes the supplied provider's bytes and execution during a served reply. A dormant provider copy that is neither executed nor served is outside that observation.

## Discoveries

- A test command must run at least one rule test to establish C-100. | Observable: Inspect the Node test report and execution of files under `test/`. | Why: The starting checkout's `npm test` exits successfully and reports zero tests.
- Provider reply text is displayed subject to the credential secrecy requirement. | Observable: Put the exact configured test credential in a prompt that normally echoes and inspect the returned pages and responses for it. | Why: The stand-in's ordinary fallback echoes input, so an unconditional exact-text comparison would contradict C-20 in that case.
- A steering acknowledgement from the provider is distinct from the outcome of appending a step. | Observable: Inspect the feedback and task progress after sending a steering request with no eligible task or with a task that finishes during the reply. | Why: The offline provider returns affirmative steering text without observing the worker's state.
