# Script APIs

The portable entry point remains `scripts/harness.py`. Python callers can import
the selected package's `scripts/harness.py` and `scripts/delivery.py` with that
scripts directory on their module search path. Use one selected package per
process. The callable entry point uses the same operation names, validation,
locking and results as the CLI; it does not parse argv or print.

| API | Result and effects |
| --- | --- |
| `harness.execute(command, *, run, **arguments)` | Returns an operation result. Validates required and unknown arguments before opening the run; locks mutations and leaves `status` read-only. Options use CLI names with underscores. Locators accept absolute strings or `Path` values. |
| `harness.normalized_request(request)` | Returns `(request, warnings)` with detached nested lists and defaults. Resolves the source path; creates no files and leaves the caller's input untouched. |
| `delivery.validate_request(request)` | Returns a detached delivery request with exactly `source`, `workspace`, `mode`, `integration`, and `checks`. Resolves the existing source path; creates no files. |
| `delivery.capture(source)` | Reads the parent Git/filesystem snapshot for a later delivery. |
| `delivery.deliver(run_dir, request, baseline, workers)` | Validates arguments before reserving an immutable delivery attempt, then verifies and optionally applies supplied contributions. It does not collect native results, accept workers, or remove worktrees. Use `execute("finish", ...)` for the complete coordinated delivery and cleanup. |

For example, after importing `execute` from the selected harness:

```python
ready = execute("init", run="/absolute/external/run",
                request="/absolute/external/request.json",
                ask_agent_card="/selected/ask-agent/SKILL.md",
                dispatcher_card="/selected/plan-dispatcher/SKILL.md")
assignments = execute("dispatch", run=ready["run"])
# The caller launches these assignments through native host tools.
recorded = execute("status", run=ready["run"])
```

Request, result and verification inputs remain JSON **file paths**, as in the
CLI. Python calls must inspect returned statuses, including `FAILED`, `BLOCKED`
and `CLEANUP_PENDING`; receiving a dictionary does not establish success.
Harness refusals raise `HarnessError` with `.record`; delivery validation raises
`DeliveryError` with `.payload`. The CLI serializes these diagnostics and exits
2. Malformed CLI syntax also returns a structured diagnostic. Help exits 0.

Invalid delivery arguments return `BLOCKED` before creating an attempt, so they
may be corrected at the same unused run path. Once an attempt is reserved,
operational failures and partial effects remain recorded and are not replayed.
Native lifecycle and semantic acceptance remain coordinator attestations. The
lower-level lifecycle helpers and `Run` object are implementation details; use
`execute` to retain the shared validation and lock boundary.

The bundled `harness_paths.py` centralizes repeated artifact names, selected
script paths and repository-path rules. Native locations use `pathlib`; Git
paths and write scopes always use `/`, regardless of the host separator.
Scopes reject drive prefixes, backslashes, traversal and noncanonical segments
before normalization. Snapshot filenames retain Git's broader POSIX filename
rules. JSON files and helper responses use explicit UTF-8 encoding.

The runtime supports Linux and macOS. It uses POSIX file locks and filesystem
semantics; portable path construction alone does not establish native Windows
support. The helper module remains within the selected package, so copying the
complete skill preserves its imports without a new cross-package dependency.
