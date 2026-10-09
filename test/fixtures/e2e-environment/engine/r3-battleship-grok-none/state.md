# ShipLoop navigator state

```shiploop-state
{
  "accepted": {
    "nav-503e9bc05ab449f690cff4fd6e585dea": {
      "headline": "server.js serves the page and the fire API on PORT",
      "outcome": "done"
    }
  },
  "history": [
    {
      "action": "nav-45a075801937477a821befeb9b9d3c03",
      "outcome": "done",
      "stage": "implement",
      "summary": "S1 replaced the rules.js placeholder. No earlier module existed, so this file is the rules unit. node --test test/rules.",
      "workitem": "W1"
    },
    {
      "action": "nav-503e9bc05ab449f690cff4fd6e585dea",
      "outcome": "done",
      "stage": "implement",
      "summary": "S2 replaced the server.js placeholder and kept require(\"./rules.js\"). The page is the HTML string that listen serves, so",
      "workitem": "W1"
    }
  ],
  "inner_loops": {
    "W1": {
      "action": {
        "id": "nav-fc245996d1d54460b11982becb5e9db1",
        "stage": "implement"
      },
      "stage": "implement"
    }
  },
  "stage": "inner-loop",
  "status": "active",
  "work_index": 0,
  "work_items": [
    {
      "id": "W1"
    }
  ]
}
```
