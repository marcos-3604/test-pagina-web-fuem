# Informe de rendimiento de la web de Formula UEM

Objetivo: que la web cargue mucho más rápido (sobre todo en móvil) y corregir los avisos objetivos de Lighthouse,
sin cambiar su aspecto, sus textos ni sus URLs.

Convención: "KB" = KiB (1 024 bytes), como en `docs/svg-optimizacion.txt`. "MB" = MiB (1 048 576 bytes), como en la salida de `tools/check_site.py`.

## Medición de partida

Lighthouse 12, móvil (SPEC.md):

| Página | LCP | Peso transferido |
|---|---|---|
| Portada (`index.html`) | 22,7 s | 7,4 MB |
| `monoplaza.html` | 50,8 s | 12,2 MB |

### Medición después (Lighthouse 12, 2026-11-05, servidor local, mismas páginas)

| Página | Modo | LCP antes → después | Peso transferido antes → después | Rendimiento antes → después |
|---|---|---|---|---|
| `index.html` | móvil | 22,7 s → 11,0 s | 7.457 KiB → 4.744 KiB | 74 → 74 |
| `index.html` | escritorio | 3,9 s → 1,9 s | 11.383 KiB → 8.670 KiB | 79 → 91 |
| `monoplaza.html` | móvil | 50,8 s → 11,6 s | 12.180 KiB → 3.211 KiB | 64 → 64 |
| `monoplaza.html` | escritorio | 8,4 s → 2,0 s | 12.180 KiB → 3.211 KiB | 71 → 87 |
| `galeria.html` | móvil | 4,4 s → 4,3 s | 3.373 KiB → 2.224 KiB | 78 → 79 |

En móvil la nota global no sube porque la limitan el CSS que bloquea el renderizado (10 hojas de estilo) y la
animación de entrada; ver «Recomendaciones no aplicadas». Accesibilidad, buenas prácticas y SEO no cambian.

**Aspecto**: capturas completas antes/después (Playwright, 1440 px y 390 px, tras cargar toda la página):
0,03 % de píxeles distintos en escritorio (recompresión de los logos, invisible); en móvil solo cambia el pie por
el logo corregido a su proporción real (2 px más alto).

## Cambios realizados

1. **Comprobador `tools/check_site.py`** (T-001, commit `40d2ca6`). Es el check del proyecto. Falla (código ≠ 0) si:
   - una referencia local de un HTML/CSS/JS no existe;
   - un `.svg` de `assets/` incrusta un PNG en base64 de más de 400 KB;
   - una página `.html` referencia más de 6 MB de imágenes (sin vídeos).

   Tiene tests en `tools/test_check_site.py`.

2. **Re-codificación de imágenes incrustadas en SVG** (T-002, commit `9075619`). Lo hace `tools/optimize_svg_images.py`:
   - `assets/v3/car-cutout.svg` y `assets/v3/part-*.svg` (6 ficheros) incrustaban la misma foto como PNG. Pasaron a WebP con pérdida (calidad 90) tras una segunda pasada con el criterio de la decisión B (ver abajo).
   - Los logos de `assets/partners/*.svg` con PNG incrustado pasaron a WebP sin pérdida o con pérdida (q90), según lo que ganara más peso sin superar el criterio de error.
   - Solo cambia el data URI de cada SVG. El script comprueba que el resto del fichero es idéntico byte a byte, y los nombres de fichero no cambian.
   - Criterio de calidad: error medio ≤ 2/255 por canal RGBA y como mucho el 0,1 % de los valores con error > 32/255. Un fichero no se reescribe si ahorra menos del 20 %.
   - Tests en `tools/test_optimize_svg_images.py`. El registro literal de las dos pasadas está en `docs/svg-optimizacion.txt`.

3. **Relación de aspecto del logo** (T-003, commit `78e9934`). Se corrigieron `width`/`height` de `fuem-logo.png` en las páginas donde no coincidían con su proporción real (aviso `image-aspect-ratio`), en español y en inglés. Son 24 ficheros HTML con una línea cambiada cada uno. Por ejemplo, `index.html` queda con `width="100" height="58"` en la cabecera y `width="140" height="82"` en el pie.

## Peso antes y después por fichero

Tamaños en bytes medidos con `git show 2c877e1:<ruta> | wc -c` (antes) y `wc -c` (después).

| Fichero | Antes (B) | Después (B) | Ahorro |
|---|---:|---:|---:|
| `assets/v3/car-cutout.svg` | 1 895 863 | 294 348 | 84,5 % |
| `assets/v3/part-body.svg` | 1 896 426 | 294 911 | 84,4 % |
| `assets/v3/part-front-wheel.svg` | 1 896 130 | 294 615 | 84,5 % |
| `assets/v3/part-front-wing.svg` | 1 896 236 | 294 721 | 84,5 % |
| `assets/v3/part-rear-wheel.svg` | 1 896 128 | 294 613 | 84,5 % |
| `assets/v3/part-rear-wing.svg` | 1 896 184 | 294 669 | 84,5 % |
| `assets/partners/avl.svg` | 319 807 | 140 412 | 56,1 % |
| `assets/partners/danima-composites.svg` | 288 357 | 72 198 | 75,0 % |
| `assets/partners/velinrent-velasco-movilidad.svg` | 257 037 | 74 542 | 71,0 % |
| `assets/partners/calspan.svg` | 151 149 | 34 902 | 76,9 % |
| `assets/partners/easy-composites.svg` | 79 123 | 15 784 | 80,1 % |
| `assets/partners/3dconnexion.svg` | 33 097 | 10 062 | 69,6 % |
| `assets/partners/alucoat.svg` | 31 838 | 31 838 | 0 % (sin PNG incrustado) |

