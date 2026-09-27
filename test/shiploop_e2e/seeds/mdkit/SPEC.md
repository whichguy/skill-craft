# mdkit specification

## 1. Purpose

mdkit is a Markdown compiler. It turns a Markdown string into an HTML string, or into a list of tokens, from a JavaScript call or from a command-line program. It implements the CommonMark 0.31.2 block and inline structure, and, when GitHub Flavored Markdown is enabled, the GFM 0.29 tables, task lists, strikethrough, and autolink extensions. It does not sanitize HTML. It does not fetch URLs, read a configuration directory on its own behalf except as the command-line program describes below, or listen on a network port.

The product name in every user-visible string, path, global, package, and command is **mdkit**. This document uses that name even where a source checkout uses a different spelling.

## 2. Runtime and launch contract

### 2.1 Runtime

- The command-line program and the library run on Node.js **20 or newer** (`package.json` `engines.node`).
- The library is an ECMAScript module. A CommonJS `require` of the ESM entry, on that Node, yields the named exports in section 3.2.
- A browser build is a UMD script. Loaded as a classic script, it defines a global `mdkit` with the same callable surface as the ESM entry.
- There is no startup banner. The process prints only what sections 2.3 and 3.1 describe.
- This release’s `--version` text is `18.0.14`.

### 2.2 Install and start

Install the package so that the executable named `mdkit` is on `PATH`. That executable is a Node script whose body sets the process title to `mdkit` and then calls the CLI main function with the real `process` object.

Equivalent direct launch: `node <package>/bin/mdkit.js [arguments…]`.

The CLI reads `process.argv` from index 2 onward. It does not read environment variables of its own. It does pass `process.env` and `process.cwd()` through to the `man` child used by `--help`.

A per-user config, when present, is loaded from the first existing file among:

1. `~/.mdkit.json`
2. `~/.mdkit.js`
3. `~/.mdkit/index.js`

`~` is only expanded at the start of a path, and it expands to the Node home directory. A `-c` / `--config` path disables this search.

### 2.3 What the CLI prints and how it exits

Success always ends with status **0**. Failure ends with status **1**.

| Situation | stdout | stderr | status |
|---|---|---|---|
| HTML result, no `-o` | the HTML, then one extra `\n` | empty | 0 |
| `--tokens`, no `-o` | `JSON.stringify(tokens, null, 2)` plus one extra `\n` | empty | 0 |
| `-o` file written | empty | empty | 0 |
| `-v` / `--version` | `18.0.14\n` | empty | 0 |
| `-h` / `--help` | whatever `man` writes (stdio is inherited) | whatever `man` writes | 0 |
| `--help` when `man` cannot be spawned | the shipped manual Markdown, then the newline `console.log` adds | empty | 0 |
| missing input file (`ENOENT`) | empty | `mdkit: ` + absolute path + `: No such file or directory` (no trailing newline) | 1 |
| `--config` path that does not exist | empty | `Cannot load config file '` + the path as given + `'` | 1 |
| `-n` and the output path already exists | empty | `mdkit: output file '` + path + `' already exists, disable the '-n' / '--no-clobber' flag to overwrite\n` | 1 |
| any other thrown error | empty | `error.message` only | 1 |

Empty input (empty stdin, or a successful read of an empty file, with no `--string`) compiles to an empty HTML string. On stdout that is a single `\n`.

`--help` does not read stdin and does not compile Markdown. It spawns `man` with one argument, the package manual page path, `cwd` and `env` copied from the parent, and `stdio: 'inherit'`. A `SIGINT` delivered to the parent is forwarded to that child as `SIGINT`. The fallback Markdown is printed only on the child’s `error` event (the `man` binary cannot be started), not when `man` runs and reports a missing page. In a tree where the formatted manual has not been generated, `man` itself writes a “No manual entry” line to stderr and the CLI still exits 0 with empty stdout.

The fallback manual text, with product branding, is the Markdown in section 3.1.7.

## 3. Public interface

### 3.1 Command-line program

#### 3.1.1 Arguments

Arguments are consumed left to right. A `--name=value` argument is split on the first `=`; the value, with any later `=` characters kept, is pushed back as the next argument. A short cluster of length greater than 2 (`-abc`) is rewritten to `-a -b -c` before the first flag is handled. A single-dash argument of length 2 (`-s`) is one flag. Anything that is not a flag below and does not start with `--` is a positional input path.

Flags:

| Flag | Meaning |
|---|---|
| `-o`, `--output` FILE | Write the result to FILE. The HTML or token JSON is written as the compiler produced it, **without** the extra stdout newline. |
| `-i`, `--input` FILE | Read that file as UTF-8. |
| `-s`, `--string` TEXT | Compile TEXT. |
| `-c`, `--config` FILE | Load FILE instead of the home-directory search. |
| `-t`, `--tokens` | Emit tokens instead of HTML. |
| `-n`, `--no-clobber` | If FILE from `-o` already exists, fail as in the table above. This flag is not the generic `--no-` option form. |
| `-h`, `--help` | Show the manual and return. |
| `-v`, `--version` | Print `18.0.14` and return. |
| `--<option>` | See 3.1.2. |
| `--no-<option>` | See 3.1.2. |

Input source, first match wins:

1. `--string`, if the string is non-empty (an empty string is treated as absent).
2. `--input`.
3. The **last** positional path. Earlier positional paths are ignored, even if they do not exist.
4. Otherwise stdin, read as UTF-8 until end. A stdin error rejects and the CLI exits 1 with that error’s message.

#### 3.1.2 Compiler options on the command line

After the specific flags above, a long option whose camel-cased name is a key of the built-in defaults is applied to the **per-call** option object. Camel-case conversion turns each `-<letter>` between word characters into that letter upper-cased (`--walk-tokens` → `walkTokens`). Names that are not default keys are skipped and do not consume a following argument.

Built-in default keys and their types: `async` boolean, `breaks` boolean, `extensions` null, `gfm` boolean, `hooks` null, `pedantic` boolean, `renderer` null, `silent` boolean, `tokenizer` null, `walkTokens` null.

- For a boolean key, `--name` sets `true` and does **not** consume a `=value` that was pushed back. `--gfm=false` therefore sets `gfm` to `true` and leaves the argument `false` to be parsed next (usually as a filename).
- `--no-name` on a boolean key sets `false`.
- For a non-boolean key, `--name` sets the option to the next argument as a **string**. `--no-name` sets it to `null`.

Those per-call options override the same keys loaded from a config file.

#### 3.1.3 Config files

The file must exist or the CLI throws `Cannot load config file '<path>'`. A path may contain `#`; it is a filename, not a URL fragment.

Loading: try CommonJS `require` of the absolute path. If that throws `ERR_REQUIRE_ESM`, import the file URL instead. Any other `require` error propagates. If the loaded value has a `default` property, that property replaces it. If the result is a function, it is called with the **shared** library entry (the same object as `import { mdkit }`). Otherwise it is passed to `mdkit.use`.

A config module of `{ breaks: true }` therefore makes a single newline render as `<br>` for that invocation, unless a CLI flag overrides `breaks`.

#### 3.1.4 Token JSON

`--tokens` runs the block lexer and pretty-prints the array with a two-space indent. Array-only JSON serialization drops the non-index `links` property, so reference definitions do not appear in the JSON even though they exist on the live token list. Example: `-s a --tokens` prints

```json
[
  {
    "type": "paragraph",
    "raw": "a",
    "text": "a",
    "tokens": [
      {
        "type": "text",
        "raw": "a",
        "text": "a",
        "escaped": false
      }
    ]
  }
]
```

followed by a newline on stdout.

#### 3.1.5 Examples

- `mdkit -s '# test'` writes `<h1>test</h1>\n` and exits 0.
- `echo '# test' | mdkit` does the same.
- `mdkit -i file.md` and `mdkit file.md` compile that file.
- `mdkit missing.md real.md` compiles only `real.md`.
- `mdkit --no-gfm -s '~~x~~'` writes `<p>~~x~~</p>\n`.
- `mdkit -s hello -o out.html` creates `out.html` containing `<p>hello</p>\n` and writes nothing to stdout.

#### 3.1.6 Option effects a caller can rely on

| CLI | Compiler effect |
|---|---|
| `--gfm` | `gfm: true` (also the default) |
| `--no-gfm` | `gfm: false` |
| `--breaks` | `breaks: true`. Line-break behavior changes only when `gfm` is also true. |
| `--no-breaks` | `breaks: false` |
| `--pedantic` | `pedantic: true`, which selects the pedantic grammar even if `gfm` is true |
| `--no-pedantic` | `pedantic: false` |
| `--silent` | `silent: true` |
| `--async` | `async: true`, so the CLI awaits the compile |

#### 3.1.7 Fallback manual (printed only if `man` cannot be spawned)

```
# mdkit(1) -- a javascript markdown parser

## SYNOPSIS

`mdkit` [`-o` <output file>] [`-i` <input file>] [`-s` <markdown string>] [`-c` <config file>] [`--help`] [`--version`] [`--tokens`] [`--no-clobber`] [`--pedantic`] [`--gfm`] [`--breaks`] [`--no-etc...`] [`--silent`] [filename]

## DESCRIPTION

mdkit is a full-featured javascript markdown parser, built for speed.
It also includes multiple GFM features.

## EXAMPLES

cat in.md | mdkit > out.html
echo "hello *world*" | mdkit
mdkit -o out.html -i in.md --gfm
mdkit --output="hello world.html" -i in.md --no-breaks

## OPTIONS

-o, --output [output file]
Specify file output. If none is specified, write to stdout.

-i, --input [input file]
Specify file input, otherwise use last argument as input file.
If no input file is specified, read from stdin.

-s, --string [markdown string]
Specify string input instead of a file.

-c, --config [config file]
Specify config file to use instead of the default `~/.mdkit.json` or `~/.mdkit.js` or `~/.mdkit/index.js`.

-t, --tokens
Output a token list instead of html.

-n, --no-clobber
Do not overwrite `output` if it exists.

--pedantic
Conform to obscure parts of markdown.pl as much as possible.
Don't fix original markdown bugs.

--gfm
Enable github flavored markdown.

--breaks
Enable GFM line breaks. Only works with the gfm option.

--no-breaks, --no-etc...
The inverse of any of the mdkit options above.

--silent
Silence error output.

-h, --help
Display help information.

## CONFIGURATION

import { Mdkit } from 'mdkit';
const mdkit = new Mdkit({ gfm: true });
mdkit.parse('*foo*');

## SEE ALSO

markdown(1), nodejs(1)
```

The source manual also documents `-v` only in the implementation, not in the synopsis. Both `-v` and `--version` work.

### 3.2 JavaScript module

Import from the package root:

```js
import {
  mdkit, Mdkit, parse, parseInline, use, options, setOptions,
  lexer, parser, walkTokens, defaults, getDefaults,
  Lexer, Parser, Tokenizer, Renderer, TextRenderer, Hooks,
} from 'mdkit';
```

`mdkit` is a function and `mdkit.parse` is that same function. `parse` is the same function. Calling `mdkit(src)` or `mdkit.parse(src, options)` compiles a document.

Shared-entry properties:

| Member | Behavior |
|---|---|
| `mdkit.parseInline(src, options?)` | Compile as inline Markdown (no paragraph wrapper, no block structures). |
| `mdkit.use(...extensions)` | Register extensions on the shared instance. Returns `mdkit`. |
| `mdkit.options` and `mdkit.setOptions` | Same function. Shallow-merge into the shared instance and return `mdkit`. |
| `mdkit.getDefaults()` | A **new** object of the original defaults, every call. |
| `mdkit.defaults` | See D-30. |
| `mdkit.walkTokens(tokens, callback)` | Walk a token list. |
| `mdkit.lexer(src, options?)` | `Lexer.lex`. |
| `mdkit.parser(tokens, options?)` | `Parser.parse`. |
| `mdkit.Lexer`, `Parser`, `Renderer`, `TextRenderer`, `Tokenizer`, `Hooks` | The classes below. |
| named `lexer`, `parser`, `use`, `options`, `setOptions`, `walkTokens`, `parseInline`, `defaults`, `getDefaults` | The same functions as on `mdkit`. |
| `Mdkit` | The class in 3.3. |

`getDefaults()` returns:

```js
{
  async: false,
  breaks: false,
  extensions: null,
  gfm: true,
  hooks: null,
  pedantic: false,
  renderer: null,
  silent: false,
  tokenizer: null,
  walkTokens: null,
}
```

There is no default export. Historical options (`smartLists`, `baseUrl`, `headerIds`, `headerPrefix`, `highlight`, `langPrefix`, `mangle`, `sanitize`, `sanitizer`, `smartypants`, `xhtml`) are not interpreted. Passing them to `use` or `setOptions` only stores extra keys on the defaults object.

### 3.3 `Mdkit` class

`new Mdkit(...extensions)` starts from `getDefaults()` and then `use`s each argument. Instances do not share defaults with each other or with the module entry.

| Member | Behavior |
|---|---|
| `parse(src, options?)` | Document compile. |
| `parseInline(src, options?)` | Inline compile. |
| `use(...extensions)` | Merge extensions. Returns the instance. |
| `setOptions(options)` / `options(options)` | Shallow-merge onto that instance’s defaults. Returns the instance. Does not touch the module entry. |
| `lexer(src, options?)` | Lex with `options` or, if omitted, the instance defaults. |
| `parser(tokens, options?)` | Parse tokens the same way. |
| `walkTokens(tokens, callback)` | Depth-first walk. `this` inside `callback` is the instance. |
| `Lexer`, `Parser`, `Renderer`, `TextRenderer`, `Tokenizer`, `Hooks` | The constructors. |
| `defaults` | The instance’s live options object. |

Per-call `options` are shallow-merged over instance defaults for that call only. They do not persist. A `renderer`, `tokenizer`, or `hooks` object supplied **on the call** replaces the instance value for that call; it is not method-merged. Method merging happens only in `use`.

### 3.4 Compile pipeline

For `parse`, block mode is on. For `parseInline`, block mode is off.

1. If instance `defaults.async === true` and the call passes `async: false`, fail with the async-extension error in 3.5.
2. If `src` is `undefined` or `null`, or is not a string, fail with the input errors in 3.5.
3. If hooks exist, set `hooks.options` to the merged options and `hooks.block` to the block-mode flag.
4. `hooks.preprocess(src)` if hooks exist.
5. Lexer: `hooks.provideLexer(blockMode)` if hooks exist, otherwise the built-in block lexer or inline lexer.
6. `hooks.processAllTokens(tokens)` if hooks exist.
7. If `walkTokens` is set, walk every token. In async mode, await every returned promise (including nested arrays of promises).
8. Parser: `hooks.provideParser(blockMode)` if hooks exist, otherwise the built-in block or inline parser.
9. `hooks.postprocess(html)` if hooks exist.

Async mode runs those steps in an async function and returns a Promise. Sync mode runs them immediately and returns a string. A thrown error is handled by 3.5.

Carriage returns are normalized inside the block lexer: every `\r\n` and `\r` becomes `\n` before tokenization.

### 3.5 Errors

Every message produced by the compiler’s error wrapper is the original message plus this exact suffix:

```
\nPlease report this to https://github.com/mdkit/mdkit.
```

| Condition | Message before the suffix |
|---|---|
| `src` is `undefined` or `null` | `mdkit(): input parameter is undefined or null` |
| `src` is not a string | `mdkit(): input parameter is of type ` + `Object.prototype.toString.call(src)` + `, string expected` |
| an extension set `async: true` and the call passes `async: false` | `mdkit(): The async option was set to true by an extension. Remove async: false from the parse options object to return a Promise.` |
| the lexer repeats a rule without consuming input | `Infinite loop on byte: ` + the code unit at the stuck position |
| the parser sees a token type it does not know | `Token with "` + type + `" type was not found.` |

`silent: false` (default): sync calls throw; async calls reject with that Error.

`silent: true`: sync calls return, and async calls resolve to, this HTML (no trailing newline):

```
<p>An error occurred:</p><pre>MESSAGE</pre>
```

`MESSAGE` is the full message including the suffix, with `&`, `<`, `>`, `"`, and `'` escaped (`'` becomes `&#39;`).

Two exceptions that do **not** use that HTML wrapper:

- Unknown token type with `silent: true`: the parser writes `Token with "…" type was not found.` to `console.error` and returns `""`.
- Infinite loop with `silent: true`: the lexer writes `Infinite loop on byte: N` to `console.error` and stops lexing, returning whatever tokens it already has.

Extension registration throws immediately, without the report suffix and without the silent wrapper:

| Condition | Message |
|---|---|
| tokenizer or renderer extension has no `name` | `extension name required` |
| tokenizer extension `level` is not `block` or `inline` | `extension level must be 'block' or 'inline'` |
| renderer override names a method that is not on the renderer | `renderer '<name>' does not exist` |
| tokenizer override names a method that is not on the tokenizer | `tokenizer '<name>' does not exist` |
| hook override names a method that is not on the hooks object | `hook '<name>' does not exist` |

### 3.6 Extensions (`use`)

`use` may be called with several extension objects. Each object is processed in order. Scalar fields are shallow-copied onto the instance defaults. `async: true` sticks: once any `use` on that instance has set async, a later `use({ async: false })` leaves `async` true. `setOptions({ async: false })` does clear it, because `setOptions` is a plain shallow merge.

Unrecognized keys on an extension object are copied onto defaults and otherwise ignored.

#### 3.6.1 Tokenizer and renderer extensions

`extensions` is an array of objects:

```js
{
  name: string,          // required
  level: 'block' | 'inline',  // required when tokenizer is present
  start?: (src) => number | void,  // this.lexer is the lexer
  tokenizer?: (src, tokens) => token | false | undefined,
  renderer?: (token) => html | false | undefined,  // this.parser is the parser
  childTokens?: string[],  // property names walked by walkTokens
}
```

Tokenizer extensions are tried **before** the built-in tokenizer, most recently registered first. A return of `false`, `undefined`, or any other falsy value tries the next tokenizer. The first truthy token wins; its `raw` length is consumed. Renderer extensions for the same `name` wrap older ones: the newest runs first; `false` falls through to the previous renderer. For a built-in token type, `false` from every extension renderer falls through to the built-in HTML renderer. For an unknown type, `false` contributes an empty string and the token is skipped.

`start` functions are recorded in registration order. While a paragraph or inline text run is being cut, each `start` may return an index; the smallest non-negative index clips the source so the extension can interrupt the paragraph or the text run.

A block extension cannot interrupt a paragraph unless `start` clips that paragraph. Without `start`, a custom block is recognized only where a top-level block is tried.

Overriding a built-in name (`heading`, `code`, `checkbox`, …) uses the same false-fallback rule, so a renderer can replace one case and return `false` for the others.

#### 3.6.2 Partial tokenizer, renderer, and hooks objects

`use({ tokenizer: { paragraph(src) { … } } })` wraps those methods on the instance tokenizer. `this` inside the override is the tokenizer, which has `.lexer` and `.options`. Returning `false` calls the previous method. The properties `options`, `rules`, and `lexer` cannot be replaced.

`use({ renderer })` does the same for renderer methods. `this` is the renderer (so `this.parser` and `this.options` work for ordinary functions and method shorthand). An arrow function does not receive that `this`. Returning `false` calls the previous method. A nullish result becomes `''`. The properties `options` and `parser` are skipped. Passing an existing `Renderer` instance whose methods were assigned as own properties uses that object as the renderer and wraps the overridden methods.

`use({ hooks })` wraps hook methods. Pass-through hooks, which always feed their return value into the previously registered hook, are `preprocess`, `postprocess`, `processAllTokens`, and `emStrongMask`. The newest hook runs first. The other hooks (`provideLexer`, `provideParser`) run the newest first and, on a return of `false`, call the previous one. In async mode the pass-through hooks except `emStrongMask` are awaited, and non-pass-through hooks are awaited. The properties `options` and `block` are skipped.

#### 3.6.3 Hook contracts

| Hook | Called with | Return |
|---|---|---|
| `preprocess` | the Markdown string | the string to lex |
| `processAllTokens` | the token list | the list to walk and parse |
| `postprocess` | the HTML string | the string returned to the caller |
| `emStrongMask` | a copy of the inline source used only to find emphasis delimiters | the masked string. The original source is still what gets sliced into tokens. |
| `provideLexer(block)` | `true` from `parse`, `false` from `parseInline` | `(src, options) => tokens` |
| `provideParser(block)` | same flag | `(tokens, options) => html` |

`this.options` inside a hook is the merged options for the call, and writing `this.options.breaks = true` during `preprocess` affects that compile. `this.block` is the same flag passed as the argument. Concurrent `parse` and `parseInline` on one instance each pass their own flag; they do not permanently swap `this.block`.

Default `provideLexer` returns the block lexer when `block` is true and the inline lexer otherwise. Default `provideParser` returns the block parser or the inline parser the same way.

Several `emStrongMask` hooks compose newest-first, and the mask affects delimiter scanning only. The characters that appear in the HTML are the original ones.

#### 3.6.4 `walkTokens`

The walker visits a token, then its children:

- `table`: each header cell’s `tokens`, then each body cell’s `tokens`. Cell objects themselves are not tokens.
- `list`: each item (a `list_item` token), which then walks its own children.
- any other token: if `extensions.childTokens[type]` lists property names, those properties are flattened one level of nesting deep and walked; otherwise a `tokens` array is walked.

The callback’s return value is ignored except that promises are collected. In async mode the compile waits for all of them. Callbacks from several `use` calls all run, newest first, on the same token object, so a later-registered callback sees mutations made by an earlier-registered one that runs first. `this` is the `Mdkit` instance, which exposes `.Lexer` (including `.lexInline`).

Mutating tokens inside `walkTokens` (changing `text`, replacing `tokens`, even changing `type`) is visible to the parser.

### 3.7 Tokens

A block lex returns an array that also has a `links` property: a null-prototype object mapping a normalized label to `{ href, title }`. `Lexer.lex` / `mdkit.lexer` return that object. `Lexer.lexInline` / inline lexing returns a plain array of inline tokens.

Label keys: trim, collapse whitespace to a single space, then `toLowerCase()`, then `toUpperCase()`, then `toLowerCase()` again. That fold is how `ẞ` and `SS` meet. Lookups use `Object.hasOwn`, so inherited names are not definitions.

Token fields a caller of `lexer` can rely on (`raw` is the exact consumed slice, after carriage-return normalization):

| `type` | Fields |
|---|---|
| `space` | `raw` |
| `code` | `raw`, `text`, optional `lang`, optional `codeBlockStyle: 'indented'` for indented (not fenced) code, optional `escaped` |
| `heading` | `raw`, `depth` (1–6), `text`, `tokens` |
| `table` | `raw`, `align` (`'left'` \| `'right'` \| `'center'` \| `null` per column), `header` (cells), `rows` (arrays of cells) |
| `hr` | `raw` |
| `blockquote` | `raw`, `text`, `tokens` |
| `list` | `raw`, `ordered`, `start` (number or `''`), `loose`, `items` |
| `list_item` | `raw`, `task`, `checked` when it is a task, `loose`, `text`, `tokens` |
| `html` | `raw`, `text`, `pre` (true for script/pre/style blocks), `block` |
| `def` | `raw`, `tag`, `href`, `title`. Definitions are not rendered. |
| `paragraph` | `raw`, `text`, `tokens` |
| `text` | `raw`, `text`, optional `tokens`, optional `escaped` |
| `escape` | `raw`, `text` (the character after the backslash) |
| `link` | `raw`, `href`, `title` (string or null), `text`, `tokens`, optional `autolink: true` |
| `image` | `raw`, `href`, `title`, `text`, `tokens` |
| `strong`, `em`, `del` | `raw`, `text`, `tokens` |
| `codespan` | `raw`, `text` |
| `br` | `raw` |
| `checkbox` | `raw`, `checked` |

