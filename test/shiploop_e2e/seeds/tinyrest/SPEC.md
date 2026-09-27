# tinyrest

tinyrest is a single-process HTTP server that exposes a JSON or JSON5 document as a REST API. Each top-level key of the document is a resource. Array values are collections of records. Any other value is one singular object. The process loads the file into memory, serves it over HTTP, and writes the whole document back when a client creates, replaces, updates, or deletes data.

This document names the executable **tinyrest**. Help text and any other place the program prints its executable name use that name.

## Runtime and launch

### Runtime

- The host is Node.js, version **22.12.0 or newer** (`package.json` `engines.node`).
- The program is an ES module. It speaks HTTP/1.1 only. It does not open a database port, and it does not require a password.
- A published install puts `tinyrest` on the executable path. From a source tree the same contract is started with Node as `node --experimental-strip-types src/bin.ts` (development) or as the compiled `lib/bin.js` entry (build). Everything below is about that CLI, not about library calls.

### Command

```text
tinyrest [options] <file>
```

`<file>` is the database path. It must already exist. Only the first positional argument is used; further positionals are ignored. A path that starts with `-` can be passed after `--`.

| Option | Environment fallback | Meaning |
| --- | --- | --- |
| `-p`, `--port <port>` | `PORT`, else `3000` | Port number printed in the banner and passed to listen. The flag wins over `PORT`. |
| `-h`, `--host <host>` | `HOST`, else `localhost` | Used only in the printed endpoint URLs. It is not the bind address. |
| `-s`, `--static <dir>` | none (repeatable) | Extra static directory. May be repeated. Relative paths are resolved from the process working directory. |
| `--help` | | Print help and exit. |
| `--version` | | Print the package version and exit. |
| `-w`, `--watch` | | Accepted and ignored, after a warning. Watching is already the default outside production. |

The port string is parsed with JavaScript `parseInt` with no radix: leading whitespace is skipped, trailing junk is ignored, and a `0x` prefix is hexadecimal. The host string is used as given.

`--version` is handled before `--watch`, `--help`, and the file check. `--help`, or a command with no positional file, prints help and exits. `--watch` without a file therefore warns and then prints help.

### What the process prints

Help (stdout), exit code 0:

```text
Usage: tinyrest [options] <file>

Options:
  -p, --port <port>  Port (default: 3000)
  -h, --host <host>  Host (default: localhost)
  -s, --static <dir> Static files directory (multiple allowed)
  --help             Show this message
  --version          Show version number
```

`--version` prints the installed package version and a newline, then exits 0. This release's version string is `1.0.0-beta.15`.

Unknown options (stdout, then the help text, exit code 1): the parser's message up to but not including the first period. For `--nope` that line is:

```text
Unknown option '--nope'
```

A missing option value (`--port` with nothing after it, and the same for `--host` and `--static`) is not turned into that help path. The process crashes with a non-zero status and a Node `ERR_PARSE_ARGS_INVALID_OPTION_VALUE` TypeError on stderr (`Option '-p, --port <value>' argument missing`, and the analogous text for the other flags).

Missing file (stdout, exit code 1):

```text
File <path> not found
```

The file is not created.

`--watch` / `-w` (stdout, then the process continues):

```text
--watch/-w can be omitted, JSON Server 1+ watches for file changes by default
```

If the file exists and its contents are empty or only whitespace, the process replaces the file with the two bytes `{}` and continues.

On a successful listen, stdout is this text (blank lines included). `${port}` is the parsed port, `${file}` is the path argument, `${host}` is the host string:

```text
JSON Server started on PORT :${port}
Press CTRL-C to stop
Watching ${file}...

${kaomoji}

Index:
http://localhost:${port}/

Static files:
Serving ./public directory if it exists

Endpoints:
${one line per resource, or the empty message}
```

The kaomoji is one of these four, chosen uniformly at random on each start:

- `♡⸜(˶˃ ᵕ ˂˶)⸝♡`
- `♡( ◡‿◡ )`
- `( ˶ˆ ᗜ ˆ˵ )`
- `(˶ᵔ ᵕ ᵔ˶)`

When there is at least one resource, each endpoint line is:

```text
http://${host}:${port}/${key}
```

Keys are in the order they have in memory after load (`$schema` is already removed). When there are none:

```text
No endpoints found, try adding some data to ${file}
```

The Index URL is always `http://localhost:${port}/`, even when `--host` is something else. The endpoint lines use `--host`. The banner still says `Watching` when watching is disabled.

When the terminal treats the stream as colored, the same characters are styled: bold for the started line and the section labels, gray for the secondary lines and the `http://…/` prefix, magenta for the kaomoji, blue for the resource key, yellow for the `--watch` warning, red for the missing-file line, the unknown-option line, and file-parse errors. With color disabled the text is plain.

The process does not print a shutdown line. It stays up until the OS stops it (the banner tells the operator to press CTRL-C). It does not log each HTTP request.

The listen socket is Node's default for `listen(port)` with no host: the unspecified address (`::` when IPv6 is available), not the `--host` value. A port that is already taken, or a port that parses as `NaN`, crashes the process instead of printing the banner. The printed port is the number that was requested. Requesting port `0` prints `:0`; the operating system may assign a different port.

### Production

`NODE_ENV=production` does two things at startup and nothing else to the HTTP API:

- The file watcher is not installed. Edits made by other programs are not reloaded. The banner still says `Watching`.
- Unhandled server errors return the plain sentence `Internal Server Error` instead of the error message (see errors below). The error is still written to stderr.

### Watch and reload

Outside production the process watches that one file path for `change` events.

- While tinyrest itself is writing the file, the change caused by that write is ignored.
- A change that arrives after the write has finished re-reads the file.
- A successful re-read replaces the in-memory document. If the sorted list of top-level keys changed, or the previous re-read was a parse error, stdout prints a blank line and the `Endpoints:` block again. Editing values without adding or removing keys does not reprint.
- A `SyntaxError` on re-read leaves the previous memory in place and prints, in red when color is on:

```text

Error parsing ${file}
${parser message}
```

- Any other re-read error is printed with the default object log and also leaves the previous memory in place.
- The initial read is not inside that handler. Invalid JSON or JSON5 at startup is an uncaught exception: non-zero exit, parser stack on stderr, no banner.

## Database file

### Shape

The file is UTF-8. The extension decides the parser:

- Extension `.json5` (case-sensitive; `.JSON5` does not qualify): JSON5 in, JSON5 out.
- Every other extension, including `.json`: JSON in, JSON out.

The top-level value must be an object. A top-level JSON `null` is treated as an empty database `{}`. Keys are resource names. `$schema` is reserved metadata, not a resource: it is removed on read and is never listed or routed.

Each remaining value is either:

- a **collection**: a JSON array of objects (records), or
- a **singular resource**: any non-array value, normally one object.

Record identity is the own property `id`.

On read, for every element of every collection:

- If `id` is a JSON number, it is replaced with that number's default decimal string (`1` becomes `"1"`, `1.5` becomes `"1.5"`).
- If `id` is missing (`undefined`), a new id is assigned (see Ids). The new key is appended on that object.
- Any other `id`, including a string, `null`, or a boolean, is left as it is.
- No other property is rewritten. A foreign key such as `postId: 1` (a number) stays a number. Relationship checks use strict equality, so a numeric foreign key does not match a string id.

These id fixes live in memory immediately, including for later GET responses. They are written to disk only on the next mutation. Until then, a restart assigns a fresh id to any record that still has no `id` in the file.

A singular object is not given an `id`.

### Ids

New ids are 8 cryptographically random bytes encoded as base64url without padding: 11 characters from `A–Z`, `a–z`, `0–9`, `-`, and `_`. The client cannot choose an id. A collision is not checked. If two records share an id, read, update, and delete affect the first one only; foreign-key cleanup still uses the id string, so every related row with that id is updated.

### Writes

Create, replace, update, and delete write the entire in-memory document back.

- `.json` (and any non-`.json5` extension): `JSON.stringify` with two-space indent and no trailing newline. Key order is the in-memory order.
- `.json5`: compact JSON5. Valid identifier keys are bare. Strings use single quotes unless the string itself contains more single quotes than double quotes. There is no insignificant whitespace and no trailing newline. Comments and trailing commas from the original file are not preserved.

Every write sets a final property `$schema` to this exact string, the concatenation of `./node_modules/json` and `-server/schema.json`. Any `$schema` the user had stored is discarded on read, so the written value is always that string.

The write is a same-directory temporary file named `.` + the database basename + `.tmp`, then a rename over the database file. Readers do not see a half-written document. Overlapping writes keep the latest full snapshot.

GET, HEAD, and OPTIONS do not write the file.

The package also contains a JSON Schema document (`schema.json`) whose `$schema` is `https://json-schema.org/draft/2020-12/schema`. It says the document is an object and each property is either an array or an object. tinyrest does not read or enforce that schema.

### Example

A file that starts as:

```json
{
  "posts": [{ "id": 1, "title": "a" }, { "title": "noid" }],
  "comments": [
    { "id": "1", "text": "c", "postId": 1 },
    { "id": "2", "text": "d", "postId": "1" }
  ],
  "profile": { "name": "ada" }
}
```

is served, before any write, as posts `{"id":"1","title":"a"}` and `{"title":"noid","id":"<new id>"}`. Embedding comments onto posts includes only the comment whose `postId` is the string `"1"`. The comment whose `postId` is the number `1` does not match. After the next mutation the file is pretty-printed, ids are strings, and `$schema` is the string above.

## HTTP interface

Base URL: `http://<bind-address>:<port>`. Clients on the same machine can use `http://127.0.0.1:<port>` or `http://localhost:<port>` because the process listens on the unspecified address.

There is no authentication, no cookies, and no API prefix. Resource names and ids are single path segments. One optional trailing slash is accepted (`/posts` and `/posts/` are the same route). Names and ids are case-sensitive: `/POSTS/1` does not find a resource named `posts`. Matching is only against the path; the query string is not part of the route.

### Common response headers

Every response that enters the application, including static files, sends:

```text
X-Powered-By: tinyhttp
```

JSON API responses (collections, records, singular objects, the JSON 404 body, and the JSON 400 body) send:

```text
Content-Type: application/json
Access-Control-Allow-Origin: *
Access-Control-Allow-Methods: GET, HEAD, PUT, PATCH, POST, DELETE
Access-Control-Allow-Headers: content-type
```

`Content-Type` has no `charset` parameter. The body is `JSON.stringify(value, null, 2)`: two-space indent, no trailing newline. Objects and arrays keep key order. There is no `ETag` on these responses. `undefined` object properties are omitted by JSON, so a missing embedded object does not appear as `null`.

CORS is applied to every request that is not answered by a static file:

- `Access-Control-Allow-Origin` is always `*`. The request `Origin` is not reflected. Credentials and `Access-Control-Max-Age` are not set.
- `Access-Control-Allow-Methods` is exactly `GET, HEAD, PUT, PATCH, POST, DELETE`. `OPTIONS` is not in the list.
- If the request has no `Access-Control-Request-Headers`, `Access-Control-Allow-Headers` is `content-type`.
- If it has that header, the header value is split on commas, each piece is trimmed, and that list **replaces** the default. Case is preserved. A request header `Content-Type, X-Foo` produces two response fields, `Access-Control-Allow-Headers: Content-Type` and `Access-Control-Allow-Headers: X-Foo`.

`OPTIONS` on a URL that is not a static file stops in this CORS layer: status **204**, `Content-Length: 0`, empty body, the CORS headers above. It does not create or delete data.

### Errors

| Situation | Status | Body |
| --- | --- | --- |
| Resource or id handled by a route but not found, or the method does not apply to that kind of resource | 404 | JSON `{"error":"Not Found"}` |
| POST, PUT, or PATCH body that is not a JSON object (array, string, number, boolean, or `null`) | 400 | JSON `{"error":"Body must be a JSON object"}` |
| Body that is not valid JSON, or a body larger than the limit | 500 | See below |

The 404 and 400 bodies are pretty-printed like other JSON. A path with extra segments (`/posts/1/extra`, `POST /posts/1`) still hits the resource handler and returns this JSON 404, not a plain-text 404.

500 responses use `Content-Type: text/plain; charset=utf-8` and `X-Content-Type-Options: nosniff`. The stack or message is also written to stderr.

- When `NODE_ENV` is `production`, the body is exactly `Internal Server Error`.
- Otherwise the body is the error message with HTML escapes (`'` as `&#39;`, `"` as `&quot;`, and the same treatment for `&`, `<`, and `>`). Invalid JSON `not-json` produces `Unexpected token &#39;o&#39;, &quot;not-json&quot; is not valid JSON`.

### Request body

`POST`, `PUT`, `PATCH`, and `DELETE` read a body. `GET`, `HEAD`, and `OPTIONS` do not.

The body is parsed as JSON regardless of `Content-Type`. An empty body becomes `{}`. A body of more than **102400** bytes is rejected (`Payload too large. Limit: 102400 bytes`, turned into the 500 above). Whitespace-only or otherwise invalid JSON is a 500, not a 400.

The 400 check applies only to POST, PUT, and PATCH. The value must be a non-null object and not an array. DELETE ignores the body.

### Routes

| Method and path | Collection | Singular object |
| --- | --- | --- |
| `GET /` | Generated homepage, unless a static `index.html` wins (see Static files) | same |
| `GET /:name` | Array of records, or a pagination object | The object itself. Query string ignored |
| `GET /:name/:id` | One record, or 404 | 404 |
| `POST /:name` | 201 and the created record | 404 |
| `POST /:name/:id` | 404 | 404 |
| `PUT /:name` | 404 | 200 and the replacement object |
| `PUT /:name/:id` | 200 and the replacement record | 404 |
| `PATCH /:name` | 404 | 200 and the merged object |
| `PATCH /:name/:id` | 200 and the merged record | 404 |
| `DELETE /:name` | 404 | 404 |
| `DELETE /:name/:id` | 200 and the removed record | 404 |
| `OPTIONS` any non-file URL | 204 | 204 |

