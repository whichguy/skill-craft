# Marketplace lifecycle E2E testing

`test/marketplace-lifecycle-smoke.py` is an explicit native-CLI check. It is
not part of `test/run-all.sh`, `test/run-integration.sh`, or CI. Run it only
when a machine has the selected host CLI installed and it is appropriate to
exercise that host's local plugin cache.

```sh
python3 test/marketplace-lifecycle-smoke.py \
  --host codex \
  --output /tmp/skill-craft-marketplace-codex-e2e
```

`--output` must name a path that does not exist. The harness creates all
fixture repositories, consumer sentinels, command receipts, and reports below
that directory. Use `--host claude`, `--host grok`, `--host codex`, or
`--host all`. `results.json` and `REPORT.md` are the review artifacts.

Each host receives a unique fixture marketplace and plugin name. The fixture
contains only a versioned `SKILL.md`: it has no commands, hooks, MCP server, or
network behavior. The native lifecycle is:

1. Create and publish a local Git fixture at `1.0.0`.
2. Install it through the host's marketplace command and record native inventory.
3. Publish `1.0.1`, refresh or re-add the fixture as the host requires, and
   verify a fresh inventory/runtime view contains exactly one v2 plugin whose
   installed skill-card bytes match the fixture.
4. Uninstall the unique plugin, verify a fresh view no longer contains it, and
   verify the consumer-state sentinel is unchanged.

Claude uses a disposable `CLAUDE_CONFIG_DIR`; Grok uses a disposable
`GROK_HOME`. The harness never assigns `HOME` or `CODEX_HOME`, and its
restricted child environment does not pass arbitrary credentials through.
Those profiles are removed after the assertions by default. `--keep-profile`
retains them only for diagnosis and should be used with an output directory the
operator can delete afterwards.

Codex plugin management does not support the profile isolation used by Claude
and Grok. Its lane instead supplies a command-scoped, unique local marketplace,
uses native `codex plugin add` and `codex plugin remove` only for its unique
`plugin@marketplace` identity, and snapshots the existing Codex configuration
before and after. The test fails if the configuration's bytes or parsed
top-level values change. It never writes or replaces the saved configuration.

Codex's runtime proof comes from a new `codex app-server --stdio` process and
a `skills/list` request after each install/upgrade/removal stage. This catches
cache-only success: a v2 install must expose one runtime skill whose card hash
matches the v2 fixture, and removal must make it disappear.

## Codex plugin ID override

For command-scoped activation, keep a `plugin@marketplace` ID inside one inline
TOML `plugins` table:

```sh
codex -c 'plugins={"fixture@marketplace"={enabled=true}}' app-server --stdio
```

Do not express that same key as a dotted override such as
`plugins."fixture@marketplace".enabled=true`. The affected Codex CLI treats
the quoted dotted segment as literal quotes, so the plugin ID does not resolve
correctly. The harness uses the inline-table form and leaves no plugin override
in the saved config.

## Preconditions and evidence boundary

The harness needs Python 3.11+ for `tomllib`, an installed selected CLI, and
`/Library/Developer/CommandLineTools/usr/bin/git`. It uses that Command Line
Tools Git executable rather than accepting an Xcode license prompt. Claude
uses a local checkout because its CLI rejects a `file://` marketplace source;
Grok uses a local `file://` Git remote so that its marketplace refresh performs
a real local fetch.

This is marketplace lifecycle evidence only. It does not invoke a model, so it
does not prove model routing, prompt selection, output quality, authentication,
quota, or paid-account permissions. It also does not test Cursor's UI import
path and does not publish, install, or update a production marketplace.
