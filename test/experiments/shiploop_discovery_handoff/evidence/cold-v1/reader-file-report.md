# Reader-reported read sequence

The fresh cold reader reports LAUNCH.md then SHIPLOOP.md; it then issued reads of DISCOVERY.md, BASELINE.txt, docs/environment.md, PACKET.md and the actual probe receipt JSONL concurrently. No exact order is claimed within that group. It finally read PLAN.md for the word count. Historical probe argv in JSONL was data, not commands it executed. This is its report from the native execution context; parent separately verified unchanged pre-existing files and PLAN.md as the only addition.
