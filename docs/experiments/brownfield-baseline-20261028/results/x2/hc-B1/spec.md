# Healthchecks: baseline specification
Baseline coverage: deep: hc, hc/api, hc/integrations, hc/front, hc/accounts, hc/lib, templates/front, static; overview: hc/logs, hc/payments, templates, templates/docs, templates/emails, docker, (root), .github; not inspected: templates/accounts, templates/admin, stuff. As of f6c46b59.

## Overview

**Purpose.** Healthchecks is a cron job monitoring service: scheduled jobs ("checks") send "pings" over HTTP or email, and when a ping does not arrive on time the service sends alerts through integrations (email, chat, SMS, webhooks and 25+ others). It also offers a live web dashboard, a Management API, status badges, periodic email reports, optional two-factor login and teams (projects, members, read-only access). It runs as the hosted service at healthchecks.io or self-hosted, BSD 3-clause licensed. (`README.md` "Healthchecks is a cron job monitoring service")

**Consumers.**
- Monitored jobs: send pings by HTTP (UUID URLs and project-key/slug URLs) or by email to the `smtpd` listener, with start, success, fail and log signals, an optional exit status and an optional body.
- Web users: project owners, team members (read-only, member, manager) and site superusers.
- API clients: the Management API (v1 to v3) authenticated with per-project read-write or read-only API keys.
- Third parties calling back: Twilio delivery status, SMTP bounce messages, the Telegram bot, OAuth redirects of integrations.
- Public or key-based viewers: status badges, the `/tv/` dashboard, Prometheus scrapers, the operator metrics endpoint (key in `METRICS_KEY`).
- Site operators who self-host and run the web server plus the long-running `sendalerts`, `sendreports --loop` and optional `smtpd` processes (Docker image or manual setup).

**Entry points.** URL routes assembled in `hc/urls.py` (accounts, api, front, payments and one URL module per integration); `manage.py` commands (`sendalerts`, `sendreports`, `smtpd`, prune commands, `render_docs`, `populate_searchdb`, `settelegramwebhook`); the container script `docker/run.sh`; configuration read in `hc/settings.py`. (`hc/urls.py` `urlpatterns`)

**Terms** (domain word, then the code name used in locators): check = `Check`; ping = `Ping`; status change = `Flip` (the record that drives alerts and downtime statistics); integration = `Channel` (older UI word: channel); delivery record = `Notification` (shown as "Downtime alert" in the Events log); transport = the class that delivers to one integration kind; project = `Project`; member = `Member`; account owner settings and quotas = `Profile`.

**Areas** (census map, with depth and a one-line scope):
- `hc` (deep): package files only. `hc/settings.py` is the configuration contract, `hc/urls.py` the route table, `hc/test.py` the shared test base class; sub-areas below carry their own depth.
- `hc/api` (deep): models (Check, Ping, Flip, Channel, Notification, TokenBucket), transport base classes, `sendalerts` and other management commands, delivery callbacks, retention. Overview only: ping endpoints, Management API check create/update, badges.
- `hc/integrations` (deep for delivery): 29 transport kinds plus the Prometheus scrape endpoint. Deep: the transport contract and the failure, retry, quota and callback behaviour of the webhook, email, SMS, call, WhatsApp, Slack, Signal, Telegram, Pushover, GitHub, Discord, Splunk On-Call and group transports. Overview only: set-up views, forms, templates and URLs of each kind.
- `hc/accounts` (deep for access and quotas): Profile limits and quota counters, Project and Member roles, API-key hashing. Overview only: login, signup, 2FA, profile, billing views.
- `hc/front` (deep for the check event log): access helpers, Events log views and filter form, details status endpoint, Test! button, Integrations list. Overview only: dashboard, checks list, docs serving, badges, copy and transfer.
- `hc/lib` (deep for `hc/lib/curl.py`, `hc/lib/emails.py`, `hc/lib/signing.py`, `hc/lib/statsd.py`, `hc/lib/urls.py`, `hc/lib/string.py`; not inspected: badges, date, html, s3, tz, typealias and webauthn modules).
- `hc/logs` (overview): a logging handler that stores `hc.*` log records and unhandled request errors in a database table (`hc/logs/__init__.py` `Handler`).
- `hc/payments` (overview): placeholder views that answer "not implemented" plus a Subscription model (`hc/payments/views.py` `pricing`).
- `templates` (overview): base layouts, page shells (`templates/base.html` navigation shows an Integrations warning mark).
- `templates/front` (deep for the event templates and the integrations list): `templates/front/log.html`, `templates/front/log_rows.html`, `templates/front/log_row.html`, `templates/front/event_summary.html`, `templates/front/details_events.html`, `templates/front/channels.html`. Overview only: the rest.
- `templates/docs` (overview): user documentation in Markdown, rendered to committed `.html-fragment` files; read: notifications, self-hosting, settings reference, API headings.
- `templates/emails` (overview): subject, text and HTML bodies named by `hc/lib/emails.py`; bodies not read.
- `templates/accounts`, `templates/admin` (not inspected).
- `static` (deep for `static/js/log.js`, `static/js/details.js`, `static/js/adaptive-setinterval.js`): the live Events log and details polling. Not inspected: CSS, fonts, images, vendored jQuery 3.6.0 and Bootstrap 3.4.1.
- `stuff` (not inspected): file listing only (Bootstrap LESS sources, icon project, favicon); the Docker build deletes it (`docker/Dockerfile` `rm -rf /opt/healthchecks/stuff`).
- `docker` (overview): reference image, compose file, `docker/run.sh` process supervisor, gunicorn settings.
- `(root)` (overview): instruction files, `requirements*.txt`, `mypy.ini`, `manage.py`, `search.db` (documentation search index).
- `.github` (overview): test matrix, mypy, coverage and Docker publish workflows; pull request template with an AI-assistance disclosure.

