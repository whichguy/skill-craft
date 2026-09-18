# Specification Improve return route

After the bound ephemeral Improve runtime returns a successful terminal packet and its exact raw JSON is preserved at:

`<study>/new/product/.shiploop-improve/nav-2148a17cdff14eef8c90236660d96142/nav-793d0de0fad045efa34073325b4a3233/packet.json`

the parent may import only the matching completion evidence with:

```sh
DEVELOPER_DIR=/Library/Developer/CommandLineTools PYTHONDONTWRITEBYTECODE=1 python3 <study>/frozen/shiploop/scripts/shiploop improve-complete --run-dir=<study>/new/run --action=nav-793d0de0fad045efa34073325b4a3233 --result=<study>/new/run/inbox/nav-793d0de0fad045efa34073325b4a3233-improve.md
```

The child may write only its explicit `.shiploop-improve/nav-2148a17cdff14eef8c90236660d96142/nav-793d0de0fad045efa34073325b4a3233/` evidence tree. It must not edit product or run candidates, install dependencies, bootstrap a harness, commit, provision a target, deploy, request remote access, or call the parent while active.
