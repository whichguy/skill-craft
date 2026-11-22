### R-3 Legacy migration

- The requester decided that startup with `DUE_TIMES=on` fills missing deadlines from stored creation time and priority, saves the file, then listens. Missing deadlines do not cause startup refusal.
- Preserve existing due, all other state, and schema version. Repeat startup with different hours and verify the assigned times are unchanged.
