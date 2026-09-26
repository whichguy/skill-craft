---
bump: minor
---
ShipLoop's quality and test loops no longer have an iteration limit: they run until their exit
condition holds. The loop contracts no longer tell the model to cancel at iteration 3 (quality) or
4 (tests), a complete loop is `done` however many iterations it took, and a cancelled loop is always
refused (a user's stop is the packet's `pause` command). A loop that stops blocked reports `blocked`,
or `revise` when the item's goal proved wrong as planned. ShipLoop's own test reruns now allow 7
refused runs before `done` is no longer accepted (was 3).
