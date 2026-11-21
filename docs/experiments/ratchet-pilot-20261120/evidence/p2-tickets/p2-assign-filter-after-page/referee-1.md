# Disputed acceptance tests

## C-74 — test corrected

The observable requires a failed assignment event’s `lastError` to contain the first 500 characters of the delivery error. Node includes the sink path in that error, and the fixture’s fixed directory padding produced a 503-character probe under the prescribed absolute `TMPDIR`. The test therefore failed before starting the service. The fixture now measures an unpadded probe and adds only the path characters needed to generate errors of exactly 500 and 501 characters. Both cases still compare the stored error with the expected prefix.