Table cells are `{ text, tokens, header, align }` and are not tokens.

Top-level paragraph text is a `paragraph` token. The first block inside a tight list item is a `text` token, not a `paragraph`. A blockquote’s paragraph child is a `paragraph`.

`Lexer.rules` is `{ block, inline }`. `block` has `normal`, `gfm`, and `pedantic`. `inline` has `normal`, `gfm`, `breaks`, and `pedantic`. Each value is a record of regular expressions the tokenizer reads.

Grammar selection for a lexer:

1. `pedantic: true` → pedantic block and inline rules. `gfm` and `breaks` do not apply.
2. else `gfm: true` and `breaks: true` → GFM block rules and breaks inline rules.
3. else `gfm: true` → GFM block and GFM inline rules.
4. else → normal (CommonMark) block and inline rules.

`lexer.inline(src, tokens = [])` does **not** tokenize immediately. It queues `src` to be inline-tokenized into `tokens` at the end of the current block lex. Extensions that build block tokens during lexing use it so inline text is tokenized after link definitions are known. `lexer.inlineTokens(src, tokens?)` tokenizes immediately.

Two `Lexer` instances, and a static `Lexer.lex` versus an instance `lex`, produce equal tokens for the same input and options.

### 3.8 HTML serialization

The renderer escapes text as follows.

- **Encode-all** (`code` text, `codespan` text, autolink href and text, silent error messages): `& < > " '` become `&amp; &lt; &gt; &quot; &#39;`.
- **Encode-unsafe** (ordinary text, link and image titles, non-autolink hrefs, image alt): `< > " '` are always escaped. `&` is escaped only when it does **not** begin a numeric reference (`&#` + 1–7 digits + `;`, or `&#x` + 1–6 hex digits + `;`) or a named reference (`&` + one or more word characters + `;`). Named references are **not** looked up in an entity table. `&MadeUpEntity;` and `&nbsp;` are left unchanged. `&x;` is left unchanged. A bare `&`, or `&` followed by something that is not that form (`&hi?;`, `&#;`, `&#abcdef0;`), becomes `&amp;`.

Numeric character references in ordinary text (not inside code spans, not inside raw HTML, not while a raw-HTML inline tag such as `pre`/`code`/`kbd`/`script` is open) are decoded before escaping. Decimal (`&#35;`) and hex (`&#X22;`, `&#xcab;`) forms of 1–7 decimal digits or 1–6 hex digits are recognized. Code point 0, any value above `0x10FFFF`, and UTF-16 surrogates `0xD800`–`0xDFFF` become U+FFFD. Other values become that Unicode character. `&#35;` is `#`, `&#1234;` is `Ӓ`, `&#0;` is U+FFFD, `&#abcdef0;` is not a numeric reference (it has a letter in the decimal form, and the hex form requires `x`) and is escaped to `&amp;#abcdef0;`. Inside a code span the characters are escaped and not decoded: `` `&#35;` `` → `<code>&amp;#35;</code>`.

`cleanUrl` runs `encodeURI` on a href and then replaces `%25` with `%`. If `encodeURI` throws, the link or image is not emitted as a link or image: a link renders as its already-rendered text, an image renders as its escaped alt text. `javascript:` URLs are **not** stripped.

Exact tag spelling (this is what `parse` returns; it does not pretty-print):

| Token | HTML |
|---|---|
| `space`, `def` | empty string |
| `hr` | `<hr>\n` |
| `heading` | `<hN>` + inline + `</hN>\n` |
| `code` with empty text | `<pre><code></code></pre>\n` or, with a language, `<pre><code class="language-LANG"></code></pre>\n` |
| `code` with text | same, but the escaped text is followed by `\n` if it did not already end with one. A language is the leading non-space run of `lang`, escaped with encode-unsafe. |
| `blockquote` | `<blockquote>\n` + rendered children + `</blockquote>\n` |
| `html` | the raw `text`, unchanged, including its own newlines |
| `list` | `<ul>\n` or `<ol>\n` or `<ol start="N">\n` when ordered and `start` is not `1`, then items, then the closing tag and `\n` |
| `list_item` | `<li>` + rendered children + `</li>\n`. No newline is inserted between `<li>` and the first child. |
| `checkbox` | `<input checked="" disabled="" type="checkbox"> ` if checked, otherwise `<input disabled="" type="checkbox"> ` (trailing space, no slash) |
| `paragraph` | `<p>` + inline + `</p>\n` |
| `table` | `<table>\n<thead>\n` + one header row + `</thead>\n` + optional `<tbody>` + body rows + `</tbody>` + `</table>\n`. There is no newline between `<tbody>` and the first `<tr>`, and none between `</tbody>` and `</table>`. An empty body omits `<tbody>`. |
| `tablerow` | `<tr>\n` + cells + `</tr>\n` |
| `tablecell` | `<th>` or `<td>`, with ` align="left"|"right"|"center"` when align is non-null, then inline, then the closing tag and `\n` |
| `strong` | `<strong>` + inline + `</strong>` |
| `em` | `<em>` + inline + `</em>` |
| `codespan` | `<code>` + encode-all(text) + `</code>` |
| `br` | `<br>` |
| `del` | `<del>` + inline + `</del>` |
| `link` | `<a href="HREF">` + text + `</a>`, with ` title="TITLE"` before `>` when title is non-empty. Autolink text and href use encode-all. Other link text is inline-rendered; href uses encode-unsafe. |
| `image` | `<img src="HREF" alt="ALT">` with optional ` title="TITLE"`. Alt is the plain-text rendering of the image’s tokens (markers such as `*` are not turned into tags), then encode-unsafe. |
| `text` | if it has child tokens, their inline HTML; else encode-all when `escaped` is true, otherwise encode-unsafe |

`parse` of the empty string returns `""` (no newline). `parse` does not add a newline after the renderer’s output. The CLI adds one when writing stdout.

`parseInline` does not wrap a paragraph and does not recognize block grammar. `# header\n\n_em_` becomes `# header\n\n<em>em</em>`. `**strong** _em_` becomes `<strong>strong</strong> <em>em</em>`.

Tight list items render their text without `<p>`. Loose items wrap that text in `<p>…</p>\n`. A list is loose when any item is separated from the next by a blank line, or when an item’s own block tokens contain a `space` token whose `raw` contains a blank line (`\n` … `\n`). When the list is loose, every item is loose, and top-level `text` children are retyped to `paragraph`.

### 3.9 Markdown language

#### 3.9.1 CommonMark (non-pedantic)

With `pedantic: false`, both `gfm: false` and `gfm: true` accept every CommonMark 0.31.2 example: the HTML a browser builds from `parse`’s output matches the HTML a browser builds from that example’s reference HTML. The bytes are often not identical. The serializer in 3.8 is the byte contract. In particular:

- Void tags are `<hr>`, `<br>`, and `<img …>` with no slash and no space before `>`.
- `<li>` is not followed by a newline before its first child. A nested list follows the preceding text immediately (`<li>foo<ul>`).
- `'` in escaped text is `&#39;`.
- Named entities are not decoded.
- Indent of four spaces that CommonMark’s reference HTML sometimes trims inside a paragraph is preserved when it was part of the paragraph source (`Foo\n    bar` is `<p>Foo\n    bar</p>\n`).
- `>\t\tfoo` is a blockquote whose code block text is `foo\n`, not two spaces plus `foo`.

The CommonMark sections covered are: tabs, backslash escapes, entities and numeric character references, precedence, thematic breaks, ATX headings, setext headings, indented code, fenced code, HTML blocks, link reference definitions, paragraphs, blank lines, block quotes, list items, lists, inlines, code spans, emphasis and strong emphasis, links, images, autolinks, raw HTML, hard line breaks, soft line breaks, and textual content.

Structural rules a client can observe, all with `pedantic: false`:

- Tabs advance to the next column multiple of 4, counting columns already consumed. Inside indented code, a tab that is part of the indent is consumed as indent and a tab that is part of the content stays a tab character.
- Backslash escapes the CommonMark punctuation set. The escaped character is emitted raw (then HTML-escaped). A backslash before a newline is a hard break when the newline is not at the end of the source.
- A hard break is two or more spaces, or a backslash, before a newline that is not the end of the input. Leading spaces and tabs on the following line are removed. A newline that is not a hard break stays a newline character inside the paragraph.
- ATX headings are 1–6 `#` at column 0–3, then a space or end of line. Closing `#` are removed only when a space or tab precedes them. `# h#` stays `h#`. More than six `#` is not a heading.
- Setext headings are a paragraph line plus a line of `=` (level 1) or `-` (level 2). They do not interrupt a CommonMark paragraph by themselves; the setext line has to be the underline of that paragraph. Trailing whitespace on the heading text is trimmed.
- Indented code is one or more lines indented at least 4 spaces or a tab. It cannot interrupt a paragraph; those lines stay paragraph text. Trailing blank lines are removed from the block except that a single trailing blank line is kept. The renderer then guarantees one trailing newline when the text is non-empty.
- Fences use three or more backticks or tildes. The info string is trimmed and backslash escapes in it are decoded; the first non-space word becomes `language-…`. The closing fence must use the same character and at least as many of them. Indentation that is common with the opening fence is stripped from each content line, and a content line indented less than the fence loses all of its indentation. An empty fence produces an empty `<code>` with no inner newline. A fence can interrupt a paragraph.
- Thematic breaks are three or more `-`, `_`, or `*` with optional spaces or tabs, at column 0–3, and they interrupt paragraphs.
- HTML blocks follow the CommonMark type 1–7 rules (script/pre/style/textarea, comments, processing instructions, declarations, CDATA, the block-tag list, and complete open or close tags). The raw HTML is copied through. Markdown inside a type-6 or type-7 block is still parsed when blank lines make the interior a separate block (`<div>\n\n*Markdown*\n\n</div>` renders the emphasis). The GFM “disallowed raw HTML” tag filter is **not** applied; `<title>`, `<style>`, `<xmp>`, and similar tags stay raw.
- Link reference definitions are not rendered. Labels match under the normalization in 3.7. A title may use `"`, `'`, or `()`. Destinations in angle brackets drop the brackets.
- Lists use `+`, `-`, `*`, or 1–9 digit numbers followed by `.` or `)`. Only a bullet, or the number 1, followed by content, can interrupt a paragraph. Other numbers and empty items cannot. The `start` attribute is the first item’s number when it is not 1 (`0` is kept as `start="0"`; `01` is the number 1 and gets no attribute). Nested lists and code inside items follow CommonMark indent rules, with tabs expanded against the item indent. A list marker that is really a thematic break ends the list.
- Block quotes strip one leading `>` and an optional following space. Lazy continuation lines (no `>`) stay in the quote until a block that cannot continue. A setext underline inside a quote is prevented from becoming a heading by indenting it when the marker is stripped.
- Code spans use matching backtick runs. Newlines inside become spaces. If the content both begins and ends with a space and contains a non-space, one space is removed from each end. Tabs at the ends are not removed. A code span is not emphasis.
- Emphasis and strong emphasis follow CommonMark flanking rules for `*` and `_`, including Unicode punctuation, nested and mixed markers, and the rule that `_` inside a word is not emphasis. Delimiters inside masked regions (links, code spans, raw HTML) are not emphasis delimiters.
- Inline links, images, reference links, and collapsed references follow CommonMark, including balanced parentheses in destinations and titles in `"`, `'`, or `()`. A link whose text contains another link is rejected and the inner link is kept; the outer brackets remain text. While that rejected text is rescanned, raw-HTML state opened by the discarded scan is cleared, so `&` before a `<pre>` in the outer text is still escaped. Example: `[a & b <pre> [x](/uri)](/uri)` renders `<p>[a &amp; b <pre> <a href="/uri">x</a>](/uri)</p>\n`.
- Angle-bracket autolinks (`<scheme:…>` and `<email@domain>`) exist in every non-pedantic mode. Email autolinks get a `mailto:` href. They are marked `autolink`, so `&` in them is fully escaped.
- Links may not be nested. Images may contain links in their alt text; the alt is flattened to text.

#### 3.9.2 GitHub Flavored Markdown

`gfm` defaults to true. On top of 3.9.1, GFM adds the following. It does not add the disallowed-raw-HTML extension.

**Tables.** A header line, a delimiter line, and optional body lines. The delimiter must contain `|` or `:`. The header column count must equal the delimiter column count; otherwise the text is not a table. Alignment: `:---` left, `---:` right, `:---:` center, otherwise no `align` attribute. Body cells are padded or truncated to the header width. Cells are trimmed. `\|` is a literal pipe. A table can interrupt a paragraph and can itself be interrupted by a heading, fence, list, quote, thematic break, or HTML block. A table with no body rows omits `<tbody>`. Example:

```
| abc | defghi |
:-: | -----------:
bar | baz
```

renders a two-column table whose header cells are `align="center"` and `align="right"`.

**Task lists.** When `gfm` is true, a list item whose text matches `[ ]`, `[x]`, or `[X]`, then one or more spaces, then a non-space, is a task. `[x]` and `[X]` are checked. The marker is removed from the item text and a `checkbox` token is inserted. In a tight list the checkbox is the first child of the item. In a loose list it is the first inline token of the item’s paragraph. With `gfm: false` the brackets stay as text.

**Strikethrough.** `~~text~~` and `~text~` render as `<del>`. The delimiter length must match. Opening and closing delimiters follow flanking rules analogous to emphasis, and `~` is not treated as punctuation for emphasis, so `~` can appear inside `em`/`strong`. Strikethrough does not cross a blank line. A run of three or more tildes is not strikethrough (`~~~not~~~` stays text). Spaces immediately inside the tildes do not strike (`~~ a ~~`).

**Autolinks (extended).** In addition to angle-bracket autolinks:

- `www.` followed by a domain becomes a link whose href is `http://` plus the matched text.
- `http://`, `https://`, and `ftp://` (any letter case) become links with that href.
- An email address becomes `mailto:` that address.
- `mailto:` and `xmpp:` followed by an email are links. `xmpp:` may include a `/resource` of letters, digits, `@`, and `.`.
- Trailing punctuation is trimmed by the backpedal rule. A final `.`, `?`, `!`, `,`, `:`, `;`, `*`, `_`, quotes, `~`, and unmatched `)` are not part of the link. Balanced parentheses can be included (`www.google.com/search?q=Markup+(business)`). An extra `)` after a balanced pair is excluded. A trailing `&hl;` that looks like an entity is not part of the link. `<` ends the link.
- These links are `autolink: true`, so every `&` in the href and the text is escaped (`&` → `&amp;`, `&amp;` → `&amp;amp;`, `&lt;` → `&amp;lt;`).
- Ordinary inline links and reference links are not autolinks: `&lt;` stays `&lt;` in the href, `&amp;` stays `&amp;`, and a bare `&` becomes `&amp;`. Image `src` uses the same encode-unsafe rule as ordinary hrefs.

**Breaks.** With `gfm: true` and `breaks: true`, a single newline inside a paragraph is a `<br>`, including a newline with no preceding spaces. `breaks` has no effect when `gfm` is false or `pedantic` is true.

#### 3.9.3 Pedantic mode

`pedantic: true` selects a looser, older grammar and ignores `gfm` for rule selection. Observable differences:

- Before block lexing, every tab is replaced by four spaces and every line that contains only spaces is deleted.
- Fenced code is not recognized. Backtick runs are inline code.
- ATX headings do not require a space after `#` and do not require the hashes to sit at column 0–3. Closing hashes are stripped even without a preceding space, so `# hi#` is `<h1>hi</h1>\n`.
- Setext headings use a simpler pattern and can interrupt more freely.
- Paragraphs are not interrupted by lists, fences, or HTML the way CommonMark interrupts them.
- HTML blocks use the older “block tag through its close tag, or a tag followed by a blank line” rule, and a set of inline tags (`a`, `em`, `strong`, `span`, `br`, `img`, …) do not open an HTML block.
- Link definitions and inline links are the older forms: the destination is the non-greedy inside of `(…)` , and a title is a quoted string after whitespace.
- Emphasis treats opening quotes and brackets as able to start strong emphasis (`**"A"**`, `**(A)**`), and the right-delimiter rules differ for markers that touch punctuation (`**foo:**bar`).
- No tables, no strikethrough, no extended autolinks. Task-list detection still checks the `gfm` flag; with the pedantic grammar and `gfm: true` a checkbox can still be recognized, but the default pedantic suites run with `gfm: false`.

The original Markdown fixture suite (amps and angle encoding, autolinks, backslash escapes, block quotes, code, hard-wrapped paragraphs, horizontal rules, inline HTML, links, literal quotes in titles, nested quotes, lists, strong punctuation, tabs, tidiness) is the pedantic contract: `parse` with `{ gfm: false, pedantic: true }` matches those fixtures under HTML-parser equality.

#### 3.9.4 Other observable rules

- A single `\n` between blocks is absorbed into the previous token’s `raw` and does not become a `space` token. Two or more newlines become a `space` token, which renders nothing, so paragraphs are separated by the tags’ own newlines only.
- Indented code that follows a paragraph is appended to that paragraph instead of becoming a code block.
- Link and image text is inline-tokenized. Image alt text uses the text renderer, so emphasis markers inside alt text are flattened, not tagged.
- Inside an open raw inline tag (`pre`, `code`, `kbd`, `script`), following text is not entity-decoded and is emitted without the encode-unsafe pass (`escaped: true`).
- Reference-style links whose label contains no definition are left as text.
- The compiler finishes the pathological inputs used as timing checks in under one second and returns HTML. Those inputs include 50 000 `a` characters (a paragraph of those characters), 10 000 lines of `- a\n` (a list of 10 000 items), a line of 101 underscores plus ` a` (plain text, not emphasis), and the other quadratic and cubic patterns in the timing suite (nested brackets, long email-like strings, long headings, unclosed HTML, reflink scans, tilde runs, empty link destinations).

### 3.10 What is not in the program

- No HTTP server, routes, or HTML pages are served by the library or the CLI.
- Output is not sanitized. `<script>`, event-handler attributes, and `javascript:` URLs pass through.
- There is no syntax highlighting, heading `id`, smart punctuation, XHTML slash, email mangling, or base-URL rewriting unless the caller supplies an extension.

## 4. Behaviour claims

D-1. The CLI process title is `mdkit`.

D-2. Node.js older than 20 is outside the supported runtime.

D-3. `mdkit -s '# test'` and `mdkit --string '# test'` write `<h1>test</h1>\n` and exit 0.

D-4. With no arguments, Markdown is read from stdin until EOF and compiled. `# test\n` on stdin yields `<h1>test</h1>\n`.

D-5. A positional path and `-i` / `--input` compile that UTF-8 file. `# file` yields `<h1>file</h1>\n`.

D-6. When several positional paths are given, only the last is read. A missing earlier path does not fail the run.

D-7. A missing positional file or a missing `--input` file exits 1 and writes `mdkit: <absolute path>: No such file or directory` to stderr with no trailing newline.

D-8. `-c` and `--config` load a module whose default export is `{ breaks: true }` and then compile the string so that `line1\nline2` becomes `<p>line1<br>line2</p>\n`.

D-9. A config filename containing `#` is loaded as a path.

D-10. `--config` of a path that does not exist exits 1 with stderr `Cannot load config file '<path>'` and does not compile.

D-11. Without `--config`, the first existing file among `~/.mdkit.json`, `~/.mdkit.js`, and `~/.mdkit/index.js` is loaded the same way, and the search stops. With `--config`, those files are not consulted.

D-12. A config value with a `default` export uses that export. A function is called with the shared `mdkit` entry. Any other value is passed to `mdkit.use`. ESM modules that CommonJS `require` rejects with `ERR_REQUIRE_ESM` are loaded with a dynamic `import` of their file URL.

D-13. `-v` and `--version` print `18.0.14` and a newline, then exit 0, without reading input.

D-14. `-h` and `--help` spawn `man` on the package manual and exit 0. They do not compile Markdown. If the `man` executable cannot be started, the manual Markdown is written to stdout. If `man` starts but the page is missing, the CLI adds no message of its own.

D-15. During `--help`, `SIGINT` is forwarded to the `man` child.

D-16. `-o` / `--output` writes the compiler string to that path and writes nothing to stdout. The extra stdout newline is not added to the file.

D-17. `-n` / `--no-clobber` with an output path that already exists exits 1 and writes `mdkit: output file '<path>' already exists, disable the '-n' / '--no-clobber' flag to overwrite` plus a newline to stderr. It does not modify the file.

D-18. `--tokens` writes the lexer array as two-space JSON. The `links` map is not in the JSON. Stdout then receives one more newline.

D-19. Long options whose names are built-in default keys set the per-call options. Boolean keys become `true`. `--no-` on a boolean key sets `false`. Non-boolean keys take the next argument as a string, and `--no-` on them sets `null`. Unknown long options are ignored.

D-20. `--name=value` splits on the first `=` and pushes the value back. For a boolean option the pushed value is not consumed as the option’s value.

D-21. A clustered short flag of length greater than 2 expands to one flag per letter.

D-22. `--string` wins over `--input` and positional files when the string is non-empty. An empty string does not win.

D-23. Per-call CLI options override keys that a config file set with `use`.

D-24. On success the CLI exits 0. On a caught error it writes the message described in section 2.3 and exits 1.

D-25. A CommonJS `require` of the ESM build can call `mdkit.parse('# test')` and the result contains `<h1`. A UMD script load defines a global `mdkit` with the same property.

D-26. The original defaults are `async: false`, `breaks: false`, `extensions: null`, `gfm: true`, `hooks: null`, `pedantic: false`, `renderer: null`, `silent: false`, `tokenizer: null`, `walkTokens: null`.

D-27. `getDefaults()` returns a new object with those values and does not track later `setOptions` changes.

D-28. `mdkit(src)` and `mdkit.parse(src)` are the same function and compile a document on the shared instance.

D-29. `parseInline('**strong** _em_')` returns `<strong>strong</strong> <em>em</em>`. `parseInline('# header\n\n_em_')` returns `# header\n\n<em>em</em>`.

D-30. Before any `use` or `setOptions` on the shared entry, assigning `mdkit.defaults.gfm = false` or `defaults.breaks = true` does not change later `parse` results. `setOptions` and `use` replace the exported `defaults` object with the shared instance’s defaults; after that, writing a property on `defaults` changes later parses that do not override it.

D-31. `setOptions` on the shared entry shallow-merges, updates `mdkit.defaults`, and returns `mdkit`. `options` is the same function.

D-32. Two `Mdkit` instances keep separate renderers, tokenizers, hooks, and options. The shared `mdkit.parse` is unaffected by `new Mdkit({ renderer })`.

D-33. `instance.lexer(src)` then `instance.parser(tokens)` uses that instance’s renderer and tokenizer.

D-34. `use` accepts a `Renderer`, `Tokenizer`, or `Hooks` instance on which the caller has assigned methods. Those methods replace the built-in ones for that registration.

D-35. A per-call option object overrides instance defaults for that call only.

D-36. `parse` of `undefined` or `null` throws, when `silent` is false, an Error whose message is `mdkit(): input parameter is undefined or null` plus the report suffix.

D-37. `parse` of a non-string throws `mdkit(): input parameter is of type ` + the `toString` tag + `, string expected` plus the report suffix. A number’s tag is `[object Number]`.

D-38. With `silent: true`, those input failures return `<p>An error occurred:</p><pre>` + the fully escaped message + `</pre>` and do not throw. With `async: true` and `silent: true` the same string is the resolved value.

