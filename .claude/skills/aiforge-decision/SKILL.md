---
name: aiforge-decision
description: Record a project decision (architecture, dependency, data model, UX, scope) in .aiforge/memory/decisions.md so every AI working on the project follows it. Use when the user decides something not already in SPEC.md.
argument-hint: "[tema] [decisión]"
---
Append an entry to `.aiforge/memory/decisions.md` (create it with `# Decisiones del proyecto` if missing):

```
## D-NNN <tema breve> · <YYYY-MM-DD> · tags: <2-4 tags en minúscula>
Decisión: <una línea>
Motivo: <una línea>
Descartado: <alternativas, si las hubo>
```

NNN = next number. Keep it to 4 lines. Do not record trivial choices.
