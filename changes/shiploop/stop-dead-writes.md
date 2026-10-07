---
bump: patch
---
Two writes no reader used are gone. The lint pass no longer writes a `.err` log per tool call (stderr is quoted in the lint report) and writes the `.out` log only when the report cites it as a byte-exact copy; a real run had 72 such files, all empty and never opened. The context index no longer points a cleared model at a `-latest.json` loop packet that nothing writes; it points at the loop receipt the runtime writes.
