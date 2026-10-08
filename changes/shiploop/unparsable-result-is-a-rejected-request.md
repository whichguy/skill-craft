---
bump: patch
---
A result file that does not parse (no shiploop-state fence, invalid JSON, an unterminated fence or a duplicate key) is now refused as a rejected request, with the file path, the parser's reason and the instruction to fix the file and run the same command again. It no longer gets the lost-state recovery text that told the model not to infer a next action; real storage faults keep that text.
