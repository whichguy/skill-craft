---
bump: minor
---
step-plan now sizes its steps. Each step lists the criteria it satisfies (`criteria`) and the paths it changes
(`paths`), and ShipLoop refuses a step plan when:
- a step names no paths;
- a step names no criteria while the item has criteria;
- a step names an unknown criterion;
- a step path is not one of the item's paths;
- a criterion is served by no step;
- a step changes only test files, unless every path of the item is a test file.

The step-plan packet adds sizing directions. Each step is one behaviour-level change that a named check proves.
Split a step that holds two separately confirmable behaviours, crosses a module or layer boundary, needs "and"
between two outcomes, or is too large to recheck in one pass. Merge a step no check can confirm on its own into
the step it serves. A single fix or mechanical rename is one step. The step-plan done-when line states the rule.
