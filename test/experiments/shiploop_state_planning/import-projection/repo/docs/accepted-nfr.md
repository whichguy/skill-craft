# Accepted fixture NFR record F-17

The following criteria are accepted for this synthetic planning input. They are
release evidence requirements, not results already observed in this repository.

- At 20 concurrent imports with 250 rows each and five simultaneous summary
  editors per import, edit application has p95 latency at or below 250 ms.
- Under that workload, projection lag from accepted edit to the compatible
  projection has p95 at or below 2 seconds.
- A 30-minute mixed-reader stage records zero version-1 or version-2 decode
  failures for the staged projection shape.
- Every stale competing edit is rejected explicitly; no accepted edit may be
  silently lost.

The first three are workload/operational criteria. Explicit stale-edit rejection
is a functional correctness condition that also needs observation at workload;
passing a unit test alone does not establish the workload criteria.

