---
bump: patch
---
The stage catalog (`defaults/stages.json`) follows the engine's stage table again: system-test-author now reads test-spec
(every item's latest test cases) and release-plan reads system-test-author (the system commands it recorded), the
producers of what those stages' packets quote under the consumer contract.
