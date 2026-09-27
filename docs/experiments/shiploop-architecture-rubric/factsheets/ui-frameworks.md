# Client-Side UI Frameworks — Fact Sheet

## Versions
- **Bootstrap 5.3.8** current stable; Bootstrap 6 is only an in-progress `v6-dev` alpha (`6.0.0-alpha1`), not yet on npm. [getbootstrap.com](https://getbootstrap.com/docs/5.3/getting-started/introduction/) / [Bootstrap Studio blog](https://canvastemplate.com/blog/bootstrap-2026)
- **Material Web** (`@material/web`): in maintenance mode, no active feature development. [GitHub discussion #5642](https://github.com/material-components/material-web/discussions/5642)
- **MUI v9** (9.4.0), released April 8, 2026. [mui.com/blog/introducing-mui-v9](https://mui.com/blog/introducing-mui-v9/)
- **Angular Material**: M3 theming experimental in v17.2, stable since v18, theming API expanded in v19. [Angular blog](https://blog.angular.dev/material-3-experimental-support-in-angular-17-2-8e681dde650e) / [GitHub issue #24395](https://github.com/angular/components/issues/24395)
- **React 19.3** (Sept 9, 2026). [react.dev/versions](https://react.dev/versions)
- **Next.js 16.3.1**, on the Next 16 line (Turbopack default, React 19.2). [Next.js blog](https://nextjs.org/blog)
- **Vue 3.5.x** stable; 3.6 in RC (`3.6.0-rc.6`, Aug 28, 2026). [npm vue](https://www.npmjs.com/package/vue?activeTab=versions)
- **Svelte 5.56.x** / **SvelteKit 2.70.x**; SvelteKit 3 preview exists. [svelte.dev/blog](https://svelte.dev/blog)
- **Tailwind CSS v4** (~4.3.3), CSS-first `@theme` config, Oxide (Rust) engine. [tailwindcss.com/blog/tailwindcss-v4](https://tailwindcss.com/blog/tailwindcss-v4)

## What each provides
- **Bootstrap**: prebuilt components (navbar, modal, cards, forms), grid, utility classes, built-in **color modes** (light/dark/auto) since 5.3; JS components (dropdown, tooltip, popover) depend on **Popper.js v2**, bundled in `bootstrap.bundle.min.js`. [getbootstrap.com](https://getbootstrap.com/docs/5.3/getting-started/introduction/)
- **Material Web**: web-component (Lit) implementations of M3 components, but frozen feature set. [material-web.dev](https://material-web.dev/)
- **MUI**: React component library still primarily implementing **Material Design 2**; M3/"Material You" adoption has been repeatedly delayed past its original end-2024 target and is not delivered as of v9. [GitHub issue #29345](https://github.com/mui/material-ui/issues/29345)
- **Angular Material**: token-based M3 theming via CSS custom properties, with M2 still fully supported side-by-side. [angular.love](https://angular.love/angular-material-theming-application-with-material-3)
- **React/Vue/Svelte**: component/reactivity primitives, no built-in design system or theming layer.
- **Next.js/SvelteKit**: full-stack meta-frameworks (routing, SSR/SSG, server actions) on top of React/Svelte.
- **Tailwind**: utility-class engine plus config surface (`@theme`, `@import "tailwindcss"`), no components or JS runtime.

## Fit in restricted hosts (Apps Script, Salesforce)
- **Google Apps Script HtmlService**: content renders inside an `IFRAME`-sandboxed page; external scripts/stylesheets **must load over HTTPS** (CDN `<script src="https://...">` works fine); no build step is provided by Apps Script itself, so React/Vue JSX or SFCs must be pre-compiled elsewhere (or you use UMD/CDN builds and plain `<script>` tags); top-level navigation needs `<base target="_top">` or explicit `target` attributes. [developers.google.com](https://developers.google.com/apps-script/guides/html/restrictions)
  - Practical fit: Bootstrap via CDN works out-of-the-box (no build step needed); Tailwind's Play CDN is explicitly **dev-only, not for production** per Tailwind's own docs, so it's a poor fit for a real Apps Script UI unless you pre-build the CSS elsewhere. [tailwindcss.com/docs/installation/play-cdn](https://tailwindcss.com/docs/installation/play-cdn)
- **Salesforce LWC**: default security model is **Lightning Web Security (LWS)**; most third-party libraries "work as expected without changes," but code has **no access to the global `window` object** — only a sandboxed copy — so DOM-global-dependent libraries can break. Third-party JS/CSS must be uploaded as a **static resource** and loaded via `lightning/platformResourceLoader`'s `loadScript`/`loadStyle`, not a live CDN `<script>` tag. [developer.salesforce.com — LWS intro](https://developer.salesforce.com/docs/platform/lightning-components-security/guide/lws-intro.html) / [platformResourceLoader guide](https://developer.salesforce.com/docs/platform/lwc/guide/js-third-party-library.html)
  - Native design system is **SLDS**; **SLDS 2 is GA as of Winter '26** but is an **opt-in** activation, not the org-wide default yet (group-based activation arrives Winter '27). [Salesforce release notes](https://help.salesforce.com/s/articleView?id=release-notes.rn_slds_slds2.htm) / [Salesforce blog](https://www.salesforce.com/blog/experience-design-with-slds-2/)

## Accessibility
- Bootstrap ships accessibility guidance but components still require developers to add correct ARIA states/labels themselves; color-mode contrast isn't automatically WCAG-checked. [getbootstrap.com](https://getbootstrap.com/docs/5.3/getting-started/introduction/)
- MUI v9 lists accessibility improvements as a stated focus of the release. [mui.com/blog/introducing-mui-v9](https://mui.com/blog/introducing-mui-v9/)
- SLDS 2 is described by Salesforce as aligning with **WCAG 2.2** and adds a Dark Mode (Beta) aimed at low-vision/light-sensitive users. [Salesforce Ben](https://www.salesforceben.com/salesforce-dark-mode-is-back-what-admins-need-to-know/) / [Trailhead](https://trailhead.salesforce.com/content/learn/modules/dark-mode-ready-components-in-slds-2/activate-slds-2-and-preview-dark-mode)
- Apps Script's IFRAME sandbox itself doesn't hinder assistive tech, but focus/keyboard management inside the iframe (e.g., after blocked top-navigation) is the developer's responsibility. [developers.google.com](https://developers.google.com/apps-script/guides/html/restrictions)
- React/Vue/Svelte/Tailwind provide no built-in accessibility guarantees — semantic HTML and ARIA remain the developer's job in all four. **Unverified**: any specific WCAG conformance level for React/Vue/Svelte core itself (none of these projects publish one).

## Common false claims
- "Bootstrap 6 is out" — false; still an unreleased alpha branch. [Bootstrap Studio blog](https://canvastemplate.com/blog/bootstrap-2026)
- "Material Web components are deprecated/abandoned" — false; Google calls it **maintenance mode**, not deprecated. [GitHub discussion #5642](https://github.com/material-components/material-web/discussions/5642)
- "MUI v9 fully supports Material Design 3" — false; MUI still implements M2 as its baseline, with M3 adoption delayed past its original 2024 target. [GitHub issue #29345](https://github.com/mui/material-ui/issues/29345)
- "Any npm package will just work in LWC" — false; it must be uploaded as a static resource and loaded via `platformResourceLoader`, and libraries relying on the global `window` may break under LWS. [developer.salesforce.com](https://developer.salesforce.com/docs/platform/lwc/guide/js-third-party-library.html)
- "SLDS 2 is now the Salesforce default" — false; it's GA but opt-in per org/theme as of Winter '26. [Salesforce release notes](https://help.salesforce.com/s/articleView?id=release-notes.rn_slds_slds2.htm)
- "Tailwind's CDN script is fine for a production Apps Script app" — false per Tailwind's own docs (Play CDN = dev only). [tailwindcss.com/docs/installation/play-cdn](https://tailwindcss.com/docs/installation/play-cdn)
- "Tailwind v4 still needs `tailwind.config.js`" — false/misleading; CSS-first `@theme` config is now the default path, JS config is legacy/optional. [tailwindcss.com/blog/tailwindcss-v4](https://tailwindcss.com/blog/tailwindcss-v4)

## As of
2026-09-26. All version numbers and status claims above were verified against official sources on this date; anything not independently confirmed is explicitly marked "unverified."
