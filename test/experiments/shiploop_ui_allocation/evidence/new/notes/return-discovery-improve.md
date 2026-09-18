# Discovery Improve return route

After, and only after, the bound ephemeral Improve runtime has returned a successful terminal packet and its exact raw JSON is preserved at the child receipt path, import the matching completion evidence with:

```sh
DEVELOPER_DIR=/Library/Developer/CommandLineTools PYTHONDONTWRITEBYTECODE=1 python3 <study>/frozen/shiploop/scripts/shiploop improve-complete --run-dir=<study>/new/run --action=nav-70d0ab5e215b4977a1131b00914b8baa --result=<study>/new/run/inbox/nav-70d0ab5e215b4977a1131b00914b8baa-improve.md
```

This child may write only its explicit `.shiploop-improve/nav-2148a17cdff14eef8c90236660d96142/nav-70d0ab5e215b4977a1131b00914b8baa/` evidence tree. It has no authority to alter product code/tests/configuration, bootstrap a harness, commit, install dependencies, provision a target, deploy, or run the parent callback before terminal success.