An unknown name is 404 for every method in the table. An unknown id is 404 for item methods.

`HEAD` is not a safe echo of `GET`. On a resource URL the write handlers also run. They see no JSON body and answer **400** with `Content-Type: application/json` (the standard body-must-be-an-object error). No write is committed, because the check fails first. Do not depend on a HEAD body being present.

### Homepage

`GET /` runs only when no static file claims `/` (see below). It is an HTML document, `Content-Type: text/html; charset=utf-8`, with a weak `ETag`.

The page title is `JSON Server`. Visible copy:

- Intro: `Available REST resources from db.json.` (this sentence is fixed, even when the file is `db.json5`).
- Section label: `Resources`.
- One link per resource, in key order, pointing at `/{name}`, showing the text `/{name}`. An array's meta text is `{length} items` (the word is always `items`, including for 1). Any non-array's meta text is `object`.
- No resources: `No resources in db.json.`
- Footer: `To replace this page, create public/index.html.`
- A heart control whose text is `❤`.

The header has two links labeled with the product name and `README`, and the heart is a link. Those three anchors open fixed upstream pages in a new tab. This specification does not reprint those addresses. A rebuild labels the product-name anchor **tinyrest** and may omit the upstream targets; the resource list, the empty sentence, and the footer sentence above are required.

The response carries a weak ETag, `W/"<hex byte length>-<first 27 characters of standard base64 of SHA-1 of the HTML body>"`. A later `GET` or `HEAD` of `/` with `If-None-Match` equal to that tag (weak or strong form accepted), and without `Cache-Control: no-cache`, returns **304** with an empty body and without `Content-Type`. JSON API responses do not participate in this.

The page lists whatever is in memory. It is regenerated on each request from current data.

### Static files

Before routing, files are looked up in this order:

1. `public` relative to the working directory (always, even when `-s` is omitted).
2. Each `-s` / `--static` directory, in the order given.

The first hit is the response. A hit does **not** add CORS headers. `X-Powered-By: tinyhttp` is still set.

Lookup of a URL path tries, in order: the path itself, `{path}/index`, then the same two with `.html` and with `.htm` appended. A trailing slash is stripped first. So `/` serves `index.html` or, if that is absent, `index.htm`. `/guide` serves `guide.html` when `guide` itself is absent. Directories are not listed.

While `NODE_ENV` is not `production` (the default):

- The file is read from disk on each request.
- `Cache-Control: no-store`.
- No `ETag`.
- `Last-Modified` is the file mtime in UTC HTTP date form.
- `Content-Length` is the file size.
- `Content-Type` comes from the extension. HTML is `text/html;charset=utf-8` (no space before `charset`). An unknown extension sends an empty content type.
- Dotfiles are served if requested.

In production the directory is snapshotted at startup. Files added later are not served until restart. Dotfiles are omitted, except paths under `.well-known`. There is no `Cache-Control` and no `ETag`. `Last-Modified`, `Content-Length`, and `Content-Type` are still set.

`Range: bytes=…` on a static file returns **206** with `Content-Range` and `Accept-Ranges: bytes`, or **416** with `Content-Range: bytes */{size}` when the start is past the end. `If-None-Match` does nothing for static files, because they have no ETag. The method is not checked: `OPTIONS` or `POST` of a path that names a static file returns that file with status 200.

If `public/index.html` exists, it replaces the generated homepage. The same is true of an earlier static directory's `index.html`. The footer's instruction is how an operator gets that replacement.

### Query string

On `GET /:name` for a **collection**, parameters are applied in this order:

1. `_embed`
2. filter (`_where`, otherwise the other parameters)
3. `_sort`
4. `_page` / `_per_page`

A singular resource ignores all of them and returns the object.

Reserved names that are **not** filters: `_sort`, `_page`, `_per_page`, `_embed`, `_where`. Every other parameter, including `_limit`, `_start`, `_expand`, and `_dependent`, is a filter on a collection GET. `_dependent` is special only on DELETE.

`+` in the query string is a space. Repeated keys are handled per parameter below.

#### Filters

A parameter `field=value` means `field` equals `value`. A parameter `field:operator=value` sets that operator. The operator is the substring after the **last** colon. An empty operator (`field:=value`) is treated as the whole key being a field name with equality. An unknown colon operator drops that parameter and keeps the rest.

A legacy form `field_operator=value` is also accepted when `operator` is entirely lowercase ASCII (`eq`, `lt`, `lte`, `gt`, `gte`, `ne`, `in`, `contains`). The split is at the last underscore. `startsWith` and `endsWith` contain uppercase letters, so only the colon form works for them; `title_startsWith=a` is an equality filter on a field whose name is the literal `title_startsWith`. `first_name_eq=Alice` is equality on `first_name`. Dots are nested paths: `author.name:eq=ada` and `author.first_name_ne=Bob`.

Operators:

| Operator | Match |
| --- | --- |
| `eq` (also the default) | Strict equality (`===`) |
| `ne` | Strict inequality (`!==`) |
| `lt`, `lte`, `gt`, `gte` | JavaScript `<`, `<=`, `>`, `>=` |
| `in` | Strict equality with any element of the list |
| `contains` | Field is a string and contains the needle, both lowercased with `toLowerCase` |
| `startsWith` | Field is a string and starts with the needle, both lowercased |
| `endsWith` | Field is a string and ends with the needle, both lowercased |

Value coercion for query parameters (not for `_where` JSON):

- `true` → boolean `true`, `false` → boolean `false`, `null` → `null`
- a whitespace-only string stays that string
- otherwise, if `Number(value)` is finite, the number is used (`100`, `0.5`, `1e2`, ` 100 `)
- otherwise the string is kept

So `published:eq=true` matches a boolean, and `views:gt=100` matches a number. A string id `"1"` does **not** match `id=1` or `postId=1`, because those values become the number `1`. The response is `200` and `[]`, not `404`. To compare a string that looks like a number, use `_where` with a JSON string.

`in` splits the value on commas, trims each piece, and coerces each piece. `id:in=1,3` is the numbers `[1, 3]`. `title:in=hello,world` is the strings `["hello", "world"]`. `title:in=a, b` is `["a", "b"]`.

Several parameters are AND. The same field may carry several operators (`views:gt=100&views:lt=300`). Repeating the same operator replaces the previous value; the last one wins. An unknown operator next to a known one is ignored (`views:foo=100&title:eq=a` keeps only the title test).

`_where` is a JSON object, percent-encoded. When it parses as a non-null object, it **replaces** the parameter filters entirely, including when it is `{}` (matches everything) or a JSON array. When it is invalid JSON, or JSON `null`, a number, or a string, it is ignored and the other parameters are used.