**Read only in part, even where an area is marked deep.** Per-integration set-up views, forms, templates and URL modules (all kinds); login, signup, 2FA, profile and project-settings views in `hc/accounts`; dashboard, checks list, badge, copy and transfer views in `hc/front`; the check create and update API, badge endpoints, `smtpd`, `submitchallenge` and report content in `hc/api`; the Django admin beyond the integration and notification pages; migrations other than the few opened; and the transports for PagerDuty, Opsgenie, PagerTree, Spike, Gotify, Google Chat, Microsoft Teams, Matrix, Zulip, Splunk On-Call, Pushbullet, Trello, Mattermost, Rocket.Chat and ntfy, of which only error, permanent-failure and rate-limit lines were read. Nothing was run: no tests, no tooling, no browser.

## Requirements

### R-1 A status change alerts the check's integrations
Status: baseline · Source: observed (`hc/api/models.py` `select_channels`); tested (`hc/api/tests/test_flip_model.py` "test_select_channels_works"); documented (`templates/docs/self_hosted.md` "Sending Status Notifications") · As of: f6c46b59
- A check going down or up is recorded as a status change; alerts are made from that record, not directly from the ping or the timeout. (`hc/api/models.py` `create_flip`)
- A check with no ping by its deadline plus grace time is marked down by the alert process, and the status change is dated at that deadline, not at the moment of detection. (`hc/api/tests/test_sendalerts.py` "test_it_creates_a_flip_when_check_goes_down")
- A failure signal, or a success signal while the check is down, is recorded by the request that received the ping. (`hc/api/models.py` `ping`)
- Pausing, resuming, and a schedule edit in the web UI that puts a check down record the change as already processed, so they send no alerts. (`hc/front/views.py` `mark_as_processed`)
- A change to "up" from "new" or "paused" sends no alerts. (`hc/api/tests/test_flip_model.py` "test_send_alerts_handles_new_up_transition")
- Only integrations assigned to the check are alerted, and disabled integrations are skipped. (`hc/api/tests/test_flip_model.py` "test_it_skips_disabled_channels")
- An integration that ignores the new status is skipped and leaves no record (for example an email or phone integration set to alert on one status only, a webhook with no URL for the status, a shell integration with no command for it, the phone-call integration for "up"). (`hc/api/tests/test_flip_model.py` "test_select_channels_handles_noop")
- Integrations are alerted in ascending order of their last measured delivery duration; integrations never used go last. (`hc/api/tests/test_flip_model.py` "test_it_sorts_channels_by_last_notify_duration")
- Handling a status change also sets or clears the next reminder date of the project owner and members. (`hc/api/tests/test_sendalerts.py` "test_it_sets_next_nag_date")

