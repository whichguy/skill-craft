# Access: sessions, roles, tokens, errors

## Why the browser

The portal signs in through SAML single sign-on, keeps a cookie session with an XSRF token on writes, supports 2FA, and
tokens minted per role guard its Results and Rankings host. Replaying that outside a browser would put a password, a cookie
or a token in a script. Running in the owner's signed-in tab avoids all three: the page already holds the session, and the
runtime reads what it needs inside the page and returns only selected data.

## Roles and scope

`S80.roles()` (and `account.roles`) lists the login's roles from `/api/account/roles`:

| Type | `body_cid` | How scope is applied |
|------|-----------|----------------------|
| Personal | none | no scope parameter |
| Club (or another organisation) | the organisation's contact id | `?body_cid=<id>` on API calls; the path prefix `/v/<id>/...` on pages |

Pick with `--role personal`, `--role club` (when the login has exactly one club), or `--role <body_cid>`. A club role shows
the banner "acting as <club>" in the portal. Scope changes the data: the club-scoped results list holds only the club's
athletes, the personal-scoped one is every event. Never pass `body_cid` by hand; the runtime applies it from the role and a
conflicting value is refused. Keep identifiers distinct: contact id (`cid`), club id (`body_cid`), event id (`eid` or the
rankings-module `event_id`), and the rankings-module `athlete_id`, which is none of the others.

A member's record is addressed by contact id (`cid`). Under `personal` the default is the login's own. Under a club role there
is no safe default, since the role's own `cid` is the club's, so pass `--param cid=<contact id>` (`sport80 js` refuses without
it; find the id with `members.quick_search`). The club role also sees a different record: club-only tabs (Notes, Additional
Trackings, REPS Membership, Background Screening Due Payment, Archive Member) and none of Entries, Addresses, Communication
Preferences or the Learning Academy. This was checked on the owner's own record only (2026-11-08); another member's tab set
may differ with the member's roles.

## Tokens

- Results and Rankings are on `window.env.RANKINGS_DOMAIN_URL`. Logged in, the runtime calls
  `/ranking_module/access_token[?body_cid=]`, which returns two header values; it sends them only to that host, with
  `credentials` omitted, and never returns them. The club-scoped pair filters rows to the club.
- Public reads (event results, rankings tables, an athlete's results, featured rankings) use the public key that every
  portal page carries in `window.env.SERVICES_API_PUBLIC_KEY`. No login is needed, but the tab must be on a portal page so
  `window.env` exists.
- The XSRF cookie is read inside the page and sent only on same-origin POSTs.

## Signing in

The owner signs in, in their own browser, with their password manager. On a host that provides a password-manager fill for
the owner's approved login, use it on the sign-in page; on one that does not, ask the owner to sign in. A verification code
goes through the host's code-entry feature or the owner. A CAPTCHA or any bot challenge is not the agent's to solve: stop and
ask. Never ask for, type or store a password in chat, a script or a file.

The session can end while the agent works. Observed: an idle tab was sent to the single sign-on page on the next
navigation. The portal's SPA sends `X-Keep-Session: keepsession` on its calls and so does the runtime, as the SPA does; there
is no background keepalive loop and none should be added. Whether that header extends the session is not known.

## Errors

The runtime does not follow redirects on portal calls. With no session, a portal call returns an opaque redirect (or throws a
network error when redirects are followed); the rankings host answers 401 readably. So `AUTH_REQUIRED` is reported only when
a follow-up ping to the roles endpoint also fails. Otherwise the outcomes stay distinct:

| Code | Cause |
|------|-------|
| `AUTH_REQUIRED` | a redirect, network error or 401 and the ping also failed |
| `PERMISSION_DENIED` | 401 with a live session: the role lacks the right (Pre-Screening Approvals for the owner's club) |
| `FORBIDDEN` | 403: a missing id (event panels without `eid`, discount-code organisations without `id`) or a missing right |
| `SERVER` | 5xx (Bulk Renewal detail without its add-on id) |
| `RANKINGS_REFUSED` | the rankings host refused the credentials for this scope |
| `UNEXPECTED_REDIRECT` | a redirect with a live session (the event finder adds a default date; pass `from_date`) |
| `NETWORK` | no response with a live session |
| `CHALLENGE`, `THROTTLED` | bot challenge or 429: stop, no retry |
| `MISSING_PARAM`, `BAD_PARAM`, `FILTER_REQUIRED`, `UNKNOWN_FILTER`, `FIELDS_REQUIRED` | refused before any request |

## Politeness

One request at a time, 150 ms between pages, whole pages only, small defaults (50 rows, sensitive tables 0). Use filters and
fields instead of reading everything. Do not parallelise, loop, or crawl during an ordinary request: discovery is a
maintenance task.

## Output limits on some hosts

A host's script tool may cap the returned text and block text that looks like cookies or query strings. Keep results small
(`--fields`, `--rows`, `--pick`), pass `--plain` to rewrite `?`, `&`, `=` in strings, and if more is needed write the result to
a scratch tab on the same origin and read that page's text (`S80.show(result)`; never in a tab you still need, since it
replaces the page body). See `hosts.md`.
