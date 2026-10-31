---
bump: patch
---
Missing or rejected required completion keeps the current action unfinished,
including at an unchanged-progress host stop. The hook and driver repeat a short
instruction derived from that action's receipt: continue partial work, preserve
recorded passes, and submit the actual required report or stage callback. They
never execute completion or restart commands. Uncertain receipt states and lost
context retain explicit recovery through `next`; pauses, blocks, ownership,
host limits and hook errors retain their existing handling.
