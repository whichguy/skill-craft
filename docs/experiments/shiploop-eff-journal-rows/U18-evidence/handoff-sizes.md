# Improve handoff sizes, before and after (unit U18)

Characters of `improve_handoff_text` for the synthetic bound walk of `test/shiploop-delegation.test.py` (`bound_walk`, one item, temp-dir paths of about 70 characters, the bare `shiploop` CLI), rendered by `render_handoffs.py` on the integration base `5e0ef0d0` (before) and on this branch (after). Plan U18 exit 3 compares the implement handoff with pilot A's 22 KB; `test/improve-route.test.py` asserts that bound on both routes at the lengths of a normal install (run dir 83, worktree 95, route 105, CLI 96), where the inline implement handoff is 19,441 characters and the ask-agent one 19,872.

| stage | inline before | inline after | ask-agent before | ask-agent after |
|---|--:|--:|--:|--:|
| spec | 26,658 | 13,008 | 28,647 | 13,359 |
| test-strategy | 27,908 | 14,295 | 29,897 | 14,655 |
| plan | 33,599 | 20,411 | 35,592 | 20,765 |
| step-plan | 30,857 | 16,307 | 33,165 | 16,753 |
| test-spec | 28,233 | 13,680 | 30,451 | 14,036 |
| implement | 33,329 | 18,790 | 35,625 | 19,224 |
| carry-forward | 33,658 | 19,136 | 35,876 | 19,496 |
| system-test-author | 27,823 | 14,230 | 29,812 | 14,595 |
| release-plan | 30,137 | 16,522 | 32,126 | 16,881 |
| mean | 30,244 | 16,264 | 32,354 | 16,640 |

Implement, inline: 33,329 -> 18,790 characters (44% less). Read beside it, once per context: the router (9,995 bytes) and the route file (45,933 bytes).
