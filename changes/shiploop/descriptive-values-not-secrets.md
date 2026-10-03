---
bump: patch
---
The credential check no longer refuses a label followed by a plain description (`session token: opaque UUID`, `auth: none required`, `auth: oauth2`, `signature: n/a.`), including punctuation or markdown around it; real secrets after the same labels are still refused. A GPT-6 Luna discovery result was refused twice for text that held no credential.
