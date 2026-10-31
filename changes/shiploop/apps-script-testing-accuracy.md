---
bump: patch
---
The Apps Script card's Testing section now says what ShipLoop does with a deployed target. The mutation check leaves those commands out and records why only when every focused command is left out; when local commands remain, a mutant that no local test kills is recorded instead of refused, and each survivor needs a disposition. The target applies to a whole command, so deployed and local tests belong in separate commands. A step that changes deployed code names its deployed-result command in its Proof only, because expectations are checked on the item's base before the step. The section had told the plan to put that command in a Proof or an expectation, and had said the mutation check always records why. No script changed.
