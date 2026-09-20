Assess owned operational, authentication and audit observability in affected
local and remote flows. Reuse existing event sources and logging systems; record
coverage, ownership and evidence, and plan only demonstrated gaps. Include
successful and failed login coverage where authentication applies, without
duplicating the responsible provider's events. Adequate coverage requires no new
system. Use the observability section of the decision guide when needed.

When an affected behavior depends on remote data, schema, authority or independently
executing services, use the remote-service decision guide. Inspect authorized
current state; map provisioning and runtime capabilities separately; resolve
applicable cache/invalidation/authorization and asynchronous completion decisions.
Retain evidence, unresolved gates and affected artifacts in the existing design
note. Link its exact sections and revalidation conditions into requirements,
tests and work-item context. Otherwise record brief inapplicability and proceed.

This proposed entry cue includes post-review and observability revisions, not
measured in the paired study. Its detailed guide is proposed-reference.md; actual package
paths and stage routing remain implementation work.
