---
bump: minor
---
Tests stay green after every stage that can edit code. On done at
`test-refine`, `static-checks` and `integration-verify`, ShipLoop reruns every
test command the step plan recorded and refuses unless each exits 0; the packet
lists the commands. Each action allows 3 refused test runs (at these stages and
the test loops); after that only `blocked` is accepted, so a restarted loop can
no longer retry forever. The lint gate now also runs on done at `test-green`
and `regression`, before the test run, since the test loops edit code too;
`lint_waivers` are accepted there as at `implement`.
