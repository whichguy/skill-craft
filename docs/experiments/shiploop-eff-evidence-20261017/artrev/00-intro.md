
  
    ShipLoop · inner loop as it runs now · updated 2026-10-17 02:54 PDT

    The inner loop, step by step

    One work item through ShipLoop's eight inner stages, recorded live: what ShipLoop printed at each step, what the model said and did in its context window (every tool call and the output it got back), the result it submitted, ShipLoop's response, and the files each stage left. Paths are shortened to <run>, <worktree>, <skills> and <out>.

    
      node-fix-bug
case: In this Node.js project, paginate() in src/paginate.js loses the last page whenever the number of items is not a multiple of the page size: …

      claude-sonnet-5-5
host claude, inline route

      223 s · 70 turns
PASS: process, inner_loop, no_overshoot, assembled, checks

      1.3.0
ShipLoop build 28b27f7ca5fb; plugin 2.3.1

    

  

  
    How the loop runs now

    Five phases, eight stages, each run as one Until Loop that ShipLoop's packet invokes by name and starts from a contract ShipLoop wrote. After each stage ShipLoop checks the loop's receipt against that contract and runs its own gates before it prints the next packet.

    
      - Plan — step-plan: behaviour-sized steps with criteria, paths and helper skills; the test, lint and build commands; expectations (works, absent or broken) for everything the steps touch; architecture decisions. test-spec: one ### <ID> case per criterion with an independent oracle. An Improve review follows each.

      - Validate existing — ShipLoop runs every expectation's check on the unchanged code. All match: recorded, no model turn. A mismatch: the model diagnoses it and fixes the environment or a known small defect (ShipLoop commits the fix), or sends the plan back.

      - Build — implement per step (checks and lint, then an Improve review of the step); test: the cases written as real assertions, every command green; ShipLoop then runs the tests on the starting code (no new test may pass), on the finished code (all pass, no fewer than before) and against mutants of the changed lines (refused if the tests catch none); document only for a behavioural change.

      - Verify — each criterion confirmed after the last edit, the whole change reviewed, one rerun, then ShipLoop commits the item.

      - Carry forward — lessons into the knowledge home, the queue revised, the reusable-skill decision; the end-of-work review on the last item.

    

    sequenceDiagram
  autonumber
  participant M as Model
  participant S as ShipLoop
  participant U as until-loop runtime
  participant R as Repository
  participant I as Improve child

  Note over M,I: Plan phase
  S->>M: step-plan packet with INVOKE /until-loop and Exit when ALL hold
  M->>U: start --receipt from ShipLoop's contract file
  loop until the exit conditions hold
    M->>R: plan steps, criteria, commands, expectations, skills
    M->>S: complete --check-only (gates run, nothing accepted)
    M->>U: done report
  end
  U-->>M: terminal receipt
  M->>S: complete step-plan done
  S->>S: receipt vs contract rebuilt from state, sizing, expectations, check rows, skills
  S->>I: Improve review of the step plan
  I-->>S: reviewed
  S->>M: test-spec packet, same loop shape
  M->>S: complete test-spec done (IDs match the focused commands)
  S->>I: Improve review of the test spec
  I-->>S: reviewed

  Note over M,I: Validate existing phase
  S->>R: run every expectation check on the unchanged checkout
  alt every expectation matches works, absent or broken
    S->>S: record validate-existing done by script, no packet
  else a mismatch
    S->>M: validate-existing packet with the failing checks
    M->>U: loop: diagnose, fix the environment or a known small defect
    M->>S: complete done, or revise with failed_expectations
    S->>R: rerun every check, then commit the preparatory fix
  end

  Note over M,I: Build phase
  loop each planned step S1..Sn
    S->>M: implement packet with the step, its skills, check commands
    M->>U: loop: change the step's paths, run checks and lint
    M->>S: complete implement done
    S->>R: lint gate on the step's changed lines
    S->>I: Improve review of this step
    I->>R: warranted edits, committed
    I-->>S: reviewed
  end
  S->>M: test packet with every command and the red-check command
  M->>U: loop: write the test-spec cases as real assertions from the oracle, run all, fix code or tests
  M->>S: shiploop red-check (base run, never counted)
  M->>S: complete test done
  S->>R: lint gate
  S->>R: base run: no new test ID passes before the change
  S->>R: candidate run: every command passes, every ID, the floor
  S->>R: mutation gate: mutate up to 8 changed lines in a copy, refuse if tests catch none
  alt the diff touches code or tests
    S->>M: document packet
    M->>S: complete document done
  else docs-only diff
    S->>S: record document not applicable
  end

  Note over M,I: Verify phase
  S->>R: change inventory and first-entry lint auto-fix
  S->>M: verify packet with the review loop
  M->>U: loop: confirm each criterion, trace entry points, review the whole diff
  M->>S: complete verify done
  S->>R: lint gate and one rerun of every recorded command
  S->>R: item commit of the declared paths

  Note over M,I: Carry forward phase
  S->>M: carry-forward packet
  M->>U: loop: lessons, queue revision, skill decision
  M->>S: complete with skill none, reuse, update or create
  opt last work item
    S->>I: end-of-work Improve over every executed step
    I-->>S: reviewed
  end
  S->>R: commit a created or updated skill
  S->>M: next item's step-plan, or the outer stages

  

  
    This run

    The harness recorded the stages before the inner loop without running them (intake, discovery, research, spec, test-strategy, plan, prepare), so the model starts at step-plan. Steps:

    - step-plan
- improve · Improve
- test-spec
- improve · Improve
- implement
- improve · Improve
- test
- document
- verify
- carry-forward
- improve · Improve
- system-test-author

    Packets written: 13 (209,452 characters on disk); what reached the model: 54,709 printed and 29,175 read from packet files. ShipLoop refusals during the run: 3.

  

  Compared with the previous run

  Same case and model; the previous run was on main before these changes ().

  StepPacket chars beforePacket chars now
step-plan30,67222,292
step-plan · Improve39,5370
test-spec20,67212,833
test-spec · Improve33,9090
implement26,19520,009
implement · Improve39,5950
test29,43019,013
document21,71713,144
verify34,13123,663
carry-forward25,17120,908
carry-forward · Improve42,1000
system-test-author20,58214,546
improve · Improve02,050

  Time 269 s → 223 s; turns 81 → 70; both PASS.

  

  
    1
    Plan · W1 · nav-3a28fd23340c…

      