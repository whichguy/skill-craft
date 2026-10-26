---
bump: minor
---
Later stages restate the unverified list. The handoff, and any stage an `unverified` entry is due at, print the
current list, pre-fill it in the result template, and must return it in their own `unverified`: drop an entry due there
that the stage observed, move one it could not observe to a later stage, and copy every other entry unchanged (`[]` once
none stays open). ShipLoop refuses a restatement that is missing, drops an entry due later, or keeps an entry due at the
stage now ending. The report shows the latest list and what later stages settled. Before this, a settled outcome lived
only in prose, so a reader could not tell "settled" from "not restated".
