---
bump: patch
---
The Run Review export and page now say what the run delivered. A `delivered` object records whether the product was merged back into
the branch the run started from (and between which commits), or that it was not and which branch holds it; the kept files sorted into
source, tests, documentation, ShipLoop's own records and skills; how the tests last ran (the widest command of the release-verify
visit, never a sum); and the skill and release stages' own words. A new "What was delivered" card shows it, merge line first. A part the
workspace records cannot give is absent with its reason, never a zero; an export from before it gets no card.
A run that never returned says so once ("Files kept: not measured ...") instead of on every row, a red run at test-red says its new tests are meant to fail there, files in system/ count as tests, and a stage summary names a file by name, never by where the run lives.
