# Living spec

## Requirements

- R-1: `render_summary(rows)` emits exactly `<target>: <status>\n` for each row in input order, with no leading or trailing spaces; an empty list returns the empty string.
- R-2: The ready local service preview journey can be observed separately from the read-only readiness probe.
- R-3: The local sandbox starts unprovisioned and unconfigured. Local provision/configuration is explicitly authorized; readiness requires a valid setup receipt, and the sandbox journey is a separate observation.
- R-4: The external grant starts unavailable and unauthorized. No grant or credential is supplied; the external-dependent journey remains outside this fixture's authority.
