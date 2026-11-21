## Failing now

none

## Discoveries

- An explicitly configured recovery path must identify a separate file even when the live snapshot already has every deadline. | Observable: Run preparation with both paths pointing to the same fully prepared file. | Why: Preparation exited 2 with a separate-file diagnostic and left the snapshot byte-identical.
- When assigning a deadline from a local clock time, preparation uses the earlier instant in a repeated hour and shifts a nonexistent time forward by the daylight-saving gap. | Observable: With `TZ=America/Los_Angeles` and zero response hours, prepare `2025-03-09T02:30:00` and `2025-11-02T01:30:00`. | Why: The nonexistent spring time advanced to `10:30:00.000Z`, and the repeated fall time used the earlier instant, `08:30:00.000Z`.
