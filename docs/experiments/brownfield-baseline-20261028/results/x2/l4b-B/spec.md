# Log4brains baseline specification

Baseline coverage: deep: packages/cli, packages/cli-common, packages/global-cli, packages/core, packages/init, e2e-tests; overview: (root), packages, packages/web, docker, scripts, .github, .vscode, docs; not inspected: packages/web/nextjs/src/components, packages/web/nextjs/src/scenes, packages/web/nextjs/src/layouts, packages/web/nextjs/src/contexts, packages/web/nextjs/src/mui, packages/core/src/lib, packages/core/src/adr/application/command-handlers. As of 17e32021a8c5.

This file records what the repository does today, before any change is specified. The request that decides depth is: add a --json option to adr list. Depth therefore follows the adr list command, the data it reads from the core library, the outputs other programs already read from it, and the cross-cutting rules a change there must keep. Nothing was run: dependencies are not installed and the packet forbids running the repository's tooling, so tested means that a named test asserts the behaviour when read, not that it was executed. Behaviour that depends on a library that is not installed is labelled inferred. Source classes used: documented, tested, observed, inferred, conflict.

## Overview

### Purpose

- Log4brains is a docs-as-code knowledge base for development and infrastructure projects: teams log Architecture Decision Records (ADRs) as markdown files in their git repository, create and list them from a command line, preview them locally with hot reload and publish them as a static website. (`README.md:24`; `README.md:39`)

### Consumers

- Developers and architects who write and browse ADRs from a terminal or an IDE. (`README.md:25`)
- CI/CD pipelines that install the tool and build the static site for GitHub Pages, GitLab Pages or S3. (`README.md:152`)
- Programs that read the output of the log4brains command: the init command reads the output of adr list --raw and of adr new --quiet, and the end-to-end script reads adr list --raw. (`packages/init/src/commands/InitCommand.ts` `adrListRes`; `e2e-tests/e2e-launcher.js` `adrListRes`)
- Programs that embed the core library. (`packages/core/README.md` `Log4brains`)
- People who run the published container image. (`docker/Dockerfile` `ENTRYPOINT`)

### Entry points

- The log4brains executable with the commands init, adr new, adr list, preview and build, plus --version and --help. (`packages/global-cli/package.json` `bin`; `packages/global-cli/src/cli.ts` `createGlobalCli`)
- The programmatic API of the core library, built around one facade class. (`packages/core/src/infrastructure/api/Log4brains.ts` `createFromCwd`)
- The Next.js web app that preview serves and build exports. (`packages/web/cli/commands/preview.ts` `previewCommand`)
- The CI workflows. (`.github/workflows/pull-request-checks.yml` `quality-checks`)

### Areas of the census map

- (root): overview. Workspace manifest, shared lint, format, compile, test and commit rules, README and CONTRIBUTING. (`package.json` `workspaces`)
- packages: overview. Container of the six published npm packages, released together at one version. (`lerna.json` `version`)
- packages/cli: deep. The adr new and adr list commands (R-1 to R-5, R-9). (`packages/cli/src/cli.ts` `createCli`)
- packages/cli-common: deep. Terminal output, prompts, tables and the exit marker shared by every command line (R-1, R-2, R-9). (`packages/cli-common/src/AppConsole.ts` `AppConsole`)
- packages/global-cli: deep. The log4brains executable: launcher script, command composition, top-level error handling (R-1, R-9). (`packages/global-cli/src/index.ts` `handleError`)
- packages/core: deep for the listing path only. ADR model, search, ordering, configuration and the programmatic API (R-3 to R-8). (`packages/core/src/infrastructure/api/Log4brains.ts` `searchAdrs`)
- packages/init: deep for the part that reads adr list --raw and adr new --quiet; overview for the rest of the init command (R-2). (`packages/init/src/commands/InitCommand.ts` `InitCommand`)
- packages/web: overview. The preview and build commands and the Next.js app; its JSON index of ADRs is recorded in R-12. (`packages/web/cli/cli.ts` `createWebCli`)
- e2e-tests: deep for the part that runs adr list. A Node script that drives the installed executable in a temporary folder (R-1, R-2). (`e2e-tests/e2e-launcher.js` `adrListRes`)
- docker: overview. Image whose entrypoint is the executable, and a Makefile that publishes it. (`docker/Dockerfile` `ENTRYPOINT`)
- scripts: overview. The manual stable-release script and a script that waits for an npm version. (`scripts/release.sh` `lerna`)
- .github: overview. CI workflows (pull request checks, alpha release on merge, post-release end-to-end, Docker and ADR publication, weekly checks) and issue templates. (`.github/workflows/reusable-tests.yml` `yarn e2e`)
- .vscode: overview. Editor settings: format on save with prettier-eslint. (`.vscode/settings.json` `formatOnSave`)
- docs: overview. The project's own ADRs: eleven records plus an index, a template and a README; every record is mapped to a decision in architecture.md. (`docs/adr/README.md:1`)

