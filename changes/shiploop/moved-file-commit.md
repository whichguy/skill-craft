---
bump: patch
---
A file moved or renamed during the work is now committed whole. ShipLoop's commit helper lists staged changes with rename detection off and takes a deletion that is already staged, and the commit before the return lists changed paths the same way. Before, the old path's deletion was left staged and uncommitted, so the return could not fast-forward and the user's checkout received the delivery as uncommitted changes.
