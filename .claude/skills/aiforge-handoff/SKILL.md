---
name: aiforge-handoff
description: Write a handoff note so another AI (Codex, Gemini or a fresh Claude session) can continue the current work. Use when the user asks to hand off, switch tools, or pause because usage limits are close.
---
Replace `.aiforge/handoff.md` with at most 40 lines, in Spanish:

1. **Objetivo** de lo que se estaba haciendo (1-2 líneas).
2. **Hecho**, con rutas.
3. **A medias**: rutas y qué falta exactamente.
4. **Siguientes pasos** concretos y en orden.
5. **Cómo comprobar** (comando).

Si en esta sesión se tomó alguna decisión de proyecto, añádela también con `/aiforge-decision`.
No copies código ni la conversación: el código está en git.
