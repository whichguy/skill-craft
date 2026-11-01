---
bump: patch
---
The Salesforce platform guide gains a `CLI login` section: the CLI's login key lives in the macOS keychain, so in any
other HOME (an isolated profile, a sandbox, CI) an org command hangs on a modal "Keychain Not Found" dialog; such a HOME
sets `SF_USE_GENERIC_UNIX_KEYCHAIN=true` and the command fails at once instead. The HOME that holds the login never sets it.
