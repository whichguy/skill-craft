---
bump: patch
---
`init` and `workspace start` now record the Improve card installed beside ShipLoop when `--improve-skill` is not given and the card validates, so the first Improve bind packet prints a real path instead of a template. Where no installed card validates, the packet prints a marked blank and the place ShipLoop looked; `--improve-skill` still wins and `--planning-review none` still requires it.