D-39. The report suffix is exactly a newline followed by `Please report this to https://github.com/mdkit/mdkit.`

D-40. `parse(src, { async: true })` returns a Promise of the HTML. `parse(src, { async: false })` returns a string. `async: true` with no `walkTokens` still returns a Promise of the normal HTML.

D-41. If any `use` set `async: true`, a later `use({ async: false })` leaves async on, and `parse(src, { async: false })` throws the async-extension error plus the report suffix.

D-42. `setOptions({ async: false })` clears async on that instance even after `use({ async: true })`.

D-43. Empty source compiles to `""`.

D-44. `\r\n` and `\r` are normalized to `\n` before block rules run. `a\r\nb` renders `<p>a\nb</p>\n`.

D-45. A block extension without `start` does not interrupt a paragraph. The same extension with `start` returning the index of its marker does interrupt, and the rest of the paragraph stays a paragraph.

D-46. An inline extension’s `tokenizer` and `renderer` run for its matches inside a paragraph.

D-47. Registering the same extension `name` twice tries the newer tokenizer first and the newer renderer first. `false` from either falls through to the older one, and a built-in name falls through to the built-in implementation.

D-48. A checkbox renderer that returns `false` for a checked box uses `<input checked="" disabled="" type="checkbox"> `, and a false renderer on a loose task list uses the checkbox inside the item’s `<p>`.

D-49. `childTokens` limits the walk to the named properties. Children are walked after the parent. Several `walkTokens` callbacks all see each token, newest registration first.

D-50. `walkTokens` on a document that contains a paragraph, thematic break, heading, fence, table, quote, list, raw HTML, link, image, strong, em, code span, strikethrough, and a hard break visits those token types in that order, children immediately after their parent, and table cells only via their inline tokens.

D-51. Editing or deleting tokens in `walkTokens` changes the HTML. An async `walkTokens` is awaited before HTML is produced, and `this.Lexer.lexInline` is available on the instance.

D-52. A renderer method and a tokenizer method supplied to `use` are called with the source token or source text, and may replace the built-in result. Several renderer overrides merge; the newest method wins unless it returns `false`.

D-53. Inside a renderer method, `this.options` is set for a normal function and for method shorthand, and is not set for an arrow function.

D-54. `use({ breaks: true })` makes `line1\nline2` render `<p>line1<br>line2</p>\n` on that instance.

D-55. An extension without `name` throws `extension name required`. A tokenizer whose `level` is missing or not `block` or `inline` throws `extension level must be 'block' or 'inline'`.

D-56. A renderer, tokenizer, or hooks override for an unknown method throws `renderer '<name>' does not exist`, `tokenizer '<name>' does not exist`, or `hook '<name>' does not exist`. Overrides of `options`, `parser`, `rules`, `lexer`, and hooks `block` are ignored rather than installed.

D-57. `preprocess` transforms the string before lexing, `processAllTokens` runs before `walkTokens`, and `postprocess` transforms the HTML. Each can be async when `async: true`.

D-58. Pass-through hooks chain newest first: the newest `preprocess` sees the raw string and its return value is passed to the older `preprocess`. The same order applies to `postprocess` and `processAllTokens`. The HTML for a second registration that wraps with `preprocess2` and a first that wraps with `preprocess1` therefore shows the first registration’s heading outside the second’s.

D-59. `provideLexer` and `provideParser` replace the lexer or parser. They receive `true` from `parse` and `false` from `parseInline`. The default hooks return the block or inline built-in matching that flag.

D-60. Setting `this.options.breaks = true` inside `preprocess` affects that compile.

D-61. `emStrongMask` hides delimiter characters from emphasis scanning without changing the characters that are rendered. Several masks compose newest-first, including in async mode.

D-62. A top-level paragraph token has `type: 'paragraph'`. The paragraph inside a blockquote is a `paragraph`. The first child of a tight list item is `text`.

D-63. Raw inline HTML is passed to `renderer.html` with `raw` equal to the matched tag source.

D-64. `[a & b <pre> [x](/uri)](/uri)` renders `<p>[a &amp; b <pre> <a href="/uri">x</a>](/uri)</p>\n`.

D-65. The renderer emits the tag spelling in section 3.8. In particular `<hr>\n`, `<br>`, `<li>` with no following newline, `<ol start="N">` only when the start number is not 1, checkbox inputs with `disabled=""` and a trailing space, and tables whose `<tbody>` is omitted when there are no body rows.

D-66. Code with a language renders `<pre><code class="language-LANG">` plus the escaped body. An empty fence renders `<pre><code></code></pre>\n` with nothing between the tags. A non-empty code body is followed by a newline inside `<code>`.

D-67. Encode-all escaping turns `& < > " '` into `&amp; &lt; &gt; &quot; &#39;`. Encode-unsafe escaping leaves `&` in place when it begins a numeric reference or a `&word;` reference, and escapes every other `&`.

D-68. Numeric character references in ordinary text decode as in section 3.8. `&#35; &#1234;` renders `<p># Ӓ</p>\n`. `&#0;` renders U+FFFD. `&#abcdef0;` renders `&amp;#abcdef0;`. A code span does not decode them.

D-69. Named character references are not decoded. `&nbsp;` stays `&nbsp;`. `&MadeUpEntity;` stays `&MadeUpEntity;`. `&amp;` stays `&amp;`. `AT&T` becomes `AT&amp;T`.

D-70. `cleanUrl` is `encodeURI` followed by replacing `%25` with `%`. A failed encoding drops the link or image and leaves text or escaped alt text. `javascript:` URLs are preserved.

D-71. With `gfm: false` and `pedantic: false`, every CommonMark 0.31.2 example’s `parse` output is HTML-equivalent to that example’s reference HTML, using the byte rules in 3.8 and 3.9.1.

D-72. With `gfm: true` and `pedantic: false`, those same CommonMark examples stay HTML-equivalent, and the GFM 0.29 table, task-list, strikethrough, and autolink examples match their reference HTML under the same comparison. The single disallowed-raw-HTML example does **not** match the filtered reference: the raw tags are preserved, and the suite records that example as an expected mismatch.

D-73. `| foo | bar |\n| --- | --- |\n| baz | bim |` renders a table with header cells `foo` and `bar` and one body row `baz`, `bim`, with no `align` attributes.

D-74. A delimiter row `:---:` / `---:` sets `align="center"` and `align="right"` on those columns.

D-75. A header/delimiter column-count mismatch is not a table. A delimiter line without `|` or `:` is not a table.

D-76. `- [ ] foo\n- [x] bar` renders an unchecked checkbox and then a checked checkbox, each inside a tight `<li>`, with the marker text removed. `- [X] t` is checked. With `gfm: false`, `- [x] a` renders the brackets as text.

D-77. A loose task list puts the checkbox inside the item paragraph.

D-78. `~~Hi~~ Hello, ~there~ world!` renders `<p><del>Hi</del> Hello, <del>there</del> world!</p>\n`. `This will ~~~not~~~ strike.` does not render `<del>`. Strikethrough does not cross a blank line.

D-79. `www.commonmark.org` renders a link to `http://www.commonmark.org`. `http://` and `https://` URLs are linked with their own scheme. `foo@bar.baz` renders `mailto:foo@bar.baz`. `mailto:` and `xmpp:` addresses are linked, and an `xmpp:` resource is included only through the first path segment the grammar allows (`xmpp:foo@bar.baz/txt/bin` links `xmpp:foo@bar.baz/txt` and leaves `/bin` as text).

D-80. Extended autolinks drop a trailing `.` that ends a sentence, keep balanced parentheses, and exclude a following entity-like `&hl;`. Every `&` inside an autolink’s href and text is encode-all escaped. The same URL written as `[text](url)` or as a reference keeps `&lt;` and `&amp;` intact and escapes a bare `&` once.

D-81. With `breaks: true` and `gfm: true`, `A\nB` renders `<p>A<br>B</p>\n`. With `breaks: false`, the newline remains inside the paragraph. `breaks` does nothing when the pedantic grammar is selected or when `gfm` is false.

D-82. Hard breaks from two spaces or a backslash drop leading spaces and tabs on the next line: `foo  \n     bar` and `foo\\\n     bar` and `foo  \n\tbar` all render `<p>foo<br>bar</p>\n`. A soft break keeps a tab: `foo\n\tbar` renders `<p>foo\n\tbar</p>\n`.

D-83. Fenced code indented by three spaces strips that indent from longer content lines and strips a shorter line completely. A fence indented by two spaces with content indented by six spaces keeps four spaces of content.

D-84. A fenced block nested in a list item, including when the fence starts on the marker line and when the content indent is a tab, keeps tab characters that are part of the code text and does not turn them into spaces. The same bytes are produced for `gfm: true` and `gfm: false`.

D-85. An indented code block of a tab, three spaces plus a tab, a lone tab, four spaces, or five spaces matches the exact HTML in `test/specs/new/tabs_indented_code.html`. A tab inside a fence is preserved.

D-86. A paragraph, a line of only spaces, and more text are two paragraphs. An indented code block keeps a single internal blank line and a following less-indented line that is still code, including one blank line that the trimmer keeps.

D-87. `# hi` in pedantic mode, with no space after `#`, renders `<h1>hi</h1>\n`. `# hi#` in pedantic mode strips the closing hash. `# hi#` in non-pedantic mode keeps `hi#`.

D-88. `>\t\tfoo` renders `<blockquote>\n<pre><code>foo\n</code></pre>\n</blockquote>\n`.

D-89. Ordered lists use the first marker’s numeric value as `start` when it is not 1. `2. a` renders `<ol start="2">`. `1. a` renders `<ol>` with no start attribute. Bullets `+`, `-`, and `*` render `<ul>`.

D-90. Code spans turn interior newlines into spaces and strip one leading and one trailing space only when both ends are spaces and the span contains a non-space. Tabs at the ends are kept.

D-91. Link labels match case-insensitively after trim and whitespace collapse, using the lower/upper/lower fold, so a reference and its definition meet even when one uses `ẞ` and the other uses `SS`.

D-92. Definitions render nothing. `[a][b]` with `[b]: /u "t"` renders `<p><a href="/u" title="t">a</a></p>\n`.

D-93. Images render `<img src="…" alt="…">` with no closing tag. Alt text is plain text, not inline HTML.

D-94. With `gfm: false` and `pedantic: true`, the original Markdown fixture pairs (encoding, autolinks, escapes, quotes, code, lists, rules, inline HTML, links, emphasis) match under HTML-parser equality.

D-95. Pedantic mode replaces tabs with four spaces and deletes space-only lines before block parsing, and it does not recognize fenced code blocks.

D-96. The timing-suite inputs in section 3.9.4 compile to their paired HTML in under one second, with `silent: false`.

D-97. An unknown token type throws `Token with "<type>" type was not found.` when `silent` is false, and when `silent` is true logs that sentence and returns `""`.

D-98. A lexer that makes no progress throws `Infinite loop on byte: ` plus the stuck code unit when `silent` is false, and when `silent` is true logs it and returns the tokens collected so far.

D-99. `parse` does not sanitize. `[a](javascript:alert(1))` is an anchor with that href, and raw HTML blocks are copied through.

D-100. The block lexer’s indentation helpers accept a zero indent: a bullet, a thematic break, a fence, a heading, an HTML block, and a block quote at column 0 all match.

D-101. Heading text is inline-tokenized. A heading of depth greater than 6 is not a heading. Trailing hashes with a preceding space are removed; trailing hashes without that space are kept, except in pedantic mode.

D-102. Setext heading text is trimmed of trailing whitespace, and a setext line that looks like a task checkbox is not treated as a task item.

D-103. Pipe tables record alignment and cell tokens. A table immediately after a paragraph is its own token when the grammar allows it. A delimiter that is really a setext heading is not a table.

D-104. List tokens record `ordered`, `start`, `loose`, and items. Parenthesis markers (`1)`) are ordered lists. Task items set `task` and `checked`. A blank line between items makes the list loose. Items that are only separated by spaces, not a blank line, stay tight.

D-105. Inline lexing of escapes, inline HTML, links with titles, images with titles, reference links, strong, em, code spans, hard breaks, strikethrough, autolinks, and extended URLs produces the token shapes in section 3.7.

D-106. The parser renders space, hr, heading, code, table, blockquote, unordered list, ordered list, task list, loose list, html, paragraph, text, escape, inline html, link, image, strong, em, codespan, br, del, and inline text to the HTML in section 3.8.

D-107. `walkTokens`’s callback is invoked with the `Mdkit` instance as `this`, including when the walk is started from a `use` hook.

D-108. Calling `use` with empty objects, an empty tokenizer, an empty renderer, an empty `walkTokens`, and an empty `extensions` array does not throw, and `# test` still renders a heading.

D-109. A block tokenizer that returns no token for a thematic-break source lets `- - -` render as a paragraph when the override consumes the `hr` method and returns `undefined`.

D-110. HTML blocks that are interrupted by the end of a list item or a block quote keep the raw tag text, and a following block is not swallowed into the tag. `<DIV CLASS="foo">\n\n*Markdown*\n\n</DIV>` renders the emphasis inside the div.

D-111. The info string ```` ```; ```` produces `class="language-;"`. An unclosed fence at EOF still renders a code block.

D-112. GFM email autolinks do not swallow a trailing hyphen or underscore that is not part of the address. `a.b-c_d@a.b-` and `a.b-c_d@a.b_` are not links. `hello@mail+xyz.example` is not a link; `hello+xyz@mail.example` is.

D-113. `www.commonmark.org/he<lp` links only `www.commonmark.org/he` and escapes the `<`.

D-114. Multiple instances’ `use`, `setOptions`, and constructor options do not leak heading renderers into the shared `mdkit.parse('# header')`, which remains `<h1>header</h1>\n`.

D-115. The CLI config function and `use` object receive the shared compiler, so a config that sets `breaks` changes that process’s compile.

D-116. `--pedantic` selects the pedantic grammar for that compile. `--gfm` selects GFM when pedantic is false. `--no-gfm` disables tables, strikethrough, extended autolinks, and task checkboxes.

D-117. A code span adjacent to a tilde, a strikethrough that contains emphasis, and emphasis that contains a strikethrough follow the flanking rules: `~` is not emphasis punctuation when GFM is on, and emphasis markers inside a code span are literal.

D-118. List items may contain a pipe table when GFM is on. A table does not swallow a following block quote, fence, heading, list, or thematic break that the table grammar treats as an interrupter.

D-119. In non-pedantic mode, only a list that starts at 1, or a bullet list, can interrupt a paragraph, and the interrupting item must contain non-space text. An empty item and a list that starts at another number do not interrupt.

D-120. Pedantic lists use a fixed indent of 2 and treat `*`, `+`, and `-` as the same bullet. Non-pedantic lists compute the content indent from the first non-space character, capping a content indent above 4 at 1 so that indented code inside an item still works.

D-121. `Lexer.lex` and `new Lexer(options).lex` return deep-equal tokens for the same string, including the `links` object.

D-122. Inline HTML that opens an anchor sets “in link” so that a following link is not taken inside it, until the matching close tag. Opening `pre`, `code`, `kbd`, or `script` sets “in raw block” until the matching close tag.

D-123. A link destination in angle brackets must have a matching closing `>` that is not escaped, or the link is not recognized, except in pedantic mode where the older `(…)` rule is used.

D-124. More opening parentheses than closing ones in a non-angle destination rejects the link. Extra balanced parentheses after the destination are not part of the destination when a title is absent.

D-125. The shared entry’s `lexer` export is `Lexer.lex` and `parser` is `Parser.parse`.

D-126. `new Mdkit()` then `use` returns the instance, so registration can be chained. The shared `use` returns the `mdkit` function.

D-127. Renderer `space` and `def` contribute no characters, so two paragraphs separated by a `space` token serialize as `<p>…</p>\n<p>…</p>\n` with no extra blank tag.

D-128. A fenced code block’s language class uses only the first non-space run, so ` ```js extra ` produces `language-js`.

D-129. Image and link titles are escaped with the encode-unsafe rule, so a title containing `"` becomes `&quot;` inside the attribute.

D-130. Autolink hrefs are escaped with encode-all, so an autolink href containing `&` contains `&amp;` in the HTML attribute, not a bare `&`.

D-131. The CLI writes token JSON or HTML with UTF-8 and does not append a byte-order mark.

D-132. Stdin is decoded as UTF-8.

D-133. Home-directory expansion applies only to a leading `~` and uses the operating-system home directory.

D-134. Existence of a config or output file is a successful `access` of the resolved path. Any access error counts as “does not exist”.

D-135. `-o` creates or overwrites the file with the compiler output when `--no-clobber` is not set, using the Node file API’s default overwrite.

D-136. A thrown exception whose `code` is `ENOENT` uses the `mdkit: path: No such file or directory` form. Every other exception uses `message` only, so a config `Error` does not gain an `mdkit:` prefix.

D-137. `--help` and `--version` return before files are read, so they exit 0 even when later arguments would have been a missing file. Flags are parsed in order, and those two return as soon as they are seen.

D-138. The manual’s `--silent` flag sets the compiler `silent` option for that compile, which turns the failures in D-36 and D-38 into the HTML error string on stdout (plus the CLI’s extra newline) and status 0, instead of status 1.

D-139. `parse` with `async: true` still validates the input before scheduling work. A non-string rejects, or resolves to the silent HTML when `silent` is true.

D-140. Hooks’ `provideLexer` result is what tokenizes the preprocessed string. A lexer that returns a single heading token causes that heading’s HTML and ignores the original Markdown’s structure.

D-141. When both a custom lexer and `processAllTokens` are set, `processAllTokens` sees the custom lexer’s tokens.

D-142. `walkTokens` on a table walks header cells left to right, then each row left to right, and does not emit a token whose type is the cell itself.

D-143. `walkTokens` on a list walks each `list_item` and then that item’s children. Nested lists are children of the item.

D-144. A custom token with `childTokens: ['dt', 'dd']` walks those arrays, flattened, and does not require a `tokens` property.

D-145. Renderer extension output is concatenated in token order. A block extension that returns `<u>text</u>\n` for a top-level match produces that string between the surrounding paragraphs’ HTML.

D-146. If every renderer for an unknown token type returns `false`, the token adds no HTML and parsing continues with the next token.

D-147. Built-in block types handled by the parser are `space`, `hr`, `heading`, `code`, `table`, `blockquote`, `list`, `checkbox`, `html`, `def`, `paragraph`, and `text`. Built-in inline types are `escape`, `html`, `link`, `image`, `checkbox`, `strong`, `em`, `codespan`, `br`, `del`, and `text`.

D-148. `text` tokens that themselves have `tokens` render those children rather than the raw string, which is how a paragraph’s inline content is nested.

D-149. Emphasis inside a heading is rendered inside the heading tags: `# *a*` is `<h1><em>a</em></h1>\n`.

D-150. A thematic break of `***`, `---`, or `___`, including with spaces between the characters, renders `<hr>\n` when it is recognized as a break.

D-151. `1. a\n2. b` is one ordered list with no `start` attribute and two items. The second marker does not start a new list.

D-152. GFM strikethrough of a single tilde and a double tilde can nest or sit beside emphasis because tilde is excluded from the GFM emphasis punctuation class.

D-153. With `gfm: false`, `~~x~~` is a paragraph of those characters, not `<del>`.

D-154. With `gfm: false`, `www.example.com` is plain text. With `gfm: true` it is `<a href="http://www.example.com">www.example.com</a>`.

D-155. Angle-bracket autolinks are active in non-pedantic CommonMark mode, not only in GFM. `<http://ex.com>` is a link whose text and href are that URL.

D-156. Mail autolinks in angle brackets use a `mailto:` href and the address as the text.

D-157. The pedantic inline link grammar stops at the first `)` in the destination rather than tracking nested parentheses.

D-158. Pedantic ATX headings are recognized at the start of a line with no required space, so `#hi` is an `<h1>`.

D-159. A paragraph that is interrupted by a fence loses the fence from the paragraph, and the fence is the next block. This holds in non-pedantic mode only.

D-160. HTML equality used by the language fixtures ignores a trailing slash on void elements. The bytes mdkit emits are still the slash-free forms in section 3.8. Fixtures marked `renderExact` compare bytes, and the examples in D-66, D-68, D-80, D-82, D-83, D-84, D-85, and D-86 are byte contracts.

D-161. `~~ a ~~` is not strikethrough, because the interior would begin with a space, which fails the left-delimiter rule.

D-162. Task markers require at least one space and then a non-space after the bracket. `- [x]` with nothing after the marker is not a checkbox.

D-163. Checkbox `raw` includes the brackets and a trailing space. `checked` is false only for `[ ]`.

D-164. Link reference definitions may be indented up to three spaces in non-pedantic mode. Their title uses double quotes, single quotes, or parentheses.

D-165. The destination of a definition drops a surrounding `<…>` pair and decodes backslash escapes.

D-166. Soft line breaks inside a paragraph are newline characters in the HTML text, not `<br>`, unless `breaks` is on.

D-167. A backslash newline at the end of the source, with nothing after it, is not a hard break (`br` requires that the newline is not followed by the end).

D-168. Indented code cannot interrupt a paragraph; the indented lines are appended to the paragraph text.

D-169. A definition that follows a paragraph is its own token and is not rendered, and the paragraph does not include the definition source.

D-170. Block quotes, lists, and HTML blocks can follow a GFM table as separate blocks when they match the table row interrupters.

D-171. The same interrupters apply after a table that has no leading pipe on the header (the GFM “no pipe” form) when the delimiter line still matches.

D-172. `parse` of a string is synchronous unless `async` is true on the merged options. Callers can branch on `typeof result === 'string'` versus a Promise.

D-173. Async hook failures reject the parse Promise when `silent` is false, and resolve to the error HTML when `silent` is true.

D-174. `emStrongMask` is not awaited even in async mode; the other pass-through hooks are.

D-175. A `start` function that returns a negative index or `undefined` does not clip. The minimum non-negative index across `start` functions wins.

D-176. Extension tokenizers are stored with the newest at the front of the list, so the newest is attempted first.

D-177. Extension `start` functions are stored with the oldest at the front.

D-178. Rendering a list item calls the block parser on that item’s tokens, so a paragraph inside a loose item includes its trailing newline inside the `<li>`.

D-179. The text renderer’s `br` is an empty string and its `checkbox` is the checkbox `raw`, so alt text and similar plain-text walks do not insert `<br>` or `<input>`.

D-180. `defaults` and `mdkit.defaults` are the same object at load. `getDefaults()` is a different object.

D-181. The CLI imports the shared compiler once per process. A config that calls `use` affects the compile performed immediately afterwards in that process.

D-182. Positional arguments that look like flags because they start with `--` are not file names. They are either compiler options or ignored unknown long options.

D-183. A single-letter unknown short flag such as `-q` is not a compiler option. It is pushed as a positional path and then fails as a missing file if it is the selected input.

D-184. Output files are written as UTF-8 strings. HTML is not wrapped in a document, `<html>` element, or trailing comment.

D-185. `~~x~~` under the default options renders `<p><del>x</del></p>\n`.

D-186. A checked task under the default options renders `<ul>\n<li><input checked="" disabled="" type="checkbox"> a</li>\n</ul>\n` for `- [x] a`.

D-187. The default compile of `# Hi` is `<h1>Hi</h1>\n`.

D-188. The default compile of a pipe table with two body cells and no alignment markers includes `<thead>`, `<tbody>`, `<th>`, and `<td>`, and does not include `align=`.

D-189. `hooks.block` is `true` while `parse` runs a hook and `false` while `parseInline` runs a hook, including when the two calls are in flight together.