## Requirements

### R-1 List the project's ADRs with adr list
Status: baseline · Source: observed (`packages/cli/src/cli.ts` `createCli`); tested (`e2e-tests/e2e-launcher.js` `adrListRes`); inferred (`packages/cli/src/cli.ts` `commander`) · As of: 17e32021a8c5
- log4brains adr list prints every ADR of the project that contains the working folder: the ADRs of the main ADR folder and those of every configured package, together in one list. (`packages/core/src/adr/infrastructure/repositories/AdrRepository.ts` `findAll`)
- The command declares no positional argument and two options only, --statuses (R-3) and --raw (R-2); there is no option to select a package or a date range. Its help description is 'List ADRs'. (`packages/cli/src/cli.ts` `createCli`)
- The command belongs to the adr group of the single log4brains executable, beside adr new; init, preview and build are top-level commands of the same executable. (`packages/global-cli/src/cli.ts` `createGlobalCli`)
- With no option the output is a table on standard output with the header cells Slug, Status, Package and Title and one row per ADR. (`packages/cli/src/commands/ListCommand.ts` `execute`)
- A row shows the slug unchanged; the status in upper case, for example ACCEPTED or SUPERSEDED; the package name, or an empty cell for an ADR that belongs to no package; the title, or 'Untitled' for an ADR without a title. (`packages/cli/src/commands/ListCommand.ts` `execute`)
- Listing is read-only and non-interactive: it writes no file and asks no question. (`packages/cli/src/commands/ListCommand.ts` `execute`)
- The README does not describe adr list or its options; the help text is the only user-facing description, and the release checklist names the command in a manual smoke test. (`README.md:116`; `scripts/release.sh` `smoketests`)
- The end-to-end script runs adr list --raw after init and one adr new, and requires the output to contain the slugs of the two starter ADRs and the title of the new one. (`e2e-tests/e2e-launcher.js` `adrListRes`)
- Inferred, not verified: with no ADR the table shows its header row only and the command still succeeds. (`packages/cli-common/src/AppConsole.ts` `printTable`)
- Inferred, not verified: an option the command does not declare, such as --json today, is refused by the argument parser with an error message and a non-zero exit. (`packages/cli/src/cli.ts` `commander`)

### R-2 Raw one-line-per-ADR output with --raw
Status: baseline · Source: observed (`packages/cli-common/src/AppConsole.ts` `printTable`); tested (`e2e-tests/e2e-launcher.js` "MADR ADR was not created by init") · As of: 17e32021a8c5
- --raw is off unless given. When given, the table is replaced by one line per ADR and nothing else is printed on standard output. (`packages/cli/src/cli.ts` `createCli`; `packages/cli-common/src/AppConsole.ts` `printTable`)
- A line holds the same four values as a table row, in the order slug, status in upper case, package (empty when none), title ('Untitled' when none), joined by commas. (`packages/cli-common/src/AppConsole.ts` `printTable`)
- Values are neither quoted nor escaped, so a comma inside a title adds a field to its line. (`packages/cli-common/src/AppConsole.ts` `printTable`)
- No header line is printed, and with no ADR the output is completely empty. (`packages/cli-common/src/AppConsole.ts` `printTable`; `e2e-tests/e2e-launcher.js` "MADR ADR was not created by init")
- The init command relies on that: it runs adr list --raw right after writing the configuration and, when the output is completely empty, creates the 'Use Markdown Architectural Decision Records' starter ADR. (`packages/init/src/commands/InitCommand.ts` `adrListRes`)
- The end-to-end script reads the same output to check that both starter ADRs and a new ADR exist. (`e2e-tests/e2e-launcher.js` `adrListRes`)