### R-2 Each delivery attempt is recorded as a notification
Status: baseline · Source: observed (`hc/api/models.py` `notify`); tested (`hc/integrations/webhook/tests/test_notify.py` "test_webhooks_handle_500") · As of: f6c46b59
- Before the integration is contacted, a record is stored with the check (empty for test notifications), the integration, the check's new status ("up" or "down"), the creation time, a random public code and the error text "Sending". (`hc/api/models.py` `n.error = "Sending"`)
- The integration is then called once with the status change; the record's error text becomes empty when the call succeeds and the error message when it fails. (`hc/integrations/webhook/tests/test_notify.py` "test_it_works")
- After every attempt the integration stores the attempt's start time, its duration and its last error text, so a success clears an earlier failure. (`hc/front/tests/test_send_test_notification.py` "test_it_clears_channel_last_error")
- An error flagged permanent also marks the integration disabled. (`hc/integrations/slack/tests/test_notify.py` "test_it_disables_channel_on_404")
- If the integration or the check no longer exists, no record is kept and the attempt reports "Channel or check does not exist any more". (`hc/api/tests/test_notify.py` "test_it_handles_deleted_channel")
- An integration that ignores the status creates no record and the attempt reports "no-op". (`hc/integrations/group/tests/test_notify.py` "test_it_handles_noop")
- The outcome is returned to the caller as text (empty for success, "no-op", or the error); the alert process, the Test! button, group fan-out and the account-deletion notice all read it. (`hc/api/management/commands/sendalerts.py` `notify`)
- Only the typed delivery error is handled. Any other exception raised during delivery escapes the attempt, leaving the record at "Sending" and the integration's last-attempt fields unchanged. (`hc/api/models.py` `transports.TransportError`)
- Error text is stored as given in a 200-character column; only the callback paths shorten it. (`hc/api/views.py` `[:200]`)

### R-3 How a failed delivery is handled today
Status: baseline · Source: observed (`hc/api/transports.py` `request`); tested (`hc/integrations/webhook/tests/test_notify.py` "test_webhooks_handle_curl_errors"); conflict (`hc/integrations/webhook/templates/webhook_form.html` "not one of: 200, 201, 202 or 204"); conflict (`hc/api/transports.py` `(200, 201, 202, 204, 205)`) · As of: f6c46b59
- HTTP integrations treat a response other than 200, 201, 202, 204 or 205 as a failure with the text "Received status code N" (some integrations add detail). (`hc/integrations/webhook/tests/test_notify.py` "test_it_handles_http_205")
- Connection problems become short texts: "Connection timed out" (30 second limit), "Could not resolve host", "Connection failed", "TLS handshake failed", "Too many redirects", "Connections to private IP addresses are not allowed", "HTTP request failed, code: N". (`hc/lib/curl.py` `CurlError`)
- Within one attempt an HTTP integration makes up to 3 tries back to back with no delay, and stops at the first error flagged permanent. (`hc/integrations/webhook/tests/test_notify.py` "test_webhooks_handle_500")
- The Signal integration makes up to 2 tries on a non-permanent error. (`hc/integrations/signal/tests/test_notify.py` "test_it_retries_network_failure")
- The email integration sends with up to 3 tries, one second apart, when the SMTP connection drops or rejects the data, and then reports "SMTP connection error". (`hc/lib/tests/test_emails.py` "test_it_limits_retries")
- Shell and Apprise integrations make one try. (`hc/integrations/shell/transport.py` `call`)
- A webhook test notification never retries. (`hc/integrations/webhook/tests/test_notify.py` "test_webhooks_dont_retry_when_sending_test_notifications")
- Errors flagged permanent are not retried and disable the integration. Which errors are permanent is decided per integration: Slack 404 and "invalid_token", Discord and Splunk On-Call 404, GitHub 410, Pushover invalid user, Twilio invalid phone number (code 21211), a removed Telegram chat, a Signal recipient that is not found; Mattermost and Rocket.Chat 404 are not. (`hc/integrations/rocketchat/tests/test_notify.py` "test_it_does_not_disable_channel_on_404")
- A disabled integration stays disabled until someone acts: saving the email integration's form clears the flag, no other integration form does. (`hc/front/tests/test_channels.py` "test_it_shows_fix_button_for_disabled_email")
- Nothing re-queues a failed delivery: after the attempt (and its in-attempt tries) the failure is final for that status change and integration. (`hc/api/management/commands/sendalerts.py` `process_one_flip`)
- The webhook set-up page tells users that failed calls are retried up to 2 additional times and lists 200, 201, 202 and 204 as the success codes; the transport also accepts 205 (conflict: the page is out of date, current behaviour stands). (`hc/integrations/webhook/templates/webhook_form.html` "retries failed webhook calls up to 2 additional times")

