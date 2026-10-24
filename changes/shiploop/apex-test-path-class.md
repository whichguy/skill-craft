---
bump: patch
---
- **Apex test classes are tests:** the path catalog classes `classes/*Test.cls` and `classes/*Tests.cls` (which
  covers `*_Test` and `*_Tests`) and their `-meta.xml` sidecars as `test`. Before, they counted as code, so a step plan
  step that only changed an Apex test class was accepted ("Tests are not a step" never fired). The `Test*` prefix
  convention is left out on purpose: it would also catch product classes such as `TestRunController`.
