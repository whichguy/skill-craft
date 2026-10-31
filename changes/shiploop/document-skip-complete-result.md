---
bump: patch
---
When ShipLoop records an item's document stage as not applicable (the item changed no file, or only files that are not code or tests), the result it writes now carries what every done document result carries: `assumptions: []` and a `knowledge` record that says each living file is unchanged, with the reason. Before, the result had neither, so the step review's hand-off gate refused it for a stage ShipLoop had already settled, and the model was sent to write a document result nobody needed. A live run hit this once. The step commit's "Knowledge home" section now reads "Unchanged: <reason>" for a left-out document.
