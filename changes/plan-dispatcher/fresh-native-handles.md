---
bump: patch
---
For the compact Ask Agent profile, reject native handles already bound to another attempt under the Dispatcher lock, including accepted and retried attempts. Keep same-attempt registration replay and ordinary Dispatcher behavior unchanged.
