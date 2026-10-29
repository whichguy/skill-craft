---
bump: patch
---
The Grok adapter no longer credits the retired `chain` verb as a direct ShipLoop command: its allowlist matches the verbs
the current `shiploop --help` lists (ShipLoop's implementation chain is retired, design T 2c-2).
