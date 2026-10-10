---
bump: patch
---
The Run Review export and page now say what the run delivered. A `delivered` object records whether the product was merged back into
the branch the run started from (and between which commits), or that it was not and which branch holds it; the kept files sorted into
source, tests, documentation, ShipLoop's own records and skills; how the tests last ran (the widest command of the release-verify
visit, never a sum); and the skill and release stages' own words. A new "What was delivered" card shows it, merge line first. A part the
workspace records cannot give is absent with its reason, never a zero; an export from before it gets no card.
