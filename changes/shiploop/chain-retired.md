---
bump: minor
---
ShipLoop's implementation chain is retired (design T section 9.1, 2c-2; owner decision G1, 2026-10-29: "Adopt (a2)").
- The `shiploop chain` command, the chain's four modules (`shiploop_chain`, `_git`, `_handoff`, `_ledger`), the
  `chain_bindings` field of the run state, the completion guard that held `complete` until a chain finished, and the chain
  orientation blocks of the packets are gone. Every route builds one step per implement action (2c-1), so nothing binds a
  Plan Dispatcher graph to an implement action.
- The chain's guides are gone: `chain-route.md`, `chain-navigation.md` and `parallel-chain.md`, and every link to them in
  the card, the README and the references. The step exit criteria are read in the stage Until Loops guide.
- The progress view no longer shows a run's chain activity or bound graphs; it shows the accepted step plan's steps.
- Plan Dispatcher and Ask-Agent stay as skills of their own. Old runs' chain ledgers, receipts and worktrees are kept on
  disk; ShipLoop no longer reads them, and a saved run from before this change is refused (state version 11).
