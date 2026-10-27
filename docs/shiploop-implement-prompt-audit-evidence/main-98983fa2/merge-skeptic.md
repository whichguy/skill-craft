# Merge review findings

## P1: `slice.py --effort-schedule` always fails before launching the scheduled slice

[test/shiploop_e2e/slice.py:376]( /tmp/shiploop-main-conflict-20261025T142207/verification/test/shiploop_e2e/slice.py:376 ) assigns `effort` to the selected effort string (`model, effort = ...`). The imported `effort` module is therefore shadowed for the rest of `main()`. When a schedule is supplied, [line 389]( /tmp/shiploop-main-conflict-20261025T142207/verification/test/shiploop_e2e/slice.py:389 ) calls `effort.parse_schedule(...)`, raising `AttributeError: 'str' object has no attribute 'parse_schedule'`; the `except effort.ScheduleError` path also refers to the shadowed string. This makes the slice experiment entry point unusable for every host and schedule.

Smallest verification: invoke `slice.main()` with a valid `--effort-schedule` JSON argument and observe the `AttributeError` before the first session launch. Rename the local string (for example `effort_level`) or alias the imported module, then exercise this entry point.
