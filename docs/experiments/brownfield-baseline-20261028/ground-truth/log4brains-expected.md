# log4brains at 17e32021a8c5: facts a baseline scoped to the L1 request (`adr list --json`) must hold

Hand-compiled from the code on 2026-10-28; never shown to a subject.

| ID | Fact | Evidence | Why it matters to the request |
|---|---|---|---|
| L1 | `log4brains adr list` filters by `--statuses` (comma-separated) and prints a table with columns Slug, Status, Package, Title; `--raw` prints it raw. | `packages/cli/src/commands/ListCommand.ts` `ListCommand.execute`; `packages/cli/src/cli.ts` | the new option sits beside these |
| L2 | The CLI reads ADRs only through the core API (`Log4brains.searchAdrs`), never from files itself; the core follows explicit architecture and DDD. | `ListCommand.ts`; `packages/core/docs/adr/20201002-use-explicit-architecture-and-ddd-for-the-core-api.md` | the JSON must come from the core API's DTO |
| L3 | An ADR's identity is its slug (`<package>/<sub slug>` or `<sub slug>`); the number-as-ID decision is superseded. | `docs/adr/20201016-use-the-adr-slug-as-its-unique-id.md` (supersedes `20200926-…`); `packages/core/src/infrastructure/api/types/AdrDto.ts` `AdrDto.slug` | the JSON "id" is the slug |
| L4 | The DTO's fields: slug, package, title, status, supersededBy, tags, deciders, body, creationDate, lastEditDate, lastEditAuthor, publicationDate, file. "date" is ambiguous among three dates. | `AdrDto.ts` `AdrDto` | the request's "date" is an open question to record |
| L5 | A monorepo of packages (cli, cli-common, core, global-cli, init, web) with Yarn and Lerna. | `docs/adr/20200925-multi-packages-architecture-in-a-monorepo-with-yarn-and-lerna.md` | placement of the change |
| L6 | Code style: Prettier with ESLint Airbnb; no default exports. | `docs/adr/20200925-use-prettier-eslint-airbnb-for-the-code-style.md`; `docs/adr/20200927-avoid-default-exports.md` | conventions the change follows |
| L7 | The repository's decision records: 11 in `docs/adr` (2 superseded: `20200926-…` by `20201016-…`, `20240926-…` by `20241217-…`), 3 in `packages/core/docs/adr`, 5 in `packages/web/docs/adr`: 19 in all. The ADRs under `packages/core/integration-tests/` and `packages/init/assets/` are test fixtures and templates, not decisions. (Corrected 2026-10-28 after the X2c judge: this row first said 10, 3 and 3, a counting error of mine; `git ls-files` at 17e32021a8c5 gives 11, 3 and 5.) | the folders named | each real record maps to one AD-<n>; fixtures map to none |
