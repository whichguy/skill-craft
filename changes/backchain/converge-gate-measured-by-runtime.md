---
bump: patch
---
The convergence reference says what the bundled Until Loop runtime does at `required_trivial_reviews: 2` now: it measures the plan unchanged since the previous pass instead of counting two reviews, needs a Git workspace, and (bundled card only) can cover the bytes of each `candidate_paths` file. The default exit condition still asks for two consecutive distinct reviews; the runtime's measurement is an additional necessary condition.
