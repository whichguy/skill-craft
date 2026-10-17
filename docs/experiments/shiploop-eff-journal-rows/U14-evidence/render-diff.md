# Render diff, before and after (unit U14), classified

Method: SP/eff2/final-verify/fv_heads.py on this branch before and after the source change (node-fix-bug, offline step slice, bare CLI path, 83-character default temp path); temp-dir names, action ids and hex ids normalised with sed before diffing. The 163 render differs by the same lines only. Every added or removed line is one of four changes.

| line | direction | unit row | characters | where |
|---|---|---|---|---|
| 'Refused runs for this action so far: 0 of 11 (base and candidate runs together); after that the item goes back to its step plan (revise). A run that times out ...' | removed at N = 0 | TD-10 | -223 | test packet, head and file |
| duty 2: 'locators and the step plan's in evidence_refs.' (reflowed to 2 lines) | removed | TD-12 | -50 | test packet, head and file |
| result template summary: '...' -> '<tests added by ID and what each asserts; test decisions retained, refined or superseded and why; any test changed to pass a run and its independent reason; ShipLoop's records hold the counts>' | replaced | TD-12 | +189 | test packet, head and file |
| 'Test rerun: ... (at most 11 refused runs, then <remedy>; ...)' -> '(if it keeps refusing, <remedy>; ...)' | replaced | TD-10 | -8 | verify packet file (not in its printed head) |

Net: -223 -50 +189 = -84, so the test packet printed -84 characters (15,561 -> 15,477 at 83; 16,682 -> 16,598 at 163), verify printed 0, verify file -8.

## diff inline/08-test.printed (83, normalised; < before, > after)
```
29,31c29,30
<    HOME/architecture.md ## Real-boundary checks. Summary: which decisions you retain, refine or supersede and why;
<    locators and the step plan's in evidence_refs. A recorded completion does not prove a harness, fixture or target
<    still works.
---
>    HOME/architecture.md ## Real-boundary checks. Summary: which decisions you retain, refine or supersede and why.
>    A recorded completion does not prove a harness, fixture or target still works.
88c87
<   "summary": "..."
---
>   "summary": "<tests added by ID and what each asserts; test decisions retained, refined or superseded and why; any test changed to pass a run and its independent reason; ShipLoop's records hold the counts>"
126d124
< Refused runs for this action so far: 0 of 11 (base and candidate runs together); after that the item goes back to its step plan (revise). A run that times out, cannot start or is skipped on budget refuses without counting.
```

## diff inline/08-test.whole (83, normalised; < before, > after)
```
30c30
<   "summary": "..."
---
>   "summary": "<tests added by ID and what each asserts; test decisions retained, refined or superseded and why; any test changed to pass a run and its independent reason; ShipLoop's records hold the counts>"
74d73
< Refused runs for this action so far: 0 of 11 (base and candidate runs together); after that the item goes back to its step plan (revise). A run that times out, cannot start or is skipped on budget refuses without counting.
122,124c121,122
<    HOME/architecture.md ## Real-boundary checks. Summary: which decisions you retain, refine or supersede and why;
<    locators and the step plan's in evidence_refs. A recorded completion does not prove a harness, fixture or target
<    still works.
---
>    HOME/architecture.md ## Real-boundary checks. Summary: which decisions you retain, refine or supersede and why.
>    A recorded completion does not prove a harness, fixture or target still works.
```

## diff inline/10-verify.whole (83, normalised; < before, > after)
```
185c185
< Test rerun: on done, ShipLoop runs every test command the step plan recorded from WORKTREE and refuses unless each passes (at most 11 refused runs, then the item goes back to its step plan (revise); a command that times out, cannot start or is skipped on budget refuses the stage without counting):
---
> Test rerun: on done, ShipLoop runs every test command the step plan recorded from WORKTREE and refuses unless each passes (if it keeps refusing, the item goes back to its step plan (revise); a command that times out, cannot start or is skipped on budget refuses the stage without counting):
```

## diff ask-agent/10-verify.whole (83, normalised; < before, > after)
```
208c208
< Test rerun: on done, ShipLoop runs every test command the step plan recorded from WORKTREE and refuses unless each passes (at most 11 refused runs, then the item goes back to its step plan (revise); a command that times out, cannot start or is skipped on budget refuses the stage without counting):
---
> Test rerun: on done, ShipLoop runs every test command the step plan recorded from WORKTREE and refuses unless each passes (if it keeps refusing, the item goes back to its step plan (revise); a command that times out, cannot start or is skipped on budget refuses the stage without counting):
```

