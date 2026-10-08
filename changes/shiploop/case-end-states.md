---
bump: patch
---
The test stages now state when a test case is finished: a case ends validated (executed, and the observation matches), validated another way (the first method could not observe it, so the method changed and the new one was executed and passed, with what changed and why), or unachievable (a named reason and the requirement it leaves unverified, reported as blocked with `blocked_by access`, or revise/replan when the plan is wrong). A case written but not run, or recorded as not run, is not an end state. The rule is in the Test consideration of test-author, test-green, regression, system-test-author and system-test, and the system-test-author duty asks it to run each system command once while authoring.
