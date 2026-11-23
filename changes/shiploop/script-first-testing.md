---
bump: patch
---
Make ShipLoop explicitly script-first for repeatable tests across `test-strategy`, `step-plan`, `test`, `system-test-author`, `release-plan`, and the testing reference guides: prefer committed, executable test scripts run directly by command over prompt-driven procedures, fragile inline shell pipelines, or MCP-wrapped harnesses, reserving Chrome DevTools and interactive host tools for inspection, probing, or fallback when no direct script runner is suitable.
