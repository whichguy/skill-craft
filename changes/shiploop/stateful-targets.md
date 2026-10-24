---
bump: minor
---
- **Commands name the target they run on:** a test command may name, in `target`, the test-strategy targets row it runs
  on. When a target keeps state between runs, the step plan's template asks for it, and a done step plan is refused
  when a focused or regression command names none or names a row that does not exist.
- **A target that keeps state is remote, on any platform:** the base run and the mutation check leave out a command
  whose target keeps state, because that target already holds the item's change. Before, only a platform card's
  Remote tests list could mark a command remote.