D-190. Providing an async lexer from an async `provideLexer`, or an async parser from an async `provideParser`, is awaited and its return value is the tokens or the HTML.

D-191. `processAllTokens` that pushes a heading token causes that heading to be rendered after the original document, and a `walkTokens` that edits the heading sees it.

D-192. The first registered pass-through hook runs last. For the pair of preprocess hooks in the hooks test, the rendered headings are `preprocess1`, then `preprocess2`, then the document, then `processAllTokens2`, then `processAllTokens1`, then `postprocess2`, then `postprocess1`.

D-193. A custom block tokenizer that returns a `code` token with extra text, combined with a code renderer that returns `false`, uses the built-in code HTML for that text, including the trailing newline inside `<code>`.

D-194. A heading renderer extension that returns HTML containing the heading text and the depth uses the built-in tokenizer’s `depth` and `text` when its tokenizer returns `false`.

D-195. `use` of two extensions in one call merges them the same way as two separate `use` calls: both inline or block names are active.

D-196. If the newest extension renderer for a duplicated name returns `false`, the older extension renderer’s HTML is used.

D-197. Link text that itself contains a link keeps the inner link only.

D-198. Images do not set the “a link was emitted” flag in a way that forbids a surrounding link; a link whose text contains an image is still a link. A link whose text contains a link is not.

D-199. The `links` object on a token list does not survive `JSON.stringify` of the array, so `--tokens` output has no `links` key.

D-200. Reference definitions are still available to inline tokenization of earlier paragraphs, because inline tokenization of queued text runs after the whole block list, including later definitions, has been scanned.

D-201. `codeBlockStyle: 'indented'` is set on indented code and is absent on fenced code. The default renderer does not read that field; HTML differs by the absence of a language class and by indent stripping rules.

D-202. Fenced code `lang` has backslash escapes decoded before the language word is taken.

D-203. A fence info string of only whitespace yields no language class.

D-204. List item `start` for bullets is the empty string, and the renderer treats only ordered lists as `<ol>`.

D-205. Ordered-list numbers are parsed in base 10. A marker of `08` has numeric value 8.

D-206. The maximum ordered-list marker length is 9 digits. A longer digit run is not a list marker.

D-207. Thematic breaks may use tabs between marker characters. They are recognized at an indent of up to three spaces.

D-208. ATX headings in non-pedantic mode allow up to three spaces of indent and require the `#` run to be followed by a space or the end of the line.

D-209. Setext underlines allow up to three spaces of indent before `=` or `-`.

D-210. Block quotes allow up to three spaces before `>`.

D-211. One newline after a block is appended to that block’s `raw` and is not a separate `space` token. A run of two or more blank lines is a `space` token.

D-212. `space` tokens render as the empty string, so they do not introduce extra tags.

D-213. The CLI does not print a banner, version, or prompt before the HTML.

D-214. The library does not read `~/.mdkit.json` by itself. Only the CLI does, and only when `--config` is absent.

D-215. The library does not open a network port and does not read the Markdown file system except when the caller passes a string it already read. The CLI is what reads files.

D-216. Package exports are the module root, the CLI path, and `package.json`. The root export is the ESM library.

D-217. `mdkit.parse('# test')` in the UMD global and in the CJS require both return HTML containing `<h1`.

D-218. A heading renderer installed on one instance does not change another instance created with a different heading renderer.

D-219. `setOptions` on one instance does not replace another instance’s renderer.

D-220. The tokenizer receives `this.lexer` so an override can call `this.lexer.inline(text, token.tokens)` and have that text inline-tokenized before `parse` returns.

D-221. Inline tokenization of queued strings happens after block structure is finished, so a tokenizer override that queues with `inline` still sees definitions collected from later blocks.

D-222. `new Lexer(options)` copies `options.tokenizer` or creates a tokenizer, and assigns `tokenizer.lexer` and `tokenizer.options`.

D-223. `new Parser(options)` uses `options.renderer` or a new renderer, and sets `renderer.parser` and `renderer.options` before rendering.

D-224. Direct `Parser.parse(tokens)` and `Lexer.lex(src)` are supported without constructing `Mdkit`.

D-225. HTML comments are raw HTML, not Markdown. They are not stripped.

D-226. A character reference that names a surrogate or a value above `0x10FFFF` or zero decodes to U+FFFD in ordinary text.

D-227. Decimal numeric references allow at most 7 digits and hex references at most 6 digits. Longer runs are not decoded as a single reference.

D-228. Inside a code span, `&` is always escaped, so `` `&amp;` `` renders `<code>&amp;amp;</code>`.

D-229. Ordinary text does not escape `&amp;`, so the paragraph `&amp;` renders `<p>&amp;</p>\n`.

D-230. The CLI option `--async` makes the compile use the async pipeline, and the CLI awaits it before writing.

D-231. `--no-breaks` forces `breaks` false for that call even if a config enabled breaks.

D-232. A config file that throws while being evaluated prints that error’s message and exits 1.

D-233. `man` is spawned with `stdio: 'inherit'`, so the CLI does not capture or rewrite the manual text when `man` starts successfully.

D-234. The fallback manual is read as UTF-8 from the Markdown manual shipped next to the executable.

D-235. GFM tables’ cells are inline-parsed, so `**bold**` inside a cell renders `<strong>bold</strong>` inside the `<td>` or `<th>`.

D-236. Escaped pipes in table cells become literal `|` characters and do not split cells.

D-237. Leading and trailing empty cells created by a leading or trailing pipe are removed. Interior empty cells are kept.

D-238. When a body row has fewer cells than the header, the missing cells are empty. Extra cells are dropped.

D-239. Alignment is decided per delimiter cell: right if the trimmed cell matches spaces, dashes, and a final colon; center if it has colons on both ends; left if it starts with a colon; otherwise `null`.

D-240. A table whose delimiter row’s column count differs from the header is refused and the source can still be a paragraph or a setext heading.

D-241. Nested block quotes and nested lists are tokens inside their parent, not flattened.

D-242. A loose list converts every item’s top-level `text` token into a `paragraph` before render, so each item’s text is wrapped in `<p>`.

D-243. Checkboxes are inserted after looseness is decided, so a loose task’s checkbox ends up inside the paragraph token.

D-244. Non-GFM compiles do not set `task: true`, so `[x]` remains in the item text.

D-245. The pedantic grammar deletes the GFM table rule and the fence rule by using the pedantic rule set, so `| a | b |` is not a table when `pedantic` is true.

D-246. `breaks: true` changes the hard-break pattern from “two or more spaces or a backslash” to “zero or more spaces or a backslash” before a newline, and only in the GFM inline grammar.

D-247. Emphasis delimiter scanning uses the masked source, so a mask that replaces the interior of `=…=` with letters prevents `*` inside that region from ending emphasis, while the rendered text still contains the original `*` characters that the underline extension did not consume.

D-248. The characters produced for an unclosed emphasis marker stay as literal `*` or `_` text.

D-249. Unicode punctuation, not only ASCII, counts as flanking punctuation for emphasis.

D-250. Pedantic emphasis allows `**"text"**` and `**(text)**` to be strong, which the non-pedantic left-delimiter rule treats more strictly.

D-251. A link title in double quotes, single quotes, or parentheses is stored without the surrounding quote characters, and backslash escapes inside it are decoded.

D-252. Autolink tokens carry `autolink: true` and a single text child equal to the matched text. Extended `www.` links prefix `http://` on the href only, not on the visible text.

D-253. `ftp://` is an extended autolink scheme. Other schemes are not extended autolinks unless they are angle-bracket autolinks.

D-254. Angle-bracket autolink schemes are an ASCII letter followed by 1–31 letters, digits, `+`, `.`, or `-`, then `:`.

D-255. The CLI’s `--string` value is not read from disk and is not trimmed. `# test` with the leading hash is a heading.

D-256. Compiling `# test` with the default options yields HTML that starts with `<h1` and contains `test`.

D-257. The shared parser used by the CLI is the same implementation as `mdkit.parse`, so `-s '# test'` and `mdkit.parse('# test')` produce the same HTML string. The CLI then appends `\n` on stdout only.

D-258. A renderer that throws during `parse` is reported through the error wrapper, including the report suffix, unless `silent` turns it into the error HTML.

D-259. `silent` does not hide extension-registration errors. Those throw from `use` before `parse`.

D-260. The language fixtures that set `gfm: false` in front matter are compiled with GFM off even though the default is on. The fixtures that set `pedantic: true` use the pedantic grammar. The fixtures that set both `breaks` and `gfm` enable hard breaks on every newline.

D-261. Those language fixtures compare through an HTML parser that treats a slash on a void element as insignificant, except fixtures whose front matter sets `renderExact`, which require byte-identical HTML.

D-262. `shouldFail` on the disallowed-raw-HTML fixture means the compiler’s HTML must **not** equal the filtered GFM reference. mdkit’s output keeps the raw tags.

D-263. No fixture requires the compiler to insert `id` attributes on headings, to mangle email addresses, or to convert quotes to smart punctuation. Those features are absent.

D-264. The block-tag list that opens a CommonMark HTML block includes `address`, `article`, `aside`, `base`, `basefont`, `blockquote`, `body`, `caption`, `center`, `col`, `colgroup`, `dd`, `details`, `dialog`, `dir`, `div`, `dl`, `dt`, `fieldset`, `figcaption`, `figure`, `footer`, `form`, `frame`, `frameset`, `h1`–`h6`, `head`, `header`, `hr`, `html`, `iframe`, `legend`, `li`, `link`, `main`, `menu`, `menuitem`, `meta`, `nav`, `noframes`, `ol`, `optgroup`, `option`, `p`, `param`, `search`, `section`, `summary`, `table`, `tbody`, `td`, `tfoot`, `th`, `thead`, `title`, `tr`, `track`, and `ul`.

D-265. Script, pre, style, and textarea HTML blocks swallow source through their closing tag, or through EOF, and are marked `pre: true` when the opening tag name is `pre`, `script`, or `style`.

D-266. A paragraph interrupter for HTML is an open or close tag of that block-tag list, or `<script`, `<pre`, `<style`, `<textarea`, or `<!--`, at up to three spaces of indent.

D-267. Inside a block quote, a list marker of any number, including an empty item, interrupts the quote’s paragraph. At the top level, only a non-empty bullet or a list starting at 1 interrupts.

D-268. The lexer refuses to loop forever on a stuck byte and surfaces D-98 instead.

D-269. `encodeURI` leaves `&` unescaped, so a non-autolink href `http://ex.com?a=1&b=2` is HTML-escaped to `http://ex.com?a=1&amp;b=2` because the `&` does not start an entity.

D-270. A non-autolink href that already contains `&amp;` or `&lt;` keeps that entity text in the attribute.

D-271. Image `src` is passed through `cleanUrl` and then encode-unsafe escaping, so `![a](http://ex.com?a=1&b=2)` has `src="http://ex.com?a=1&amp;b=2"`.

D-272. Alt text of an image whose marker text contains `&` is encode-unsafe escaped.

D-273. The CLI token mode and the HTML mode share the same option object, so `--no-gfm --tokens` lexes with the CommonMark grammar.

D-274. Pretty-printed token JSON uses two-space indentation and a trailing newline on the last `]` before the CLI adds one more newline on stdout.

D-275. `list.loose` is true if any item ends with a blank line before the next item, or if any item contains a double-newline spacer token.

D-276. The final list item’s `raw` and `text` are trimmed of trailing whitespace, and the list’s `raw` is trimmed the same way, so a trailing newline after the list is not part of the list token.

D-277. A list match that produces zero items is rejected and the source is not consumed as a list.

D-278. Horizontal-rule-shaped list markers (`- - -` when it matches the hr rule) end list parsing rather than becoming an item.

D-279. Following lines of a list item end when the next line, at the item’s indent, is a fence, heading, HTML block, block quote, bullet, or thematic break.

D-280. A line that is not indented far enough ends the item if the item was already on a blank line; otherwise it can continue a paragraph unless the previous line was itself an indented code block, fence, heading, or thematic break.

D-281. Pedantic item continuation rewrites 1–4 spaces that precede a further indent into two spaces, instead of expanding tabs the CommonMark way.

D-282. Non-pedantic item lines expand leading tabs to spaces using column arithmetic before the indent is measured. Tabs that remain after the indent stay in the content, including inside code spans and fences.

D-283. Code-span text inside a list item keeps a tab that was not part of the list’s structural indent. `- \`foo\tbar\`` renders `<ul>\n<li><code>foo\tbar</code></li>\n</ul>\n`.

D-284. A tab used as the indent of fence content inside a list item contributes the spaces required by the column rule, so `- \`\`\`\n\tfoo\tbar\n  \`\`\`` renders the code text as two spaces, `foo`, a tab, `bar`, and a newline.

D-285. An ordered list item whose fence contains a tab behaves like the bullet case: `1. \`\`\`\n   foo\tbar\n   \`\`\`` renders `<ol>\n<li><pre><code>foo\tbar\n</code></pre>\n</li>\n</ol>\n`.

D-286. A tilde fence inside a list keeps repeated tabs in the code text.

D-287. A list marker and the item text may be separated by a tab: `-\t\`foo\tbar\`` renders the same code span as a space-separated marker.

D-288. CommonMark mode and GFM mode produce the same HTML for those list-and-tab fixtures.

D-289. A fenced code block that is indented under a list item strips only the fence’s own indent, so a list item whose body is a four-space-indented fence under a one-space marker still shows the code without the fence indent. The fixture `code_compensation_indent` renders the list item’s code as `const x = 5;\nconst y = x + 5;\n` with no leading tabs.

D-290. Both fenced and indented code blocks include a trailing newline inside `<code>` when they have text, and the sentence after them is a paragraph.

D-291. Four spaces of indent after a paragraph line are not enough to end the paragraph, so `Foo\n    bar` is one paragraph whose HTML preserves the four spaces.

D-292. Three spaces before a thematic break that is otherwise indented as code do not make a code block when the break rule matches first at that indent; a four-space indent before `***` stays inside the paragraph in the CommonMark example `Foo\n    ***`.

D-293. The character `'` is escaped as `&#39;` wherever encode-all or encode-unsafe escaping runs, including in ordinary text that contains an apostrophe produced by a backslash escape of `'`.

D-294. Backslash escapes of ASCII punctuation emit that punctuation and then the normal HTML escape, so `\*` is `*`, `\&` is `&amp;`, and `\"` is `&quot;`.

D-295. A backslash that does not precede CommonMark punctuation stays a backslash.

D-296. Inline code uses the longest run of backticks that can close, and a shorter run inside does not close it. An unclosed run is not a code span.

D-297. Strong emphasis uses a delimiter run of length at least 2 when the flanking rules pair them as strong; a run of length 1 is emphasis. The smaller matching length wins when both are possible, following CommonMark.

D-298. `_` emphasis does not start or end in the middle of a word of letters or numbers. `*` can.

D-299. GFM extended autolinks are not recognized when `gfm` is false because the `url` rule is disabled in the normal inline grammar.

D-300. Strikethrough is disabled in the normal and pedantic inline grammars (`del` does not match), so tildes are ordinary text there.

D-301. The CLI exits 0 when stdin is empty and no paths are given, and stdout is a single newline.

D-302. Compiler options passed on the CLI that name `renderer`, `tokenizer`, `hooks`, `extensions`, or `walkTokens` are strings or null, not objects. A string renderer will fail when the parser tries to call it, and that failure is reported with status 1 and the error message.

D-303. Boolean CLI flags do not consume the following argument. `--silent next.md` sets silent and then reads `next.md` as the input file if it is positional.

D-304. `-o` and `-i` and `-s` and `-c` do consume the following argument.

D-305. The order of flags is significant only because `-h` and `-v` return immediately and because later copies of the same compiler option overwrite earlier ones in the option object.

D-306. `Mdkit` constructor arguments are `use`d in order, so a later argument’s scalar options overwrite an earlier argument’s, and `async: true` in any of them sticks.

D-307. Instance `defaults` starts as a fresh default object, not a reference shared with `getDefaults()`’s return value or with another instance.

D-308. The module-level `defaults` export starts equal to `mdkit.defaults` and is **not** the object `new Mdkit()` stored, until `use` or `setOptions` on the shared function assigns the instance object into the export.

D-309. After that assignment, `mdkit.defaults` and the exported `defaults` stay identical, and `parse` reads that object when the call does not override a key.

D-310. `walkTokens` concatenates callback results, including arrays of promises returned by a callback, and async parse waits for every promise in that list.

D-311. Sync `walkTokens` does not wait. A promise returned from a sync walk is not awaited, and the HTML may be produced before it settles.

D-312. `preprocess` may return a non-string in sync mode; the lexer then sees that value. Returning a non-string is outside the supported contract and surfaces as a lexer or type error through D-258. Supported preprocessors return a string.

D-313. `postprocess` may return any string, and that string is the compile result, including a string that is not HTML.

D-314. The default `preprocess`, `postprocess`, `processAllTokens`, and `emStrongMask` return their argument unchanged.

D-315. Link and image rendering of a `null` title omits the `title` attribute. An empty string title also omits it, because the renderer tests truthiness.

D-316. Heading depth is the number of `#` characters, an integer from 1 to 6, written as `<h1>` through `<h6>`.

D-317. Setext `=` is depth 1 and setext `-` is depth 2.

D-318. The language class prefix is exactly `language-` with no extra prefix option.

D-319. There is no `headerIds`, `headerPrefix`, `langPrefix`, `mangle`, `sanitize`, `sanitizer`, `smartypants`, `xhtml`, `baseUrl`, `highlight`, or `smartLists` behavior. Those keys are not read by the lexer, parser, or renderer.

D-320. The UMD bundle and the ESM bundle expose the same compile function. The UMD global name is `mdkit`.

D-321. Source maps may be shipped beside the bundles. They are not part of runtime behavior.

D-322. The formatted `man` page is optional. Its absence does not change compile results. `--help` then shows `man`’s own missing-page diagnostic on stderr and still exits 0.

D-323. `parse` trims nothing from the caller’s string except the carriage-return normalization inside the lexer.

D-324. A final newline in the Markdown is not required. `# Hi` without a trailing newline still renders `<h1>Hi</h1>\n`.

D-325. Two paragraphs `a\n\nb` render `<p>a</p>\n<p>b</p>\n`.

D-326. A block quote of `> a\n> b` renders `<blockquote>\n<p>a\nb</p>\n</blockquote>\n`.

D-327. Inline HTML `<pre>&#65;</pre>` with no trailing newline renders exactly `<pre>&#65;</pre>` with the reference still encoded, because the block is raw HTML and numeric decoding does not apply inside it.

D-328. `***` renders `<hr>\n` in non-pedantic mode.

D-329. `` `a\`b` `` is not one code span of `a\b`. The first closing backtick ends the span, so the HTML is `<p><code>a\</code>b`</p>\n` (the backslash is inside the code span and the last backtick is text).

D-330. GFM autolink backpedal removes trailing characters from the class of punctuation listed in the `_backpedal` rule until the match is stable, so a URL ending in `).` loses the period when it is the trailing punctuation of the sentence `Visit www.commonmark.org.`.

D-331. `(www.example.com)` includes the URL and excludes the surrounding parentheses when the parentheses are not balanced inside the URL.

D-332. A `www.` autolink must contain a dot-separated domain after `www.`. The grammar requires at least one domain label after the prefix.

D-333. Email autolinks allow `+`, `_`, `.`, and `-` in the local part as the GFM pattern states, and require a dot in the domain. A trailing `-` or `_` on the domain is not included.

D-334. `xmpp:` autolinks allow one `/resource` segment of ASCII letters, digits, `@`, and `.`, and stop before a second slash.

D-335. Task-list checkboxes are not recognized inside a setext heading’s text as list tasks; the heading stays a heading.

D-336. A setext heading separated from following text by a blank line does not absorb that text into the heading.

D-337. Multiple spaces inside a link label collapse to one space for matching, so a definition label and a reference label with different internal spacing still match.

D-338. Labels are trimmed of leading and trailing whitespace before they are stored and before they are looked up.

D-339. The `links` map is a null-prototype object, so a label of `toString` or `constructor` is an own property match, not an inherited method.

D-340. When `silent` is false, unknown-token and infinite-loop errors thrown from a direct `Parser.parse` or `Lexer.lex` do **not** receive the report suffix unless they pass through `Mdkit.parse`’s wrapper. `Mdkit.parse` adds the suffix.

D-341. The suffix is appended by mutating `error.message`, so the thrown Error’s message contains both the original sentence and the suffix.

D-342. HTML-escaping of the silent error message uses encode-all, so `<` in a message cannot break out of the `<pre>`.

D-343. The silent error HTML does not end with a newline.

D-344. CLI stdout HTML always ends with a newline even when the compiler string already ended with one, because the CLI concatenates one more `\n`. A compiler string `<h1>test</h1>\n` is written as `<h1>test</h1>\n\n` only if the compiler included a newline and the CLI added another. The heading renderer includes one newline, and the CLI adds another, so the bytes are `<h1>test</h1>\n` plus the CLI newline, i.e. the heading line and a blank line.

D-345. The unit test for `-s '# test'` compares stdout to `<h1>test</h1>` using HTML equality, which accepts the extra CLI newline. The bytes on stdout are the compiler HTML plus `\n`.

D-346. File output does not receive that extra newline. `-s hello -o out.html` writes exactly `<p>hello</p>\n`.

D-347. Overwriting an existing output without `-n` replaces the file contents with the new compiler output.

D-348. `-n` checks existence before writing. A path that does not exist is created.

D-349. Config `require` is attempted before dynamic import, so a JSON file loads as a CommonJS JSON module.

D-350. If the loaded config object’s `default` field is present, including a JSON object that happens to have a `default` key, that field is used instead of the object.

D-351. The function form of a config is invoked with one argument, the shared `mdkit` function, and its return value is ignored.

D-352. The object form is passed as the only argument to `mdkit.use`.

D-353. `use` of a plain `{ breaks: true }` sets breaks on the shared instance before `parse` is called with the CLI option object.

D-354. Camel-casing of CLI options only rewrites a hyphen that sits between two word characters, once per such pair. `--no-` is stripped before camel-casing, so `--no-gfm` looks up `gfm`.

D-355. `--no-clobber` is handled by the specific `-n` case, not by the generic `--no-` default lookup. There is no `clobber` default key.

D-356. `--tokens` may be combined with compiler options and with `-o`. The file then receives the JSON text without an extra CLI newline.

D-357. `--tokens` uses the block lexer, not the inline lexer, so a heading is a `heading` token rather than text.

D-358. The lexer records `escaped: false` on ordinary text tokens that are not inside a raw HTML span.

D-359. Text inside a raw HTML span is `escaped: true` and the renderer returns it unchanged.

D-360. `inRawBlock` is cleared if a link token is discarded because it contained another link, so the rescan does not inherit that flag.

D-361. A successful link sets `linkEmitted` so a parent link under construction can detect it.

D-362. Images do not set `linkEmitted`.

D-363. The outer link scan saves and restores `inLink`, `inRawBlock`, and `linkEmitted`.

D-364. Code fences of backticks cannot contain a longer run of backticks than the opener in the info string; the opener must be followed by a non-backtick rest-of-line. Tilde fences do not have that restriction.

D-365. The closing fence may be longer than the opening fence and may be indented up to three spaces, and it may have trailing spaces.

D-366. An unclosed fence consumes the rest of the source, including a missing final newline.

D-367. Indent stripping of fence content uses the exact whitespace prefix of the opening fence line, not a tab-expanded width. A tab and spaces are different characters for this comparison.

D-368. Indented code removes one level of up to four spaces or one tab from each line.

D-369. Pedantic indented code does not run the trailing-blank-line trimmer; non-pedantic indented code does.

D-370. The trimmer keeps the original string when there are fewer than two trailing blank lines to remove, so one trailing blank line remains.

D-371. When more than one trailing blank line is present, they are removed through the last non-blank line, and the joiner does not add a new trailing newline of its own beyond what the remaining lines contain.

D-372. The renderer adds a newline after non-empty code text if `text` does not already end with `\n`.

D-373. Empty code text does not gain that newline.

D-374. Language class text is escaped, so `<` in an info string cannot open a tag inside the attribute.

D-375. The info-string word is matched by `^\S*`, so it stops at the first space and does not include a tab that is later. A tab is whitespace and ends the word.

D-376. Table header cells are `header: true`. Body cells are `header: false`. Both carry the column’s align.

D-377. The header row is always rendered in `<thead>` inside one `<tr>`, even when body rows exist.

D-378. Body rows are rendered in order, each as its own `<tr>`.

D-379. A cell’s inline parse is not wrapped in `<p>`.

D-380. `align` of `null` omits the attribute rather than writing `align="null"`.

D-381. List HTML does not include a `type` attribute or a class. Task lists are ordinary `<ul>` or `<ol>` plus checkbox inputs.

D-382. The checkbox is disabled and is not given a `name` or `value`. The checked state is the attribute `checked=""` when checked.

D-383. There is a single space after the checkbox tag and before the item text, because the checkbox HTML includes that space and the item text no longer includes the marker.

D-384. Nested task lists put the nested `<ul>` or `<ol>` inside the parent `<li>` after the parent’s text.

D-385. A paragraph inside a block quote is indented in the source but the `>` markers are not part of the paragraph text.

D-386. Lazy continuation lines in a block quote are part of the quote’s paragraph.

D-387. A block quote can contain a list, a fence, a heading, or another quote.

D-388. Setext headings inside a block quote are suppressed when the marker-stripping pass indents the underline by four spaces, so the underline stays text unless it is a real setext underline of the quote’s paragraph.

D-389. Continuation lines after a nested block quote are reparsed with one quote marker stripped, so a repeated `>` does not create an extra nesting level beyond the markers that are actually present.

D-390. Continuation lines that belong to a list inside a quote are given back to the list tokenizer.

D-391. A code block at the end of a quote stops the quote from absorbing following continuation lines.

D-392. HTML block `raw` has trailing blank lines trimmed by the same trimmer as indented code, but the text that is emitted is that trimmed raw string, not a re-serialized DOM.

D-393. Inline HTML tags are tokenized as `html` tokens with `block: false` and are emitted raw, so `<em>` in a paragraph becomes a raw `<em>` rather than an emphasis token.

D-394. A raw `<em>` tag and a Markdown `*em*` are different: the tag is copied, the markers become `<em>` elements produced by the renderer.

D-395. Comments, processing instructions, declarations, and CDATA sections are inline HTML when they appear inside a paragraph, and block HTML when they match the block rule at the start of a line.

D-396. The inline tag grammar accepts tag names of a letter followed by letters, digits, or hyphens, and attributes in the CommonMark shapes (unquoted, single-quoted, double-quoted).

D-397. Self-closing tags and closing tags are raw HTML.

D-398. A `<` that does not start a tag, autolink, or comment is text, and it is escaped to `&lt;`.

D-399. `>` in text is escaped to `&gt;`.

D-400. `"` in text is escaped to `&quot;`.

