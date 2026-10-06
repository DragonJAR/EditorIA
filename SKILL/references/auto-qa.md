# Auto-QA — el loop cerrado de ver, detectar y corregir

El agente no entrega un video que no haya *mirado*. Este es el protocolo
obligatorio después de cada render, antes de entregar.

## El loop

```
render → auto_qa.py → MIRAR el sheet → confirmar/descartar → corregir →
re-render → auto_qa.py → comparar → entregar
```

1. **Barrido máquina**: `python scripts/auto_qa.py video.mp4`
   Detecta sin visión: frames negros, imagen congelada >1s, flashes,
   silencios largos, clipping. Sale 1 si hay defectos.
2. **Revisión visual** (obligatoria aunque salga 0): abrir el contact sheet
   el contact sheet `video_qa.png` y mirarlo cuadro por cuadro. La máquina no ve texto
   cortado, solapes, ni errores de marca — el agente sí. Con
   `--safe plataforma` (reels, tiktok, shorts…) el sheet dibuja la zona
   segura en cada tile: lo que quede fuera lo tapa la UI.
3. **Confirmar o descartar**: cada defecto máquina se confirma con los ojos
   o se descarta con motivo (ej. fade-out intencional → usar
   `--ignorar-fin` en la siguiente pasada).
4. **Corregir** según la tabla de abajo.
5. **Re-verificar**: re-render + `auto_qa.py` de nuevo. El reporte debe salir
   limpio *y* el sheet debe verse bien.
6. **Documentar**: cada defecto real deja su lección en
   `references/reglas-tecnicas.md`.

## Métricas de animación (antes de renderizar)

`python scripts/medir_animacion.py` mide el catálogo sin codificar (unos
minutos): pops, tirones, tiempo muerto, densidad, letra y zona por escena y
formato, con nota 0–100. Es el banco de la mejora recursiva: toda mejora se
mide contra `metricas/historial.jsonl` y se queda solo si sube la nota sin
romper `validate_skill.py`. Un pop se diagnostica con
`--ver escena:v|h:segundo` (par de frames con los bloques abruptos marcados).
`--plan plan.json` mide un plan entero (cortes incluidos) y `--video x.mp4`
cualquier video ya renderizado, a su propio fps.

Qué mide cada número (calibrado con casos sintéticos en `validate_skill.py`):
- **pop**: en un frame, ≥ 35 % de los bloques que cambian de golpe no tienen
  origen cerca en el frame anterior (ni exacto ni suavizado). Lo que aparece
  deja casi todo sin origen; lo que se mueve o escala, solo su borde. Las
  cifras que cuentan quedan exentas (cambian por diseño).
- **tirones**: un frame quieto entre dos que se mueven (corte o salto de un
  frame) o un frame que se mueve 4× más que sus dos vecinos (teletransporte).
- **muerto**: % del hold con quietud SOSTENIDA (≥ 0.5 s bajo el umbral de
  auto_qa); el punto de giro de una flotación no cuenta.
- **densidad**: eventos de movimiento por segundo (doctrina: 0.5–2).
- **letra**: tamaño mínimo de texto ya asentado (≥ 26 px sobre 1080).
- **zona**: factor de `escala_segura` (1 = compuesta dentro de la zona segura).
Causas que encontró (y su fix en la primitiva): ease aplicado dos veces
(cursor a 85 px/frame), resorte en barras de datos (rebota por encima del
valor), cifras proporcionales al contar (tiemblan de lado), texto que entra
sin el alfa de su tarjeta, tamaños de letra enteros al escalar (saltos de
1 px), odómetro de 0.25 s con ease_out (saltaba ~100 px/frame).

## Tabla de defectos → causa → fix

| Defecto máquina | Causa probable | Fix |
|---|---|---|
| `black_frame` | escena que termina antes que el video; fade no intencional | revisar `to` de la última escena; `--ignorar-fin` si el fade es intencional |
| `frozen` | fondo sin animación; elemento estático | fondo vivo continuo; la respiración común de `componer` (push-in lento) — si la escena la apaga (`"respira": false`) o mueve su propia cámara, idle/breathing en el elemento |
| `flash` | pop de audio con corte visual; glitch de render | micro-fade 30ms en el corte; re-renderizar el tramo |
| `silencio` | música que no arranca; gap entre segmentos de voz | revisar mezcla; fundidos en `musica.py` |
| `clipping` | mezcla caliente | bajar master; re-medir con `medir_mezcla.py` |
| `fotosensible` | más de 3 destellos en 1 s (WCAG 2.3.1; medido a fps completo, en pantalla o en un cuadrante) | espaciar los flashes a ≥1/3 s, bajar el contraste del destello o achicar su área |
| `sobresalto` | el audio salta >6 dB al entrar un corte (asusta, no edita) | entrar las capas de a una o dos por compás; marcar el corte con armonía, no con volumen |
| `loop` (con `--loop`) | el último frame no empalma con el primero | igualar composición, posición y color del cierre al frame 0 |

Con `--end-screen 15` el sheet dibuja, en los últimos 15 s, las zonas de la
pantalla final de YouTube (marca en el tercio izquierdo, tarjetas a la
derecha): nada propio debe caer bajo las tarjetas.

## Defectos que solo el ojo ve (checklist visual del sheet)

- **Texto cortado** en bordes → auto-fit o centro mal calculado.
- **Solapes** entre elementos → revisar coordenadas en el plan.
- **Marca**: colores/tipos/logos del pack, sin deformar ni rotar.
- **Coherencia espacial**: `references/coherencia-espacial.md`.
- **Ritmo**: si se lee como diapositivas → `scripts/verificar_ritmo.py`.

## Reglas del loop

- Ningún video se entrega con defectos máquina sin descartar.
- Ningún descarte sin motivo escrito (una línea basta).
- Si un defecto reaparece 2 veces, la causa está en el renderer o el plan,
  no en los parámetros: arreglar la raíz, no el síntoma.
- El sheet final limpio se guarda junto al entregable como evidencia de QA.
