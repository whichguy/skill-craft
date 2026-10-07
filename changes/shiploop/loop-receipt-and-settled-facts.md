---
bump: patch
---
The test-loop and quality-loop duties no longer tell the model to save each returned packet to a "printed latest-packet path" and to write the terminal packet itself; the packet prints a receipt the runtime writes and says not to touch it, so the two now agree (the runtime's receipt carries `next_argv` for a resume). The plan duty asks each work item to state its module format and loadable seam, and the test-strategy duty asks the plan to say which test ids each command may print and to keep a host-dependent case (host browser, device, account, service) out of the project's default test command, after naming and probing its tool.
