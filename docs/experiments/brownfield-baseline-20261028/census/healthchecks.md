# Census of healthchecks at f6c46b594dec

- 1275 tracked files; 3998 commits from 2015-06-11 to 2026-10-28 (443 in the last 365 days); size class large; census took 1.33 s.
- Classes (files / text lines): code 990 / 61326; config 6 / 177; docs 42 / 11008; test 237 / 23573
- Code lines by extension: .py 21668, .html 12316, .css 8565, .less 8050, .html-fragment 7521, .js 2667, .example 160, .txt 134, .svg 108, (none) 56, .sh 32, .yml 29

## Map (code, test and docs weight; commits touching it in 365 days)

| Path | Code files / lines | Test files / lines | Docs files | Commits 365d |
|---|---|---|---|---|
| hc | 589 / 26052 | 237 / 23573 | 0 | 734 |
| hc/integrations | 311 / 9274 | 115 / 10597 | 0 | 286 |
| hc/api | 144 / 7499 | 35 / 5089 | 0 | 198 |
| hc/accounts | 71 / 3924 | 33 / 3262 | 0 | 99 |
| hc/front | 19 / 2474 | 42 / 3978 | 0 | 89 |
| hc/lib | 14 / 1765 | 10 / 615 | 0 | 32 |
| hc/logs | 9 / 210 | 2 / 32 | 0 | 13 |
| hc/payments | 15 / 228 | 0 / 0 | 0 | 1 |
| templates | 182 / 15735 | 0 / 0 | 35 | 199 |
| templates/docs | 35 / 7521 | 0 / 0 | 35 | 99 |
| templates/front | 70 / 4497 | 0 / 0 | 0 | 50 |
| templates/accounts | 22 / 2138 | 0 / 0 | 0 | 12 |
| templates/emails | 43 / 1167 | 0 / 0 | 0 | 35 |
| templates/admin | 5 / 37 | 0 / 0 | 0 | 0 |
| static | 134 / 11081 | 0 / 0 | 0 | 82 |
| stuff | 74 / 8125 | 0 / 0 | 0 | 6 |
| docker | 6 / 282 | 0 / 0 | 1 | 41 |
| (root) | 5 / 51 | 0 / 0 | 5 | 170 |
| .github | 0 / 0 | 0 / 0 | 1 | 28 |

## Root files

.gitignore, CHANGELOG.md, CONTRIBUTING.md, LICENSE, README.md, SECURITY.md, manage.py, mypy.ini, requirements-dev.txt, requirements.txt, search.db

## Documentation

- READMEs: README.md (606 lines), docker/README.md (189 lines)
- Instruction files at the root: CHANGELOG.md, CONTRIBUTING.md, README.md, SECURITY.md, docker/README.md
- Markdown-like files in all: 58
- Decision records (found by content): none

## Hot spots (code and test files changed most in 365 days)

- requirements.txt (46)
- hc/api/models.py (35)
- hc/front/views.py (30)
- requirements-dev.txt (25)
- hc/api/views.py (23)
- hc/accounts/models.py (22)
- docker/Dockerfile (20)
- hc/settings.py (13)
- hc/integrations/email/tests/test_notify.py (10)
- hc/integrations/email/transport.py (10)
- hc/lib/emails.py (10)
- hc/accounts/admin.py (9)

## Recent commits

- 2026-10-28 Fix Management API validation logic to reject NUL characters
- 2026-10-28 Replace CR and LF in header lines in the webhook integration
- 2026-10-27 Fix heading in CHANGELOG
- 2026-10-27 Update Docker base image to python:3.14.10-slim-trixie
- 2026-10-27 Add "Delete User" action in Profile admin
- 2026-10-27 Remove the "usage" column in user admin list view
- 2026-10-26 Upgrade minismtpd to v0.5 to enable concurrent SMTP sessions
- 2026-10-22 Fix a race condition in Profile.for_user()