### R-4 Delivery feedback can arrive after the attempt
Status: baseline · Source: observed (`hc/api/views.py` `notification_status`); tested (`hc/api/tests/test_notification_status.py` "test_it_handles_twilio_failed_status"); tested (`hc/api/tests/test_bounces.py` "test_it_handles_permanent_notification_bounce") · As of: f6c46b59
- Providers and mail systems report failures after the attempt has returned; the report updates the same notification record and never creates a new one. (`hc/api/views.py` `bounces`)
- The status callback is a POST to `/api/v1/notifications/<code>/status` (also v2, v3) that needs no API key or session; the record is found by its random code. A missing record, or one older than 1 hour, is ignored with HTTP 200. (`hc/api/tests/test_notification_status.py` "test_it_checks_ttl")
- The callback address is sent to Twilio for SMS, WhatsApp and phone-call deliveries only. (`hc/integrations/sms/tests/test_notify.py` "test_it_works")
- A failed or undelivered message status, or a failed call status, records the error "Delivery failed (status=...)."; a generic `error` field is recorded cut to 200 characters; `mark_disabled` also disables the integration. (`hc/api/tests/test_notification_status.py` "test_it_handles_mark_disabled_key")
- A callback never clears an error: a "delivered" status leaves the record and the integration unchanged. (`hc/api/tests/test_notification_status.py` "test_it_handles_twilio_delivered_status")
- A failure report copies its text to the integration's last error. (`hc/api/tests/test_notification_status.py` "test_it_handles_error_key")
- Email bounces arrive as messages at the bounce endpoint, addressed to a signed identifier that expires after 48 hours; the record must be younger than 48 hours. (`hc/api/tests/test_bounces.py` "test_it_checks_notification_age")
- Status 4.x.x and 5.4.4 bounces are transient (error recorded, integration stays enabled); other 5.x.x bounces are permanent (integration disabled); other statuses are ignored. (`hc/api/tests/test_bounces.py` "test_it_categorizes_5_4_4_as_transient")
- An alert email carries the bounce identifier only as the envelope sender, and only when the site sets `EMAIL_MAIL_FROM_TMPL` (a setting absent from the settings reference); without it the identifier is dropped and bounces cannot be tied to a record. (`hc/integrations/email/tests/test_notify.py` "test_it_sets_custom_mail_from")

### R-5 Deliveries consume quotas and rate limits
Status: baseline · Source: observed (`hc/accounts/models.py` `authorize_sms`); tested (`hc/integrations/sms/tests/test_notify.py` "test_it_enforces_limit") · As of: f6c46b59
- SMS and WhatsApp share one monthly send counter per account owner; phone calls have their own. The counter goes up before the provider is called and is not reversed when the provider call fails. (`hc/integrations/sms/tests/test_notify.py` "test_it_works")
- At the monthly limit an attempt fails with "Monthly SMS limit exceeded", "Monthly message limit exceeded" or "Monthly phone call limit exceeded" without calling the provider. (`hc/integrations/call/tests/test_notify.py` "test_call_limit")
- Each such refused attempt emails the project owner and members a notice containing the alert text; there is no de-duplication. (`hc/integrations/call/tests/test_notify.py` "test_call_limit")
- Counters reset at the start of each calendar month. (`hc/integrations/sms/tests/test_notify.py` "test_it_resets_limit_next_month")
- Telegram, Signal, Pushover and ntfy allow 6 messages per minute per recipient, chat, user key or topic; beyond that the attempt fails with "Rate limit exceeded", which is not permanent. (`hc/integrations/telegram/tests/test_notify.py` "test_it_obeys_rate_limit")
- Quotas and rate limits are checked inside each attempt, so every call to an integration spends them, including test notifications. (`hc/integrations/signal/tests/test_notify.py` "test_it_obeys_rate_limit")

### R-6 A group integration alerts its members
Status: baseline · Source: observed (`hc/integrations/group/transport.py` `notify`); tested (`hc/integrations/group/tests/test_notify.py` "test_it_works") · As of: f6c46b59
- A group lists integrations of the same project; one alert to the group makes one delivery record for the group plus one per member, each in the check's log. (`hc/integrations/group/tests/test_notify.py` "test_it_works")
- Members that ignore the status are not counted as failures; unknown or foreign member codes are ignored. (`hc/integrations/group/tests/test_notify.py` "test_it_ignores_invalid_channels")
- If any member fails the group's own attempt fails with "N out of M notifications failed". (`hc/integrations/group/tests/test_notify.py` "test_it_reports_failure_count")
- Members are called whether or not they are disabled. (`hc/api/models.py` `group_channels`)