### R-3 Filter by status with --statuses
Status: baseline · Source: observed (`packages/cli/src/commands/ListCommand.ts` `execute`); tested (`packages/core/src/adr/application/query-handlers/SearchAdrsQueryHandler.test.ts` "filters the ADRs on their status") · As of: 17e32021a8c5
- --statuses takes a comma-separated list of status names. Without it, or with an empty value, no filter applies and every ADR is listed. (`packages/cli/src/commands/ListCommand.ts` `execute`)
- An ADR is listed when its status equals any name of the list, so several names give the union of their ADRs, in the usual order. (`packages/core/src/adr/application/query-handlers/SearchAdrsQueryHandler.ts` `execute`; `packages/core/integration-tests/ro.test.ts` "with filter on statuses")
- Valid names are draft, proposed, rejected, accepted, deprecated and superseded. Case is ignored, and a name that starts with 'superseded by' counts as superseded. (`packages/core/src/adr/domain/AdrStatus.ts` `createFromName`; `packages/core/src/adr/domain/AdrStatus.test.ts` "works with 'superseded by XXX")
- Names are not trimmed: a space after a comma makes that name unknown. (`packages/cli/src/commands/ListCommand.ts` `split`; `packages/core/src/adr/domain/AdrStatus.ts` `createFromName`)
- An unknown name stops the command before anything is printed, with the message 'Unknown ADR status (name)', reported as described in R-9. (`packages/core/src/adr/domain/AdrStatus.ts` `createFromName`; `packages/core/src/adr/domain/AdrStatus.test.ts` "throws when unknown name")
- The help text does not list the valid names; a code comment marks this as a to-do. (`packages/cli/src/cli.ts` `statuses`)

### R-4 Order of the listed ADRs
Status: baseline · Source: documented (`docs/adr/20201016-use-the-adr-slug-as-its-unique-id.md:19`); tested (`packages/core/src/adr/domain/Adr.test.ts` "sorts between two publicationDates"); observed (`packages/core/src/adr/domain/Adr.ts` `compare`) · As of: 17e32021a8c5
- ADRs are listed oldest first. (`packages/core/src/adr/domain/Adr.ts` `compare`)
- An ADR is placed by its publication date when it has a valid one and by its creation date otherwise; the publication date wins even when the creation dates say the opposite. (`packages/core/src/adr/domain/Adr.ts` `compare`; `packages/core/src/adr/domain/Adr.test.ts` "sorts between two publicationDates")
- ADRs with the same date are ordered by the name part of the slug (the part after the package prefix), ignoring case, digits before letters; if that is still equal, by the whole slug, ignoring case. (`packages/core/src/adr/domain/Adr.ts` `compare`; `packages/core/src/adr/domain/Adr.test.ts` "sorts by slug when two same publicationDates"; `packages/core/src/adr/domain/Adr.test.ts` "does not take slug's package part into account"; `packages/core/src/adr/domain/Adr.test.ts` "does not take case into account"; `packages/core/src/adr/domain/Adr.test.ts` "sorts numbers before letters")
- A publication date is read as the end of that day in the project time zone, so ADRs without a Date line that were created earlier on the same day come before the dated one. (`packages/core/src/adr/domain/Adr.ts` `publicationDate`; `packages/core/src/adr/domain/Adr.test.ts` "a publicationDate on the same day of a creationDate is always older")
- The creation date is the date of the first Git commit that touched the file (renames are not followed); for a file Git does not know yet, or when Git is not available, it is the file's last modification time. (`packages/core/src/adr/infrastructure/repositories/AdrRepository.ts` `getGitMetadata`; `packages/core/src/adr/infrastructure/repositories/AdrRepository.ts` `getLastEditDateFromFilesystem`)
- The README requires the full Git history in CI for the tool to work correctly; the creation, last edit and author values are read from that history. (`README.md:273`; `packages/core/src/adr/infrastructure/repositories/AdrRepository.ts` `getGitMetadata`)
- Ordering is done once, by the core; the command does not sort again, so the table, the raw lines, the static site and the preview API show the same order. (`docs/adr/20201016-use-the-adr-slug-as-its-unique-id.md:26`; `packages/cli/src/commands/ListCommand.ts` `execute`)
- A real mixed order over a fixture project with packages is recorded in a snapshot. (`packages/core/integration-tests/__snapshots__/ro.test.ts.snap` "E2E tests / RO searchAdrs() all 1")

