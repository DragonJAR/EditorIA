# Share copy: el texto que acompaña al video

Adaptado de `/brag` (latent-spaces/brag). Cada video que se publica lleva su
caption escrito, no improvisado en el momento. El share copy es canónico:
1–3 frases, posteable tal cual, específico del tema, con el tono de la pieza.

Se escribe en `share-copy.txt` junto al video final. Si hacen falta variantes
por plataforma, van en `share-copy-variants.md` aparte — nunca mezclar
variantes largas en el archivo canónico.

## Reglas

- Específico o nada: prohibido "emocionado de compartir", "mira esto",
  "optimiza tu flujo de trabajo". Usar el copy real del tema.
- Tono-compat: el caption suena como el video. Un video `caos` no lleva un
  caption `anuncio`.
- Español por defecto (salvo que el brand pack o el brief indiquen otro idioma).
- Incluir el dato más fuerte cuando el video lo tenga (cifra, nombre, fecha).

## Plantillas por tono

**`demo`:**
```
[Qué hace] en [cuánto tiempo / con qué].
[La frase más fuerte del video.]
```

**`resumen`:**
```
Resumen de [evento] #[N]: [3–4 temas separados por ·].
[Frase de cierre del video].
```

**`anuncio`:**
```
Presentamos [producto]: [one-liner limpio].
[Stack o dato notable si aporta].
```

**`trailer`:**
```
[Producto].
[Tagline del video, textual o casi.]
```

**`parodia`:**
```
Construimos [producto] para resolver [problema dicho en serio].
[Dato deadpan].
```

**`caos`:**
```
[AFIRMACIÓN EN MAYÚSCULAS].
[Producto] es [descripción exagerada].
Link abajo.
```

## Ejemplo (AI Tinkerers #20)

```
Resumen de AI Tinkerers Manizales #20: OpenCode 2.0 con subagentes,
JEP para decisiones en tiempo real, orquestación de agentes en 3D y ORCA.
¡Y vamos por más!
```

## Dónde va

```
proyecto/
  video_final.mp4
  video_final_poster.jpg   # ver scripts/poster_frame.py
  share-copy.txt           # este archivo
```

---

→ Canónico: `references/copy.md` · Dominio: copy · Vecinos: `references/copy.md`, `references/i18n.md`, `references/referencia-video.md`
