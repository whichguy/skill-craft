---
bump: patch
---
The one-pass plan packet now says the whole Backchain child is the host's choice (nothing refuses a plan without it, and ShipLoop cannot see whether it ran), that the dependency audit is not optional, and that the result's summary names the route taken. A `backchain-check` on a candidate that is not JSON now points at Backchain's "Plan document shape" instead of leaving the model to read the checker's source.
