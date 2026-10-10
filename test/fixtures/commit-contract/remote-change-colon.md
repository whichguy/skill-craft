chore: record the staging cache purge

Remote change: staging-site, purged the CDN cache after build 41 (evidence: /tmp/release-check.log)
Key learnings: the staging host caches index.html for ten minutes; purge after every deploy.
Learned-from: 3f2a9c1e0b7d4a5c8e6f1a2b3c4d5e6f708192a3 the release-check log format

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