### R-5 What counts as an ADR and how it is identified
Status: baseline · Source: documented (`docs/adr/20201016-use-the-adr-slug-as-its-unique-id.md:15`); observed (`packages/core/src/adr/domain/AdrSlug.ts` `createFromFile`); tested (`packages/core/integration-tests/__snapshots__/ro.test.ts.snap` "E2E tests / RO searchAdrs() all 1") · As of: 17e32021a8c5
- ADRs are the markdown files placed directly in the main ADR folder or in the ADR folder of a configured package; sub-folders are not searched. (`packages/core/src/adr/infrastructure/repositories/AdrRepository.ts` `findAllInPath`)
- Files that are not markdown, and files named template, readme, index or backlog with the extension .md in any letter case, are never ADRs and are skipped without a message. (`packages/core/src/adr/domain/AdrFile.ts` `reservedFilenames`)
- The identifier of an ADR is its slug: the file name without .md, prefixed by the package name and a slash for an ADR of a package. There is no ADR number and no separate id. (`packages/core/src/adr/domain/AdrSlug.ts` `createFromFile`; `docs/adr/20201016-use-the-adr-slug-as-its-unique-id.md:15`)
- The slug is what the commands print and accept: adr new --quiet prints it and preview takes it to open one ADR. (`packages/cli/src/commands/NewCommand.ts` `quiet`; `packages/web/cli/commands/preview.ts` `adrSlug`)
- The name part of a slug cannot contain a slash. (`packages/core/src/adr/domain/AdrSlug.ts` `AdrSlug`)
- The package of an ADR is the name of the configured package whose ADR folder holds the file, and none for the main ADR folder. (`packages/core/src/adr/infrastructure/repositories/AdrRepository.ts` `findAll`; `packages/core/integration-tests/__snapshots__/ro.test.ts.snap` "E2E tests / RO getAdrBySlug() existing ADR 1")
- Slugs made by adr new start with the creation day as yyyymmdd followed by the slugified title, with a numeric suffix when the name is taken. (`packages/core/src/adr/domain/AdrSlug.ts` `createFromTitle`; `packages/core/src/adr/infrastructure/repositories/AdrRepository.ts` `generateAvailableSlug`)

