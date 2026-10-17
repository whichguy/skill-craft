# ADDENDUM 2026-10-17 (supersedes plan statements about the host cut; read before U7, U8, U9, U18, U22, U25)

Measured by the main session (full table: /Users/dadleet/e2e-runs/20261017/probe-cut/RESULTS.md; raw streams there):
- **Grok** gives the model an output whole up to **20,000 characters**. Above that it gives the first ~10,000 plus the last ~10,000 characters with the MIDDLE elided
  ("[truncated: showing first/last ...]"). It is NOT a tail cut.
- **Claude Code** gives a print whole up to at least 30,000 characters; a 40,000-character print was replaced by a 2 KB preview and a file path.
- **Codex** gave 40,000 characters whole; it truncates head and tail somewhere above that (66,400 chars: "original token count 17000").

What changes in the plan:
1. D-27 / ladder rung 5 ("accept a cut that takes chrome only") is **not safe on Grok** unless the cut region is exactly chrome. Do NOT rely on a host cut. The robust rule: the
   printed output of `next`, `complete`, `init`, `resume` (what the model is given) must be **at most 20,000 characters at the normal install (83-character run dir, 96-character
   CLI path)**, including the status block, `HEAD_END` and pointer lines; the head builder (one ordered list, D-17) keeps P0 blocks and as many lower blocks as fit and leaves the rest to
   the packet file (which holds the whole packet). Lines past the budget are NOT cut by the host; the script leaves them out and says where they are.
2. The hard test is therefore: for every stage, route and packet kind, printed length <= 20,000 at 83 (CLI path 96), P0 tokens all present; at 163 the length may exceed 20,000 only if
   the journaled value says so and the part that falls in the middle (characters ~10,000 to length-10,000) holds only lines the file repeats AND that are P2 or lower (test it: build
   the "Grok view" = first 10,000 + last 10,000 characters and assert every P0 token is in it). Add that Grok-view assertion to the head tests.
3. Ask-agent step-plan (required text near 19.7 KB, projected) cannot reach 20,000 with the chrome: close the shortfall with rungs 1 to 4 (the conditional bullets of duty 9 move to
   `skills/shiploop/references/plan-record.md` is allowed if wording and offsets are not enough; tell the owner in the journal).
4. HEAD_END and the tail: for Grok the LAST ~10,000 characters are always seen, so the END of a print (the `HEAD_END` line, the pointer to the packet file) is the second most reliable
   place after the first lines; put the lines that must survive a middle cut (callback again? no: keep one callback) accordingly. Do not add a second callback.
5. Claude: nothing changes (all prints < 30,000).
Measured round 0 on main (2026-10-17, Claude slice of node-fix-bug, evidence /Users/dadleet/e2e-runs/20261017/round0-claude-main): the released hook recorded the improve skill at 4 of 4 Improve
stages; the gate refused once (test-spec) and the model followed the named exit; no credential wording appeared. Slice PASS, 71 turns.
