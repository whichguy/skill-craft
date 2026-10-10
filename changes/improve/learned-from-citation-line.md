---
bump: patch
---
In a ShipLoop run, cite a commit that helped on a line of its own, `Learned-from: <commit id> <what it contributed>`: `improve-commit` checks that line against Git and writes the full ID into the commit, while a citation inside a sentence is not checked.
