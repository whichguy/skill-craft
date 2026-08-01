# Anti-patterns (fail skill-interop review)

1. **Host-only prompt** — only procedure is “open Claude and run X” with no pasteable prompt.  
2. **Divergent copies** — different generator text in Grok vs Hermes skill trees.  
3. **Silent fallback** — measured path fails → native results labeled as measured.  
4. **Absolute external symlink** as sole Hermes install when container mounts only skill home.  
5. **Unresolved template tokens** left in rendered prompts.  
6. **Scripts re-author policy** — shell reimplements planning rules instead of filling prompt placeholders.  
7. **Overclaim** — chat JSON called “validated” / “EVSI” without packaging or EVSI backend.  
8. **Silent empty** — zero work reported as “nothing to do” without `considered`/`kept` or error.  
9. **Discovery as execution** — skill-dir or plugin install on N hosts claimed as multi-host **runtime** for an engine that only works with one transport (e.g. Hermes-only).  
10. **Unprovenanced materialization** — real tree under a skill home claimed as “installed by skill-craft” without a managed provenance marker (or equivalent).  
11. **Symlinks inside a copy-installed package** — package-internal links that escape package root or point at host-only paths after materialization.  
