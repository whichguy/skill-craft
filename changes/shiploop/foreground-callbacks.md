---
bump: patch
---
Every packet now tells the host never to end its turn while a ShipLoop command is still running: keep the command in the foreground, or wait for it in the same turn when the host backgrounds it. A test-stage `complete` reruns the recorded tests and can take minutes, and a headless Grok session ends when the turn ends, which lost a callback in a live run. The keepalive self-install notice now says the current session is not protected (headless sessions never are).