D-401. The pedantic HTML block rule requires a blank line or EOF after a tag, or a matching close tag, and it refuses to treat the inline-tag name list as a block.

D-402. Pedantic paragraphs are not ended by a list marker, so a list-like line can remain inside the paragraph when pedantic mode is on.

D-403. Pedantic mode still recognizes thematic breaks, ATX headings, setext headings, indented code, block quotes, and lists, using the pedantic patterns.

D-404. The normal block grammar’s table rule never matches, so tables exist only in the GFM block grammar.

D-405. Selecting GFM because `gfm` is true and `pedantic` is false uses `lheading` rules that treat a table delimiter as able to interrupt a setext heading’s paragraph.

D-406. CommonMark setext headings do not treat a table delimiter specially, because the normal grammar has no tables. A line of dashes is a setext heading when it meets the setext rule.

D-407. Four-space-indented content inside a list is a code block when the item indent says it is, and the code text has the structural indent removed.

D-408. Trailing blank lines of indented code are represented in the non-pedantic token the way the trimmer leaves them, and the lexer tests require those tokens to deep-equal the expected `raw` and `text`.

D-409. Fenced code tokens include the fences in `raw` and exclude them from `text`.

D-410. A fence language token stores the trimmed, unescaped info string, while the HTML class uses only the first word of that string.

D-411. Headings store both `text` (plain, with inline markers still in the string) and `tokens` (the inline token list). The renderer uses `tokens`, not `text`.

D-412. A custom renderer may read `token.text` instead of parsing tokens. The built-in heading renderer does not.

D-413. Paragraphs store `text` without a single trailing newline that the match included, while `raw` keeps the matched source.

D-414. Thematic-break `raw` has trailing newlines removed.

D-415. Heading `raw` has trailing newlines removed.

D-416. Definition `raw` has trailing newlines removed.

D-417. Table `raw` has trailing newlines removed.

D-418. Block quote `raw` is the joined quote lines without a trailing newline past the content the quote consumed.

D-419. `links[tag].href` and `title` are the strings later copied onto link tokens that resolve that label.

D-420. An unresolved reference is not a link token. The brackets remain text.

D-421. A collapsed reference `[text][]` uses `text` as the label.

D-422. A shortcut reference `[text]` uses `text` as the label when it is not followed by `[` or `(`.

D-423. Images use the same reference forms with a leading `!`.

D-424. The `!` is not part of the alt-text label. Alt text is the inside of the brackets.

D-425. Alt text is inline-tokenized and then flattened by the text renderer, so `!*b*` inside an image becomes an alt of `*b*` or the text content of the emphasis, not an `<em>` tag. The text renderer returns the emphasis token’s `text` field, which still contains the inner characters without tags.

D-426. Link text that is not an autolink is inline-rendered, so `[`*b*`](/u)` contains `<em>` inside the anchor.

D-427. Autolink text is not inline-rendered. It is encode-all escaped, so emphasis markers are not interpreted inside an autolink because the autolink token’s children are a single text node produced by the autolink tokenizer, not a second inline pass of the renderer.

D-428. The visible autolink text does not include the angle brackets.

D-429. The href of a scheme autolink is the interior, not the brackets. The href of an email autolink is `mailto:` plus the interior.

D-430. Extended email autolinks do not include a `mailto:` prefix that was not in the source; the tokenizer adds `mailto:` itself when the match is an address without a scheme.

D-431. When the source already starts with `mailto:` or `xmpp:`, that scheme is the href.

D-432. `www.` links do not keep a user-supplied scheme. The href is always `http://` plus the matched text.

D-433. Comparison of `www.` is case-sensitive at the prefix: the pattern is the lowercase letters `www.`. `HTTP://` is matched by the case-insensitive scheme pattern, not by the `www.` rule.

D-434. Scheme letters in extended autolinks are case-insensitive for `http`, `https`, and `ftp` only.

D-435. A newline ends an extended autolink. Autolinks do not span lines.

D-436. Soft breaks therefore cannot occur inside an extended autolink; the link ends at the line break and the next line is text or a new link.

D-437. Hard breaks are recognized before ordinary text, so two spaces before a newline become `<br>` rather than remaining spaces plus a newline.

D-438. The inline try order recognizes escapes, tags, links, reflinks, emphasis, code spans, breaks, strikethrough, autolinks, and URLs before plain text. The first match at the current position wins.

D-439. Plain text is merged into the previous text token when two text matches are adjacent, so the token list does not contain one text token per character.

D-440. A `br` token is not merged into neighboring text.

D-441. Emphasis tokens contain the inner tokens, not a pre-rendered HTML string. The renderer walks them.

D-442. Strikethrough tokens similarly contain inner tokens, so `~~*a*~~` can contain an `em` token.

D-443. Code span tokens do not contain child tokens. Their `text` is already processed (newlines to spaces, optional edge-space trim).

D-444. Escape tokens do not contain child tokens. `text` is one character.

D-445. The escape regex covers the punctuation `!"#$%&'()*+,-./:;<=>?@[\]^_` + `` ` `` + `{|}~`.

D-446. A newline after a backslash is handled by the break rule, not by the escape rule, when the break rule matches.

D-447. Spaces before a hard break are consumed as part of the `br` token’s `raw` and are not emitted.

D-448. The `<br>` tag has no trailing newline of its own. The following text continues immediately, and a paragraph’s final `</p>\n` still follows.

D-449. Multiple hard breaks in one paragraph produce multiple `<br>` tags inside one `<p>`.

D-450. `breaks: true` makes a newline with zero preceding spaces a hard break, so every line in the paragraph is joined with `<br>` instead of `\n`.

D-451. `breaks: true` does not turn a blank line into a `<br>`. A blank line still ends the paragraph, because block parsing splits paragraphs before inline breaks are considered.

D-452. Therefore `a\n\nb` with `breaks: true` is still two paragraphs, while `a\nb` is one paragraph with a `<br>`.

D-453. The CLI config fixture `line1\nline2` with `breaks: true` is one paragraph with a break, confirming D-452’s single-newline case.

D-454. GFM is on by default, so a caller who does not pass options gets strikethrough, tables, task lists, and extended autolinks.

D-455. Passing `{ gfm: false }` on one call does not change the instance default. The next call without options is GFM again.

D-456. Passing `{ pedantic: true }` on one call uses the pedantic grammar for that call only.

D-457. `pedantic: true` together with `gfm: true` still selects pedantic rules, not GFM rules.

D-458. `pedantic: true` together with `breaks: true` does not enable the breaks inline grammar.

D-459. The instance stores the merged defaults, so `instance.defaults.gfm` after `setOptions({ gfm: false })` is false.

D-460. `setOptions` returns the instance, allowing a second `setOptions` to merge again.

D-461. A second `setOptions` does not reset unspecified keys. `{ gfm: false }` leaves `breaks` at its previous value.

D-462. `use` also shallow-merges, so `use({ breaks: true })` leaves `gfm` true unless the object says otherwise.

D-463. `use`’s async sticky bit is computed before the merge, from the previous defaults and the new object. A new object that omits `async` does not turn async off.

D-464. A new object with `async: true` turns async on even if the previous value was false.

D-465. Several objects in one `use` call are applied left to right, and async sticks across them. `use({ async: true }, { async: false })` leaves async true.

D-466. `new Mdkit({ async: true }, { async: false })` likewise leaves async true.

D-467. Registration errors abort `use` at the bad extension. Earlier extensions in the same call have already been merged.

D-468. A tokenizer extension that returns a token without a `raw` string throws when the lexer reads `token.raw.length`, and that error is wrapped by `parse` as in D-258.

D-469. A tokenizer extension that returns a token whose `raw` is longer than the remaining source can skip past the end; the supported contract is that `raw` is a prefix of the remaining source.

D-470. Renderer extensions receive the token object the tokenizer returned, including custom fields.

D-471. The renderer extension’s `this.parser.parseInline` and `this.parser.parse` compile child tokens with the same options.

D-472. Custom tokens that are not in the built-in list need a renderer. Without one they hit the unknown-type error, or add nothing if an extension renderer returns `false`.

D-473. Block and inline extension renderers are stored on the same `renderers` map, keyed by `name`. A block token and an inline token with the same `name` share that renderer.

D-474. `childTokens` is also keyed by `name` and replaces any previous list for that name.

D-475. The walk of `childTokens` flattens one level of nested arrays (`flat` without a depth argument flattens all levels in the language used here: `Array.prototype.flat` with no argument flattens one level). Nested token arrays one level down are walked. Deeper nesting stays as elements only if they are tokens; a deeper array would be passed to the walker as a non-token.

D-476. The walker ignores a missing child property by throwing when it tries to read `.flat` on `undefined`. Extensions that declare `childTokens` must put arrays on those properties. The supported contract is that each named property is an array.

D-477. Tokens without `childTokens` and without `tokens` are leaves.

D-478. `checkbox` tokens are leaves. They appear as children of list items or of the item’s paragraph.

D-479. `br`, `codespan`, `escape`, `hr`, `space`, and `html` block tokens are leaves unless an extension added `tokens`.

D-480. The timing constraint is one second of process time per fixture when `async` is not set. A compile that takes a full second or more fails that check. The implementation finishes the published timing fixtures faster than that.

D-481. Those timing fixtures are compiled with `silent: false` as the suite default, then the runner also forces `silent: true` only when `silent` is undefined. Because the suite passes `silent: false`, silent stays false. The fixtures still complete and match their HTML.

D-482. Language fixtures other than the timing suite leave `silent` undefined, and the runner sets `silent: true` before parsing. That does not change successful HTML. It would turn a throw into error HTML, which would fail the HTML comparison. Successful fixtures therefore do not throw.

D-483. Front matter on a fixture is merged over the suite’s default options. `gfm: false` in front matter overrides the GFM suite and the “new” suite’s default of `gfm: true`.

D-484. Fixture Markdown is the file body after front matter is removed. The HTML file is the expected HTML, including its trailing newline when the file has one.

D-485. The “new” suite has no default option object, so unspecified fixtures use instance defaults: GFM on, pedantic off, breaks off.

D-486. The CommonMark suite forces `gfm: false` and `pedantic: false`.

D-487. The GFM suite forces `gfm: true` and `pedantic: false`, and it includes both the CommonMark example file and the GFM extension file.

D-488. The original suite forces `gfm: false` and `pedantic: true`.

D-489. There are 652 CommonMark 0.31.2 examples, 28 GFM 0.29 extension examples (8 tables, 2 task-list examples, 3 strikethrough examples, 14 autolink examples, 1 disallowed-raw-HTML example), 183 additional Markdown/HTML pairs, 22 original pairs, and the timing files under the timing directory.

D-490. The disallowed-raw-HTML example is the only GFM extension example that must not match its reference HTML.

D-491. Table example 205, a header and delimiter with no body, renders `<table>\n<thead>\n<tr>\n<th>abc</th>\n<th>def</th>\n</tr>\n</thead>\n</table>\n` up to the void-tag and whitespace equivalence the fixture allows. The byte form has no `<tbody>`.

D-492. Task example 279’s byte form uses `<input disabled="" type="checkbox">` and `<input checked="" disabled="" type="checkbox">` with the trailing space before `foo` and `bar`.

D-493. Strikethrough example 491’s visible result is `<del>Hi</del>` and `<del>there</del>` inside one paragraph.

D-494. Autolink example 622’s href is `http://www.commonmark.org` and the text is `www.commonmark.org`.

D-495. Autolink example 630’s href is `mailto:foo@bar.baz` and the text is `foo@bar.baz`.

D-496. A pipe in a code span inside a table cell does not split the row. The cell text contains the code span and the pipe.

D-497. Table cells trim leading and trailing whitespace, so padding spaces around cell text do not appear in the HTML.

D-498. A cell that is only whitespace becomes an empty cell.

D-499. Inline Markdown in a header cell is rendered inside `<th>`, not escaped as a whole string.

D-500. The lexer’s `state.top` is true at the start of a document and false while tokenizing the inside of a list item, which changes whether a paragraph rule or a text rule is used for the item’s first line.

D-501. Because list-item interiors are tokenized with `top` false, the first run of text is a `text` token rather than a `paragraph`, unless looseness later retypes it.

D-502. Block quotes are tokenized with `top` forced true for their interior, so the first text run inside a quote is a `paragraph`.

D-503. After a block quote returns, the previous `top` flag is restored.

D-504. List items are block-tokenized after the full item text is known and trimmed, not incrementally in a way that would leave the last item’s trailing newline in `text`.

D-505. The inline queue is cleared after it is flushed, so a second `lex` on the same lexer does not replay the first document’s inline work. A fresh `Lexer.lex` uses a new lexer.

D-506. Reusing one lexer instance for two `lex` calls appends to `this.tokens` because `lex` does not reset the token array. The supported way to lex two documents is `Lexer.lex` or a new instance per document. `Mdkit.lexer` uses `Lexer.lex`, so it does not append across calls.

D-507. `Lexer.lex` returns the lexer’s token array, which is the same object that was filled, including `links`.

D-508. Mutating a token after `lexer` returns and before `parser` is called changes the HTML, because the parser reads the objects it is given.

D-509. The parser does not clone tokens.

D-510. The parser concatenates renderer strings with `+=` in token order and does not insert separators of its own.

D-511. A renderer that returns `undefined` or `null` contributes nothing visible for that token when the extension wrapper coerces nullish to `''`, and a built-in renderer is not expected to return nullish. Built-in methods return strings.

D-512. Returning `false` from a built-in method that was wrapped by `use` retries the previous method. Returning `false` from a built-in method that was not wrapped is concatenated by the parser only when it is an extension renderer; the stock methods do not return `false`.

D-513. The stock `html` renderer returns the raw text, which may be the empty string, and that string is concatenated as-is.

D-514. The stock `code` renderer always ends with `</code></pre>\n`.

D-515. The stock `blockquote` renderer always ends with `</blockquote>\n` and always puts a newline after `<blockquote>`.

D-516. The stock `list` renderer always ends with `</ul>\n` or `</ol>\n`.

D-517. The stock `listitem` renderer always ends with `</li>\n`.

D-518. The stock `paragraph` renderer always ends with `</p>\n`.

D-519. The stock `heading` renderer always ends with `</hN>\n`.

D-520. The stock `hr` renderer is exactly `<hr>\n`.

D-521. The stock `table` renderer always starts with `<table>\n<thead>\n` and always ends with `</table>\n`.

D-522. The stock `tablerow` renderer wraps cells in `<tr>\n` … `</tr>\n`.

D-523. The stock `tablecell` renderer ends the cell with a newline.

D-524. Strong, em, del, codespan, link, image, and br do not add a trailing newline.

D-525. A paragraph that contains only inline markup therefore ends with one newline after `</p>`, and the inline markup has no extra newlines around the inner tags.

D-526. `**b**` renders `<p><strong>b</strong></p>\n`.

D-527. `*b*` renders `<p><em>b</em></p>\n`.

D-528. `_b_` and `__b__` are emphasis and strong under the default grammar, same as `*` and `**`, when they are flanked as words.

D-529. `` `b` `` renders `<p><code>b</code></p>\n`.

D-530. A link `[a](http://ex.com "t")` renders `<p><a href="http://ex.com" title="t">a</a></p>\n`.

D-531. An image `![a](http://ex.com)` renders `<p><img src="http://ex.com" alt="a"></p>\n`.

D-532. Angle-bracket destinations drop the brackets in the href: `[a](<http://ex.com>)` has `href="http://ex.com"`.

D-533. The CLI and the library accept UTF-8 Markdown, including non-ASCII link text and heading text, and emit UTF-8 HTML. Non-ASCII letters are not escaped.

D-534. U+FFFD produced by a bad numeric reference is emitted as that character, not as an entity.

D-535. A numeric reference is decoded in the text node before HTML escaping, so `&#60;` becomes `<` and is then escaped to `&lt;`.

D-536. `&#38;` becomes `&` and is then subject to encode-unsafe rules. Because the decoded character is a bare ampersand, it is escaped back to `&amp;`.

D-537. References are not decoded inside code spans, so `&#60;` inside backticks is escaped as text `&amp;#60;`, not turned into `&lt;` via a decode.

D-538. References are not decoded in raw HTML, so a raw block that contains `&#65;` still contains those characters.

D-539. The decode pass runs only in `inlineText`, not in code, link destinations, or HTML chunks.

D-540. Link destinations still pass through `encodeURI`, which percent-encodes characters that are not URI characters, and then `%25` is turned back into `%` so an already-percent-encoded octet is not double-encoded.

D-541. `encodeURI` does not encode `&`, `+`, `=`, `?`, `#` is encoded by `encodeURI` (`#` becomes `%23`). A hash in a destination is percent-encoded.

D-542. Spaces in a destination are percent-encoded by `encodeURI` to `%20`.

D-543. The pedantic destination rule is not passed through the CommonMark angle-bracket balancer.

D-544. Non-pedantic destinations that are not angle brackets use `findClosingBracket` to stop at the matching `)`.

D-545. `findClosingBracket` treats a backslash as escaping the next character, and it counts nested brackets of the given pair.

D-546. If the brackets never close, the function returns -2 and the link is rejected. If there is no closing bracket at all, it returns -1.

D-547. A rejected link does not consume the source as a link; a later rule or plain text does.

D-548. Label-end detection refuses a link whose closing bracket would fall inside an autolink or HTML tag that started inside the label, except in pedantic mode.

D-549. That check looks for `<` in the label and then for a tag or autolink at that position.

D-550. Code spans inside a label are skipped by that scan so that a `<` inside a code span does not confuse the label end.

D-551. The maximum label length used by the reference search is 999 characters, matching CommonMark’s limit. Longer labels are not found by the masked reference search.

D-552. The inline label used by a direct link match allows nested brackets to a fixed depth of one extra bracket level inside the label pattern, which is enough for the CommonMark examples.

D-553. Reference search masks those references before emphasis scanning so brackets are not treated as emphasis punctuation in a way that would split the link.

D-554. `emStrongMask` is applied to the masked source on top of that link masking.

D-555. The mask string is only a guide for delimiter positions. Slices of the original source become the token text.

D-556. If `emStrongMask` changes the length of the string, delimiter indexes no longer line up with the original, and emphasis pairing is unspecified. Supported masks preserve length, as the tests do when they replace a span with the same number of placeholder letters.

D-557. Placeholder masks in the test replace the interior and keep the delimiter characters out of the mask by substituting the whole `=…=` match with brackets and letters of the same length.

D-558. A block extension and an inline extension can cooperate: the block tokenizer calls `inlineTokens` on its text, and the inline extension tokenizes that text.

D-559. The description-list example in that test renders `<dl>` with `<dt>` and `<dd>` children and still renders the introductory line as a paragraph.

D-560. Options other than the extension list may sit on the same `use` object as `extensions`, and both apply. `silent: true` plus a block extension still renders the extension and the following HTML.

D-561. `:test:\ntest\n<div></div>` with that extension renders `<u>test</u>\n<p>test</p>\n<div></div>`.

D-562. A following raw HTML block is not passed through the extension.

D-563. The extension’s `start` at the first `:` is what allows `:test:` to interrupt after a newline that would otherwise stay in a paragraph.

D-564. Without a blank line, `Not Underlined\n:Underlined\nNot Underlined` is one paragraph because the extension does not interrupt, when `start` is absent.

D-565. With a blank line on each side, the same marker is its own block.

D-566. Inline extensions inside a paragraph do not need a blank line. `Not Underlined =Underlined= Not Underlined` mixes text and the extension’s HTML inside one `<p>`.

D-567. An inline extension `start` that returns the index of `=` clips the preceding text token so the extension is tried at that index.

D-568. If the inline tokenizer then fails to match, parsing continues with ordinary text at that position.

D-569. Block extension tokenizers are tried before `space`, `code`, fences, headings, and the rest of the built-in block order.

D-570. The built-in block order after extensions is newline, indented code, fences, ATX heading, thematic break, block quote, list, HTML, definition, table, setext heading, paragraph, then text.

D-571. The first matching built-in rule wins and consumes `token.raw`.

D-572. Definitions are recognized only when the definition rule matches at the current position, which is after lists and HTML in that order, so a definition-shaped line inside a list item is handled by the list’s interior lex, not by the top-level definition rule.