Verificados con `git show` / `wc -c`: los 6 SVG de `assets/v3`, y `avl`, `danima-composites`, `velinrent-velasco-movilidad`, `calspan`, `easy-composites`, `3dconnexion` y `alucoat` de `assets/partners`. Los demás ficheros de la tabla de `docs/svg-optimizacion.txt` no se han contrastado byte a byte.

Sin cambios de peso: los 9 logos sin PNG incrustado (`alucoat`, `elegoo`, `mad-cup`, `matva`, `pma`, `rgb-racing-team`, `tf3p`, `vila-rino-motorsport`, `wurth-elektronik`).

Total según `docs/svg-optimizacion.txt`: **13 364,6 KB → 2 831,8 KB (−78,8 %)**. Este total no se ha re-verificado byte a byte.

## Peso por página (imágenes)

Salida de `python3 tools/check_site.py` sobre el árbol del commit base `2c877e1` (antes) y sobre el árbol actual (después). El número de imágenes referenciadas no cambia.

| Página | Imágenes | Antes | Después |
|---|---:|---:|---:|
| `404.html` | 0 | 0,00 MB | 0,00 MB |
| `actualidad.html` | 50 | 3,61 MB | 2,48 MB |
| `contacto.html` | 39 | 2,48 MB | 1,36 MB |
| `equipo.html` | 43 | 3,16 MB | 2,04 MB |
| `eventos.html` | 40 | 3,19 MB | 2,07 MB |
| `formula-student.html` | 42 | 2,84 MB | 1,71 MB |
| `fuentes.html` | 39 | 2,48 MB | 1,36 MB |
| `galeria.html` | 60 | 5,18 MB | 4,06 MB |
| `historia.html` | 51 | 2,83 MB | 1,70 MB |
| `index.html` | 53 | 5,79 MB | 3,14 MB |
| `monoplaza.html` | 44 | 11,53 MB | 2,77 MB |
| `patrocinadores.html` | 39 | 2,48 MB | 1,36 MB |
| `unete.html` | 39 | 2,48 MB | 1,36 MB |
| `en/actualidad.html` | 50 | 3,61 MB | 2,48 MB |
| `en/contacto.html` | 39 | 2,48 MB | 1,36 MB |
| `en/equipo.html` | 43 | 3,16 MB | 2,04 MB |
| `en/eventos.html` | 40 | 3,19 MB | 2,07 MB |
| `en/formula-student.html` | 42 | 2,84 MB | 1,71 MB |
| `en/fuentes.html` | 39 | 2,48 MB | 1,36 MB |
| `en/galeria.html` | 60 | 5,18 MB | 4,06 MB |
| `en/historia.html` | 51 | 2,83 MB | 1,70 MB |
| `en/index.html` | 53 | 5,79 MB | 3,14 MB |
| `en/monoplaza.html` | 44 | 11,53 MB | 2,77 MB |
| `en/patrocinadores.html` | 39 | 2,48 MB | 1,36 MB |
| `en/unete.html` | 39 | 2,48 MB | 1,36 MB |

Resultado del comprobador sobre el árbol actual: **OK**, código de salida 0. Tests (`unittest`): 30 de 30 OK.

## Metadatos C2PA

**Se pierden.** Los PNG originales de la foto del coche (`assets/v3`) tenían metadatos C2PA (Content Credentials, chunk `caBX`). Los WebP que los sustituyen no los conservan. Se pierde también el resto de metadatos del PNG. Sí se conserva el perfil de color ICC, si existía. Ver `docs/svg-optimizacion.txt`.

Si la procedencia de la foto (Content Credentials) tiene valor para el cliente, hay que decidirlo antes de desplegar.

## Recomendaciones no aplicadas

Estas recomendaciones no se aplicaron porque cambian el diseño o requieren una decisión del dueño del proyecto:

1. **Contraste de botones.** Algunos botones no alcanzan el contraste mínimo de Lighthouse. Corregirlo cambia los colores que se ven.
2. **Tamaños de letra pequeños.** Hay textos por debajo del tamaño mínimo legible en móvil. Subirlos cambia la maquetación.
3. **hreflang absoluto con el dominio definitivo.** Las URLs de hreflang deben ser absolutas con el dominio final, que aún no está decidido.
4. **Vídeos en móvil.** Cargar vídeos más ligeros o no cargarlos en móvil cambia lo que ve el usuario. Requiere decisión.
5. **CSS que bloquea el renderizado.** Diferir o incrustar CSS cambia el orden de carga y puede provocar parpadeo de estilos.
6. **Animación de entrada (lo que más pesa ahora en móvil).** Tras la optimización, en la portada la imagen principal ya está descargada a los ~1,8 s, pero se pinta a los 11 s: Lighthouse atribuye 9,1 s a «Render Delay» (11,2 s en `monoplaza.html`). Coincide con la animación de entrada (`#intro`, contador «000»; `--intro-run` 3,3 s + `--intro-exit` 0,5 s en `interactive.js`), que ya se muestra solo una vez por sesión, pero que con la CPU lenta que simula Lighthouse en móvil se alarga mucho. Acortarla en móvil o permitir saltarla acercaría el LCP de la primera visita a ~2 s. Es una decisión de diseño, así que no se ha tocado.

## Aviso: generador de la web

El repositorio lo publica un generador (`.fuem-pages.json`: `fuem-pages-v1`, revisión 14; commits «Publish FUEM
content revision N»). Si ese generador vuelve a publicar copiando sus propios `assets/` o regenerando los HTML,
podría deshacer estos cambios (SVG recomprimidos y `height` del logo). Antes de la próxima publicación conviene
llevar las imágenes optimizadas y el ajuste del logo a la fuente del generador, y ejecutar
`python3 tools/check_site.py` después de publicar para detectar una regresión.
