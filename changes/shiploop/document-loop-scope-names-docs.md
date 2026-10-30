---
bump: patch
---
The document stage's loop scope now lists the documentation files ShipLoop commits with the step (README and other Markdown, files under docs/, LICENSE, CHANGELOG), next to the step plan's paths and docs/shiploop/. It also says product documentation never goes in docs/shiploop/. The old scope allowed only the step plan's paths and docs/shiploop/, so a model that followed it left the README unchanged and wrote the product's API reference into ShipLoop's knowledge home.
