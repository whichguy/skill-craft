# Host selection and qualification

The live native tool schema is the launch contract. Before every launch, check
that the selected host can create the required fresh coordinator or worker,
return an identifiable native handle, and provide the actual terminal result.
The harness script does not provide a model launcher or host adapter. Qualification
belongs to a retained invocation with native evidence; a local script check or
an available tool name does not qualify an end-to-end host route.

| Host route | Coordinator boundary | Route-specific condition |
| --- | --- | --- |
| Codex native agents | One fresh native coordinator | Use live spawn and collection tools. Current-workspace read-only functionality was observed locally, but that trial did not achieve three-worker overlap. |
| Claude Code headless | Fresh top-level CLI session for explicitly requested diagnostics only | Unattended use is deferred on 2.1.296: nested trials returned early, and a later direct coordinator delivered successfully but did not exit. Markdown scratch reports were also refused by the host. |
| Claude Code interactive | Native nesting is documented; locally unqualified | Check actual tools and qualify completion before promising unattended operation. |
| Grok Build | One fresh top-level coordinator CLI session | Local 1.0.50 trials demonstrated three committed edits and five findings-only worktrees with native overlap. These used a controlled synthetic fixture; inspect hooks as potential writers. |

Keep qualification evidence separate by host, interface,
and runtime version. The local Grok depth observation comes from the selected
Build 1.0.50 guide; the public [Grok subagent guide](https://docs.x.ai/build/features/subagents)
does not establish that depth limit. Recheck the live guide and tool schema when
the route is used.

## Claude Code

The official [subagent guide](https://code.claude.com/docs/en/sub-agents#let-subagents-spawn-their-own-subagents)
documents the nested-subagent coordinator route. Use it only when the selected
native tool schema permits the top-level coordinator to start those workers.
Do not assume descendants have been incorporated into a headless coordinator's
final result: the coordinator must explicitly wait for and collect every
descendant's result, then report any incomplete or failed descendant. The
availability of nested agents alone does not qualify their completion behavior.

The local Claude Code 2.1.296 headless nested route failed two bounded live
trials: the coordinator returned before its workers and needed the initiating
conversation to resume it. Do not use that route for unattended coordination.
A fresh top-level Claude coordinator avoided the nested resume problem, but a
later direct trial produced its successful aggregate at about 105 seconds and
remained open beyond ten minutes with all three workers stopped. The trial was
terminated and is not successful process-completion evidence. Another direct
trial correctly retained five blocked attempts when the host refused Markdown
findings files. Do not bypass that refusal through another write tool.
Unattended headless Claude coordination remains deferred on this tested version.
For an explicitly requested diagnostic trial, use one fresh top-level process
with the existing CLI and normal permission settings. That process owns workers. This is the same
external coordinator boundary used for Grok; the Python helper does not launch
models, and selecting this route never authorizes a different provider.

For an explicitly requested diagnostic after Claude and the model have been selected, construct
a typed argument vector and start it with the source checkout as process cwd:

```python
argv = [
    "claude", "--print", "--session-id", new_uuid,
    "--model", selected_model, "--effort", selected_effort,
    "--output-format", "stream-json", "--verbose", coordinator_prompt,
]
```

Keep the returned process/session handle, collect its terminal output, and read
the aggregate evidence it names. Normal host permission settings still apply.
The initiating conversation monitors this one coordinator; it does not collect
or merge the leaf workers. Do not resume an existing session for a fresh task.

Do not compensate for an unreliable nested completion channel with an open-ended
shell sleep loop, worker resumes, or parent status nudges. Requalify nested
headless operation only when the live host provides a reliable blocking result
collection mechanism and a retained trial proves all descendants complete before
the coordinator returns. Interactive Claude nesting is a separate, unqualified
route: its documented behavior is not proof of headless behavior.

## Grok Build

Because the selected local guide reports depth one, the initiating conversation
must start exactly one fresh top-level Grok coordinator through the explicitly
selected existing host CLI. Do not place this coordinator underneath another
Grok agent. The coordinator itself starts task workers through Grok's native
subagent tool. This typed argument vector illustrates that one coordinator
startup; it is not a launcher implemented by this skill, does not resume a
session, and does not grant permissions:

```python
argv = [
    "grok", "--no-auto-update", "--cwd", str(repo),
    "--session-id", new_uuid,
    "--output-format", "json", "-p", coordinator_prompt,
]
```

Use a newly generated session ID. Do not add `--always-approve`; check that the
effective permission mode is appropriate before starting. Do not invoke this
CLI unless Grok was explicitly selected for the coordinator. The skill does
not select a production launcher. Worker tasks still launch through Grok's
native subagent tool, and every child result must be collected before the
coordinator returns. See the official
[Grok headless CLI reference](https://docs.x.ai/build/cli/headless-scripting).

The positive local Grok trials included the exact empty feedback backlog file
that an active host hook otherwise created outside worker write scopes. No hooks
were disabled and no ignore rules were widened. The prior ambient-hook failure
remains a qualification limit for other repositories. Native trace parser repairs
were checked by a separately identified diagnostic re-audit; the original failed
audits were retained. This is a local pilot result, not a universal host guarantee.

## Capability gate

Before dispatching, inspect the current session's actual tool schema for the
selected host. Confirm the concrete operation for starting a fresh task,
retaining its returned handle, and collecting its terminal result. For a
headless coordinator, also confirm how it waits for its own task workers and
any permitted descendants. A skill card, runtime version, model name, or
successful preparation does not establish these capabilities. If one is
missing, do not substitute a shell-launched worker, external API, another host,
or inherited parent context. Preserve the prepared run and report the
prerequisite instead.