### R-7 Test notifications
Status: baseline · Source: observed (`hc/front/views.py` `send_test_notification`); tested (`hc/front/tests/test_send_test_notification.py` "test_it_sends_test_email") · As of: f6c46b59
- The Test! button on the Integrations page sends a synchronous alert for a dummy check named "TEST" in the "down" state; if the integration ignores "down" it sends an "up" alert instead. (`hc/front/tests/test_send_test_notification.py` "test_it_handles_up_only_sms_channel")
- The page then shows "Test notification sent!" or "Could not send a test notification." followed by the error. (`hc/front/tests/test_send_test_notification.py` "test_it_sets_channel_last_error")
- A test delivery record has no check and is never listed in a check's log; each new test first deletes the integration's earlier test records. (`hc/front/views.py` `Notification.objects.filter(channel=channel, owner=None).delete()`)
- Any project member, including a read-only member, may send a test. (`hc/front/tests/test_send_test_notification.py` "test_it_allows_readonly_user")
- Test deliveries update the integration's last error and last attempt. (`hc/front/tests/test_send_test_notification.py` "test_it_clears_channel_last_error")
- The account-deletion warning also sends a test-style alert through every integration of the owner when 14 or fewer days remain. (`hc/accounts/management/commands/senddeletionscheduled.py` `send_channel_notifications`)

### R-8 The check event log lists a check's events
Status: baseline · Source: observed (`hc/front/views.py` `_get_events`); tested (`hc/front/tests/test_log_events.py` "test_it_works") · As of: f6c46b59
- The Events page for a check is `/checks/<code>/log/`; its first rows are rendered with the page and later rows are fetched from `/checks/<code>/log_events/`. (`hc/front/urls.py` `check_urls`)
- The list merges pings, status changes and, when requested, notifications, newest first, at most 1000 entries; a status change sorts after a ping with the same timestamp. (`hc/front/views.py` `_get_events`)
- The covered period starts at the later of the check's creation and the oldest retained ping, and ends now or at the chosen `end` time. (`hc/front/tests/test_log_events.py` "test_it_does_not_show_too_old_notifications")
- Filter flags `success`, `fail`, `start`, `log`, `ign`, `notification` and `flip` select entry kinds; with none selected the list is empty; the `success` flag also matches pings with no kind. (`hc/front/forms.py` `LogFiltersForm`)
- The timestamps `u` and `end` must be Unix times between 1262296800 and 1893448800 (about 2010 to 2030), otherwise the request is rejected with HTTP 400. (`hc/front/tests/test_log_events.py` "test_it_rejects_bad_u_parameter")
- The initial page lists pings and status changes only. Notifications appear after the user ticks "Downtime alert", which starts unticked. (`templates/front/log.html` "Downtime alert")
- Only notifications about a "down" alert are ever listed; recovery ("up") alerts are not. (`hc/front/views.py` `check_status="down"`)
- The Management API has no notification listing: it lists a check's pings and status changes and the project's integrations (id, name, kind). (`hc/api/urls.py` `api_urls`)
- Not protected by tests: the same-named test in `hc/front/tests/test_log.py` asserts the text "Sent email to", which the page never renders, and the initial page never lists notifications. (`hc/front/tests/test_log.py` "test_it_does_not_show_too_old_notifications")

### R-9 A notification row in the event log
Status: baseline · Source: observed (`templates/front/event_summary.html` `event.error`); tested (`hc/front/tests/test_log_events.py` "test_it_shows_email_notification") · As of: f6c46b59
- A notification row has an alert icon, the attempt's creation time (formatted in the browser's selected time zone) and a one-line description. (`templates/front/log_row.html` `event.check_status`)
- The description depends on the integration kind: "Sent an email to <address>", "Sent a Slack alert", "Sent a Pushover notification", "Called a webhook <down URL>", "Sent an SMS to <number>", "Sent a WhatsApp message to <number>", "Added a Trello card", "Executed a shell command", "Made a phone call to <number>", "Sent a Signal message to <number>", "Sent a Gotify notification", "Sent a group notification", "Created a GitHub issue in <repo>", otherwise "Sent an alert to <kind>". (`hc/front/tests/test_log_events.py` "test_it_shows_webhook_notification")
- When the record's error text is not empty a second line "Error: <text>" is shown, escaped. This includes the in-flight text "Sending" and failures reported later by callbacks. (`templates/front/event_summary.html` `event.error`)
- The row reads the integration's current settings, so editing an integration changes how its earlier rows read (for example the webhook URL). (`templates/front/event_summary.html` `down_webhook_spec`)
- New integration kinds are expected to add their own description branch. (`CONTRIBUTING.md` "event_summary.html")

