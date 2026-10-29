---
bump: minor
---
Each stage of a step lists the skills meant for it (design T section 8.2c, F9).
- A step plan's skill entry takes an optional `stages` list: implement, test, document or improve. Without one, a
  skill is implement's, as before.
- The test and document packets print the step just built and their "Skills for this stage" line, and the step
  review's handoff prints "Skills for this review". Each names the skill's use and locator, or says none is listed
  and points at KNOWLEDGE/environment.md `## Skills`.
- The test stage uses each skill its packet lists; it still never assumes an unlisted skill or MCP is available.
- Lint records say "changed since the base" instead of "this item changed", since each gate measures from its own
  base. An inline step's lint refusal says "on lines this step changed".
