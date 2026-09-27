# Web UI frameworks

Return to the [guidance selector](../coding-guidance.md#select-guidance) when the host or framework changes.

Identity and authorization here means the host's execution sandbox, not a login system. Apps Script HtmlService content renders inside an IFRAME-sandboxed page ([developers.google.com](https://developers.google.com/apps-script/guides/html/restrictions)). Salesforce LWC runs under Lightning Web Security by default, which gives code a sandboxed copy of browser globals with no access to the real `window` object, so most third-party libraries "work as expected without changes" but anything relying on the true global window can break ([LWS intro](https://developer.salesforce.com/docs/platform/lightning-components-security/guide/lws-intro.html)).

State, consistency, and concurrency are largely out of scope for a framework choice itself: React, Vue, and Svelte supply only component and reactivity primitives, with no built-in state store or theming layer. Next.js and SvelteKit add routing, SSR/SSG, and server actions on top of React or Svelte respectively, but only when a full-stack meta-framework is deliberately chosen rather than a plain component library.

Connectivity is about how UI code and assets actually reach the rendered page. In Apps Script, external scripts and stylesheets must load over HTTPS, so a CDN `<script src="https://...">` works, but Apps Script provides no build step, so JSX- or SFC-based frameworks must be pre-compiled elsewhere or used as UMD/CDN builds with plain `<script>` tags; top-level navigation also needs `<base target="_top">` or explicit `target` attributes ([developers.google.com](https://developers.google.com/apps-script/guides/html/restrictions)). In Salesforce LWC, third-party JS/CSS cannot be pulled from a live CDN tag at all — it must be uploaded as a static resource and loaded via `lightning/platformResourceLoader`'s `loadScript`/`loadStyle` ([platformResourceLoader guide](https://developer.salesforce.com/docs/platform/lwc/guide/js-third-party-library.html)). Bootstrap fits the Apps Script CDN path with no build step; Tailwind's Play CDN is documented by Tailwind itself as dev-only, not for production, so it is a poor fit for a real Apps Script UI unless the CSS is pre-built elsewhere ([Play CDN docs](https://tailwindcss.com/docs/installation/play-cdn)).

Caching, secrets, and scheduled or background work are not distinguishing factors for choosing among these UI frameworks; nothing in their scope touches server-side data freshness, credential storage, or retryable jobs, so a single-user, client-only product needs none of that machinery to pick a component library or CSS engine.

Accessibility is a limit worth checking directly rather than assuming: Bootstrap ships guidance but still requires developers to add correct ARIA states themselves, and color-mode contrast is not auto-checked ([getbootstrap.com](https://getbootstrap.com/docs/5.3/getting-started/introduction/)); MUI v9 lists accessibility improvements as a stated release focus ([mui.com/blog/introducing-mui-v9](https://mui.com/blog/introducing-mui-v9/)); SLDS 2 is described as aligning with WCAG 2.2 ([Salesforce Ben](https://www.salesforceben.com/salesforce-dark-mode-is-back-what-admins-need-to-know/)); React, Vue, Svelte, and Tailwind provide no built-in accessibility guarantee at all.

Local development in a normal browser does not prove behavior inside a restricted host: it does not establish whether a library survives Apps Script's iframe sandbox or LWC's windowless sandbox, whether a CDN script will actually load under the target host's rules, or whether SLDS 2 is even activated for a given Salesforce org, since it is GA but opt-in, not the default ([release notes](https://help.salesforce.com/s/articleView?id=release-notes.rn_slds_slds2.htm)).

## Current facts (as of 2026-09-26)

- Bootstrap 5.3.8 stable; Bootstrap 6 is only an unreleased `v6-dev` alpha, not on npm — [getbootstrap.com](https://getbootstrap.com/docs/5.3/getting-started/introduction/)
- Material Web (`@material/web`) is in maintenance mode — [GitHub discussion #5642](https://github.com/material-components/material-web/discussions/5642)
- MUI v9 (9.4.0), released April 8, 2026 — [mui.com/blog/introducing-mui-v9](https://mui.com/blog/introducing-mui-v9/)
- Angular Material M3 theming stable since v18, theming API expanded in v19 — [Angular blog](https://blog.angular.dev/material-3-experimental-support-in-angular-17-2-8e681dde650e)
- React 19.3 (Sept 9, 2026) — [react.dev/versions](https://react.dev/versions)
- Next.js 16.3.1 — [Next.js blog](https://nextjs.org/blog)
- Vue 3.5.x stable; 3.6 in RC (`3.6.0-rc.6`) — [npm vue](https://www.npmjs.com/package/vue?activeTab=versions)
- Svelte 5.56.x / SvelteKit 2.70.x; SvelteKit 3 preview exists — [svelte.dev/blog](https://svelte.dev/blog)
- Tailwind CSS v4 (~4.3.3), CSS-first `@theme` config — [tailwindcss.com/blog/tailwindcss-v4](https://tailwindcss.com/blog/tailwindcss-v4)
- SLDS 2 GA as of Winter '26, opt-in per org — [Salesforce release notes](https://help.salesforce.com/s/articleView?id=release-notes.rn_slds_slds2.htm)

Recheck these against the linked pages when they matter to a decision.

## Claims to check

- "Bootstrap 6 is out" — false; still an unreleased alpha branch ([Bootstrap Studio blog](https://canvastemplate.com/blog/bootstrap-2026)).
- "Material Web components are deprecated/abandoned" — false; Google calls it maintenance mode, not deprecated ([GitHub discussion #5642](https://github.com/material-components/material-web/discussions/5642)).
- "MUI v9 fully supports Material Design 3" — false; MUI still implements M2 as its baseline, with M3 delayed past its original 2024 target ([GitHub issue #29345](https://github.com/mui/material-ui/issues/29345)).
- "Any npm package will just work in LWC" — false; it must be uploaded as a static resource and loaded via `platformResourceLoader`, and window-dependent libraries may break under LWS ([developer.salesforce.com](https://developer.salesforce.com/docs/platform/lwc/guide/js-third-party-library.html)).
- "SLDS 2 is now the Salesforce default" — false; GA but opt-in per org/theme as of Winter '26 ([Salesforce release notes](https://help.salesforce.com/s/articleView?id=release-notes.rn_slds_slds2.htm)).
- "Tailwind's CDN script is fine for a production Apps Script app" — false per Tailwind's own docs, which mark Play CDN dev-only ([tailwindcss.com/docs/installation/play-cdn](https://tailwindcss.com/docs/installation/play-cdn)).
- "Tailwind v4 still needs `tailwind.config.js`" — misleading; CSS-first `@theme` config is now the default path, with JS config legacy/optional ([tailwindcss.com/blog/tailwindcss-v4](https://tailwindcss.com/blog/tailwindcss-v4)).
