# Environment

Synthetic fixture prerequisites, not a model discovery result.

- node --test exercises existing local board state and the inherited web-choice checks.
- scripts/check-board-browser.cjs accepts explicit chosen anchors, a dark class and summary geometry options. It uses PLAYWRIGHT_NODE_PATH and BROWSER_EXECUTABLE_PATH if the host provides them. Discover/probe actual availability before claiming any rendered result. A planned command is not an executed check.
