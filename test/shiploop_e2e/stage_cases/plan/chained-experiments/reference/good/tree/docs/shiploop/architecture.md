# Architecture

## Stack
- Node.js CommonJS, zero dependencies.

## Decisions

### AD-1
Keep zero external npm dependencies and preserve CommonJS module structure.

### AD-2
Use `node tools/export-v2-stream.js --mode jsonl` chunked to <= 4096 bytes per invocation after isolated probes showed `export-v1.js` stops at 20 records and `export-v2-stream.js` emits CSV unless `--mode jsonl` is passed and fails with `ERR_STREAM_BUFFER` above 4096 bytes.
