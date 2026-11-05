# test-pagina-web-fuem

Hacer que la web de Formula UEM cargue mucho más rápido (sobre todo en móvil) y corregir los avisos objetivos de Lighthouse, **sin cambiar su aspecto, sus textos ni sus URLs**.

## Comandos
- Check del proyecto (tests del comprobador): `python3 -m unittest discover -s tools -p test_*.py`
- Comprobador del sitio real: `python3 tools/check_site.py` (opción `--json`; falla si hay referencias rotas, SVG con PNG > 400 KB o páginas con > 6 MB de imágenes). Hoy falla a propósito (SVG de assets/v3 y monoplaza); pasa a ser el check de T-002/T-004 cuando las imágenes estén optimizadas. No lo debilites.

## Convenciones
- (ninguna aún)

## Trampas
- (Añade aquí solo lo que haya hecho falta corregir dos veces.)

## Flujo de trabajo
- `SPEC.md` contiene el objetivo y las decisiones cerradas. No supongas nada que no esté ahí: pregunta.
- Decisiones posteriores: `.aiforge/memory/decisions.md` (léelo solo si tu tarea toca ese tema).
- Si te quedas sin cupo o el trabajo pasa a otra herramienta, deja `.aiforge/handoff.md` con estado, trabajo a medias y siguientes pasos.
- Nunca hagas push, merge ni despliegues: eso lo aprueba el usuario.
