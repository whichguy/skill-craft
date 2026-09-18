# Controlled status schema

`GET /api/exports` is read-only and account-scoped by host authorization. It returns:

```json
{
  "revision": 42,
  "jobs": [
    {"id": "exp-17", "status": "queued", "label": "September archive"}
  ]
}
```

`revision` is a monotonically increasing integer for the authorized account. Each job has a stable opaque `id`, a user-facing `label`, and `status` in `queued`, `running`, `complete`, or `failed`. The response is complete for this fixture; no collection selector, request operation, pagination, response-schema discovery, download path, or terminal download transition is needed. `GET /api/exports/:jobId` returns the same job shape if a focused job is already known; it is optional. Poll only while visible; on foreground, refetch authoritative status. Errors retain current displayed data and a concise retryable status message. No persistent local storage is required or available.
