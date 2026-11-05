---
flexible: [nombres, estructura de los scripts, calidad de compresión dentro de los límites, orden de las tareas]
---
# Objetivo
Hacer que la web de Formula UEM cargue mucho más rápido (sobre todo en móvil) y corregir los avisos objetivos de
Lighthouse, **sin cambiar su aspecto, sus textos ni sus URLs**.

Medición de partida (Lighthouse 12, móvil): portada LCP 22,7 s y 7,4 MB; `monoplaza.html` LCP 50,8 s y 12,2 MB.

## Alcance
1. **Comprobador** `tools/check_site.py` (Python estándar + Pillow si hace falta), que es el check del proyecto y la
   primera tarea (las demás dependen de ella). Falla (código ≠ 0) si:
   - una referencia local de un HTML/CSS/JS (src, href, srcset, url(), rutas `assets/...` en JS) no existe;
   - un `.svg` de `assets/` incrusta un PNG en base64 de más de 400 KB;
   - una página `.html` (es o en) referencia en total más de 6 MB de imágenes (sin contar vídeos).
   Imprime un resumen por página (peso de imágenes) y por fichero problemático.
2. **Imágenes incrustadas en SVG**: `assets/v3/car-cutout.svg` y `assets/v3/part-*.svg` (≈1,9 MB cada uno) incrustan
   la misma foto como PNG; los logos de `assets/partners/*.svg` incrustan PNG de hasta 320 KB. Re-codificar la imagen
   incrustada como WebP con transparencia (o lossless si es más pequeño), conservando exactamente el resto del SVG
   (viewBox, máscaras, transformaciones, títulos) y el nombre del fichero. La conversión la hace un script
   reutilizable `tools/optimize_svg_images.py` que verifica que la imagen decodificada no se aparta visualmente de la
   original (error medio por canal RGBA ≤ 2/255 y máximo razonable) y no reescribe un fichero si no gana al menos un 20 %.
   Los metadatos C2PA del PNG original pueden perderse; dejarlo anotado en el informe.
3. **Relación de aspecto del logo**: corregir los `width`/`height` de `fuem-logo.png` en las páginas donde no
   coinciden con su proporción real (aviso `image-aspect-ratio`), en español y en inglés.
4. **Informe** `docs/RENDIMIENTO.md`: qué se cambió, peso antes/después por fichero y por página (salida del
   comprobador) y recomendaciones que **no** se aplicaron porque cambian el diseño o requieren decisión del dueño
   (contraste de botones, tamaños de letra pequeños, hreflang absoluto con el dominio definitivo, vídeos en móvil,
   CSS que bloquea el renderizado).

## Restricciones
- No cambiar diseño, colores, textos, estructura de páginas ni URLs. Las páginas `en/` igual que las españolas.
- No tocar `.github/` (workflows, script de Instagram) ni `instagram-feed.json`.
- La web es estática (GitHub Pages): nada de build, dependencias npm ni servidores.

## Preguntas abiertas
