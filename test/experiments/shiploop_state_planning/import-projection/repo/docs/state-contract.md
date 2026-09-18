# Import state contract

Each imported file has an `id`, `revision`, `state`, source row count, and a
summary list. The valid transitions are:

```text
received -> validating -> accepted -> projecting -> projected
                       \-> rejected
projecting -> failed -> projecting
```

`projected` and `rejected` are terminal for one import revision. A corrected
file starts a new import revision; it does not reopen a projected record.

Summary edits are accepted only in `accepted` or `projecting`. Every edit carries
the caller's expected revision. A stale revision must receive a conflict result,
not last-writer-wins behavior. A projection records the import ID and the source
revision used to construct it.

