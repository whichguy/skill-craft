ShipLoop navigator | intake | revision 0
Callback for this stage (run once after its work; the result file is named below): python3 /Users/dadleet/e2e-runs/20261005/v1210-battleship-luna-xhigh/home/.codex/plugins/cache/whichguy/skill-craft/1.21.0/skills/shiploop/scripts/shiploop complete --run-dir=/Users/dadleet/e2e-runs/20261005/v1210-battleship-luna-xhigh/.shiploop-runs/work-20261005-044509-c4c5ac/run --action=nav-9ba67ad41a6a46f4b4bf8e5fae7c4e87 --result=/Users/dadleet/e2e-runs/20261005/v1210-battleship-luna-xhigh/.shiploop-runs/work-20261005-044509-c4c5ac/run/inbox/nav-9ba67ad41a6a46f4b4bf8e5fae7c4e87.md
Goal: Confirm the request, boundaries and open questions.
Done when (confirm each before calling done; keep going until all hold):
- every sentence of the request maps to an outcome, a boundary or an open question
- each open question names who answers it (the user now, or discovery) and what it blocks
- the result says where the outcome will be visible, and when
Considerations for this stage:
- Deploy: Name where the result must become usable; a request that names the target is the grant.
Write the structured result to: /Users/dadleet/e2e-runs/20261005/v1210-battleship-luna-xhigh/.shiploop-runs/work-20261005-044509-c4c5ac/run/inbox/nav-9ba67ad41a6a46f4b4bf8e5fae7c4e87.md
Result template:
# ShipLoop navigator result

```shiploop-state
{
  "evidence_refs": [
    "<absolute path of each file this stage wrote, or of the check output it recorded>"
  ],
  "headline": "<one line for the user, under 100 characters: what this step established>",
  "outcome": "done",
  "summary": "..."
}
```
Allowed outcomes: done | repeat | blocked.
A blocked result adds blocked_by: user | access | external (who can unblock it); a problem this run can fix itself is repaired in this stage, not blocked.
Run context index (the run's request, planning basis, work items and results; open it when you need the global picture, for example after compaction): /Users/dadleet/e2e-runs/20261005/v121
[trimmed in the fixture; the run's packet file was 27379 bytes]