### R-10 The Events page and the details page update live
Status: baseline · Source: observed (`static/js/log.js` `fetchNewEvents`); tested (`hc/front/tests/test_status_single.py` "test_it_omits_events"); inferred (`static/js/log.js` "formatPingDates(dateFormat, tbody.querySelectorAll") · As of: f6c46b59
- The Events page asks for newer rows every 3 seconds (for 20 polls after the last mouse movement or the tab becoming visible) and once a minute regardless, only while the "older than" slider is at "now" and no request is pending. (`static/js/adaptive-setinterval.js` `adaptiveSetInterval`)
- A poll sends the ticked filters and the full-precision timestamp of the newest row; the server returns only entries created after it (HTML rows) and the newest timestamp in the `X-Last-Event-Timestamp` header. (`hc/front/tests/test_log_events.py` "test_it_accepts_start_parameter")
- Changing a filter or the slider reloads the whole list with the new filters. (`static/js/log.js` `applyFilters`)
- Reading the code, the success handler of the live poll calls the date formatter with an identifier (`dateFormat`) that is defined nowhere in `static/js`, and the formatter takes one argument, so prepending new rows probably throws before the rows are added. Not run in a browser; no JavaScript tests exist. (`static/js/log.js` "formatPingDates(dateFormat, tbody.querySelectorAll")
- The details page shows the 30 newest events from a status endpoint polled by script; that list never contains notifications, and the endpoint omits the HTML when the caller already has the newest timestamp. (`hc/front/views.py` `status_single`)

### R-11 Who may see a check's events and change them
Status: baseline · Source: observed (`hc/front/views.py` `_get_check_for_user`); tested (`hc/front/tests/test_log_events.py` "test_it_checks_ownership"); tested (`hc/front/tests/test_clear_events.py` "test_it_requires_rw_access") · As of: f6c46b59
- A logged-in user may view a check's events if they own its project, are a member of it with any role, or are a superuser; everyone else gets "not found" (HTTP 404), not "forbidden". (`hc/front/tests/test_log_events.py` "test_it_checks_ownership")
- A team member of any role can open the log. (`hc/front/tests/test_log_events.py` "test_team_access_works")
- Everyone who can open the log sees the integration targets it prints (email addresses, phone numbers, webhook URLs). (`templates/front/event_summary.html` `event.channel.email.value`)
- The events fragment and the status endpoint answer anonymous requests with HTTP 403; page views redirect to the login page. (`hc/front/tests/test_status_single.py` "test_it_returns_403_for_anon_requests")
- Members with the read-only role cannot clear a check's events (HTTP 403). (`hc/front/tests/test_clear_events.py` "test_it_requires_rw_access")
- Clearing (POST only) resets the check to "new" and deletes its pings, notifications and status changes. (`hc/front/views.py` `clear_events`)
- Management API calls use the project's API key (read-write, or read-only for GET endpoints); keys select the project, never an individual user. (`hc/api/decorators.py` `authorize_read`)
- Delivery callbacks use no user identity: possession of a record's random code, or a signed expiring bounce address, is the credential (see R-4). (`hc/api/views.py` `unsign_bounce_id`)

### R-12 Notification records are retained with the ping history
Status: baseline · Source: observed (`hc/api/models.py` `prune`); tested (`hc/api/tests/test_check_model.py` "test_it_prunes"); documented (`README.md` "Database Cleanup") · As of: f6c46b59
- Notification records older than the oldest retained ping of their check are deleted when the check prunes, which happens on every 100th ping and when the batch command runs. (`hc/api/tests/test_check_model.py` "test_it_prunes")
- The number of retained pings per check defaults to 100 and is changed per account owner by site administrators. (`hc/accounts/models.py` `ping_log_limit`)
- Status changes are pruned when older than the oldest retained ping and older than 93 days. (`hc/api/tests/test_check_model.py` "test_it_does_not_prune_flips_less_than_93_days_old")
- The batch prune command prunes every check with more than 100 pings. (`hc/api/tests/test_prunepingsslow.py` "test_it_works")
- Deleting a check or an integration deletes its notification records; clearing a check's events deletes the check's. (`hc/api/models.py` `models.CASCADE`)
- The README says old rows of the ping, status-change and notification tables are removed automatically. (`README.md` "Database Cleanup")

