---
bump: minor
---
The bundled Until Loop card can now be invoked by the model (`disable-model-invocation: false`) and opens with
"Start from a parent-written contract": when the argument or packet names a `Contract:` file and a `Receipt:`, it
skips interpretation and runs exactly `python3 <script> start --receipt <Receipt> < <Contract>`; the file wins over
the argument text, and an existing active receipt is continued through its `next_argv` instead of starting a second
run. The callback adapter reference says the same. The runtime script is unchanged.
