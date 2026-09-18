# Reader compatibility window

During the current rollout, version 1 and version 2 readers run at the same
time. Version 1 accepts the base projection fields only. Version 2 also reads a
`summary` field. A writer change must keep the version 1 shape readable while
version 2 receives the new summary representation.

Do not remove the version 1 representation or destructively rewrite stored
projections until a separately recorded reader-retirement decision exists. A
source test of one version is not evidence that the mixed-reader window works.