`_where` values are not coerced. `{"title":{"eq":"foo"}}` uses the string `foo`. `{"title":"foo"}` does not match, because a filter value that is not an object never matches.

Filter objects:

- Keys are AND, except the key `or`.
- `or` must be a non-empty array. Elements that are not objects are skipped. The item matches `or` if any remaining element matches. An empty array, a missing array, or an array of only non-objects rejects the item. `or` is itself ANDed with sibling keys. `or` may be nested.
- A value that is an object may contain operators. All known operators present must match (AND). Unknown keys inside that object are ignored. If the field is missing (`undefined`), any known operator rejects the item.
- If the object contains **no** known operator and the field is an object, the same rules run on the nested object (`author.name` via `{"author":{"name":{"eq":"bar"}}}`).
- If the object contains no known operator and the field is not an object (a number, string, array, or missing), that key is skipped and does **not** reject the item. `{"a":{"foo":10}}` matches a record whose `a` is `10`. `{"missing":{"foo":1}}` matches a record with no `missing` property.
- A non-object filter value (string, number, boolean, `null`, array) rejects the item immediately.
- `in` inside `_where` may be an array, or a single value which is treated as a one-element list. Membership is `===`.
- `contains`, `startsWith`, and `endsWith` require `typeof field === "string"`. The needle is `String(needle)`. Comparison is case-insensitive. An empty needle matches every string. A non-string field does not match. These operators do not use locale case folding, only `toLowerCase`.
- `lt` / `lte` / `gt` / `gte` / `eq` / `ne` use JavaScript's own conversions. `"100" > 20` is true; `null < 1` is true because `null` becomes `0`; `eq` does not coerce.

Embedding is applied before filtering, on a copy of each record. A singular embed can therefore be filtered (`GET /comments?_embed=post&post.title:eq=a`). A plural embed is an array. A nested object filter on that array does not look inside it; the key is skipped and the record stays. `GET /posts?_embed=comments&comments.text:eq=c` does not mean "posts that have such a comment".

Records that fail the filter are omitted. The order of survivors stays the current order until `_sort`.

#### Sort

`_sort` is a comma-separated list. The first key that differs wins. A key starting with `-` is descending on the rest of the name (`-views`, `-author.name`). Dots are nested paths. If `_sort` is omitted, the collection order is unchanged (file order, then newly created records at the end, with deletions spliced out).

Comparison:

- Equal values are ties. The sort is stable.
- Strings use `localeCompare` with the process default locale and no options.
- Numbers and other ordered values use `<` / `>`.
- `0` is a real value. `null`, `undefined`, `false`, and `""` are empty. Empty values sort **after** non-empty values when ascending and **before** them when descending.

The first `_sort` parameter wins if the key is repeated. `_sort` without `_page` returns a JSON array, not a pagination object.

#### Pagination

Pagination is used only when `_page` is present and `parseInt` of it is not `NaN`. `_per_page` by itself does nothing. `parseInt` rules are the same as for the port: `_page=1.9` is page 1, `_page=10items` is page 10, `_page=abc` and `_page=` disable pagination and return a plain array.

When pagination is on and `_per_page` is omitted or not a finite integer parse, the page size is **10**. A parsed size that is `0` or negative becomes **1**. The page size actually used is the integer part of a positive size.

Let `n` be the number of records after filter and sort, and `s` the page size. `pages = max(1, ceil(n / s))`. The requested page is clamped into `1 … pages` (so `0`, negatives, and pages past the end are clamped). The body is:

```json
{
  "first": 1,
  "prev": null,
  "next": 2,
  "last": 1,
  "pages": 1,
  "items": 0,
  "data": []
}
```

- `first` is always `1`.
- `prev` is `null` on page 1, otherwise the previous page number.
- `next` is `null` on the last page, otherwise the next page number.
- `last` equals `pages`.
- `items` is `n`, the full filtered count, not the page length.
- `data` is the slice for that page, in sorted order.

An empty collection still returns `pages: 1`, `items: 0`, `data: []`, `prev: null`, `next: null`.

`_page=1&_per_page=2` on five items returns `data` of the first two, `pages: 3`, `next: 2`, `prev: null`. Page `2` returns items 3 and 4, `prev: 1`, `next: 3`. Page `9` is clamped to the last page and returns the final item, `prev: 2`, `next: null`.

#### Embed

`_embed` may be repeated. One parameter is one name. A comma inside one parameter is part of the name, not a list. Each name is applied in order, on copies, for both `GET /:name` and `GET /:name/:id`.

English singular/plural is the default behavior of the Inflection library (version 3): regular `-s` plurals, and its irregular and uncountable lists (`person`/`people`, `mouse`/`mice`, `child`/`children`, uncountables unchanged, and so on). The tested mapping is `posts` ↔ `post`, `comments` ↔ `comment`.

Let the embed argument be `R` and the parent resource be `P`.

- If `R` is singular (`singular(R) === R`), this is a to-one embed. The related collection is `plural(R)`. The attached value is the first related record whose `id` is strictly equal to the parent property `R + "Id"`, or `undefined` if none (the property is then omitted from JSON). If `plural(R)` is not a collection, the parent is unchanged.
- If `R` is plural, this is a to-many embed. The related collection is `R` itself. The attached value is the array of related records whose property `singular(P) + "Id"` is strictly equal to the parent `id`. The array may be empty and is still present. If `R` is not a collection, the parent is unchanged.

Examples: `GET /posts?_embed=comments` adds `comments` to each post: the comments whose `postId` equals that post's `id`. `GET /comments/1?_embed=post` adds `post`: the post whose `id` equals the comment's `postId`. `GET /posts?_embed=author` looks for a collection `authors`; if it does not exist, no `author` property is added.

Embedded values are not written back to the file.

### Create, replace, update, delete

**Create** `POST /:name` with a JSON object. The record stored and returned is a shallow copy of the body with `id` set to a new id. A body `id` is overwritten. The record is appended. Status **201**. The body is the stored record. `POST` of an unknown name, a singular resource, or an item URL is 404. `POST` with no body creates `{"id":"<new>"}`.

**Replace a record** `PUT /:name/:id`. The stored record becomes a shallow copy of the body with `id` forced to the URL id. Fields that were on the old record and are absent from the body are dropped. Status 200 and the stored record. Unknown name or id: 404, and nothing is written.

**Replace a singular resource** `PUT /:name`. The resource becomes the body object itself (no injected `id`). Status 200 and that object. `PUT` on a collection URL is 404.

**Update a record** `PATCH /:name/:id`. Shallow merge: start from the old record, overlay body properties, force `id` to the URL id. Missing body fields are kept. Nested objects are replaced, not merged. Status 200. Unknown name or id: 404.

**Update a singular resource** `PATCH /:name`. Shallow merge of the body onto the existing object. Status 200. `PATCH` on a collection URL is 404.

