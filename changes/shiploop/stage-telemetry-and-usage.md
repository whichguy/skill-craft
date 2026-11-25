---
bump: minor
---

Add stage entry/pause/active lifecycle timing and passive per-session token usage telemetry:

- Record `entered`, `paused_since`, `paused_action`, and `paused_seconds` in derived `RUN/timeline.json`, preserving superseded, send-back, and Improve action entries without adding telemetry bloat to `state.md`.
- Extend `shiploop_keepalive.py` at the thin host-adapter boundary with fail-open `observed_usage()` extraction for Codex rollout `token_count`, deduplicated Claude Code transcript `message.usage`, and normalized hook `payload["usage"]`, deduplicated in `STOP_MEMORY` and written as `hook=usage` events via `shiploop_trace.record_usage()`.
- Compute monotonic per-`(host, session)` token deltas, `active_seconds`/`wall_seconds`/`paused_seconds`/`duration_basis` (`recorded_entry`, `first_packet`, `accept_delta`, `unmeasured`), and stage `(model, effort)` metadata in `shiploop_trace.py` (`build()` and non-locking `telemetry_summary()`), resolving no-packet stages such as `validate-existing` and excluding passive `model`/`usage` hooks from stop-hook counts.
- Surface stage active/paused timing, token totals, and model metadata in `shiploop_story.py`, `status_block()` (when traced or requested via `include_telemetry=True`), `shiploop_progress_data.py`, `shiploop_progress_render.py`, and `shiploop_trace_page.py`.
