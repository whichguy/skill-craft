# Architecture

## AD-1: Plain HTML/CSS/JS with no build step

Keep the repository plain HTML, CSS, and JavaScript with no bundler, no transpiler, and zero external npm dependencies. Browser scripts run directly from `index.html`, and pure helpers remain CommonJS-compatible for `node --test`.