**Delete** `DELETE /:name/:id`. The first record with that id is removed and returned with status 200. Then, on every **other** collection, each record whose property `singular(name) + "Id"` is strictly equal to the deleted id has that property set to `null`. Singular resources are not walked. Then, if the query contains `_dependent`, each listed collection (exact key, not a pluralized guess) drops every record whose that foreign key is `null`, including records that were already `null` before this delete. One `_dependent` parameter is one name. Repeat the parameter for several collections. `comments,tags` as a single value looks for a collection literally named `comments,tags`.

Deleting `posts` id `"1"` with a comment `{ "id": "1", "postId": "1" }` leaves that comment in place with `postId: null` when `_dependent` is absent. `DELETE /posts/1?_dependent=comments` removes that comment. A comment whose `postId` is the number `1` is not nullified and not removed.

Unknown name, unknown id, `DELETE` of a collection URL, and `DELETE` of a singular resource are 404 and do not write.

## Behaviour claims

D-1. tinyrest requires Node.js 22.12.0 or newer. Evidence: `package.json:72-74`.

D-2. With no positional argument, or with `--help`, the process writes the usage text to stdout and exits 0. The usage line names the executable tinyrest, and the options are `-p/--port` default 3000, `-h/--host` default localhost, repeatable `-s/--static`, `--help`, and `--version`. Evidence: `src/bin.ts:21-30`, `src/bin.ts:92-95`.

D-3. `--version` prints the package version (`1.0.0-beta.15` in this release) and exits 0, and it does so before help, watch, or the file check. Evidence: `src/bin.ts:74-81`, `package.json:3`.

D-4. An unknown option writes the parser message up to the first period, then the help text, to stdout, and exits 1. `--nope` produces the line `Unknown option '--nope'`. Evidence: `src/bin.ts:104-108`.

D-5. A missing option value such as a bare `--port` is not caught by the unknown-option path and fails the process with `ERR_PARSE_ARGS_INVALID_OPTION_VALUE`. Evidence: `src/bin.ts:104-111`.

D-6. A file that does not exist prints `File <path> not found` and exits 1 without creating it. Evidence: `src/bin.ts:117-119`.

D-7. A file whose trimmed contents are empty is replaced with `{}` before it is parsed. Evidence: `src/bin.ts:122-125`.

D-8. `--watch` or `-w` prints `--watch/-w can be omitted, JSON Server 1+ watches for file changes by default` and then continues the normal startup. Evidence: `src/bin.ts:83-90`.

D-9. The port defaults to `process.env.PORT` when that variable is set, otherwise `3000`, and `-p` / `--port` overrides it. The host defaults to `process.env.HOST` when set, otherwise `localhost`, and `-h` / `--host` overrides it. Evidence: `src/bin.ts:43-52`.

D-10. The process listens with the port only. `--host` is not passed to listen. Endpoint lines use `http://${host}:${port}/${key}`. The Index line is always `http://localhost:${port}/`. Evidence: `src/bin.ts:145-156`, `src/bin.ts:165-176`.

D-11. After a successful listen the banner text is `JSON Server started on PORT :${port}`, `Press CTRL-C to stop`, `Watching ${file}...`, one of the four kaomoji, an `Index:` line, a `Static files:` line reading `Serving ./public directory if it exists`, and an `Endpoints:` block. An empty document prints `No endpoints found, try adding some data to ${file}`. Evidence: `src/bin.ts:145-183`.

D-12. The kaomoji is chosen from `♡⸜(˶˃ ᵕ ˂˶)⸝♡`, `♡( ◡‿◡ )`, `( ˶ˆ ᗜ ˆ˵ )`, and `(˶ᵔ ᵕ ᵔ˶)`. Evidence: `src/bin.ts:158-163`.

D-13. Only the first positional path is the database. `-s` may be given more than once. Evidence: `src/bin.ts:53-58`, `src/bin.ts:98-102`.

D-14. A `.json5` file is parsed and written as JSON5. Any other extension is parsed as JSON and written with two-space `JSON.stringify`. Evidence: `src/bin.ts:129-136`, `node_modules/lowdb/lib/adapters/node/JSONFile.js:3-7`.

D-15. When `NODE_ENV` is `production` the watcher is not installed, but the banner still contains `Watching ${file}...`. Otherwise a watcher is installed on that file. Evidence: `src/bin.ts:168-172`, `src/bin.ts:185-223`.

D-16. A `change` event re-reads the file unless a write from this process is in progress. A change of the sorted top-level keys, or the first successful read after a parse error, reprints the endpoints block after a blank line. A `SyntaxError` prints `Error parsing ${file}` and the parser message and keeps the previous document. Evidence: `src/bin.ts:186-222`.

D-17. The initial read has no parse-error handler. Invalid syntax at startup fails the process. Evidence: `src/bin.ts:139-140`.

D-18. On read, `$schema` is deleted and is not a resource. On every write, `$schema` is set to the concatenation of `./node_modules/json` and `-server/schema.json`. Evidence: `src/adapters/normalized-adapter.ts:6`, `src/adapters/normalized-adapter.ts:25`, `src/adapters/normalized-adapter.ts:44-45`. Test: `write always overwrites $schema`. Test: `read removes $schema and normalizes ids`.

D-19. A numeric record `id` becomes its decimal string on read. A missing `id` becomes a non-empty string. A singular object is not given an `id`. Evidence: `src/adapters/normalized-adapter.ts:27-39`. Test: `read removes $schema and normalizes ids`.

D-20. New ids are 8 random bytes in unpadded base64url. Evidence: `src/random-id.ts:1-5`.

D-21. `POST` stores a shallow copy of the body and overwrites any client `id` with a generated string id, appends it, and returns that record. An unknown collection returns no record. Evidence: `src/service.ts:145-153`. Test: `create`.

D-22. `POST /:name` of a collection answers 201. `POST` of an item URL, a singular resource, or an unknown name answers 404 with `{"error":"Not Found"}`. Evidence: `src/app.ts:143`, `src/app.ts:159-166`. Test: `POST /posts`. Test: `POST /posts/1`. Test: `POST /object`. Test: `POST /not-found`.

D-23. `PUT` on a singular resource replaces it with the body and returns that body. `PUT` on a collection URL or an unknown name returns no value. Evidence: `src/service.ts:156-163`, `src/service.ts:186-188`. Test: `update`.

D-24. `PUT /:name/:id` replaces the record, forces `id` to the URL id, and drops fields that are not in the body. An unknown name or id returns no record. Evidence: `src/service.ts:166-184`, `src/service.ts:194-196`. Test: `updateById`.

D-25. `PUT /:name/:id` of an existing record answers 200. `PUT` of a singular resource answers 200. `PUT` of a collection URL, a missing id, a singular item URL, or an unknown name answers 404 with `{"error":"Not Found"}`. Evidence: `src/app.ts:145-147`, `src/app.ts:159-166`. Test: `PUT /posts/1`. Test: `PUT /object`. Test: `PUT /posts`. Test: `PUT /posts/-1`. Test: `PUT /object/1`. Test: `PUT /not-found`.

