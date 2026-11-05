# UI development

Use the [guidance selector](../coding-guidance.md#select-guidance) for a UI
runtime or boundary. Aim high: a plain, static, form-and-button screen is an
unfinished interface, not a safe default. Build a distinctive, highly
interactive experience: direct manipulation, inline editing, live previews, drag
and drop where it fits the task, keyboard paths for frequent actions, optimistic
feedback reconciled with the confirmed result, and expressive animated
transitions between states. Design every loading, empty, error and success
state. Scale back only for a stated user constraint, a target runtime limit, or
accessibility, and record which one. Preserve accepted component, interaction,
and visual premises. Separate editable drafts, request state, and accepted
server state; name which response may update each surface. With overlapping
requests or changed identity, prevent superseded results and errors from
replacing the latest accepted state. Cancellation does not undo a server effect.

Prefer native controls or maintained accessible primitives before custom
interaction code. Verify accessible names, keyboard behavior, focus ownership
and return, pending/error status, and applicable reduced-motion behavior in the
composed UI. Exercise rendered outcomes through stable semantic queries and
controlled response completion; avoid arbitrary sleeps and implementation
selectors where a user-facing contract exists. [Playwright's guidance](https://playwright.dev/docs/best-practices)
supports isolated, user-visible checks, but DOM or ARIA assertions alone are
not a complete accessibility audit.

Keep feature ownership and dependency direction explicit without copying a
whole application's folder tree. Start with local state where it fits; introduce
a shared store, memoization, or virtualization for a demonstrated need.
When delivery matters, verify production assets, routing, and host restrictions:
a development server is not deployment evidence.

Custom element names, `window` globals, unscoped CSS classes and storage keys
are shared across the whole page or origin, including third-party scripts. Use
the house scoping (CSS modules, shadow DOM, a class prefix) and a prefix for
storage keys, and do not add globals to pass data between modules.

## Light expressive starting point

For a new graphical UI, fill unspecified visual choices from this profile.
Explicit visual constraints, established product identity and platform conventions
take precedence. Inspect
existing interfaces and tokens before choosing: missing design documents do
not erase an accepted identity, and a new screen within an existing product
inherits it. Treat a template as an unstyled starter only when the request or
repository evidence establishes that it is new; plain styling alone does not
justify a redesign. Respect authorized scope. Terminal interfaces and static
rendered documents keep their own medium's conventions. For a new web UI without
an appearance requirement, present light first and retain the required dark
option; native interfaces follow their platform's appearance policy. Retain
accessibility obligations.

Target the light Google Gemini look and feel using Material 3 Expressive
principles: airy composition, tonal rounded surfaces, friendly precise type,
confident primary actions, subtle luminous accents and purposeful transitions.
Adapt this reference to the product's own name, content and identity; it mandates
no toolkit, exact palette or layout. Record concrete choices through the existing
[UI design procedure](../plan-record.md#concrete-ui-direction). Implementation
applies the choices selected by the step's criteria, not a new concept.

Use a luminous light canvas, subtly tinted layered surfaces, generous but disciplined space, confident typographic hierarchy, precise alignment, and a restrained saturated accent. Place tonal surfaces across the working composition where they distinguish navigation, activity and supporting material; a palette list alone does not determine their visible effect. Combine softly rounded containers with smaller controls in a deliberate shape hierarchy; depth should distinguish layers. Use gradients only where they direct attention or explain state. Choose a clear, humanist or geometric sans-serif using available local fonts, with readable fallbacks.
Give the user's primary activity the strongest position and visual weight. For example, a game centers the board, resolved pieces, player/turn state and compact controls; a chat app centers readable message groups, threads, artifacts and a reachable composer; a work app centers its content and next action. Make supporting information quieter while preserving required text and control contrast. Let the product's content determine the layout.
Create one memorable, useful visual signature: for example a crafted board frame, integrated turn indicator, or unusually clear selection treatment. Resolve selected, disabled, hover, keyboard focus and completion states as part of the same system. Use short, responsive motion only to clarify change. The mobile composition must feel intentionally designed, with the primary task and next action prominent.
When planning acceptance for the selected choices, describe the visible focal point, typography hierarchy, balanced density, consistent details and task-specific character. Check the rendered result against those choices; use the existing correction route if they need revision. Record concrete decisions in the AD, not only adjectives like modern or premium.
