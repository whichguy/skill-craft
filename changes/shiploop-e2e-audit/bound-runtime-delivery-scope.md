---
bump: patch
---
Internal performance-harness qualification now keeps raw Git status visible while distinguishing exact, completed, run-bound direct Improve runtime files from uncommitted product files. Missing ownership proof, unknown files and runtime contamination continue to fail delivery; no existing run is regraded. This concerns the repository's internal evaluator, which is separate from the bundled game-audit harness; it adds no packaged audit-runtime behavior.

Recognize each current-spec snapshot only when its enumerated review pass binds the exact filename and SHA-256. Extra or tampered snapshots remain uncommitted product files.