D-26. `PATCH` on a singular resource shallow-merges the body onto the existing object. `PATCH` on a collection or an unknown name returns no value. Evidence: `src/service.ts:156-163`, `src/service.ts:190-192`. Test: `patch`.

D-27. `PATCH /:name/:id` shallow-merges, keeps fields omitted from the body, and forces `id` to the URL id. An unknown name or id returns no record. Evidence: `src/service.ts:166-184`, `src/service.ts:198-200`. Test: `patchById`.

D-28. `PATCH /:name/:id` of an existing record answers 200. `PATCH` of a singular resource answers 200. `PATCH` of a collection URL, a missing id, a singular item URL, or an unknown name answers 404 with `{"error":"Not Found"}`. Evidence: `src/app.ts:149-151`, `src/app.ts:159-166`. Test: `PATCH /posts/1`. Test: `PATCH /object`. Test: `PATCH /posts`. Test: `PATCH /posts/-1`. Test: `PATCH /object/1`. Test: `PATCH /not-found`.

D-29. `DELETE /:name/:id` removes the first matching record and returns it. An unknown name or id returns no record. Evidence: `src/service.ts:202-220`. Test: `ignores unknown resources`.

D-30. After that delete, every other collection has `singular(name) + "Id"` set to `null` where it was strictly equal to the deleted id. Evidence: `src/service.ts:49-64`, `src/service.ts:215`. Test: `nullifies foreign keys`.

D-31. `_dependent` names collections that then drop records whose that foreign key is `null`. Evidence: `src/service.ts:67-78`, `src/service.ts:216-217`, `src/app.ts:153-156`. Test: `deletes dependent resources`.

D-32. `DELETE /:name/:id` of an existing record answers 200. `DELETE` of a collection URL, a singular resource, a singular item URL, a missing id, or an unknown name answers 404 with `{"error":"Not Found"}`. Evidence: `src/app.ts:153-166`. Test: `DELETE /posts/1`. Test: `DELETE /posts`. Test: `DELETE /object`. Test: `DELETE /object/1`. Test: `DELETE /posts/-1`. Test: `DELETE /not-found`.

D-33. `GET /:name` of a collection answers 200 with the records. `GET /:name/:id` of an existing id answers 200. A missing id, a singular item URL, and an unknown name answer 404 with `{"error":"Not Found"}`. `GET` of a singular resource answers 200. Evidence: `src/app.ts:123-141`, `src/app.ts:159-166`, `src/service.ts:110-124`. Test: `GET /posts`. Test: `GET /posts/1`. Test: `GET /posts/-1`. Test: `GET /object`. Test: `GET /object/1`. Test: `GET /not-found`.

D-34. `GET /:name/:id` returns the first record whose `id` is strictly equal to the URL segment, with embeds applied, and returns nothing for an unknown id or unknown collection. Evidence: `src/service.ts:96-108`. Test: `findById`.

D-35. `OPTIONS` of a resource URL answers 204. Evidence: `src/app.ts:108-116`, `node_modules/@tinyhttp/cors/dist/index.js:61-88`. Test: `OPTIONS /posts`.

D-36. CORS on non-file responses sets `Access-Control-Allow-Origin: *`, methods `GET, HEAD, PUT, PATCH, POST, DELETE`, and `Access-Control-Allow-Headers` from `Access-Control-Request-Headers` split on commas and trimmed, or `content-type` when that request header is absent. An `OPTIONS` request ends with status 204 and `Content-Length: 0`. Evidence: `src/app.ts:108-116`, `node_modules/@tinyhttp/cors/dist/index.js:61-88`.

D-37. Every response sets `X-Powered-By: tinyhttp`. Evidence: `node_modules/@tinyhttp/app/dist/app.js:237-240`.

D-38. JSON bodies use `Content-Type: application/json` and two-space stringify. Evidence: `node_modules/@tinyhttp/send/dist/json.js:5-8`.

D-39. A POST, PUT, or PATCH body that is an array, a string, or `null` answers 400 with `{"error":"Body must be a JSON object"}`. Evidence: `src/app.ts:68-76`, `src/app.ts:80-90`. Test: `POST /posts with array body returns 400`. Test: `PATCH /posts/1 with string body returns 400`. Test: `PUT /posts/1 with null body returns 400`.

D-40. An empty POST, PUT, PATCH, or DELETE body is parsed as `{}`. JSON is parsed for those methods with no content-type check. A body bigger than 102400 bytes fails. Evidence: `src/app.ts:119`, `node_modules/milliparsec/dist/index.js:4`, `node_modules/milliparsec/dist/index.js:72-78`, `node_modules/milliparsec/dist/utils.js:1-3`.

D-41. Outside production, a failed JSON body answers 500 as `text/plain; charset=utf-8` with `X-Content-Type-Options: nosniff` and an HTML-escaped message. In production the body is `Internal Server Error`. The error is written to stderr in both cases. Evidence: `node_modules/@tinyhttp/app/dist/onError.js:4-40`.

D-42. `GET /` answers 200 when no static index file is served. Evidence: `src/app.ts:102-105`, `src/app.ts:121`. Test: `GET /`.

D-43. A file in `./public` is served with 200, and a file in a `--static` directory is served with 200. Evidence: `src/app.ts:102-105`. Test: `GET /test.html`. Test: `GET /file.html`.

D-44. The generated homepage title is `JSON Server`. It lists each resource in key order as a link to `/{name}`, with `{n} items` for arrays and `object` otherwise, the intro `Available REST resources from db.json.`, the empty sentence `No resources in db.json.`, and the footer `To replace this page, create public/index.html.` Evidence: `views/index.html:6`, `views/index.html:121`, `views/index.html:128`, `views/index.html:134`, `views/index.html:141`, `src/app.ts:121`.

D-45. In non-production, a static hit sends `Cache-Control: no-store`, `Last-Modified`, `Content-Length`, and a mime type, and HTML is `text/html;charset=utf-8`. It does not add the CORS headers. Evidence: `src/app.ts:102-105`, `node_modules/sirv/build.js:38-52`, `node_modules/sirv/build.js:103-118`, `node_modules/sirv/build.js:169-183`.

D-46. Static lookup tries the path, `{path}/index`, and those plus `.html` and `.htm`. `/` therefore serves `public/index.html` when that file exists, instead of the generated page. Evidence: `node_modules/sirv/build.js:15-28`, `views/index.html:141`.

D-47. `GET /posts?_where={"title":{"eq":"foo"}}` returns 200 and the records that match that object, and a valid `_where` object replaces ordinary parameters such as `title:eq=bar`. Evidence: `src/app.ts:42-52`. Test: `GET /posts?_where=... uses JSON query`. Test: `GET /posts?_where=... overrides query params`.

D-48. Invalid `_where` JSON is ignored and the other parameters are kept. A parsed non-null object, including a JSON array, replaces them. Evidence: `src/app.ts:42-52`.

D-49. Reserved query keys `_sort`, `_page`, `_per_page`, `_embed`, and `_where` are not field filters. Other keys are. Evidence: `src/app.ts:28-40`.

