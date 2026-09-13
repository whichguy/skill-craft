# /shiploop

Use the ShipLoop 0.9 action protocol. Start a fresh run with:

~~~sh
python3 "$SKILL_ROOT/scripts/shiploop" init \
  --repo "$REPO" [--run-dir "$REPO/.shiploop"] --prompt='<user request>'
~~~

Read the resulting action packet, retrieve only the durable context it points
to, and complete it with the exact action ID and Markdown result. See
the action protocol reference; do not use legacy inferred-completion commands.