### R-6 Title, status and dates of an ADR
Status: baseline · Source: documented (`docs/adr/template.md:3`); observed (`packages/core/src/adr/domain/Adr.ts` `status`); tested (`packages/core/src/adr/domain/Adr.test.ts` "returns the default status") · As of: 17e32021a8c5
- The title is the text of the first level-1 heading of the file; an ADR with no such heading has no title. (`packages/core/src/adr/domain/Adr.ts` `title`; `packages/core/src/adr/domain/Adr.test.ts` "returns undefined when no title")
- The status comes from the Status line of the first bullet list that precedes the first level-2 heading, the key being matched ignoring case. No such line means accepted, text that is not a known status means draft, and text starting with 'superseded by' means superseded. (`packages/core/src/adr/domain/Adr.ts` `status`; `packages/core/src/adr/domain/MarkdownBody.ts` `getHeaderMetadataElementAndMatch`; `packages/core/src/adr/domain/Adr.test.ts` "returns the default status")
- The publication date comes from the Date line of that same list, written YYYY-MM-DD or DD/MM/YYYY and parsed strictly; a missing or unreadable value means no publication date and no error. (`packages/core/src/adr/domain/Adr.ts` `dateFormats`)
- The ADR template describes the Date line as the day the decision was last updated, optional, and meant to control ordering without relying on edit dates. (`docs/adr/template.md:5`)
- The publication date is interpreted in the time zone configured for the project and placed at 23:59:59 of that day; as an exported instant it is UTC text, so with Europe/Paris in winter the day 2020-01-01 becomes 2020-01-01T22:59:59.000Z. (`packages/core/src/adr/domain/Adr.ts` `publicationDate`; `packages/core/src/adr/domain/Adr.test.ts` "timezone works"; `packages/core/integration-tests/__snapshots__/ro.test.ts.snap` "E2E tests / RO getAdrBySlug() existing ADR 1")
- Creation date, last edit date and last edit author come from the Git history of the file; for a file with no Git history they are the file's modification time and the Git user name, or 'Anonymous' when Git is not available. (`packages/core/src/adr/infrastructure/repositories/AdrRepository.ts` `getAnonymousAuthor`)

### R-7 ADR search result of the programmatic API
Status: baseline · Source: observed (`packages/core/src/infrastructure/api/Log4brains.ts` `searchAdrs`); tested (`packages/core/integration-tests/ro.test.ts` "all") · As of: 17e32021a8c5
- The call that lists ADRs takes optional filters (statuses only) and returns every matching ADR, oldest first, as read-only records. The call is documented to raise a domain error for any non-recoverable problem, although a missing main ADR folder surfaces as the raw file-system error (R-8). (`packages/core/src/infrastructure/api/Log4brains.ts` `searchAdrs`)
- A record holds: slug; package (null when none); title (null when none); status (one of the six lower-case names); supersededBy (a slug or null); tags (lower case, possibly empty); deciders (possibly empty); body (raw markdown and enhanced MDX); creationDate; lastEditDate; lastEditAuthor (a name); publicationDate (null when none); file (relative and absolute path); and, when the Git remote is known, repository (provider and view URL). (`packages/core/src/infrastructure/api/types/AdrDto.ts` `AdrDto`; `packages/core/src/infrastructure/api/transformers/adr-transformers.ts` `adrToDto`)
- Dates are ISO 8601 UTC text. (`packages/core/src/infrastructure/api/transformers/adr-transformers.ts` `toJSON`)
- A record has no field called id or date: the identifier is the slug and three dates exist. (`packages/core/src/infrastructure/api/types/AdrDto.ts` `AdrDto`)
- Building a record parses and link-resolves the whole ADR body even when the caller needs only a few fields. (`packages/core/src/infrastructure/api/transformers/adr-transformers.ts` `getEnhancedMdx`)
- A record carries machine-specific and personal data: the absolute path of the file and the Git author's name. (`packages/core/src/infrastructure/api/types/AdrDto.ts` `absolutePath`)
- For the fixture project, a missing title, package or publication date is null and the status is lower case. (`packages/core/integration-tests/__snapshots__/ro.test.ts.snap` "E2E tests / RO searchAdrs() all 2")