D-573. Tables are attempted only when the GFM grammar’s table regex matches. In the normal grammar the table method returns undefined immediately.

D-574. Setext headings are attempted after tables, so a GFM table consumes a delimiter line before setext can.

D-575. Paragraphs are attempted only when `state.top` is true. Inside list items, the text rule is used instead for ordinary lines.

D-576. Adjacent text tokens produced by the text rule are merged.

D-577. A paragraph that was clipped by an extension `start` and is followed by more paragraph text is merged back when `lastParagraphClipped` is set.

D-578. That merge updates the queued inline source so the paragraph is inline-tokenized once as a whole.

D-579. Indented code merged into a preceding paragraph likewise updates the queued inline source.

D-580. Fences are not merged into a preceding paragraph. They are always their own token when they match, and they can interrupt.

D-581. ATX headings are not merged into a preceding paragraph.

D-582. Thematic breaks are not merged into a preceding paragraph.

D-583. A single newline token of length 1 is appended to the previous token’s `raw` when a previous token exists, instead of being pushed.

D-584. A newline run longer than one character is a `space` token.

D-585. The newline rule matches spaces and tabs on the blank lines as well as the newlines.

D-586. A line that contains only a tab is a blank line for that rule in non-pedantic mode. Pedantic mode has already turned tabs into spaces and deleted space-only lines.

D-587. Pedantic preprocessing uses a global tab-to-four-spaces replacement, not column-aware tab stops. Every tab becomes exactly four spaces regardless of column.

D-588. Non-pedantic tab handling elsewhere is column-aware with tab stops every 4 columns.

D-589. Column counting starts at the `indent` argument, which list handling sets from the marker length.

D-590. A tab at column 0 expands to four spaces. A tab at column 1 expands to three spaces. A tab at column 3 expands to one space. A tab at column 4 expands to four spaces.

D-591. Those expanded spaces are how list indentation and indented code decide whether a tab completes a 4-space indent.

D-592. The CommonMark example of a tab at the start of a line producing an indented code block holds: `\tfoo\tbaz\t\tbim\n` renders a code block whose text keeps the interior tabs.

D-593. Two spaces then a tab also open an indented code block, and the content tabs remain.

D-594. Interior tabs in indented code are not expanded.

D-595. The indent remover only strips a prefix of one to four spaces or a tab. It does not expand tabs in the remaining text.

D-596. Five spaces of indent on a code line leave one space in the code text.

D-597. A line of exactly four spaces of indent plus content has no leading space in the code text.

D-598. A line that is only a tab, at the top level, is an indented code block whose content is empty on that line or whose indent consumed the tab, matching the fixture where a lone tab renders a code block of a newline only when the rest of the line is empty. The fixture `lone tab` renders `<pre><code>lone tab` only when the word is present; a tab that is the entire indent of `lone tab` produces code text `lone tab\n`.

D-599. Three spaces and a tab before `three spaces and a tab` produce an indented code block with that text and no leading spaces.

D-600. Fenced code does not expand a tab that is content. `` ```\n\ttab\n``` `` renders `<pre><code>\ttab\n</code></pre>\n`.

D-601. The CLI and `parse` agree on that fence when GFM or CommonMark fences are enabled (non-pedantic).

D-602. Pedantic mode would have replaced that tab with four spaces before parsing, and would not treat the backticks as a fence, so the output differs from D-600.

D-603. Users who want byte-stable fences must leave `pedantic` false.

D-604. The default `pedantic` value is false.

D-605. The default `gfm` value is true.

D-606. The default `breaks` value is false.

D-607. The default `silent` value is false.

D-608. The default `async` value is false.

D-609. `extensions`, `hooks`, `renderer`, `tokenizer`, and `walkTokens` default to `null`, which means “use the built-in”.

D-610. A `null` renderer on the options object is replaced inside the parser by a new stock renderer.

D-611. A `null` tokenizer on the options object is replaced inside the lexer by a new stock tokenizer.

D-612. A `null` hooks value skips every hook step.

D-613. A `null` `walkTokens` skips the walk.

D-614. Setting `walkTokens` to a function via `setOptions` or `use` installs it.

D-615. A per-call `walkTokens` replaces the instance function for that call because of the shallow merge. It does not chain with the instance’s `walkTokens`. Chaining happens only across `use` registrations.

D-616. A per-call `hooks` object replaces the instance hooks for that call and is not method-merged.

D-617. A per-call `renderer` object replaces the instance renderer for that call.

D-618. Callers that want fallback-to-built-in behavior must `use` the partial renderer rather than pass it on the call.

D-619. The documented `parse` entry is `mdkit.parse(markdownString, options?)`.

D-620. The documented inline entry is `mdkit.parseInline`.

D-621. Creating `new Mdkit(options)` is the supported way to keep options off the shared entry.

D-622. The shared entry is what the CLI mutates when a config file is loaded.

D-623. Library callers who do not construct `Mdkit` share one global compiler inside the process, so `use` in one module changes `parse` in another module that imported the same package instance.

D-624. Separate `import` evaluations in the same Node process share that instance because it is module state, not per-call state.

D-625. `new Mdkit()` does not read or write that shared instance.

D-626. The HTML for the shared entry’s default heading remains `<h1>header</h1>\n` when only other instances override headings.

D-627. Overriding the shared entry’s heading renderer changes `mdkit.parse` for later callers.

D-628. The test that installs a shared heading renderer resets defaults in `beforeEach` via `setOptions(getDefaults())`, which restores built-in behavior for later tests. Application code must do that itself if it wants the original renderer back. There is no `reset` method other than `setOptions(getDefaults())`, and that does not uninstall wrapped renderer methods if a previous `use` replaced `renderer` and `getDefaults()` sets `renderer: null`. After `setOptions(getDefaults())`, `renderer` is `null`, so the next parse constructs a stock renderer.

D-629. `setOptions(getDefaults())` therefore restores stock rendering, stock options, and `async: false`.

D-630. It does not remove properties that were assigned onto a renderer object the caller still holds. It only drops the instance’s reference when the new defaults say `renderer: null`.

D-631. Tokens produced by the stock lexer for `a` are one paragraph whose text is `a` and whose inline content is one text token `{ type: 'text', raw: 'a', text: 'a', escaped: false }`.

D-632. That paragraph’s `raw` and `text` are both `a` when the input has no trailing newline.

D-633. When the input is `a\n`, the newline rule may attach the newline to `raw` while `text` stays `a`, and the HTML is still `<p>a</p>\n`.

D-634. The CLI string `# test` includes a heading token of depth 1 and text `test`, rendered `<h1>test</h1>\n`.

D-635. File fixture `bin-input.md` is the single line `# file` and renders `<h1>file</h1>\n` before the CLI newline.

D-636. The executable used by the integration test is the bin script, and it produces the same HTML as the `main` function for stdin, `--string`, `--input`, and a positional file.

D-637. The integration test invokes `node` on that script, so a shebang of `#!/usr/bin/env node` is not required for the Node launch, but the file has that shebang for `PATH` execution.

D-638. The script is an ES module, matching the package `"type": "module"`.

D-639. The CLI imports the built ESM library, not the TypeScript sources. A published package must contain that build.

D-640. The published file set is the binary directory, the library build, and the manual directory.

D-641. Type declarations are published at the types entry next to the ESM build.

D-642. The types describe `parse` as returning `string` when `async` is false or omitted, and `Promise<string>` when `async` is true.

D-643. The types allow `parse` to return `Promise<string>` as well when extensions have set async, even if the call does not pass `async: true`.

D-644. If the call passes `async: false` while the instance is async, the return is the thrown error, not a string. The type overload that says `async: false` returns `string` does not cover that failure. Runtime behavior is the throw in D-41.

D-645. `walkTokens` on the function is also a named export and walks whatever list it is given, independent of a compile.

D-646. That export uses the shared instance’s `walkTokens`, so `this` is the shared instance.

D-647. Custom `childTokens` on the shared instance’s defaults are honored by that export, because the walker reads `this.defaults.extensions`.

D-648. A walk that is given an empty array returns an empty list of callback results and does not call the callback.

D-649. The callback’s return values are concatenated in visit order and returned from `walkTokens`. `parse` discards them except to await promises.

D-650. Visit order is parent, then children, left to right.

D-651. Space tokens are visited.

D-652. Definition tokens that the lexer dropped from the top-level list because they were recorded as links are not visited as their own rendered nodes. When a `def` token is present in a list handed to the parser, it renders nothing but `walkTokens` still visits it if it is in the list.

D-653. The lexer removes definition source from the stream by consuming it as a `def` token, and it also stores the link. Whether the `def` token stays in the array depends on the lexer pushing it. The definition method returns a token and the lexer pushes tokens that methods return, so `def` tokens are in the array, render as empty, and are visited by the walker.

D-654. Their presence does not add HTML, so two paragraphs with a definition between them still look like those paragraphs.

D-655. A definition’s `tag` is the normalized label, not the original spelling.

D-656. A definition’s `href` has angle brackets removed and backslash escapes decoded.

D-657. A definition without a title stores the title match as it was captured; a missing title is undefined or empty according to the match, and the link renderer omits the attribute when the title is null or empty. The definition tokenizer sets `title` from the capture, which is `undefined` when the group is missing. The link path uses `title || null` in `outputLink`, so missing titles become `null`.

D-658. Duplicate definitions: the later definition overwrites `links[tag]` because assignment replaces the property. Both `def` tokens may still appear in the token list.

D-659. Lookup uses the label after whitespace collapse and normalization, not the original raw label.

D-660. A reference to a missing label does not throw.

D-661. The first matching inline rule at the current index is used; later rules are not tried after a match.

D-662. An empty match does not count as progress. The infinite-loop guard fires if the source length does not shrink.

D-663. Extension tokenizers that return a token with `raw: ''` trip that guard.

D-664. The guard reports the code unit `charCodeAt(0)` of the stuck source.

D-665. In silent mode the guard does not throw, so `parse` returns the HTML of the tokens collected before the stuck point, after logging.

D-666. Silent mode does not suppress `console.error` for that guard or for unknown tokens.

D-667. Silent mode does suppress the throw-and-suffix path for errors thrown inside the try, replacing them with the error HTML.

D-668. An infinite-loop condition that is handled inside the lexer by logging and breaking is not a throw, so silent and non-silent differ: non-silent throws before the break’s caller can return, because `infiniteLoopError` throws. Silent logs and breaks.

D-669. The thrown infinite-loop Error, when it escapes `lex` into `parse`, receives the report suffix.

D-670. Direct `Lexer.lex` of a stuck input throws without the suffix.

D-671. The paragraph rule does not match an empty string. End of input stops the loop.

D-672. A document of only blank lines becomes one `space` token or several, and renders as the empty string because space renders nothing. The CLI still adds its stdout newline.

D-673. A document of only a definition renders no visible HTML, because `def` renders empty. The token list is not empty.

D-674. A document of only a thematic break renders `<hr>\n`.

D-675. Three or more identical list-marker characters with spaces can be a thematic break rather than a list, and the hr check inside list parsing refuses to treat them as items when the hr rule matches the whole remainder.

D-676. `***` at the start of a line is a thematic break, not emphasis and not a list.

D-677. `* * *` is a thematic break.

D-678. `- - -` is a thematic break when it matches the hr rule before the list rule. The block order tries hr before list, so `- - -` is `<hr>\n` by default.

D-679. An override that disables `hr` lets the list rule see `- - -`. If that also produces no items, the paragraph rule renders `<p>- - -</p>\n`.

D-680. Underscore thematic breaks `___` are breaks, while a single `_` can be emphasis. The hr rule requires three.

D-681. Emphasis and thematic breaks do not conflict at the start of a line because block rules run before inline rules.

D-682. Inside a paragraph, `***` on its own line can end the paragraph and become a break because the paragraph rule treats a thematic break as an interrupter.

D-683. A thematic break interrupter needs to be at the beginning of a line, at up to three spaces of indent.

D-684. Four spaces of indent before `***` keep it inside the paragraph.

D-685. A fence interrupter is three backticks or tildes at up to three spaces of indent.

D-686. A heading interrupter is one to six hashes followed by a space or end of line, at up to three spaces.

D-687. A block-quote interrupter is `>` at up to three spaces.

D-688. A list interrupter at paragraph level is a bullet or the digit `1` followed by `.` or `)`, then whitespace, then a non-space.

D-689. Inside a block quote the list interrupter also allows any 1–9 digit number and an empty item.

D-690. HTML interrupters are the block-tag open and close forms and the raw-HTML openers listed in D-266.

D-691. Setext underlines do not interrupt an already-started CommonMark paragraph from the outside; they are recognized as the second line of a setext heading when the lheading rule matches a fresh block.

D-692. The paragraph regex is what prevents a setext underline from being required to interrupt; the lheading rule is a separate block rule tried before the paragraph rule.

D-693. So `Foo\n---` at the start of a block is a setext heading, not a paragraph plus a break.

D-694. `Foo\n===` is a level-1 setext heading.

D-695. A setext underline of more than one character is still a heading. `===` and `---` of any length of one or more match.

D-696. Trailing spaces after the underline are allowed.

D-697. The heading text of a setext heading is trimmed.

D-698. ATX heading text is trimmed, and then closing hashes are optionally removed, and then trimmed again.

D-699. Closing hashes in non-pedantic mode require the character before them, after stripping hashes from the end, to be a space or tab, or the text to be empty.

D-700. `#` with no text renders an empty heading `<h1></h1>\n` when the rule matches (hash at the start, no required text).

D-701. `####### foo` is not an ATX heading, because the hash run is limited to six.

D-702. Pedantic headings use `#{1,6}` without the space requirement and without the indent limit, anchored at the start of the string the tokenizer sees.

D-703. A pedantic heading can therefore be `#hi` with the text `hi`.

D-704. The CLI `--pedantic -s '#hi'` renders `<h1>hi</h1>\n` plus the stdout newline.

D-705. The CLI default `-s '#hi'` does not treat it as a heading, because a space is required. It is a paragraph containing `#hi`.

D-706. `# hi` is a heading in both modes.

D-707. Heading text is inline, so `# *a*` contains `<em>a</em>`.

D-708. Heading text does not include the leading space after the hashes.

D-709. Heading text does not include a trailing newline.

D-710. The HTML heading contains no `id` attribute.

D-711. Fenced code HTML contains no `id` attribute.

D-712. Links contain `href` and optional `title` and no `target` or `rel`.

D-713. Images contain `src`, `alt`, and optional `title`, and no `width` or `height`.

D-714. The image tag is not self-closed with `/`.

D-715. The break tag is not self-closed with `/`.

D-716. The horizontal rule is not self-closed with `/`.

D-717. Checkbox inputs are not self-closed with `/`.

D-718. Attribute order on a checkbox is `checked=""` (if present), then `disabled=""`, then `type="checkbox"`.

D-719. Attribute order on a link is `href` then `title`.

D-720. Attribute order on an image is `src`, `alt`, then `title`.

D-721. Attribute order on a code element is a single `class` when a language exists.

D-722. Double quotes are the attribute quote character. Attribute values are escaped so they cannot contain a raw `"`.

D-723. The class value is `language-` plus the escaped language word, with no extra quotes inside.

D-724. Table `align` values are the lowercase words `left`, `right`, and `center` only.

D-725. The `start` attribute’s value is the decimal integer without padding.

D-726. `start="0"` is emitted for a list that starts at 0.

D-727. Negative numbers are not list markers. A hyphen is a bullet, not a signed number.

D-728. `1)` and `1.` are both ordered markers and may be mixed only when the list tokenizer’s bullet pattern allows the next item. The next-item pattern for an ordered list is “digits, then the same delimiter”, so `1.` does not continue as `2)`.

D-729. Bullet lists do not continue with a different bullet in non-pedantic mode. `*` items do not swallow a following `+` item as the same list; the `+` item starts a new list or ends the item according to the next-bullet test.

D-730. Pedantic mode treats `*`, `+`, and `-` as one bullet class, so they can continue the same list.

D-731. Ordered pedantic lists still require the same delimiter character the first item used, because the pedantic rewrite only replaces unordered bullets.

D-732. A new list of a different type after a finished list is a separate token and therefore a separate `<ul>` or `<ol>`.

D-733. There is no HTML comment or blank line inserted between adjacent lists.

D-734. Adjacent lists of the same type are still separate lists when the first list ended. They are not merged.

D-735. The end of a list is when the next item regex fails or an hr/fence/heading/html/quote rule cuts the item.

D-736. Blank lines alone do not end a list. They make it loose and can be the empty part of an item.

D-737. An item may start with a blank line, and a second blank line ends that item early.

D-738. Item text does not include the marker or the marker’s trailing space. It starts at the content indent.

D-739. In pedantic mode the content is `trimStart` of the first line and the indent is fixed at 2.

D-740. A content indent greater than 4 is treated as 1 so that a code block on the first line of an item remains code.

D-741. That rule is why a first line that is itself a fence or code can still be recognized after the marker.

D-742. The marker length includes the spaces before the marker, up to three, plus the marker characters.

D-743. Those leading spaces are part of `cap[1]` from the item regex.

D-744. The bullet used for subsequent items is a regex escaped copy of the first marker, or a digit pattern plus the original delimiter.

D-745. The first marker’s literal text decides `ordered` by whether its trimmed form is longer than one character.

D-746. A one-character trimmed marker is `*`, `+`, or `-`, hence unordered. A number plus delimiter is longer than one character, hence ordered.

D-747. `start` for an ordered list is the integer value of the marker without its last character.

D-748. The last character of an ordered marker is `.` or `)`.

D-749. Unordered `start` is `''`, and `'' !== 1`, but the renderer only emits `start` when `ordered` is true, so bullets do not get `start=""`.

D-750. Loose-list retyping happens before render and mutates the tokens.

D-751. A caller that lexes and then inspects tokens sees `paragraph` children on loose items and `text` children on tight items.

D-752. Tight items that contain a nested list still have a `text` token for the item’s own text plus a `list` token.

D-753. The nested list is a block token inside the item, so the HTML is `<li>text<ul>…</ul>\n</li>\n` with no newline between the text and the `<ul>`.

D-754. CommonMark’s reference HTML for that example inserts newlines that mdkit does not. HTML parsers treat them as equivalent. The byte contract is the stock renderer.

D-755. Example 6 of CommonMark (`>\t\tfoo`) is HTML-parser-equivalent in the suite only because the comparator collapses differences the bytes do not. The bytes are `<blockquote>\n<pre><code>foo\n</code></pre>\n</blockquote>\n`.

D-756. Named-entity differences versus the CommonMark reference are also HTML-parser-equivalent and are not byte-equivalent. mdkit leaves `&nbsp;` and unknown `&Word;` sequences in place.

D-757. A rebuild that decodes the full HTML named-entity set will not match mdkit’s bytes, and it is not what this specification requires.

D-758. A rebuild that emits `<br />` or `<hr />` will not match mdkit’s bytes.

D-759. A rebuild that inserts a newline after `<li>` before a block child will not match mdkit’s bytes.

D-760. A rebuild that filters raw HTML tags will not match mdkit, including the GFM disallowed-raw-HTML case.

D-761. A rebuild that strips `javascript:` URLs will not match mdkit.

D-762. A rebuild that adds heading ids will not match mdkit.

D-763. A rebuild that enables smart quotes will not match mdkit. `"` stays `&quot;` when escaped, and curly quotes are not introduced.

D-764. A rebuild that wraps the fragment in `<html>` or `<body>` will not match mdkit.

D-765. The CLI does not add a doctype.

D-766. The CLI does not resolve relative image URLs against the input file’s directory.

D-767. The CLI does not watch files. One compile, then exit.

D-768. The CLI does not start a worker. The library call is in-process.

D-769. A caller may put the library in a worker of their own. The library does not do that by itself.

D-770. There is no `baseUrl` join. Relative hrefs are emitted as written, after `cleanUrl` and escaping.

D-771. `cleanUrl` does not resolve `.` or `..` segments and does not add a scheme.

D-772. `www.` hrefs are the one place a scheme is added, and that happens in the tokenizer before `cleanUrl`.

D-773. Email hrefs gain `mailto:` in the tokenizer, not in `cleanUrl`.

D-774. The visible text of those links does not gain the prefix.

D-775. Titles on autolinks are null, so no `title` attribute is written.

D-776. Reference links copy the definition’s title, which may be null.

D-777. Inline links with a title include that title after HTML escaping.

D-778. Titles that contain `<` are escaped so the attribute cannot end early.

D-779. The destination is not passed through the HTML sanitizer because there is none.

D-780. Percent-encoding from `encodeURI` happens even when the destination is already safe ASCII. Safe ASCII is unchanged.

D-781. A destination containing a newline does not match the inline link rule, which excludes raw newlines from the destination.

D-782. A destination may contain spaces only in the pedantic grammar’s looser capture. The CommonMark grammar’s non-angle destination excludes spaces.

D-783. Angle-bracket destinations may contain spaces because the angle form is `<` plus escaped or non-bracket characters plus `>`.

D-784. An angle destination whose `>` is escaped is rejected in non-pedantic mode.

D-785. An angle destination missing `>` is rejected in non-pedantic mode.

D-786. Pedantic mode does not apply those angle checks.

D-787. Image destinations use the same rules as link destinations.

D-788. A failed image still returns escaped alt text from the renderer when `cleanUrl` fails, but a tokenizer rejection never creates an image token.

D-789. `cleanUrl` fails only when `encodeURI` throws, which is limited to malformed surrogate pairs in the string. Ordinary Markdown destinations succeed.

D-790. When it fails, a link’s already-rendered inner HTML is returned without an anchor, and an image’s escaped alt text is returned without an `img` tag.

D-791. The inner HTML of a failed link has already been parsed, so emphasis inside the label remains.

D-792. Autolink hrefs are also passed through `cleanUrl` and then encode-all.

D-793. Encode-all of an autolink runs after `cleanUrl`, so percent-escapes introduced by `encodeURI` are not turned into entities except for `&` if one were present. `encodeURI` does not introduce `&`.

D-794. Non-autolink hrefs use encode-unsafe after `cleanUrl`, which is why `&amp;` in the source can remain `&amp;` in the attribute while a bare `&` becomes `&amp;`.

D-795. The source characters `&amp;` in a non-autolink destination are the six characters ampersand, `a`, `m`, `p`, `;`. They match the named-reference exception and are not double-escaped.

D-796. The same six characters in an autolink are fully escaped to `&amp;amp;` because autolinks use encode-all.

D-797. That difference is a byte contract, marked `renderExact` on the fixture.

D-798. GFM `www.` links are autolinks, so they follow the encode-all side of that difference.

D-799. Angle-bracket links are autolinks and follow encode-all.

D-800. Reference links and bracket links are not autolinks and follow encode-unsafe.

D-801. The `autolink` flag is the switch. Extensions that create link tokens can set it to choose the escaping.

D-802. Omitting the flag is encode-unsafe, the same as a normal link.

D-803. The flag does not change the tag name. Both are `<a>`.

D-804. The flag does not add `mailto:` by itself. The tokenizer does that before rendering.

D-805. A caller who builds a link token with `href` already set sees that href escaped and not rewritten, except for `cleanUrl`.

D-806. `Parser.parse` of a hand-built token list does not lex Markdown again. It only renders.

D-807. Hand-built tokens must include the fields the renderer reads. A heading needs `depth` and `tokens`. A code token needs `text` and may omit `lang`.

D-808. A code token whose `text` is `code` renders `<pre><code>code\n</code></pre>\n` because the renderer adds the newline.

D-809. The parser test compares that with HTML equality to `<pre><code>code</code></pre>`, which accepts the extra newline and the missing trailing newline on `</pre>` only insofar as the differ allows. The bytes include `\n` before `</code>` and `\n` after `</pre>`.

