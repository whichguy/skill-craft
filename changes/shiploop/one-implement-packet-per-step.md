---
bump: minor
---
A done `step-plan` must list `steps: [{"id": "S1", "task": "..."}]`, every implementation step in the order to do them (one step is fine). On the inline route ShipLoop then issues one `implement` packet per step: each names its step, the steps already accepted and the ones still to come, and the callback after the last step moves to the test stages. Which steps are done is read from the run's history, so recovery after a lost context reprints the current step. A revised step plan starts its steps over. The ask-agent route is unchanged: a chain runs every step inside its one `implement` action.
