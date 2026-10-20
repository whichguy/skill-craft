---
bump: patch
---
- **Progress narrative cap:** the narrative a packet prints stays within 900 characters. When it would run over, the
  oldest finished steps fold into one "N earlier steps: done" row, newest first kept; a text still over the cap is cut
  with an ellipsis.
