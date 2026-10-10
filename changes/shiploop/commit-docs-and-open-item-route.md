---
bump: patch
---
ShipLoop now commits an item's changed documentation files (README.md, files under docs/) at integrate even when the step plan did not declare them, so the model no longer commits them by hand; the document and integrate packets print one consistent rule and the integrate packet lists the files ShipLoop will and will not commit. A test case that cannot run on the host is recorded as an open item with its due stage and the run continues; blocked is for when nothing else can proceed, and system-test treats a route that fails at run time like a missing route.