### R-13 Integration health is visible to users and administrators
Status: baseline · Source: observed (`templates/front/channels.html` `last_error`); tested (`hc/front/tests/test_channels.py` "test_it_shows_channel_issues_indicator") · As of: f6c46b59
- The Integrations page shows each integration as "Disabled", "Unconfirmed" (unverified email) or "Ready to deliver", and its last attempt as "Delivered, <time ago>", "Failed, <time ago>" with the error as a tooltip, or "Never". (`templates/front/channels.html` "Ready to deliver")
- A project's navigation shows a warning mark on Integrations when it has no integration or any integration has a non-empty last error. (`hc/accounts/models.py` `have_channel_issues`)
- SMS, WhatsApp and call integrations also show the month's quota use. (`templates/front/channels.html` "sends this month")
- Site administrators can filter integrations by kind, slow delivery, last error and disabled flag, and disable several at once. (`hc/api/admin.py` `LastErrorFilter`)
- Site administrators can list and search delivery records, filtered by integration kind, date and error. (`hc/api/admin.py` `NotificationsAdmin`)

### R-14 Operators can observe delivery and failures
Status: baseline · Source: observed (`hc/api/management/commands/sendalerts.py` `notify`); tested (`hc/api/tests/test_sendalerts.py` "test_it_increases_statsd_fail_counter"); tested (`hc/api/tests/test_metrics.py` "test_it_returns_max_notification_id") · As of: f6c46b59
- For each processed status change the alert process prints "<check code> goes <status>" and one line per integration: the first 8 characters of its code, its kind, and either "OK in N.Ns" or "Error in N.Ns: <error>". (`hc/api/management/commands/sendalerts.py` `notify`)
- With `STATSD_HOST` set it counts `hc.notifications.<kind>.success` and `.fail` and times dwell and send time; without it the calls do nothing. (`hc/api/tests/test_sendalerts.py` "test_it_increases_statsd_success_counter")
- The metrics endpoint returns the newest ping id, the newest notification id and the number of unprocessed status changes when called with the matching `X-Metrics-Key`; it answers 403 when the key is unset or wrong. (`hc/api/tests/test_metrics.py` "test_it_handles_incorrect_metrics_key")
- Unexpected exceptions while sending are logged at error level with the traceback by the application logger, which stores them in a database table, and are re-raised. (`hc/api/management/commands/sendalerts.py` `on_notify_done`)
- Expected delivery failures are not logged as exceptions; they are visible as record error text, integration last error, a statsd failure count and the process log line. (`hc/api/tests/test_sendalerts.py` "test_it_increases_statsd_fail_counter")

