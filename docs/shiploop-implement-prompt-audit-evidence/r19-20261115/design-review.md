### 1. Goal

Keep ordinary-stage live state inside its owning run by appending `--directory str(receipt.parent)`, while preserving receipt ownership, recovery behavior, and parent acceptance.

### 2. Material issues

**The proposed directory is sufficient; I found no source-level reason for a second directory.** Receipt validation already requires an existing parent, and contract recovery uses an atomic writer that creates parents. The runtime creates a random `innerloop-*.json`, sets mode `0600`, and deletes only the inode it opened. Sharing `RUN/loops` therefore does not imply shared state or directory-wide cleanup. [Runtime — directory validation and allocation](/Users/dadleet/src/skill-craft-r19-20261115/skills/improve/runtime/until-loop/scripts/until_loop_ephemeral.py:949), [store — parent creation](/Users/dadleet/src/skill-craft-r19-20261115/skills/shiploop/scripts/shiploop_store.py:153), [runtime — owned deletion](/Users/dadleet/src/skill-craft-r19-20261115/skills/improve/runtime/until-loop/scripts/until_loop_ephemeral.py:572).

**Append the option after the existing receipt argument.** The test parser recognizes the literal substring ` start --receipt `. Inserting `--directory` immediately after `start` would break discovery unnecessarily. The smallest production change is:

```python
["python3", bound["runtime_cli"], "start", "--receipt", str(receipt),
 "--directory", str(receipt.parent)]
```

Keep the existing `shlex.join` and quoted redirection. [start_command](/Users/dadleet/src/skill-craft-r19-20261115/skills/shiploop/scripts/shiploop_loops.py:481), [LoopBlock — command recognition](/Users/dadleet/src/skill-craft-r19-20261115/test/shiploop_loop_support.py:128).

**Make the regression prove location through the emitted command.** `Synthetic.start` and `finish_loop` construct their own launches without this formatter, so those helpers cannot establish R19 coverage. Extend the existing literal-command test with an independent assertion that `Path(packet["state_file"]).parent == receipt.parent`; comparing the command against `start_command()` alone is circular. [Literal-command test](/Users/dadleet/src/skill-craft-r19-20261115/test/shiploop-loops.test.py:387), [bypassing helper](/Users/dadleet/src/skill-craft-r19-20261115/test/shiploop_loop_support.py:69).

**Describe the improvement narrowly: run-owned placement, not lost-state reconstruction.** `next_packet` requires the backing file; an active receipt remains nonrestartable even when that file disappears. Preserve those failures. [Runtime — restart refusal](/Users/dadleet/src/skill-craft-r19-20261115/skills/improve/runtime/until-loop/scripts/until_loop_ephemeral.py:406), [runtime — resume](/Users/dadleet/src/skill-craft-r19-20261115/skills/improve/runtime/until-loop/scripts/until_loop_ephemeral.py:996).

### 3. Minor nits

- Packet text and comments incorrectly say a second start “resets” an active loop. This predates R19; record it separately rather than expanding this repair. [Invocation wording](/Users/dadleet/src/skill-craft-r19-20261115/skills/shiploop/scripts/shiploop_loops.py:494).
- No new fingerprint exclusion appears necessary: Until Loop excludes `innerloop-*.json`, while ShipLoop’s check snapshots exclude the run directory. [Runtime exclusions](/Users/dadleet/src/skill-craft-r19-20261115/skills/improve/runtime/until-loop/scripts/until_loop_ephemeral.py:480), [ShipLoop exclusions](/Users/dadleet/src/skill-craft-r19-20261115/skills/shiploop/scripts/shiploop_lint.py:481).

### 4. Open unknowns

- This is source verification only; I ran no tests, callbacks, agents, or mutations. The location gap still needs its fail-first execution.
- Distinct receipts receive distinct allocations. Simultaneous starts against **the same receipt** have a pre-existing check-before-write race; the directory change neither introduces nor resolves it. Do not claim general concurrent-start safety.
- Run ownership does not establish durability against removal of the run directory or relocation of its absolute paths.

### 5. If I were implementing tomorrow

1. Extend the emitted-command test with paths containing spaces, a foreign cwd, and the location assertion; record its failure before editing.
2. Append the two argv elements above. Keep formatting read-only and leave the runtime unchanged.
3. Resume using exact `next_argv`; run the real successful check → exact `done_argv` → parent callback chain once. Assert acceptance, retained terminal receipt, and deleted backing state.
4. Check refused active restart and missing-state resume preserve receipt bytes and parent position.
5. Keep two distinct actions live in one directory: verify different files/tokens, reject a crossed token, and prove completing one leaves the other resumable. Also verify separate run directories.
6. Exercise the existing missing-contract recovery launch, retain existing rejection coverage, add the required change note, and stop unless these controls reproduce another defect.
