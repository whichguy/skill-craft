---
bump: patch
---
The test-strategy duty now says a host-dependent tool (a browser, a device, an account, a service) is probed against a stand-in, such as a one-line page opened by `file:` URL or from a throwaway static server, when the product does not exist yet; a request to the product's own address says nothing about the tool.
