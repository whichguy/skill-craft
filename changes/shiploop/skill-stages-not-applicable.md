---
bump: minor
---
A done step-plan result may carry `skill_na`, the reason no repo-local skill is selected, created or changed for the item: ShipLoop then records skill-assess and skill-validate as not applicable to that item, with a history row and a result file whose text starts "Not applicable to this item" and carries that reason, instead of issuing them. A step plan that lists a skill file in `paths` is refused with `skill_na` (at `complete` and at `improve-complete`), and `document`'s done is refused when the item's real diff touches a skill file; without `skill_na`, or after either refusal, both stages run as before. The skill-file lists are the new `skill_surface` data in `references/path-classes.json`, not a path class.