### R-15 Alerts are sent by a separate, always-running process
Status: baseline · Source: observed (`hc/api/management/commands/sendalerts.py` `process_one_flip`); documented (`templates/docs/self_hosted.md` "Sending Status Notifications"); tested (`hc/api/tests/test_sendalerts.py` "test_it_processes_flip"); conflict (`docker/README.md` "They are run automatically on"); conflict (`docker/run.sh` `SMTPD_PORT`) · As of: f6c46b59
- Without the alert process no alerts are sent; unprocessed status changes wait in the database. (`templates/docs/self_hosted.md` "Sending Status Notifications")
- The process repeats: mark overdue checks down and record status changes, then handle unprocessed status changes one at a time, then sleep 2 seconds when idle or all workers are busy. (`hc/api/management/commands/sendalerts.py` `handle`)
- A status change is claimed with a conditional update before delivery starts; if another process already claimed it, this one skips it. (`hc/api/tests/test_sendalerts.py` "test_it_processes_flip")
- `--num-workers N` (default 1) sets how many status changes are delivered at the same time; integrations of one status change are called one after another. (`hc/api/management/commands/sendalerts.py` `add_arguments`)
- On SIGTERM or SIGINT it stops taking work and waits for running deliveries to finish. (`hc/api/management/commands/sendalerts.py` `on_signal`)
- Because the status change is marked processed before delivery, a crash or an escaped exception leaves the remaining integrations of that status change unalerted, and nothing retries them. (`hc/api/management/commands/sendalerts.py` `num_updated`)
- A check whose status cannot be computed is pushed back one hour so the process does not crash-loop. (`hc/api/management/commands/sendalerts.py` `handle_going_down`)
- The Docker image starts the alert process and `sendreports --loop` in the background and exits when any child exits. (`docker/run.sh` `wait -n`)
- The main README and `docker/README.md` say `smtpd` starts automatically in the container, but the script starts it only when `SMTPD_PORT` is set (conflict; the script's behaviour stands). (`README.md` "Docker Image")

### R-16 Delivery is shaped by settings
Status: baseline · Source: observed (`hc/settings.py` `WEBHOOKS_ENABLED`); documented (`README.md` "Configuration"); tested (`hc/integrations/webhook/tests/test_notify.py` "test_it_requires_webhooks_enabled") · As of: f6c46b59
- Settings come from environment variables; values in the optional local settings file (hc/local_settings.py, git-ignored) override them; secrets can be read from a file named by `<NAME>_FILE`. (`README.md` "Configuration")
- Integration kinds are gated by settings read at send time: webhooks (`WEBHOOKS_ENABLED`, default on), shell commands (`SHELL_ENABLED`, default off), Slack and others (`*_ENABLED`, default on), Twilio kinds (credentials), Signal (socket), Apprise (flag and library). (`hc/integrations/slack/tests/test_notify.py` "test_it_requires_slack_enabled")
- A kind switched off at send time fails the attempt with a text such as "SMS notifications are not enabled", which is not permanent. (`hc/integrations/sms/tests/test_notify.py` "test_it_requires_twilio_configuration")
- Private network targets are refused unless `INTEGRATIONS_ALLOW_PRIVATE_IPS` is true. (`hc/lib/tests/test_curl.py` "test_it_rejects_private_ip")
- No setting controls retries: the request timeout (30 seconds) and the in-attempt try count (3) are constants in code. (`hc/api/transports.py` `tries_left`)
- Every setting is documented in the settings reference, one section per setting in alphabetical order. (`templates/docs/self_hosted_configuration.md` "INTEGRATIONS_ALLOW_PRIVATE_IPS")
- `PUSHOVER_EMERGENCY_RETRY_DELAY` configures how often Pushover itself repeats an emergency alert; it is not the platform's retry. (`hc/settings.py` `PUSHOVER_EMERGENCY_RETRY_DELAY`)

### R-17 Delivery and its display protect privacy and security
Status: baseline · Source: observed (`hc/lib/curl.py` `opensocket`); documented (`templates/docs/self_hosted_configuration.md` "INTEGRATIONS_ALLOW_PRIVATE_IPS"); tested (`hc/integrations/webhook/tests/test_notify.py` "test_webhooks_replace_cr_lf_in_headers") · As of: f6c46b59
- Outbound HTTP from integrations refuses private addresses by default; Apprise uses its own client and is exempt. (`templates/docs/self_hosted_configuration.md` "INTEGRATIONS_ALLOW_PRIVATE_IPS")
- Webhook header values have non-Latin-1 characters turned into character references and CR or LF replaced with spaces. (`hc/integrations/webhook/tests/test_notify.py` "test_webhooks_replace_cr_lf_in_headers")
- Placeholders in webhook text are replaced without re-expanding values, so a check name containing `$` cannot inject another placeholder. (`hc/lib/string.py` `replace`)
- Alerts link to a cloaked check URL and must not contain the check's ping code. (`hc/integrations/email/tests/test_notify.py` "test_it_works")
- Delivery error text and integration targets in the log are escaped by the template engine. (`templates/front/event_summary.html` `event.error`)
- The shell integration is off by default; its commands run with the alert process's system permissions. (`README.md` "Shell Commands")
- The status callback and the bounce endpoint are unauthenticated by design and bounded by record age (1 hour, 48 hours) and, for bounces, by an HMAC signature. (`hc/api/tests/test_bounces.py` "test_it_handles_bad_signature")
- Vulnerability reports go to the address in the security policy. (`SECURITY.md` "Reporting a Vulnerability")

### R-18 Notification data persists in a relational database
Status: baseline · Source: observed (`hc/api/models.py` `Notification`); documented (`README.md` "Database Cleanup"); observed (`.github/workflows/tests.yml` `matrix`) · As of: f6c46b59
- A delivery record has a unique random code, an optional check, a status of at most 6 characters, an integration, a creation time (default now, UTC) and an error text of at most 200 characters. (`hc/api/models.py` `Notification`)
- The site runs on SQLite (default), PostgreSQL, MySQL or MariaDB, and CI runs the full suite on all four with Python 3.12 to 3.15. (`.github/workflows/tests.yml` `matrix`)
- Schema changes ship as numbered Django migrations in `hc/api/migrations` (the latest at this baseline is 0123) and are applied by `manage.py migrate` on upgrade. (`hc/api/migrations/0123_alter_channel_kind.py` `Migration`)
- The settings check requires `TIME_ZONE` to be UTC; times are stored timezone-aware. (`hc/api/apps.py` `hc.api.E003`)
- The model declares no explicit index beyond the unique code (Django adds foreign-key indexes); the only other option it sets is the latest-record field. (`hc/api/models.py` `get_latest_by`)