### R-8 Finding and reading the project configuration
Status: baseline · Source: documented (`README.md:429`); observed (`packages/core/src/infrastructure/config/builders.ts` `findWorkdirRecursive`) · As of: 17e32021a8c5
- The project is the nearest folder that contains the file .log4brains.yml, searched from the current folder (or from the folder named by the environment variable LOG4BRAINS_CWD) up through its parents; the command therefore works from any sub-folder. (`packages/cli/src/cli.ts` `getL4bInstance`; `packages/core/src/infrastructure/config/builders.ts` `findWorkdirRecursive`)
- The executable's own help says commands should be run from the project root folder, while the code accepts any sub-folder. (`packages/global-cli/src/cli.ts` `createGlobalCli`)
- The file must give a project name, a time zone and the main ADR folder. It may add packages (each with a name that is a valid host name, a path and an ADR folder) and repository details (url, provider github, gitlab, bitbucket or generic, and a view-file pattern). (`packages/core/src/infrastructure/config/schema.ts` `schema`; `README.md:429`)
- A file that cannot be read or parsed stops the command with 'Impossible to read the .log4brains.yml config file'; one that does not validate stops it with 'There is an error in the .log4brains.yml config file' followed by the validation messages. Duplicated package names stop it with 'Some package names are duplicated', an unknown time zone with 'Unknown timezone', and a package whose path or ADR folder is missing with 'Package path does not exist' or 'Package ADR folder path does not exist'. (`packages/core/src/infrastructure/config/builders.ts` `buildConfig`; `packages/core/src/adr/infrastructure/repositories/PackageRepository.ts` `buildPackage`; `packages/core/src/adr/domain/Adr.ts` `setTz`)
- No configuration file in the folder or its parents ends the command with 'Cannot find .log4brains.yml' and the hint 'You are in the wrong directory or you need to run log4brains init', with status 1. (`packages/global-cli/src/index.ts` `handleError`)
- The main ADR folder is not checked for existence: when it is missing, the file-system error itself is what gets reported. (`packages/core/src/adr/infrastructure/repositories/AdrRepository.ts` `findAllInPath`)
- The repository URL and provider, used only for links inside records, come from the file or are guessed from the origin remote in .git/config. (`packages/core/src/infrastructure/config/guessGitRepositoryConfig.ts` `guessGitRepositoryConfig`)

### R-9 Failure reporting, output streams and exit status
Status: baseline · Source: observed (`packages/global-cli/src/index.ts` `handleError`); inferred (`packages/global-cli/src/log4brains` `spawn`) · As of: 17e32021a8c5
- A failure raised while a command runs reaches one top-level handler that prints it and ends the process with status 1. (`packages/global-cli/src/index.ts` `handleError`)
- A domain error is a short sentence with optional details, shown as 'sentence (details)'. (`packages/core/src/domain/Log4brainsError.ts` `Log4brainsError`)
- A failure is shown on standard error as a FATAL line with the message; the stack trace is added only when the environment variable DEBUG is set or NODE_ENV is development. (`packages/cli-common/src/AppConsole.ts` `fatal`; `packages/global-cli/src/index.ts` `traces`)
- A command that has already reported its problem can end the process with status 1 without a second message. (`packages/cli-common/src/FailureExit.ts` `FailureExit`)
- Standard output carries only data (the table or the raw lines); warnings, errors and fatal messages go to standard error. (`packages/cli-common/src/AppConsole.ts` `printlnErr`)
- The debug helper writes to standard output when DEBUG is set, but the listing path never calls it. (`packages/cli-common/src/AppConsole.ts` `debug`; `packages/cli/src/commands/ListCommand.ts` `execute`)
- Callers that react to an error match on its sentence, for example the command wrapper matches 'The template.md file does not exist', so the wording of a domain error is part of the contract. (`packages/cli/src/cli.ts` `execWithErrorHandler`)
- Inferred, not verified: the executable that users run is a launcher that starts the real command as a child process and does not hand on the child's exit status, so a failed run can still end with status 0 for its caller. (`packages/global-cli/src/log4brains` `spawn`)

### R-10 Local, credential-free operation (identity and access, privacy and security)
Status: baseline · Source: inferred (`packages/core/src/infrastructure/api/Log4brains.ts` `createFromCwd`); observed (`packages/web/cli/commands/build.ts` `NEXT_TELEMETRY_DISABLED`); documented (`README.md:152`) · As of: 17e32021a8c5
- Inferred, not verified: there are no accounts, sign-in, tokens or roles; the tool acts with the permissions of the operating-system user who runs it, on local files and the local Git repository. A search of the package sources for password, credential, oauth, API key, login, bearer, authorization and authentication found nothing. (`packages/core/src/infrastructure/api/Log4brains.ts` `createFromCwd`)
- Listing makes no network request and sends no telemetry; the web commands switch Next.js telemetry off. (`packages/web/cli/commands/build.ts` `NEXT_TELEMETRY_DISABLED`)
- Publishing the output of build is a separate step performed by the user or CI. (`README.md:152`)
- Inferred, not verified: the preview server listens on its port without naming a network interface, so while it runs the ADR text it serves may be reachable from other machines. (`packages/web/cli/commands/preview.ts` `listen`)
- Release secrets (npm and GitHub tokens) are kept out of the repository: the release script reads them from a git-ignored local file and CI uses repository secrets. (`scripts/release.sh` `release-credentials.local.sh`; `.github/workflows/on-merge-to-develop.yml` `secrets`)

