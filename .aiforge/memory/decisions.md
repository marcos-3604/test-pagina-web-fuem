# Decisiones del proyecto

## D-001 verification of t-001 against the expected exit code (usuario) · 2026-11-05 · tags: tooling, check, verification of t-001 against the expected exit code
Pregunta: The task requires `python3 tools/check_site.py` to exit ≠ 0 on today's repo, but the verification step treats that exit code as a failure. How should T-001's verification handle this?
Respuesta: Correcto: tools/check_site.py debe seguir fallando hoy (detecta los SVG pesados reales); no lo debilites. Ya he cambiado la verificación: el check del proyecto pasa a ser 'python3 -m unittest discover -s tools -p test_*.py' (los tests del propio comprobador, con fixtures pequeños que cubran cada regla), y check_site.py en el repo real será el check de T-002 y T-004, cuando las imágenes ya estén optimizadas. Termina T-001 así.

## D-002 umbral de error máximo para la foto del coche (assets/v3) (usuario) · 2026-11-05 · tags: images, performance, umbral de error máximo para la foto del coche (assets/v3)
Pregunta: Con el máximo estricto de 32/255 la foto del coche tiene que ir sin pérdida (919 KB) y monoplaza.html se queda en 7,39 MB, por encima de los 6 MB. ¿Mantengo la regla e informo del exceso, o permito unos pocos picos aislados para poder usar WebP con pérdida (215 KB, error medio 0,76/255)?
Respuesta: B) Como mucho un 0,1 % de valores por encima de 32/255 y error medio ≤ 2/255; elige la calidad más baja que cumpla ambas. Anótalo en el informe.
