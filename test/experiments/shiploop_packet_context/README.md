# Packet context experiment

Run the same renderer fixture separately against a preserved baseline and the
candidate's script directory. Each run traverses an independently listed
34-stage graph with synthetic results, rendering producer and selected-skill
handoff packets for ordinary and oversized work-item context.

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -B test/experiments/shiploop_packet_context/measure.py \
  --scripts-dir /absolute/package/shiploop/scripts \
  --output /absolute/evidence/packet-size.json \
  --packets-dir /absolute/evidence/packets
```

The selected Improve package must be beside the selected ShipLoop package.
Its card/runtime locators are resolved, but neither its runtime nor a model is
executed. Output records character counts, including differing locator lengths.
They are not measured tokens, model latency, or semantic-quality scores.
Optional representative packets support a separately labeled cold-reader
interpretation study. Do not execute their illustrative callbacks.

The packet-bounds regression suite separately proves large values remain in
durable state, omitted required context has precise locators, and callback
identity and recovery routes survive rendering. A smaller prompt is useful only
when the host still retrieves the required context and follows the correct action.