D-50. `field=value` and `field:eq=value` mean equality. `field:gt`, `field:lt`, `field:gte`, `field:lte`, and `field:ne` set those operators. Dotted paths build nested objects. Two operators on one field are kept together. `true`, `false`, `null`, and finite numbers are coerced; other tokens stay strings. Evidence: `src/parse-where.ts:6-69`. Test: `views:gt=100&title:eq=a`. Test: `title=hello`. Test: `author.name:lt=c&author.id:ne=2`. Test: `views:gt=100&views:lt=300`. Test: `views:gt=100&published:eq=true&ratio:lt=0.5&deleted:eq=null`.

D-51. An unknown colon operator is dropped. A lowercase `_operator` suffix is accepted for real operators, including on names that already contain underscores, and it combines with a colon operator on the same field. A bare `first_name=Alice` is equality. Evidence: `src/parse-where.ts:6-28`. Test: `views:foo=100&title:eq=a`. Test: `views:foo=100`. Test: `views_gt=100&title_eq=a`. Test: `first_name_eq=Alice&author.first_name_ne=Bob`. Test: `first_name=Alice`. Test: `views_gt=100&views:lt=300`.

D-52. `in` splits on commas and coerces each piece. `contains`, `startsWith`, and `endsWith` are stored under those names. Evidence: `src/parse-where.ts:31-42`. Test: `id:in=1,3`. Test: `title_in=hello,world`. Test: `title:contains=ello`. Test: `title:startsWith=hel`. Test: `title:endsWith=rld`.

D-53. The operator set is `lt`, `lte`, `gt`, `gte`, `eq`, `ne`, `in`, `contains`, `startsWith`, `endsWith`. Evidence: `src/where-operators.ts:1-12`.

D-54. Equality, inequality, and the four inequalities match as strict or relational JavaScript comparisons, and several operators on one record are AND. Evidence: `src/matches-where.ts:46-55`. Test: `{"a":{"eq":10}}`. Test: `{"a":{"eq":11}}`. Test: `{"c":{"ne":"y"}}`. Test: `{"c":{"ne":"x"}}`. Test: `{"a":{"lt":11}}`. Test: `{"a":{"lt":10}}`. Test: `{"a":{"lte":10}}`. Test: `{"a":{"lte":9}}`. Test: `{"b":{"gt":19}}`. Test: `{"b":{"gt":20}}`. Test: `{"b":{"gte":20}}`. Test: `{"b":{"gte":21}}`. Test: `{"a":{"gt":0},"b":{"lt":30}}`. Test: `{"a":{"gt":10},"b":{"lt":30}}`.

D-55. `or` matches when any object element matches, and fails for an empty list or when every element fails. Evidence: `src/matches-where.ts:26-38`. Test: `{"or":[{"a":{"lt":0}},{"b":{"gt":19}}]}`. Test: `{"or":[{"a":{"lt":0}},{"b":{"gt":20}}]}`.

D-56. A nested object with no operator at the outer level is matched recursively. Evidence: `src/matches-where.ts:74-79`. Test: `{"nested":{"a":{"eq":10}}}`. Test: `{"nested":{"b":{"lt":20}}}`. Test: `{"where":{"author":{"name":{"eq":"bar"}}}}` under `find`.

D-57. `in` matches when the field is strictly equal to any listed element, and it is ANDed with other operators on that field. A non-array `in` value is one element. Evidence: `src/matches-where.ts:56-59`. Test: `{"a":{"in":[10,11]}}`. Test: `{"a":{"in":[1,2]}}`. Test: `{"c":{"in":["x","y"]}}`. Test: `{"c":{"in":["y","z"]}}`. Test: `{"a":{"in":[10,11],"gt":9}}`. Test: `{"a":{"in":[10,11],"gt":10}}`.

D-58. An object of only unknown operator names does not reject the record, even when the field is missing. Unknown names beside a real operator are ignored. Evidence: `src/matches-where.ts:43-79`. Test: `{"a":{"foo":10}}`. Test: `{"a":{"foo":10,"eq":10}}`. Test: `{"missing":{"foo":1}}`.

D-59. `contains`, `startsWith`, and `endsWith` are case-insensitive on strings and reject non-strings, including when the needle is a number. Evidence: `src/matches-where.ts:60-71`. Test: `{"c":{"contains":"x"}}`. Test: `{"c":{"contains":"X"}}`. Test: `{"c":{"contains":"z"}}`. Test: `{"a":{"contains":"1"}}`. Test: `{"c":{"contains":1}}`. Test: `{"c":{"startsWith":"x"}}`. Test: `{"c":{"startsWith":"X"}}`. Test: `{"c":{"startsWith":"z"}}`. Test: `{"a":{"startsWith":"1"}}`. Test: `{"c":{"startsWith":1}}`. Test: `{"c":{"endsWith":"x"}}`. Test: `{"c":{"endsWith":"X"}}`. Test: `{"c":{"endsWith":"z"}}`. Test: `{"a":{"endsWith":"1"}}`. Test: `{"c":{"endsWith":1}}`.

D-60. A filter value that is not an object and is not `or` rejects the record. A known operator on a missing field rejects the record. Evidence: `src/matches-where.ts:47-48`, `src/matches-where.ts:82-84`.

D-61. Collection find filters with the where object, then sorts if `sort` is set. `_sort=-views` orders by `views` descending. Evidence: `src/service.ts:126-136`. Test: `{"where":{"title":{"eq":"b"}}}`. Test: `{"where":{},"sort":"-views"}`.

D-62. Sort keys are comma-separated. A leading `-` is descending. Nested paths use dot access. String ties use default-locale `localeCompare`. Empty values other than `0` sort last when ascending and first when descending. Evidence: `src/service.ts:134-136`, `node_modules/sort-on/index.js:19-60`.

D-63. When `page` is set, the result is a pagination object and the page size defaults to 10. Page 2 with size 2 of three records returns `first: 1`, `prev: 1`, `next: null`, `last: 2`, `pages: 2`, `items: 3`, and the third record. Evidence: `src/service.ts:138-140`. Test: `{"where":{},"page":2,"perPage":2}`.

D-64. Pagination clamps the page into `1 … pages`, uses page size 1 when the requested size is 0 or negative, and an empty list yields `pages: 1`, `items: 0`, `data: []`, `prev: null`, `next: null`. Five items, page 1, size 2 yields data `[first, second]`, `pages: 3`, `next: 2`. Page 2 yields the next two, `prev: 1`, `next: 3`. Page 9 yields the last item, `prev: 2`, `next: null`. Page 0 yields the first page. Evidence: `src/paginate.ts:11-37`. Test: `page=1 perPage=2 items=5 -> [1,2]`. Test: `page=2 perPage=2 items=5 -> [3,4]`. Test: `page=9 perPage=2 items=5 -> clamp to last`. Test: `page=0 perPage=2 items=3 -> clamp to first`. Test: `items=[] page=1 perPage=2 -> stable empty pagination`. Test: `perPage=0 -> clamp perPage to 1`.

