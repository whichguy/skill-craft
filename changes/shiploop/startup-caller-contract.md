---
bump: patch
---
Startup and recovery examples expose the loaded package's literal absolute CLI
path to the existing keepalive observer. Request arguments retain their exact
text through shell quoting, including embedded quotes and terminal newlines.