### R-11 State, persistence and background work
Status: baseline · Source: documented (`README.md:39`); observed (`packages/core/src/adr/infrastructure/repositories/AdrRepository.ts` `getGitMetadata`); tested (`packages/core/integration-tests/rw.test.ts` "in global scope") · As of: 17e32021a8c5
- ADR markdown files in the configured folders are the only record of the ADRs and Git history supplies dates and authors. Nothing is stored between runs: every run re-reads each file and asks Git for the history of each file. (`packages/core/src/adr/infrastructure/repositories/AdrRepository.ts` `findAllInPath`; `packages/core/src/adr/infrastructure/repositories/AdrRepository.ts` `getGitMetadata`)
- Listing only reads. Writes happen in adr new (a new markdown file from the template), init (the configuration file, template, index, README and starter ADRs) and build (the output folder, .log4brains/out by default). (`packages/core/src/adr/infrastructure/repositories/AdrRepository.ts` `save`; `packages/init/src/commands/InitCommand.ts` `execute`; `packages/web/cli/commands/build.ts` `buildCommand`; `packages/core/integration-tests/rw.test.ts` "in global scope")
- Listing does its work once and ends. The only long-running work is preview, which serves the site, watches the ADR folders for changes and pushes updates over a socket until the user stops it. (`packages/web/cli/commands/preview.ts` `previewCommand`; `packages/core/src/infrastructure/file-watcher/FileWatcher.ts` `FileWatcher`)

### R-12 Machine-readable ADR index of the static site and the preview API
Status: baseline · Source: observed (`packages/web/cli/commands/build.ts` `toAdrLight`); observed (`packages/web/nextjs/src/pages/api/adr.ts` `toAdrLight`) · As of: 17e32021a8c5
- log4brains build writes data/BUILD_ID/adrs.json under the output folder: a JSON array with one object per ADR, in the usual order, holding slug, package, title, status, creationDate and publicationDate. (`packages/web/cli/commands/build.ts` `toAdrLight`; `packages/web/nextjs/src/lib-shared/types.ts` `AdrLight`)
- The preview server returns the same objects for GET /api/adr and answers 404 to any other method. (`packages/web/nextjs/src/pages/api/adr.ts` `toAdrLight`)
- Absent package, title and publication date are null, the status is lower case and dates are ISO text, exactly as in the programmatic records. (`packages/web/nextjs/src/lib-shared/types.ts` `toAdrLight`)
- This projection lives in the web package; the package that holds adr list does not depend on it. (`packages/cli/package.json` `dependencies`)

## Not inspected

- packages/web/nextjs/src components, scenes, layouts, contexts and mui folders, and the Storybook setup: the UI is outside the request.
- packages/core/src/lib (markdown-to-cheerio helpers and path helpers) and packages/core/src/adr/application/command-handlers (create from template, supersede): not on the listing path.
- packages/core/src/adr/application/query-handlers other than the search handler.
- packages/init/assets: only the two starter ADRs were read, not README.md, index.md and template.md; packages/init/src/commands/InitCommand.ts was read for the configuration, starter-ADR and list steps only.
- .github: the scheduled workflows and the reusable version-loading and npm-wait workflows were not read in full; docker/Makefile was only skimmed.
- Third-party libraries (commander, cli-table3, Joi, simple-git) were not read because dependencies are not installed; the behaviour attributed to them is labelled inferred.
- yarn.lock files, CHANGELOG files and images.