D-810. A heading token of depth 1 and text tokens `heading` renders `<h1>heading</h1>\n`.

D-811. An `hr` token renders `<hr>\n`. The parser test’s expected `<hr />` is HTML-equivalent, not the bytes.

D-812. A table token with left and right alignment renders `align="left"` and `align="right"` on both the header and the body cells.

D-813. The table renderer does not look at `token.align` except through the cells. Each cell’s own `align` is what is written. The stock lexer copies the column align onto every cell.

D-814. A cell with `align: null` omits the attribute even if the table’s `align` array says otherwise. The renderer does not consult the table array.

D-815. Header cells use `<th>` even if a caller sets `header: false`. The `header` boolean is the switch.

D-816. Body cells use `<td>` when `header` is false.

D-817. Checkbox rendering ignores any label. The following text is a separate token.

D-818. A checked checkbox’s HTML starts with `<input checked=""`.

D-819. An unchecked checkbox’s HTML starts with `<input disabled=""`.

D-820. Both include `type="checkbox"` and a trailing space.

D-821. The list item renderer does not add its own checkbox. The checkbox must be a token.

D-822. Disabling GFM removes the checkbox token, so the brackets render as text inside the item.

D-823. The text of a task item after marker removal does not include a second copy of `[x]`.

D-824. Marker removal also edits the queued inline source so the brackets are not tokenized as text.

D-825. The checkbox is unshifted onto the front of the item’s tokens or onto the front of the first paragraph’s tokens.

D-826. If a task item’s first token is neither `text` nor `paragraph`, `task` is cleared and no checkbox is inserted.

D-827. That happens when the item starts with a block such as a fence or a list, so a checkbox-shaped prefix that did not stay in the first text token is not a task.

D-828. `listIsTask` requires the item contents to start with the bracket pattern and then a non-space, so an item whose first block consumed the marker is not a task.

D-829. The pattern is case-sensitive for `x` and `X` only. `[X]` is checked. Other letters are not task markers.

D-830. `[x]` with a lowercase x is checked. `[ ]` with a space is not.

D-831. Tabs between the brackets and the text still count as the required space, because the pattern uses a space class of one or more spaces after the brackets only in `listIsTask` (` +`), which is the space character, not tabs. A tab immediately after `]` does not match `listIsTask`. The marker must be followed by at least one U+0020 space.

D-832. `listReplaceTask` removes the marker and the following spaces, not a following tab.

D-833. The checked test compares the matched bracket text to the two characters `[` and `] ` with a space. Any other fill character that still matched `[ xX]` is checked. The only such fills are `x` and `X`.

D-834. The checkbox `raw` is the bracket match plus one space, not the whole item.

D-835. That `raw` is also prefixed onto the paragraph `raw` and `text` when the list is loose, so the paragraph source still shows the marker plus the remaining text.

D-836. The visible HTML does not repeat the marker, because the checkbox renderer emits an input and the paragraph’s inline tokens start with the checkbox rather than the bracket characters.

D-837. Tight lists do not prefix the marker back onto a paragraph, because there is no paragraph. The checkbox token stands alone before the text token.

D-838. The text token’s text no longer includes the marker, so the HTML text is the item text only.

D-839. Nested lists inside a task item are later tokens and are rendered after the checkbox and the text.

D-840. A task item can be ordered. `1. [x] a` is an `<ol>` whose item starts with a checked checkbox.

D-841. The `gfm` flag, not the grammar name alone, gates `listIsTask`. Pedantic rules plus `gfm: true` still recognize tasks if the item text matches, but pedantic preprocessing may have changed tabs to spaces first.

D-842. With pedantic preprocessing, a tab after a marker has already become four spaces, so indentation differs from CommonMark column tabs.

D-843. Callers who need CommonMark tab columns must leave `pedantic` false.

D-844. The original fixture suite is the compatibility target for pedantic mode, not the CommonMark suite.

D-845. Running the CommonMark suite with `pedantic: true` is not what the tests require and will not match CommonMark reference HTML.

D-846. Running the GFM extension file with `gfm: false` will not match the table, task, strikethrough, or autolink references.

D-847. The additional 183 fixtures are part of the contract for the default grammar except where their front matter changes options. Their expected HTML is the paired `.html` file, compared as in D-261.

D-848. Those fixtures include, and mdkit satisfies, exact byte cases for fence indent, empty fences, code newlines, hard-break whitespace, list tabs, numeric references, and autolink versus link escaping, as quoted in sections 3.8 and 3.9.

D-849. The remaining additional fixtures are HTML-parser-equivalent to their paired HTML under the default or front-matter options. They cover emphasis nesting, lists, tables interrupting blocks, block quotes, HTML blocks, setext headings, and autolink edges that the rules in section 3.9 already state.

D-850. No fixture requires a network request, a file read from inside `parse`, or a particular current working directory. `parse` is a pure function of its string and options, plus the instance’s registered extensions and defaults.

D-851. `parse` is not pure with respect to `use` on the same instance. `use` changes later results.

D-852. `parse` does not mutate the input string. It may mutate tokens it creates. It does not mutate the options object the caller passed, except that hooks receive that merged object as `this.options` and may assign to its properties.

D-853. The merged options object is a shallow copy. Nested objects such as a renderer are shared with the instance. A hook that mutates `this.options.renderer` mutates the instance renderer.

D-854. Scalar overrides on the call (`{ gfm: false }`) do not write back to `instance.defaults`.

D-855. `this.options` inside a hook is the per-call merged object, not `instance.defaults`, unless no per-call options were passed and the spread still copied the references. Scalars are copied by value, so assigning `this.options.gfm = false` does not change `instance.defaults.gfm`.

D-856. Assigning `this.options.breaks = true` does change the object the lexer is about to read, which is why D-60 works, without persisting to the next `parse`.

D-857. The lexer copies `options` by reference (`this.options = options`). It sees hook writes that happen in `preprocess` before `lex`.

D-858. Grammar selection happens in the lexer constructor, which runs at the start of `lex`, after `preprocess`. A `preprocess` hook that sets `breaks` or `gfm` or `pedantic` affects grammar selection for that compile.

D-859. A `walkTokens` hook that sets `options.gfm` is too late to change grammar selection. The tokens already exist.

D-860. A `postprocess` hook that sets options does not affect the HTML already produced, except through the string it returns.

D-861. `processAllTokens` runs after lexing, so it cannot change which grammar was used. It can replace the token list.

D-862. Replacing the token list with an empty array renders the empty string.

D-863. Replacing it with a heading token renders that heading.

D-864. The token list’s `links` property is preserved if the hook mutates the same array. A hook that returns a new array without `links` drops unresolved-reference data, but references have already been turned into link tokens during inline lexing, so the HTML of ordinary documents does not consult `links` again during parse.

D-865. Inline lexing of link references reads `tokens.links` at lex time, not at parse time.

D-866. Therefore a `processAllTokens` hook cannot add a definition that earlier inline tokens will see, unless it also rewrites those tokens.

D-867. It can still append tokens that render after the document.

D-868. `provideLexer` that ignores its input and returns a fixed token list skips grammar selection entirely.

D-869. `provideParser` that ignores tokens can return a constant string, and `postprocess` still sees that string.

D-870. If `provideParser` returns `false`, the previous parser is used, including the built-in parser when no older hook exists. The default hook does not return `false`; it returns the built-in parser function.

D-871. If `provideLexer` returns `false`, the previous lexer is used the same way.

D-872. Pass-through hooks do not treat `false` as fallback. `preprocess` that returns `false` passes `false` into the older preprocess or into the lexer.

D-873. That is why supported preprocessors return strings.

D-874. `emStrongMask` returning the same string is a no-op.

D-875. `emStrongMask` is called with the masked inline source during inline lexing, once per inline run.

D-876. It is not called for block structure.

D-877. A document with no inline content still does not need a mask call to succeed. Empty inline runs may still call it when the lexer inlines a string. The default mask returns the argument.

D-878. Custom masks see the source after link masking, because the hook is how the lexer obtains the mask string from the hooks object when hooks are installed. When hooks are absent, the lexer’s own mask is the only mask.

D-879. Installing hooks replaces the default hooks object and wraps `emStrongMask`, so the default identity mask still runs as the older hook and receives the newer mask’s output.

D-880. The older identity mask returns what it was given, so a single custom mask’s return value is the final mask.

D-881. Two custom masks both run, newest first, then the identity mask.

D-882. The identity mask does not undo a custom mask.

D-883. Async `emStrongMask` is not part of the awaited set. A mask that returns a Promise will be used as the mask string incorrectly. Supported masks are synchronous and return a string.

D-884. Async `preprocess`, `postprocess`, and `processAllTokens` must be used with `async: true` or the sync path will pass a Promise into the lexer. The supported way to use async hooks is to set `async: true`.

D-885. With `async: true`, those three hooks may return Promises and are awaited.

D-886. A sync hook on an async instance is still safe, because awaiting a non-Promise yields the value.

D-887. The async path catches rejection and routes it through the error wrapper.

D-888. The sync path catches throws the same way.

D-889. Programming errors inside renderers are caught by that wrapper when the call went through `parse`. They are not caught when the caller invoked `renderer.heading` directly.

D-890. Direct renderer calls do not add the report suffix.

D-891. The report suffix text is stable and does not include the input Markdown.

D-892. The original message and the suffix are separated by a single newline, not by a space.

D-893. The suffix includes the final period.

D-894. Silent HTML includes that period inside the `<pre>`.

D-895. Silent HTML escapes the newline in the message as a raw newline inside `<pre>`, not as `<br>`.

D-896. The newline is not escaped by the entity encoder, because the encoder does not replace `\n`.

D-897. `<` in the message is escaped, so the prefix `mdkit():` stays text.

D-898. The words `mdkit():` appear at the start of the input-type and async-extension messages.

D-899. They do not appear at the start of the infinite-loop or unknown-token messages. Those messages are only `Infinite loop on byte: N` and `Token with "TYPE" type was not found.`

D-900. When those are wrapped by `parse`, the suffix is added but the `mdkit():` prefix is not added.

D-901. CLI failures do not add `mdkit():` either, except the ENOENT line and the no-clobber message, which use the `mdkit: ` prefix with a space and no parentheses.

D-902. The ENOENT prefix is `mdkit: ` with a colon and a space, then the path, then `: No such file or directory`.

D-903. The path in that message is `error.path` from the filesystem error, which is the path that was opened.

D-904. The no-clobber message quotes the path with single quotes and includes the flag names `-n` and `--no-clobber`.

D-905. The no-clobber message ends with a newline character that is part of the string.

D-906. The ENOENT message does not end with a newline.

D-907. The config-missing message does not end with a newline and does not start with `mdkit`.

D-908. Version output ends with a newline because it uses `console.log`.

D-909. Version output has no `v` prefix. It is the bare `18.0.14`.

D-910. There is no `--version` long-option collision with a compiler default, because `version` is not a default key. It is handled before the generic long-option code.

D-911. `--help` is likewise handled before the generic code. `help` is not a default key.

D-912. `--input`, `--output`, `--string`, `--config`, `--tokens`, and `--no-clobber` are handled before the generic code and are not compiler defaults.

D-913. `--no-clobber` would not match a default even if it fell through, because `clobber` is not a key. The specific case returns no compiler option named `noClobber`.

D-914. Generic `--no-gfm` does match, because `gfm` is a boolean default.

D-915. `--gfm` sets true even though the default is already true. It is idempotent.

D-916. `--pedantic` sets `pedantic` true and therefore changes grammar even when `--gfm` is also present. If both flags are passed, the resulting options object has both `pedantic: true` and `gfm: true`, and the lexer prefers pedantic.

D-917. The order of `--pedantic` and `--gfm` does not matter for grammar selection. Both values are simply stored, and the lexer checks `pedantic` first.

D-918. `--breaks` without `--gfm`, when `gfm` has been turned off, stores `breaks: true` but the lexer ignores it.

D-919. `--breaks` with default `gfm` enables single-newline breaks.

D-920. A config that sets `gfm: false` and a CLI `--breaks` still leaves breaks ineffective, because the merged call has `gfm: false` and `breaks: true`.

D-921. A config that sets `breaks: true` and a CLI `--no-gfm` likewise disables the breaks grammar.

D-922. A config that sets `breaks: true` and a CLI `--no-breaks` disables breaks even if `gfm` stays true.

D-923. Flags the CLI does not understand and that are not defaults, such as `--not-a-real-opt`, are ignored, and a later `-s` still compiles.

D-924. The ignored token does not consume a following value. `--not-a-real-opt foo` treats `foo` as a positional file if it does not start with `-`.

D-925. `--gfm` does not consume a following file name, because it is boolean. `mdkit --gfm file.md` compiles `file.md` with GFM on.

D-926. `-o` consumes the next argument even if that argument starts with `-`. `mdkit -o --weird` tries to write a file named `--weird`.

D-927. If `-o` is the last argument, the output path is `undefined` and the write fails with a runtime error message and status 1.

D-928. If `-s` is the last argument, the string is `undefined`, which is falsy, so the CLI falls through to a file or stdin.

D-929. If `-i` is the last argument, `input` is `undefined` and `readFile` fails. The resulting error is reported with status 1.

D-930. If `-c` is the last argument, the config path is `undefined`, the existence check fails, and the message is `Cannot load config file 'undefined'`.

D-931. Stdin is not read when `--string` or a file supplied the source. The CLI does not wait for stdin in those cases.

D-932. When stdin is read, `resume` is called so a paused stdin still emits data.

D-933. Stdin chunks are concatenated as strings, not buffers, because the encoding is set to utf8.

D-934. A stdin error rejects the read and the CLI prints `error.message` if the error is not `ENOENT`.

D-935. An `ENOENT` on stdin, if one were raised with a path, would use the ENOENT format. Typical stdin errors are not `ENOENT`.

D-936. The process exits even after a successful write. It does not stay alive for more input.

D-937. The exit is `process.exit(0)` or `process.exit(1)`, which flushes stdio and terminates.

D-938. Help returns from `start` and then hits the same `exit(0)` path.

D-939. Version does the same.

D-940. A help `man` child that is still running is awaited. The CLI does not exit before `man` closes.

D-941. The `close` event resolves the wait even when `man` exits non-zero. The CLI still exits 0.

D-942. The CLI does not inspect `man`’s status code.

D-943. Therefore a missing manual page is not a CLI failure.

D-944. The Markdown manual file is only read in the spawn-error fallback.

D-945. That read uses UTF-8.

D-946. `console.log` of the manual adds a newline if the file did not already end by satisfying `console.log`’s formatting. `console.log` always terminates the line.

D-947. The manual path is resolved next to the executable’s directory, one level up, in `man/`.

D-948. The executable directory is derived from `import.meta.url`, not from `process.cwd()`.

D-949. Config paths and output paths are resolved from `process.cwd()` via `path.resolve`, except for the leading `~` expansion.

D-950. Input paths are passed to `readFile` as given. Relative paths are resolved by the filesystem against the current working directory.

D-951. The ENOENT `path` is the path `readFile` attempted, which for a relative path is that relative path or the absolute path Node puts on the error. The test expectation is the absolute path produced by `path.resolve` of the fixture, and the assertion compares equal to that absolute string. Node’s `ENOENT` for an absolute path echoes that absolute path.

D-952. The CLI does not canonicalize `..` before the filesystem sees a relative input. `path.resolve` is used for config and output and for the `~` form, and `readFile` receives `input` or the positional string as stored.

D-953. Output `writeFile` receives the path after it was stored, not `resolveFile`, except the existence check uses `resolveFile`. A relative `-o` is existence-checked and written consistently enough that a relative path and the same relative path refer to the same file from the current directory. `fileExists` resolves it; `writeFile` is given the original string. Both name the same relative location.

D-954. `~` in an output path is expanded only for the existence check if `resolveFile` is used there. `fileExists` does call `resolveFile`, but `writeFile` uses the raw string. A `~` output path is therefore existence-checked in the home directory and written using the literal `~` string, which is not the home directory. Supported output paths do not rely on `~`. Config paths do use `resolveFile` for both the check and the load.

D-955. Supported config paths may use a leading `~`.

D-956. The default config names are exactly `~/.mdkit.json`, `~/.mdkit.js`, and `~/.mdkit/index.js` in that order.

D-957. A directory `~/.mdkit` is not itself loaded. Only `~/.mdkit/index.js` is.

D-958. JSON config is loaded by `require`, which returns the parsed object.

D-959. A JSON array is not a valid config object for `use`. `use` would treat it as an extension object only if it were passed through. Arrays are objects and would be iterated as extension packs incorrectly if passed as one argument. The supported config JSON is a plain object of options or an ESM/CJS function.

D-960. An ESM config must use a file extension Node will import, typically `.js` with the package or the file treated as ESM. The CLI does not rewrite extensions.

D-961. `pathToFileURL` is used for the import, so spaces and `#` in the absolute path are encoded as a file URL.

D-962. The hash-in-filename fixture loads successfully through this path when `require` throws `ERR_REQUIRE_ESM`, or through `require` when it does not.

D-963. The fixture enables `breaks`, and the HTML contains `<br>` between `line1` and `line2`.

D-964. There is no `<p>` around each line separately. Both lines are one paragraph.

D-965. The paragraph tags are `<p>` and `</p>`, and the break is `<br>` with no slash.

D-966. Default `line1\nline2` without that config is `<p>line1\nline2</p>\n`.

D-967. The CLI test for the config expects the break form, confirming the config was applied.

D-968. The same HTML is expected for `-c` and `--config`.

D-969. Positional file tests expect `<h1>file</h1>` under HTML equality.

D-970. Stdin tests expect `<h1>test</h1>` under HTML equality.

D-971. The string form tested by spawning the executable uses `-s "# test"` and expects the same heading.

D-972. Spawning the executable with the fixture path and with `-i` expects `<h1>file</h1>`.

D-973. The missing-file stderr in the unit test includes the resolved fixture path and the `mdkit: ` prefix and status 1. This specification spells that prefix `mdkit`.

D-974. The unit test’s HTML comparison is `htmlIsEqual`, so insignificant void-tag slash differences would pass. The implementation’s heading HTML has no void tag and is exactly `<h1>test</h1>\n` from the compiler, plus the CLI newline on stdout.

D-975. `htmlIsEqual` does not ignore text content. `test` versus `wrong` fails.

D-976. `htmlIsEqual` ignores a self-closing slash.

D-977. It does not ignore comments. Comments are significant.

D-978. Raw HTML comments in the Markdown therefore remain and are part of the comparison.

D-979. The timing suite’s expected HTML for 50 000 `a` characters is a single paragraph of those characters.

D-980. The timing suite’s expected HTML for 10 000 lines of `- a` is a single `<ul>` of 10 000 `<li>a</li>` items, compared as HTML, so newlines the renderer inserts between items are acceptable to the comparator. The bytes are `<ul>\n` plus `<li>a</li>\n` repeated plus `</ul>\n`.

D-981. The timing suite’s expected HTML for 101 underscores, a space, and `a` is a paragraph of that text, not emphasis.

D-982. Those inputs must not throw and must not hit the infinite-loop error.

D-983. They must finish in under one second on the runner’s clock, which is process hrtime, failing when the whole-second component is greater than 0.

D-984. Async compiles are exempt from that one-second assert.

D-985. The default compile is synchronous, so the limit applies to ordinary `parse`.

D-986. A correct implementation may use any algorithm that meets the HTML and the time limit. It does not have to use the same regular expressions, but the observable tokens and HTML must match.

D-987. `Lexer.rules` is still a public object. Code that reads `Lexer.rules.block.gfm.table` or similar receives the built-in regular expressions. A rebuild that exposes `Lexer.rules` must provide regular expressions that accept the same strings the tokenizer accepts for each named rule, or callers that reuse those expressions will diverge. The HTML contract does not require the expression source text to be identical.

D-988. The zero-indent helpers `nextBulletRegex(0)`, `hrRegex(0)`, `fencesBeginRegex(0)`, `headingBeginRegex(0)`, `htmlBeginRegex(0)`, and `blockquoteBeginRegex(0)` match `- item\n`, `---\n`, a fence opening, `# heading`, `<div>`, and `> quote` respectively.

D-989. Those helpers live on `lexer.tokenizer.rules.other`, which is the shared `other` rule record.

D-990. `rules.other` is the same object for every grammar. Only `block` and `inline` change with options.

D-991. `other.carriageReturn` matches `\r\n` and `\r`.

D-992. After normalization, no `\r` remains in token `raw` strings.

D-993. Token `raw` slices are taken from the normalized string, so they use `\n` only.

D-994. The original source’s `\r` is not recoverable from tokens.

D-995. HTML output uses `\n` only, never `\r`, except where raw HTML copied from the source contained `\r` that had already been normalized. Raw HTML is copied from the normalized source, so it also has `\n` only.

D-996. A raw HTML block therefore cannot preserve a CR LF pair. It is LF.

D-997. The CLI does not reintroduce CR when writing. The string is written as JavaScript produced it.

D-998. On Windows or any other platform, stdout is the JavaScript string encoded by the Node stream. The logical characters are `\n`.

D-999. The library does not call `process.exit`. Only the CLI does. Embedding `parse` in a server does not terminate the process.

D-1000. The library does not write the HTML to stdout by itself. The caller prints it. The CLI is the caller that writes stdout.

D-1001. Embedding `parse` does not read stdin.

D-1002. The classes `Lexer`, `Parser`, `Renderer`, `TextRenderer`, `Tokenizer`, and `Hooks` are constructible without `new Mdkit`.

D-1003. `new Renderer()` methods are the stock HTML methods.

D-1004. Replacing `renderer.heading` on that object and passing the object to `use` installs the replacement and keeps the other stock methods.

D-1005. The same is true of `Tokenizer` and `Hooks`.

D-1006. A tokenizer override that returns a heading token with custom text causes that text to be rendered by the stock heading renderer.

D-1007. A hooks `preprocess` that returns a constant string causes that string to be compiled instead of the input.

D-1008. Those class instances can be installed on the shared entry as well as on `new Mdkit()`, and each installation affects only that entry or instance.

D-1009. Installing the same renderer object on two compilers shares the object. A later write to `renderer.heading` is visible to both if both stored that object. `use` wraps methods on the object it is given when the object is already a renderer, so both compilers point at the wrapped object.

D-1010. The wrapper calls the user function first and, on `false`, the previous function.

D-1011. The previous function for the first wrap is the original prototype method.

D-1012. A second `use` that overrides the same method wraps again. The newest user function runs first, then the older user function, then the original.

D-1013. Arrow functions used as renderer methods do not see `this.options` and do not see `this.parser`.

D-1014. Method shorthand and `function` keywords do see them.

D-1015. The parser sets `renderer.parser` to itself before each `parse` and `parseInline`.

D-1016. Renderers can call `this.parser.parseInline(token.tokens)` to render children the way the stock methods do.

D-1017. `parseInline` of the parser does not re-enter block rules. It only walks inline token types.

D-1018. Giving `parseInline` a block token such as `hr` hits the unknown-inline-type path.

D-1019. Giving `parse` a purely inline token such as `strong` hits the unknown-block-type path unless an extension renderer claims that type.

D-1020. Checkbox tokens are legal in both walks. The block walk and the inline walk both have a `checkbox` case, because a tight list places the checkbox as a direct child of the item (block walk) and a loose list places it inside the paragraph (inline walk).

D-1021. Both cases call `renderer.checkbox`.

D-1022. An extension renderer for `checkbox` therefore affects both tight and loose lists.

D-1023. Returning a string from that extension replaces the input element.

