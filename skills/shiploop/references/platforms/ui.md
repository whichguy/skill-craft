# UI development

Use the [guidance selector](../coding-guidance.md#select-guidance) for a UI
runtime or boundary. Aim high: a plain, static, form-and-button screen is an
unfinished interface, not a safe default. Build a distinctive, highly
interactive experience: direct manipulation, inline editing, live previews,
drag and drop where it fits the task, keyboard paths for frequent actions,
optimistic feedback reconciled with the confirmed result, and expressive
animated transitions between states. Design every loading, empty, error and
success state. Scale back only for a stated user constraint, a target runtime
limit, or accessibility, and record which one. Preserve accepted component, interaction, and visual
premises. Separate editable drafts,
request state, and accepted server state; name which response may update each
surface. With overlapping requests or changed identity, prevent superseded
results and errors from replacing the latest accepted state. Cancellation does
not undo a server effect.

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