D-65. `_page` and `_per_page` come from `parseInt`. A `NaN` page disables pagination. A `NaN` page size falls through to the default 10. A present numeric page paginates even when the page size parameter is absent. Evidence: `src/app.ts:54-63`, `src/service.ts:138-140`.

D-66. `_embed=comments` on a post collection attaches the comments whose `postId` equals the post id. `_embed=post` on a comment attaches the post whose `id` equals the comment's `postId`. Evidence: `src/service.ts:23-47`, `src/service.ts:96-104`, `src/service.ts:129-131`. Test: `findById`. Test: `GET /posts?_embed=comments`. Test: `GET /posts/1?_embed=comments`.

D-67. Embedding a name whose collection does not exist leaves the record unchanged. A plural embed that matches nothing is an empty array. Evidence: `src/service.ts:26-27`, `src/service.ts:37-38`, `src/service.ts:42-46`.

D-68. A non-array resource is returned as-is from find, with no filter, sort, page, or embed. Evidence: `src/service.ts:120-124`.

D-69. Query `postId=1` on a collection whose `postId` values are strings is equality against the number `1`, so strict equality fails and the JSON array is empty while the status stays 200. Evidence: `src/parse-where.ts:44-56`, `src/matches-where.ts:54`, `src/app.ts:159-166`. Test: `GET /comments?postId=1`.

D-70. Writes are the full document. JSON writes are two-space indented and include the normalized ids. The writer writes `.{basename}.tmp` in the same directory and renames it onto the database file. Evidence: `node_modules/lowdb/lib/adapters/node/JSONFile.js:5-6`, `node_modules/steno/lib/index.js:6-8`, `node_modules/steno/lib/index.js:51-55`, `src/service.ts:152`.

D-71. A singular embed looks up `plural(related)` and matches `item[related + "Id"]` to the related `id`. A plural embed looks up that collection and matches `related[singular(parent) + "Id"]` to the parent `id`. Evidence: `src/service.ts:23-46`.

D-72. `GET /:name` reads `_embed` from the parsed query object, so a repeated `_embed` is a list of names and a single `_embed` is one name. Evidence: `src/app.ts:64`, `src/service.ts:19-21`, `src/service.ts:129-131`.

D-73. The generated homepage is sent with a weak ETag of the body. A conditional GET whose `If-None-Match` matches, and which is not `Cache-Control: no-cache`, returns 304 and an empty body. Evidence: `src/app.ts:121`, `node_modules/@tinyhttp/send/dist/send.js:34-48`, `node_modules/@tinyhttp/send/dist/utils.js:4-6`, `node_modules/@tinyhttp/etag/dist/index.js:3-18`, `node_modules/@tinyhttp/req/dist/fresh.js:29-49`.

D-74. Static `Range` requests answer 206 with `Content-Range`, or 416 when the start is past the end. Evidence: `node_modules/sirv/build.js:73-91`.

D-75. In production, static files are the startup snapshot of each directory, dotfiles are skipped except `.well-known`, and they have no `Cache-Control` and no ETag. Evidence: `src/app.ts:16`, `src/app.ts:102-105`, `node_modules/sirv/build.js:131-134`, `node_modules/sirv/build.js:155-167`.

D-76. A top-level JSON `null` read becomes an empty in-memory document because a null adapter result is ignored. Evidence: `src/adapters/normalized-adapter.ts:21-23`, `node_modules/lowdb/lib/core/Low.js:15-18`.

D-77. `GET` with `_embed` does not by itself write the database. Evidence: `src/service.ts:110-143`.

D-78. Foreign-key nullify and dependent deletion use strict equality on `singular(collection) + "Id"` and do not coerce numbers. A dependent list is the `_dependent` query value, either one string or an array of strings when the parameter is repeated. Evidence: `src/service.ts:19-21`, `src/service.ts:49-78`, `src/app.ts:155`.

D-79. Collection `find` with an equality filter returns only the matching records, in their existing order when no sort is given. Evidence: `src/service.ts:126-141`. Test: `{"where":{"title":{"eq":"b"}}}`.

D-80. The homepage response, when generated, is HTML (`text/html` with a utf-8 charset) rather than JSON. Evidence: `src/app.ts:121`, `node_modules/@tinyhttp/send/dist/send.js:23-30`.

## Relationships

- **Node.js 22.12+** runs the process and provides HTTP, files, `parseArgs`, and `crypto.randomBytes`.
- **HTTP stack**: an application framework that contributes the `X-Powered-By: tinyhttp` header, route matching (one optional trailing slash, case-sensitive captures), and the 500 handler.
- **CORS middleware**: the allow-origin, allow-methods, and allow-headers rules, and the 204 preflight.
- **JSON body parser**: empty object, 102400-byte limit, no content-type gate.
- **Static file server**: `public` and `-s` directories, index fallback, range requests, dev `no-store`.
- **HTML templates**: the homepage is rendered from `views/index.html` with the in-memory document.
- **Document store**: one JSON or JSON5 file, whole-document reads and writes, atomic rename via a sibling temp file.
- **JSON5**: parse and compact stringify for `.json5` files.
- **English inflection**: singular and plural forms for embed and foreign-key names.
- **Nested paths**: dot paths in filters and sort keys.
- **Sort**: multi-key sort with `-` for descending.
- **File watch**: change notifications on the database path outside production.
- **Terminal color**: optional ANSI styling of the banner and errors.

Clients are anything that speaks HTTP: browsers (the homepage and static files), `curl`, and application code. There is no separate admin protocol. Editors may follow the written `$schema` path to `schema.json`; the server will not.

The process reads and writes only the database file (and its temporary sibling), and it reads static files under `./public` and the `-s` directories. It does not phone home.

## Unknowns

- **U-1.** Filesystem events other than `change` (for example a rename onto the database path) are not handled. Default: do not reload until a `change` event is delivered for that path.
- **U-2.** String sort order uses the process default locale. Default: call `localeCompare` with no locale and no options.
- **U-3.** A top-level JSON value other than an object or `null` is not a supported database. `null` becomes `{}`. Default: fail startup for any other non-object.
- **U-4.** Whether the 400 from `HEAD` includes the JSON bytes on the wire or only the status and `Content-Type`. Default: clients must honor the status and must not require a HEAD body.
- **U-5.** Which address is bound when IPv6 is disabled. Default: Node's hostless `listen(port)` (the IPv4 unspecified address when IPv6 is unavailable).

## Left free

- Source layout, types, and which libraries implement HTTP, files, JSON5, inflection, sorting, and watching, as long as the observable results match, including `X-Powered-By: tinyhttp`.
- The random-byte source, as long as new ids are 11-character unpadded base64url from 8 random bytes and are not taken from the client.
- Homepage CSS, spacing, and the upstream anchor targets. The required visible strings are those in the homepage section.
- In-memory locking, as long as each successful write response matches the mutation it applied and the file ends as the full document from the last completed write.
- Whether production caches the homepage template source. The HTML must still show the current resources.
