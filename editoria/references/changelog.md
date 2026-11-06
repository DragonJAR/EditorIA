# Changelog

Registro de lo que cambia en la skill, por versión. El detalle de *por qué*
está en el mensaje de cada commit (`git log`); aquí está el *qué*.

La skill se publica en `https://github.com/DragonJAR/EditorIA`; la copia
instalada (`~/.minimax/skills/editoria`) se sincroniza con lo publicado: el
repo manda.

## Sin publicar

**Cambiado**
- `render_plan.py` **borra `{salida}.frames/`** cuando el video queda
  codificado y dice cuántos GB liberó. Los PNG sin comprimir pesan ~1,5 GB
  por minuto a 1920x1080: en un lote de 25 piezas de ~2 min dejaron ~3 GB
  cada una y llenaron el disco a mitad del lote. Un render que falla los
  deja (el siguiente intento retoma); `--conservar-frames` los conserva.

## 1.11.4 — la convergencia con el fork del 30-oct

Dos líneas de la misma skill se desarrollaron por separado durante un día:
esta (`main`, con las rondas de primitivas y los guards) y un fork
(1.11.2 → 1.11.3, con el eje de contrato y robustez). Este lote integra lo
que del fork aportaba valor real, **adaptado al motor de aquí** (que dibuja
con `pon_texto`, `sobre_capa` y `capa_fija`; el fork dibujaba con `d.text`
crudo).

**Añadido**
- La **firma del plan**: el video lleva en su comentario el hash de lo que
  pintó (plan + motor + pack) y la puerta lo compara con el plan. Antes,
  cambiar el plan y re-renderizar sin `--force` reutilizaba los frames
  viejos: la pieza entregada no era la del plan y la puerta la aprobaba.
- El **ESQUEMA de las escenas**: tipo, obligatorios, significado, markup,
  rol de tamaño y duración, derivado del propio código de cada escena. Un
  campo obligatorio que falta es ahora un error con escena y campo, no un
  `KeyError` en el render.
- El **kit de tiempo para los motores HTML** (`assets/js/tiempo.mjs`): el
  espejo del motor Python, para que una pieza mixta no tenga dos físicas.
- Las **reglas de marca** que el pack declara y el motor ahora obedece:
  `rebote`, `particulas`, `volumen` y `outro_sobrio`.
- `references/creditos.md`: el material de terceros, con su licencia.

**Corregido**
- La caché de frames se invalida cuando cambia el plan, el motor o el pack.
- El techo de sonoridad se **verifica sobre el resultado** (el AAC suma
  sobrepico después de loudnorm) y la mezcla se normaliza al objetivo de la
  plataforma.
- El símbolo de moneda lleva su aire; el descuento de una oferta sale solo si
  el plan lo pide; el tachado es fino.
- El pack por nombre resuelve (`carbon`), y el pack inexistente es un error
  que dice qué packs hay.
- La apertura deja la primera frase el tiempo de poder leerse.
- El cierre acepta `marca` o `titulo`.
- El reel normaliza cada entrada antes del xfade (ffmpeg 7 lo rechazaba).
- Los umbrales de la casa tienen una sola fuente: `LETRA_MIN` y
  `OCUPACION_MIN` en `_comun`; `QUIETO_MAX` es `auto_qa.FROZEN_MAX`.

**Integración con main (metodo de dirección Lemo-Opuscar)**
- `references/metodo-direccion.md` entra al mapa (dominio `estructura`) y
  `scripts/medir_silencios.py` entra al SKILL.md con su comando de ejemplo.
- La regla «numero de referencias» del guard ya no se mantiene a mano:
  `actualizar_conteos.py` reescribe su `valor` con el conteo real del árbol
  (la prosa y la regla ya no pueden divergir).
- `creditos.md` por unión: la atribución de pdoom-video ampliada, y las
  filas de lemo-opuscar y mg-styles-15.

**Puerta**
- El censo de la suite pasa de `timeout=900` a `timeout=1800`: medido en
  vacío toma ~870 s, y un 3 % de margen muere por TIMEOUT bajo cualquier
  carga honesta (un fallo de la medición, no del código).
- Cuando la suite falla dentro de la puerta, el log ya no imprime solo la
  última línea (`FAILED (failures=N)` sin nombres): imprime el bloque de
  fallos de unittest con los nombres de los tests.

**Documentación**
- `references/tiempo-html.md`: el tiempo en los motores HTML.

## 1.10.2 y anteriores

Sin registro en este fichero: el historial está en los mensajes de commit
(`git log --oneline`). A partir de esta versión, cada cambio anotado aquí.

---

Licencia MIT. Autor: Jaime Andrés Restrepo (DragonJAR).

---

→ Canónico: `references/mapa.md` · Dominio: operacion · Vecinos: `references/instalacion.md`, `references/capacidades.md`, `references/qa-entrega.md`
