---
bump: patch
---
A refused ShipLoop result now says how to fix it. A result that wraps its fields in action and result keys (the shape of the stored files under results/) is told to move the fields up and delete the named keys; a result missing outcome or summary is told which; a blocked, repeat, revise or replan result that still holds done-only fields (work_items, assumptions, steps, test_commands and the like) is refused once with every such field named; an awaiting wait without no_default is told where it goes, with the exact shape; unsupported fields are named; an Improve opening whose section heading is renamed is told the heading it must read and the headings it found. Each reply ends by telling the model to run the same command again. No check was loosened.
