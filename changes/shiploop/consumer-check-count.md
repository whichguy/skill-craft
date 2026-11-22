---
bump: minor
---
At `release-verify`, where the consumer checks run in a clean copy of the returned result, ShipLoop now also runs each regression command of the last work item whose step plan records one, where no check already is that command, and it must pass there. A delivery whose own suite fails in the clean copy is refused whatever consumer checks were written; the packet and the refusal mark the added commands. The refusal names two exits: `send-back` when the release plan lacks a step the suite needs there (install, build), `add-work` when the delivery must change. No test count is compared.
