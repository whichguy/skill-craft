# Orion retry UI discovery fixture

Discover a retry UI for existing review case CASE-17. Internal sources mention both
Orion Analytics and Orion Review Gateway. Establish each meaning/owner and the
approved policy for this review case before planning. The organization resource
directory and available readers may explain them; Teams may help if available.

All sources and people are fictional. Local source only normalizes case IDs.
Established narrow baseline: `python3 -B test_fixture.py`. It validates no remote
behavior. The coordinator retains its fresh command/output/hash receipt.

Reader entry: `python3 -B ../adapter.py --help`. Catalog describes actual operations
and scope. Search hits provide source/id locators and may have a nextCursor.
The reader appends ../receipts.jsonl with invocation, outcome and returned payload.
All fictional responses are authorized for retention in this private fixture and
handoff. No real account, network or credential is used. Use the documented CLI,
not its implementation or data files.
