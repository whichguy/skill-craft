# Orion retry UI discovery fixture

This local UI client needs a retry flow for Orion. Establish the relevant meaning,
owner and approved behavior before planning the UI. Useful leads may include
engineering discussion, internal ADRs and the private gateway repository; Teams
may have background if a reader is available.

All materials here are fictional. The local source contains only a case identifier
helper. Existing baseline: `python3 -B test_fixture.py`. This is one narrow offline
check and says nothing about remote behavior.

The coordinator supplies the read-only fictional source CLI in ../adapter.py.
Start with `python3 -B ../adapter.py --help`. Catalog lists available sources and
operations. Search results contain IDs and may include a nextCursor; fetch reads
an identified record. Invocations append ../receipts.jsonl. Data reads are local;
there are no actual corporate connections.
