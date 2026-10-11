---
bump: minor
---
Packets state each fact once (owner, 2026-10-11: "the full packet file looks far too verbose ... consolidate the
language and deduplicate").

- **Shared rules.** A producer packet no longer prints COMMON, the requirement and reference-handoff rules, or the
  progress paragraph. One short **Rules for every stage** list replaces them. The long texts stay whole in the run
  reference file (`reference.md` #rules, #requirements, #progress). Improve, paused and blocked packets print a
  three-line progress rule instead of the paragraph.
- **Removed duplicates.**
  - The Progress snapshot, which repeated the status block (report.html keeps it).
  - The second "Call this when done" callback.
  - The separate result-path line.
  - The "Owner:" line.
  - The four recovery prose lines; one Recovery command line remains.
  - The Improve line's repeated blocked sentence.
  - Test-source blocks for results that "Results this stage builds on" already lists.
  - The last transition's "read the durable state" sentence, and its empty evidence list.
- **Run locators.** The 15 policy and guide lines print only when the packet's own text names one. Every other
  locator is reached from reference.md#policies through one line. The state, CLI, scratch, keepalive and SHIPLOOP.md
  index lines remain.
- **Workspace return.** The return route (plan-return, review-return and the rollback route) prints only at
  release-plan, release-check, release and handoff. Every other worktree packet carries one "Execution checkout"
  line.
- **Result template.** It is the same JSON in the same fence, laid out with one key per line and one list element
  per line. The step-plan template drops from 115 lines to about 25.
- **step-plan.** Its duty is a numbered list, one item per result field plus the plan note, knowledge and evidence.
  - Step sizing, the test-facility and test-decision handoffs, the planning handoff and the design-basis text are
    folded into it.
  - The interaction and state-lifecycle text moves to the Interaction design guide.
  - An inline step-plan carries one optional Backchain audit line in place of the caller guidance.
- **Shorter texts.** The inline preamble, the Until Loop duty paragraph and the pass-log rule are shorter.
- **Size.** Measured offline on node-fix-bug, the inner loop drops from 431k to 270k characters, and its step-plan
  packet from 58k to 33k.