D-1024. Returning `false` restores the input element.

D-1025. The extension may return `false` for some tokens and a string for others. Checked versus unchecked is visible on `token.checked`.

D-1026. `token.checked` is boolean.

D-1027. List items also copy `checked` onto the item when a checkbox is created.

D-1028. Non-task items omit `checked` or leave it undefined. They do not render an input.

D-1029. `item.task` is true only for recognized tasks.

D-1030. The stock list renderer does not read `item.task` or `item.checked`. It renders whatever child tokens exist.

D-1031. A caller can therefore remove the checkbox token in `walkTokens` and the input disappears.

D-1032. A caller can add tokens in `walkTokens` and they will render if their types are known.

D-1033. Changing `token.type` in `walkTokens` to another built-in type renders it as that type.

D-1034. The styled-paragraph example in that test produces `<p style="color:blue;">…</p>\n` and `<h1 style="color:red;">…</h1>\n` by rewriting the token into a custom type whose renderer edits the built-in HTML.

D-1035. That example removes a trailing `{color}` inline token before render so the braces are not shown.

D-1036. The braces form is an extension, not built-in syntax. Without the extension, `{blue}` is text.

D-1037. Underlines of the form `:text:` are an extension in the tests, not built-in syntax. Without the extension they are text or a definition-like paragraph.

D-1038. Built-in syntax does not have description lists, admonitions, or footnotes.

D-1039. Those can be added only by extensions the caller registers.

D-1040. The CLI loads extensions only through the config file’s `use` or function. It does not load a plugin directory.

D-1041. A config function that calls `mdkit.use(extension)` enables that extension for the CLI compile.

D-1042. The documented pattern of importing the library, calling `use`, then importing the CLI entry relies on the CLI using the shared instance. That pattern works when the CLI module is loaded after `use`.

D-1043. Importing the CLI entry runs `main(process)` immediately. The `use` must happen before that import, in the same process.

D-1044. Calling `main` again is not what the executable does. The executable calls it once.

D-1045. Tests call `main` with a fake process and a fake argv that begins with `node` and the script name, then the user arguments. `main` slices two entries off before parsing.

D-1046. The fake process must supply `cwd`, `env`, `argv`, `stdout.write`, `stderr.write`, `stdin` with `setEncoding`, `on`, and `resume`, and `exit`.

D-1047. `stdout.write` receives the full HTML or JSON including the extra newline as one or more writes. The implementation uses a single `write` of `html + '\n'`.

D-1048. `stderr.write` receives the error string as a single write.

D-1049. `exit` is called with 0 or 1 exactly once on those paths.

D-1050. The successful path does not write stderr.

D-1051. The failure path does not write stdout for the errors the unit tests cover (missing file, missing config).

D-1052. HTML equality in those tests allows the stdout string to differ from the expected fragment by a trailing newline and by void-tag slashes, but the assertions pass for the implementation’s actual strings.

D-1053. Missing-config stderr is exactly the `Cannot load config file` sentence with the path, with no `mdkit:` prefix and no extra newline added by the CLI beyond what `message` contains. The `Error` message has no trailing newline, and `stderr.write` adds none.

D-1054. The implementation constructs that failure with `throw Error(...)`, so `message` is the sentence and `name` is `Error`. The CLI prints only `message`.

D-1055. It does not print `error.stack`.

D-1056. It does not print the `Error:` name prefix.

D-1057. Compiler errors that flow out of `parse` as exceptions have the suffix inside `message`, and the CLI prints that full message, including the suffix and its newline.

D-1058. A silent compiler error does not throw, so the CLI treats it as success and writes the error HTML plus a newline to stdout, status 0.

D-1059. `--silent -s` with a valid string still compiles the string. Silent does not suppress HTML.

D-1060. Silent only changes the failure path.

D-1061. Valid Markdown never takes the failure path.

D-1062. The empty string is valid Markdown and is success.

D-1063. A string of only spaces is valid Markdown.

D-1064. A string that is only `null` the four letters is valid Markdown, a paragraph `null`. The value `null` is not valid.

D-1065. The number `0` is not a string and fails D-37. Its tag is `[object Number]`.

D-1066. A boolean fails the same way with `[object Boolean]`.

D-1067. An object fails with `[object Object]`.

D-1068. An array fails with `[object Array]`.

D-1069. A function fails with `[object Function]`.

D-1070. A symbol fails with `[object Symbol]`.

D-1071. The tag is produced by `Object.prototype.toString.call`, not by `typeof`.

D-1072. `typeof null` is `object`, but the null check happens first, so the message is the undefined-or-null message, not `[object Null]`.

D-1073. `undefined` uses that same message, not `[object Undefined]`.

D-1074. The check is `=== undefined || === null`, so document fragments that are strings containing the word undefined are compiled.

D-1075. No other input validation runs. A huge string is accepted and subject to the time the algorithm takes.

D-1076. The timing fixtures are the practical bound the test suite enforces.

D-1077. There is no maximum input length constant.

D-1078. There is no maximum token count constant.

D-1079. Output size is proportional to the rendered HTML of the input. The 10 000-item list produces one `<li>` per item.

D-1080. The implementation does not insert ellipses or truncate long paragraphs. 50 000 `a` characters are all present in the output.

D-1081. It does not pretty-print HTML. There is no indent option.

D-1082. Token JSON is the only pretty-printed output, and only when `--tokens` is set, with a fixed indent of 2.

D-1083. There is no flag to change that indent.

D-1084. There is no flag to minify HTML.

D-1085. There is no flag to select a different dialect name besides the `gfm`, `breaks`, and `pedantic` booleans.

D-1086. There is no CommonMark version flag. Non-pedantic behavior is the CommonMark 0.31.2 structure plus the serializer in this document.

D-1087. There is no GFM version flag. GFM behavior is the 0.29 extension set described here, minus disallowed raw HTML.

D-1088. Future CommonMark examples beyond 0.31.2 are not part of this contract.

D-1089. The example numbers in the CommonMark file run through the 0.31.2 suite of 652 examples.

D-1090. GFM extension example numbers in the fixture file include 198–205 for tables, 279–280 for tasks, 491–493 for strikethrough, 622–635 for autolinks, and 657 for disallowed raw HTML.

D-1091. Example 657 is the one that must fail equality with the reference.

D-1092. Its Markdown starts with `<strong> <title> <style> <em>` and includes a block quote containing `<xmp>` and `<XMP>`. mdkit does not turn those tags into text.

D-1093. `<strong>` in that position is inline HTML or text according to the normal rules, not a filtered tag.

D-1094. The suite’s `shouldFail` flag inverts the assertion: equality with the reference is a test failure.

D-1095. No other shipped fixture sets `shouldFail`.

D-1096. `renderOk` and `only` and `skip` are fixture-runner features. The shipped fixtures that set `renderExact` require byte equality. None of the shipped language fixtures require `renderOk`.

D-1097. `description` in front matter is ignored by the loader except as an unused attribute that remains in `options` if it was not deleted. The loader deletes only `skip` and `only`. A `description` key therefore becomes a parse option that the compiler ignores.

D-1098. Extra option keys do not change HTML.

D-1099. `renderExact: true` on a fixture is an option key the compiler ignores. The runner reads it before or while comparing, from the options object it merged. The compiler’s ignoring it does not stop the runner from seeing it on the options object it still holds. The HTML must still be byte-identical for those fixtures.

D-1100. Byte-identical fixtures include a trailing newline where the HTML file has one. The compiler’s block renderers supply those newlines.

D-1101. `new Hooks()` has `preprocess`, `postprocess`, `processAllTokens`, `emStrongMask`, `provideLexer`, and `provideParser`.

D-1102. `new Hooks()` stores the options it was given, or the module default object if none were given.

D-1103. `new Renderer()` stores options the same way.

D-1104. `new Tokenizer()` stores options the same way.

D-1105. `new Lexer()` without options uses the module default object as its options at the time of construction, which may be the pre-`setOptions` object. `Mdkit.lexer` passes the instance defaults explicitly, so it does not depend on that fallback.

D-1106. `Lexer.lex(src)` without options uses that same fallback. Callers who changed instance defaults via `Mdkit` should pass those defaults or call `instance.lexer`.

D-1107. The named export `lexer` is `Lexer.lex`, so `lexer(src)` uses the fallback options, not the shared instance’s defaults, unless they are the same object. After `setOptions` they may differ from a lexer constructed earlier. `mdkit.lexer` on the function is also `Lexer.lex` via the export assignment `mdkit.lexer = _Lexer.lex`. It is **not** `instance.lexer`. Calling `mdkit.lexer(src)` therefore uses `Lexer.lex`, which falls back to the module `_defaults` object when options are omitted.

D-1108. After `setOptions`, `changeDefaults` points `_defaults` at the instance defaults, so `Lexer.lex(src)` with no options then sees the updated defaults.

D-1109. Before `setOptions` or `use`, `_defaults` and the instance defaults are different objects with the same values, so the difference is invisible until something mutates one of them.

D-1110. `use` on the shared entry also calls `changeDefaults`, so after `use` the module `_defaults` is the instance defaults.

D-1111. `use` on a separate `Mdkit` instance does not call `changeDefaults` and does not change `Lexer.lex`’s fallback.

D-1112. `instance.lexer(src)` passes `instance.defaults` and does not use the module fallback.

D-1113. `instance.parse(src)` uses `instance.defaults` even when the module fallback differs.

D-1114. This is why two instances do not affect `mdkit.parse`.

D-1115. `parser` as a named export is `Parser.parse`, which uses the options argument or the module fallback renderer options.

D-1116. `instance.parser(tokens)` passes instance defaults.

D-1117. Rendering with the wrong defaults is visible when `breaks` or extensions changed the tokens, not when the stock renderer ignores `gfm`. The stock renderer does not branch on `gfm`. Grammar differences are already baked into the tokens.

D-1118. The stock renderer does not read `breaks`, `pedantic`, or `gfm`.

D-1119. It reads `this.options` only as stored state for extensions that look at `this.options`. The stock methods listed do not branch on those flags.

D-1120. Checkbox HTML does not depend on a renderer option. It depends on the token existing.

D-1121. Language class HTML does not depend on a `langPrefix` option. The prefix is fixed.

D-1122. Escaping does not depend on an option. There is no `mangle` switch in the renderer.

D-1123. `silent` is not read by the renderer. It is read by the lexer, the parser, and the `parse` wrapper.

D-1124. A direct `Parser.parse` of an unknown token throws or returns `""` based on `options.silent`, without the `parse` wrapper’s HTML error page. When `silent` is false it throws the short message. When `silent` is true it logs and returns `""`.

D-1125. That `""` is different from the wrapper’s `<p>An error occurred:</p><pre>…</pre>`, which is used only when `parse` catches a throw.

D-1126. If the parser returns `""` because of a silent unknown token, `parse` returns `""` and does not wrap it.

D-1127. If the parser throws, `parse` wraps.

D-1128. Unknown token with `silent: false` throws, so `parse` wraps that throw and the caller sees the suffix.

D-1129. Unknown token with `silent: true` does not throw, so the caller sees `""` from `parse`, not the error HTML.

D-1130. This split is observable and easy to get wrong: silent unknown tokens are empty output plus a console error, while silent input-type errors are the error HTML and no console error.

D-1131. Input-type errors do not write to `console.error`.

D-1132. They throw or return the error HTML only.

D-1133. Infinite-loop errors write to `console.error` only when `silent` is true. When `silent` is false they throw and do not also log.

D-1134. The log message and the thrown message are the same sentence before any suffix. The suffix is added only if something catches the throw and appends it. The lexer throws before appending. `parse` appends after catching.

D-1135. `console.error` of the silent infinite-loop message does not include the suffix, because the lexer logs before any wrapper.

D-1136. `console.error` of the silent unknown-token message does not include the suffix.

D-1137. The error HTML for a thrown infinite-loop error does include the suffix, and the logged line does not, because silent infinite-loop does not throw.

D-1138. Non-silent infinite-loop thrown through `parse` includes the suffix and is not logged.

D-1139. Extensions that throw inside `preprocess` follow the thrown path, not the lexer log path.

D-1140. Extensions that throw inside a renderer follow the thrown path.

D-1141. The message of a user-thrown error is preserved and the suffix is appended.

D-1142. If the thrown value is not an Error, the wrapper still assigns `message` and may throw when reading it. Supported failures are Error objects. The wrapper’s parameter type is `Error`.

D-1143. `onError` returns a function used both as a sync catch handler and as a Promise rejection handler.

D-1144. In async silent mode the handler returns `Promise.resolve(html)` rather than the html string, so the caller’s Promise fulfills.

D-1145. In async non-silent mode it returns `Promise.reject(error)`.

D-1146. In sync silent mode it returns the html string.

D-1147. In sync non-silent mode it throws.

D-1148. The decision uses the merged options’ `silent` and `async` flags from the start of the call, not flags a hook changes later.

D-1149. A hook that sets `silent` during `preprocess` does not change the wrapper chosen for that call.

D-1150. A hook that sets `async` during `preprocess` does not switch the already-chosen sync or async pipeline.

D-1151. The pipeline is chosen by `opt.async` after the merge, before hooks run.

D-1152. `opt.async` is true if the call passed true or the instance default is true.

D-1153. The conflict check uses `this.defaults.async` and the original call’s `async` before considering the merge’s other fields. If the instance is async and the call explicitly says `async: false`, it fails even if other call options are set.

D-1154. If the instance is not async and the call says `async: true`, there is no conflict. The call is async.

D-1155. If neither says true, the call is sync.

D-1156. `async: false` on a non-async instance is sync.

D-1157. Omitting `async` uses the instance value.

D-1158. The CLI omits `async` unless `--async` or `--no-async` was passed.

D-1159. `--no-async` sets `async: false` on the call. If a config `use` set async true, the CLI call throws the conflict error and exits 1, printing the message and suffix.

D-1160. `--async` sets the call to async and the CLI awaits the Promise before writing.

D-1161. A config that sets `async: true` without a CLI override makes the CLI await as well, because `parse` returns a Promise and the CLI awaits `marked.parse`.

D-1162. The await is unconditional. Awaiting a string still yields the string, so sync compiles work.

D-1163. Token mode also awaits `marked.lexer`, which is synchronous and returns an array. `JSON.stringify` of that array is the output.

D-1164. `marked.lexer` does not return a Promise in the stock implementation. Async hooks are not consulted by `lexer`, because `lexer` is `Lexer.lex`, not `instance.parse`.

D-1165. CLI `--tokens` therefore does not run `preprocess`, `walkTokens`, or `postprocess`. It lexes the raw string.

D-1166. CLI HTML mode does run hooks installed by the config, because it calls `parse`.

D-1167. A config `preprocess` changes HTML mode and does not change `--tokens` mode.

D-1168. A config renderer changes HTML mode and does not change `--tokens` mode.

D-1169. A config tokenizer changes both, because both HTML mode and token mode ultimately lex with the instance tokenizer if `parse` or a lexer that received instance options is used. `--tokens` calls `marked.lexer(data, options)`, and `marked.lexer` is `Lexer.lex`, which constructs a new lexer with the per-call options only. Those options include CLI flags but **do not** automatically include the tokenizer installed on the instance unless it was copied into the per-call object. `Lexer.lex(data, options)` uses `options` as given. The CLI `options` object contains only the flags it parsed, not `instance.defaults`. A tokenizer installed with `use` is on `instance.defaults`, not on the CLI flag object.

This means CLI `--tokens` and CLI `parse` do **not** behave the same with extensions:

- `parse(data, flagOptions)` merges `instance.defaults` with flag options, so `use`’d tokenizers and renderers apply.
- `lexer(data, flagOptions)` does **not** merge instance defaults. It uses only flag options.

D-1170. Therefore a config that only calls `use({ tokenizer })` affects `mdkit -s` HTML, and does not affect `mdkit --tokens` unless the tokenizer is also somehow in the flag object, which the CLI never does.

D-1171. A config that calls `setOptions({ gfm: false })` updates `_defaults` via the shared `setOptions`. `Lexer.lex` without relying on the flag object then sees `gfm: false` through the module fallback **only when the CLI omits the options argument**. The CLI always passes the flag object, even when it is empty. An empty options object is used instead of the fallback, because the code is `options ?? this.defaults` inside instance.lexer, but `Lexer.lex(src, options)` receives the object the CLI built, and the lexer constructor does `this.options = options || _defaults`. An empty object is truthy, so `_defaults` is **not** used. Grammar selection then reads `options.pedantic`, `options.gfm`, and `options.breaks`, which are `undefined`. `undefined` is falsy, so the grammar is the normal CommonMark grammar, **not** the GFM default, whenever `--tokens` is used without also passing `--gfm`.

That is a CLI `--tokens` quirk: omitted boolean flags are `undefined` on the object passed to `Lexer.lex`, and `undefined` does not select GFM.

D-1172. HTML mode does not have that quirk. `parse` merges instance defaults, and the instance default `gfm` is true, so HTML mode is GFM unless `--no-gfm` or a config turned it off.

D-1173. `--tokens --gfm` passes `gfm: true` and selects the GFM grammar.

D-1174. `--tokens` without `--gfm` passes an options object without `gfm` and selects the normal grammar. Tables, strikethrough, and extended autolinks are not tokenized.

D-1175. This difference is observable by comparing `mdkit -s '| a | b |\n| --- | --- |'` (a table) with `mdkit --tokens -s '| a | b |\n| --- | --- |'` (not a table token).

D-1176. `--tokens --pedantic` selects the pedantic grammar.

D-1177. `--tokens --breaks` without `--gfm` does not select the breaks grammar, because `gfm` is undefined and the breaks branch requires `gfm` to be true.

D-1178. `--tokens --gfm --breaks` selects the breaks inline grammar.

D-1179. HTML mode `--breaks` without any gfm flag still breaks lines, because the merged default `gfm` is true.

D-1180. Callers of `Lexer.lex(src, {})` get the normal grammar, not GFM. Callers of `Lexer.lex(src)` get whatever `_defaults` currently says. Callers of `mdkit.parse(src)` get GFM by default.

D-1181. `new Lexer({}).lex(src)` matches `Lexer.lex(src, {})`.

D-1182. `new Lexer().lex(src)` matches `Lexer.lex(src)` and uses `_defaults`.

D-1183. After shared `setOptions({ gfm: false })`, `new Lexer().lex` and `Lexer.lex(src)` see `gfm: false`.

D-1184. `new Mdkit().lexer(src)` still passes that instance’s own defaults, which still have `gfm: true` if that instance was not modified.

D-1185. The CLI HTML path is `parse`, so it follows the instance, not the empty-object lexer quirk.

D-1186. The CLI token path is the empty-object-or-flags lexer quirk in D-1171.

D-1187. Documented `--tokens` output for the one-letter input `a` is a paragraph token, which both grammars produce, so the quirk is invisible on that input.

D-1188. It is visible on `| a |` plus a delimiter line, on `~~a~~`, on `www.example.com`, and on `- [x] a`.

D-1189. Implementations must reproduce that CLI split: HTML mode merges defaults; token mode passes only the explicit flags into `Lexer.lex`.

D-1190. `mdkit.lexer` in JavaScript is the same `Lexer.lex` the CLI calls, not `instance.lexer`.

D-1191. `instance.lexer` is a different function that does merge by passing `this.defaults` when the argument is omitted, and passes the argument through when it is present. `Lexer.lex(src, options)` uses the argument as the full option set.

D-1192. `instance.lexer(src, {})` therefore also drops GFM, because the empty object is passed through (`options ?? this.defaults` uses `{}` when the argument is present).

D-1193. `instance.lexer(src)` keeps instance defaults.

D-1194. `??` treats only `null` and `undefined` as missing. `{}` is used as-is.

D-1195. `parse(src, {})` still merges, so `{}` does not drop `gfm`. The merge is `{ ...defaults, ...{} }`, which keeps `gfm: true`.

D-1196. `parse(src, null)` is treated as options present in the type union. The implementation spreads `origOpt`, and spreading `null` in the object literal `{ ...this.defaults, ...null }` is a no-op in JavaScript, so `null` options keep the defaults. `parse`’s parameter default is not applied when `null` is passed, but the spread ignores it.

D-1197. `parse(src, undefined)` uses the default parameter behavior only if the implementation’s signature supplies it. The body always does `const origOpt = { ...options }`. Spreading `undefined` yields `{}`, then merging defaults keeps defaults. `parse(src)` and `parse(src, undefined)` and `parse(src, null)` all compile with instance defaults.

D-1198. They do not throw.

D-1199. `parse()` with no string throws the undefined-input error.

D-1200. The CLI never calls `parse` without a string. Stdin at EOF yields `''`, which is a string.

## 5. Relationships

- **Runtime:** Node.js 20 or newer for the CLI and for `require` of the ESM build. A browser can load the UMD build.
- **What it reads:** Markdown strings from the caller; CLI stdin; CLI input files; one optional config file; the manual page via `man` or, if `man` cannot be spawned, the shipped manual Markdown.
- **What it writes:** HTML or token JSON to stdout or to the `-o` file; diagnostics to stderr; the process title; `console.error` only for the silent lexer and parser cases in section 3.5.
- **Libraries:** the CLI uses Node’s `fs`, `path`, `os`, `module`, `url`, and `child_process`. The compiler itself does not require a Markdown library, a sanitizer, or a network stack. The test suite (not the program) compares HTML with an HTML differ that ignores void-element slashes.
- **Integration:** other programs import the module, call `parse` or `parseInline`, or spawn the `mdkit` executable. Extensions are plain objects passed to `use`. Workers are the caller’s responsibility.
- **Standards:** CommonMark 0.31.2 is the structural target when `pedantic` is false. GFM 0.29 tables, task lists, strikethrough, and autolinks are the structural target when `gfm` is true and `pedantic` is false. Byte-level HTML follows section 3.8, not the CommonMark reference serializer and not the GFM raw-HTML filter.

## 6. Unknowns

- U-1. The formatted roff manual is not in the source tree, so the exact bytes `man` would show after a release build that generates it were not observed. Default reading: `--help` behavior is the spawn described in D-14, and the fallback text is section 3.1.7.
- U-2. HTML-parser equivalence hides some byte differences from the language fixtures (newlines inside `<li>`, named entities, `&#39;` versus a raw apostrophe in a reference file). Where this document gives bytes, the bytes win. Where it only says the fixture matches, either byte form that the shipped HTML differ accepts is enough to pass that fixture, but a compatible mdkit emits the stock renderer’s bytes.
- U-3. Engines without `RegExp` lookbehind use a fallback in the emphasis mask for code spans. The difference was not executed here. Default reading: modern Node 20 and current browsers take the lookbehind path. Evidence of the branch: `src/rules.ts:33-41`, `src/rules.ts:314-318`.
- U-4. A config file whose `require` fails for a reason other than `ERR_REQUIRE_ESM` was not catalogued. Default reading: the error’s `message` is printed and the status is 1, unless `code` is `ENOENT`.
- U-5. Whether `man`’s missing-page wording is stable across operating systems was not compared. The CLI does not generate that wording.

## 7. Left free

- Module layout, file names inside the package, and bundling, as long as the exports and the `mdkit` executable behave as specified.
- The regular-expression source text, provided tokens and HTML match and the timing fixtures finish in under a second.
- Data structures used to walk the source, provided the observable token fields and HTML match.
- Source maps, comments, and license banners inside build artifacts.
- Whether `Lexer.rules` expressions are identical as text. Their accept sets for the named rules that tests touch must match.
- Documentation websites, demos, and publishing scripts. They are not part of the compiler or the CLI.

SPEC WRITTEN: 1200 claims, 5 unknowns
