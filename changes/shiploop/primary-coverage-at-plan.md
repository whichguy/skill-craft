---
bump: minor
---
ShipLoop checks that the plan covers the request at plan time, and a step's tests follow that step. Each work item now carries an optional `follows` (the R-<n> it serves and the AD-<n> it follows), and a plan, or a carry-forward queue that replaces the future queue, is refused unless every primary requirement of the spec is in some work item's `follows` (widen the item that serves it or add one). The last test-spec is no longer refused for missing cases of requirements other steps own, so a step is tested for its own intention. The `suite_requirements` row of that last test-spec is retired, with its refusal.
