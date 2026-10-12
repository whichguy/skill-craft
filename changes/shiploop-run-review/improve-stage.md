---
bump: patch
---
The export reads Improve as a stage of its own: it finds the Improve packet by the stage id that state.md records
(`packets/<improve stage id>.md`), and still reads the older `packets/<action>-improve.md` layout. It recognises the
Improve stage's `complete` as the return step of the compact packet.
