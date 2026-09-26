---
bump: patch
---
The bundled Until Loop runtime is 0.7.0: `start --receipt <absolute file>` makes the runtime write every packet it returns to that file (atomically, mode 0600) before printing it, including the terminal packet, which it writes before deleting its state. In a ShipLoop subcall, start the bound runtime with the printed host receipt path as `--receipt`; ShipLoop imports only a packet the runtime wrote there.
