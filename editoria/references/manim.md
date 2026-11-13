# Manim — explicadores matemáticos (capacidad)

Cuando la pieza pide **ecuaciones, pruebas, algoritmos o visualización a lo
3Blue1Brown**, el motor de planes no es el oficio: hace falta Manim Community
Edition. EditorIA no vendoriza Manim: clona bajo demanda el skill
[Yusuke710/manim-skill](https://github.com/Yusuke710/manim-skill) (MIT) y
limpia `/tmp` al terminar.

## Cuándo usarla (y declararla si falta)

- El brief pide animar un concepto matemático, una derivación o un algoritmo.
- El texto en pantalla es fórmula (`MathTex` / `Tex`), no un titular de anuncio.
- Se quiere voz en off sincronizada con subtítulos por segmento (Kokoro local
  opcional en el skill clonado).

Si Manim / `uv` / el skill no están, **declarar** en la primera respuesta con
el comando (`capacidades.md`). No sustituir en silencio por una escena
`stats` o un diagrama SVG.

## Cómo se pide (catálogo único)

```bash
python scripts/repertorio.py sugerir --pedido "demostrar el gradiente con manim"
python scripts/repertorio.py resolver --id manim
python scripts/motores_externos.py receta --id manim
```

## Flujo (resumen; detalle en el SKILL del clone)

1. Sesión plana fuera del cwd del usuario:
   `SESSION_DIR="${MANIM_SKILL_HOME:-$HOME/.manim-skill}/<slug>"`.
2. Narración → TTS (si hay Kokoro) → `script.py` (una clase por escena) →
   `manim` → mux → `video.mp4`.
3. Preview barato (854×480 @ 15 fps) antes del render final.
4. El MP4 entra al montaje EditorIA como cualquier clip; la puerta es la misma
   (`qa-entrega.md`).

## Qué se descartó del skill

| pieza | por qué |
|---|---|
| Instalar Manim dentro de EditorIA | dependencia pesada; opt-in |
| Submodule / vendor del repo | basta clone-on-demand |
| Forzar Kokoro | TTS local opcional; ElevenLabs / voz local de EditorIA cubren otras vías |

## Licencia

MIT, Copyright 2025 Yusuke Miyashita. Créditos: `references/creditos.md`.

---

→ Canónico: `references/motores-externos.md` · Dominio: herramienta · Vecinos: `references/capacidades.md`, `references/animacion.md`, `references/diagramas.md`, `references/creditos.md`
