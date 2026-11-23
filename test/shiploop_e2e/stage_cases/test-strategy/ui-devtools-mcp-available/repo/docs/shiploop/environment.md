# Environment

## Runtime and tools

- Local Node.js is installed and runs the existing unit suite via `node --test` (`node:test`, zero external npm dependencies).
- Local Chrome is installed at `/Applications/Google Chrome.app/Contents/MacOS/Google Chrome` and can run standalone headless browser test scripts over Chrome DevTools Protocol (CDP) or a local test runner.
- Chrome DevTools MCP (`chrome-devtools` MCP server) is configured on the host for interactive browser inspection, DOM snapshots, and click/key commands.

## Commands

```sh
node --test
```
