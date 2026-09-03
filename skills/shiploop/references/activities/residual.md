Session closer only. The spec is still **frozen**. Do not rewrite it. Do not
invent a new state-machine phase.

Follow this order. Each `/goal` below is a new outer-loop turn, not a nested
`/goal` and not a DAG step.

1. Do not open `/goal` until the bound repo’s Test command is green and the
   implementation commits are landed. Otherwise `/shiploop complete --blocked
   --resume-to residual --reason …`.
2. When green and landed, run review-coverage Phase B for the bound plan
   `{{BOUND_PLAN}}` under host `/goal`. Follow the review-coverage skill
   (Look here). Ledger: repo-root `{{LEDGER_PATH}}`. Do not treat a foreign
   or unlanded ledger as success.
3. When the bound ledger is `complete` and landed, or the bound plan H2 has
   a real residual waiver, dest-reread then finish only what the frozen spec
   named:

   Before quality or publish — cheap dest reread (not a spec edit). Read
   frozen `{{ENV_MD}}` (`routing.user_entrypoint`) and `{{SPEC_MD}}`
   (placement answers, `done_sentence`). When a dest writer is frozen,
   writer status/list once. Compose the live dest URL (HEAD/staging/prod)
   with that frozen user entrypoint (or documented product path). Do not
   write those URLs into `{{ENV_MD}}`. Quality and publish hit that composed
   entrypoint, not the dest default, not a module helper.

   Stay frozen (compose) when routing was frozen, empirical dest-hit matches
   it, Q2/Q3 still describe what is left, and any watch MCP for Q3 is already
   in `{{ENV_MD}}` `mcp:`/`tools`. Product README may name the user path.

   Unfreeze is `/shiploop complete --blocked --resume-to validate-spec`
   (clears hashes and receipts — expensive; contract drift only), when any
   of: dest-hit was never frozen, or `done_sentence` still claims the default
   dest URL while empirical dest-hit differs; Q2 mismatches the walk
   (`outer-loop` but publish already ran; `dag` but the deploy step never
   produced a slot and residual still needs one; residual would publish
   "just to test" against a writer anti-pattern that says push/HEAD is
   enough); Q3=yes and the named check needs a watch MCP not in frozen
   `{{ENV_MD}}` `mcp:`/`tools`; empirical dest-hit contradicts frozen
   `routing`. Do not dest-block for learning the URL string. README-only
   dest-hit fix is allowed only when routing was already frozen and
   `done_sentence` already names the user entrypoint.

   Paste Frozen (printed above this Next body) before each quality turn.
   1. **Quality test/fix `/goal` A.** If Q3=yes, run host `/goal` A to test
      and fix the completed product at the composed user entrypoint (the
      named check), then close A. A DAG sink that already play-through’d the
      frozen user entrypoint may skip only that duplicate play-through and do
      dest-reread plus spot-check instead. Play-through needs a watch MCP in
      frozen `{{ENV_MD}}` `mcp:`/`tools`; missing/locked → dest-block
      validate-spec, not a helper that bypasses the dispatcher.
   2. **Improve `/goal` B.** If Q3=yes, after A open host `/goal` B = Frozen + this goal (do not nest B inside A):
      /goal
      {{IMPROVE_GOAL}}
      Do this activity until these conditions are met:
      - only trivial findings remaining for 2 consecutive cycles
      - remaining trivial changes committed
      Max 12 improve cycles; on exceed, commit leftovers and go to step 3.
      If Q3=no, skip A and B; the spec is SoT — do not override a no.
   3. **Outer-loop deploy/publish.** After B, if Q2 is **outer-loop**, do
      that now with the writer's publish tool (dest-discovery Q1), on the
      same composed entrypoint for that slot. If Q2 is **dag** or **none**,
      skip (dag already ran in the walk). Do not open a new DAG step. Do not
      publish "just to test" if the writer says push/HEAD is enough.
   4. Then invoke `/shiploop complete`. dest `done` writes the
      end-of-run walk-back at `{{RECAP_HTML}}` (HTML covering intent, the
      original spec, what was accomplished, what materially changed, the
      end result, the final outcome, and what was verified). Recap
      Verified reports review-coverage; it does not witness this quality
      `/goal` A or Improve `/goal` B, or treat `done_sentence` as
      harness-verified. Do not
      hand-author that file.

When the bound ledger is `stopped (...)`, invoke `/shiploop complete` (harness dests halted).
