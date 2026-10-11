---
bump: patch
---
The bundled Until Loop runtime is upstream 0.8.2 (whichguy/until-loop v0.8.2, f7d97f6): a contract without exit checks, as Improve and ShipLoop write, no longer gets the verify-script instruction or the check-repairs schema entry, so its packets are 24% smaller than in 0.8.1 (about 6% above 0.7.0).
