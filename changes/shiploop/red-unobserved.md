---
bump: minor
---
- **Remote commands are left out per command:** the mutation check runs only the focused commands that run on the
  checkout and records the remote ones it skipped. Before, one remote command beside local ones spent the budget on
  mutants it could never reach. When every command is remote, the check is skipped with the reason.
- **RED unobserved is printed:** verify (for its item) and product-acceptance (for every item) print the focused
  commands the base run left out as remote, so no failure on the old code was seen and the candidate runs are their
  only evidence.
