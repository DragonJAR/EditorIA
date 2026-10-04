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

## Tabla de defectos → causa → fix

| Defecto máquina | Causa probable | Fix |
|---|---|---|
| `black_frame` | escena que termina antes que el video; fade no intencional | revisar `to` de la última escena; `--ignorar-fin` si el fade es intencional |
| `frozen` | fondo sin animación; elemento estático | fondo vivo continuo; idle/breathing en el elemento |
| `flash` | pop de audio con corte visual; glitch de render | micro-fade 30ms en el corte; re-renderizar el tramo |
| `silencio` | música que no arranca; gap entre segmentos de voz | revisar mezcla; fundidos en `musica.py` |
| `clipping` | mezcla caliente | bajar master; re-medir con `medir_mezcla.py` |

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
