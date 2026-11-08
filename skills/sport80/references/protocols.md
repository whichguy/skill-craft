# Protocols the runtime speaks

All verified live on 2026-11-08 unless marked. Paths are shown without the origin; `<body_cid>` is a club role's id and is
added by the runtime, never by hand. The portal is Laravel with an Inertia/Vue front end plus an older server-rendered layer.

## Menus: the capability inventory

`GET /api/menu/main[?body_cid=]` returns `{topMenu[], bottomMenu[]}` and `GET /api/menu/top[?body_cid=]` the account menu
(`{data[]}`). An item is `{title, type internal|vue|external|parent, url, route, vue_component, vue_component_data{url,
handler, profile_url, access_token_url}, subtypes[], sub_routes[], hidden}`. The menu differs by role, so it is the list of
what that role can do. A sub-route's `url_params` map route parameters to query names: the SPA appends `&eid=<value>` to the
component URL (`{{param_1}}` is `eid`).

## Datatable (`s80-datatable`)

1. `GET <descriptor>` returns `{title, paginated, initial_page, items_per_page, has_search, has_select, has_filters,
   has_advanced_filter, columns[{value,text,sortable}], filters[{name,type,label,...}], top_buttons[], data_url}`.
2. `POST <data_url>?p=<page, zero-based>&l=<page size>&sort=<column>&d=asc|des&s=<search>&st=<search type>` with the JSON body
   `{"columns": [], "filters": {name: value}}` (`filters` is `[]` when `has_advanced_filter`). Headers
   `X-Requested-With: XMLHttpRequest`, `X-Keep-Session: keepsession` and `X-XSRF-TOKEN` from the `XSRF-TOKEN` cookie.
3. The reply is `{total, page, items_per_page, statistics, data[]}`; each row has its columns and an `action[]` list of
   `{type, url, text}` (only `View` on Results rows has been seen). `l` sets the page size. Returned whole pages mean
   `maxRows` is a minimum; `next` says where to continue and `complete` is true only when the response holds every row.
4. Unfiltered quick search returns no rows. Date filters are `YYYY-MM-DD`. The Smart List descriptor lists only an action
   column: its rows need the saved view's column model in the body (not exercised).

## Tab menus (`s80-tab-menu`) and profile tabs

`GET <url>` returns `{name, buttons[], tabs[{title, vue_component, vue_component_data{url}, route, subtypes[]}]}`. Each tab is
another endpoint; nested tabs hang under `subtypes`. A person's tabs are
`/competitor_dashboard/profile_tabs?cid=<member cid>`; a club's are `/body_dashboard/profile_tabs?cid=<body_cid>&bt=5`. Most
person tabs are `/add_on_portal/c_add_ons_data_table?cid&contact_type&id_sport&id_cat`, a datatable whose `id_cat` selects the
category; the runtime resolves the tab by title so category ids never appear in the catalogue.

## Redirect pointers

`/api/contact/list/view_format` returns `{type, url}` naming the real list (cards for a personal login, the Smart List
configuration for a club). `/api/contact/list/config` returns the saved views, 72 column groups, `columns_model` and the
actions Edit Columns, Download Report, Create Subscriber Group, Send Email, Legacy List.

## Pages

- Inertia: the HTML holds `<div data-page="{...}">` with `{component, props}`. The runtime returns the component, prop keys and
  a shape; values only for props you `pick` (and `fields` you name). A form's `props.form.fields` gives field names (token
  fields and numeric ids are dropped).
- Legacy fragments (`AjaxContainer`): server-rendered HTML; the runtime reads headings, table headers, button labels and the
  form count, never cell text. Some fields load by script and need the page itself.
- The event finder redirects `/e_locator/<type>/find` to the same URL with `?from_date=<today>`; pass `from_date` so the
  call does not redirect. `/e_locator/<type>/event_search?from_date=` returns `{events[], page, total_pages}`.

## Results and Rankings (a second host)

`window.env.RANKINGS_DOMAIN_URL` (the rankings host). Same descriptor-then-rows protocol on these paths:

| Path | Notes |
|------|-------|
| `/api/events/table?platform=1` | Results: meet, level, date, results, action; filters `date_range_start`, `date_range_end`, `level` |
| `/api/categories/rankings/table?platform=1` | Rankings; filters add weight class, ages, level, WSO (and club when public) |
| `/api/events/<event_id>/table` | one event's results: lifter, bodyweight, six attempts, bests, total |
| `/api/athletes/<athlete_id>/table?platform=1`, `.../rankings/table` | one athlete; the id is from the person's Results & Rankings tab, not the contact id |
| `/api/categories/featured` | featured rankings (JSON) |

Credentials: logged in, two header values from `/ranking_module/access_token[?body_cid=]`; public, `X-API-Token` set to the
page's public key. The club token scopes the Results list to the club's athletes; the personal token and the public key give the
national list. CORS allows the portal origin. A bad or missing token is a readable 401.

## Writes and flows (not exercised)

Writes are plain form posts and page flows (checkout, add-on forms, entry wizard, sanction request) and are not driven by the
runtime. The catalogue lists them as guided entries with confirm text, naming the pages from the front-end inventory.
