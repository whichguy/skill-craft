---
bump: patch
---
ShipLoop now creates the directory of a bound Improve child's opening file whenever it prints the packet, so the printed step "write the opening file" needs no `mkdir`. A run bound earlier gets the directory on its next `next`.
