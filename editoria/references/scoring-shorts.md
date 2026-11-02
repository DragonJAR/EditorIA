# Scoring de "momentos fuertes" (resúmenes y shorts)

Método oficial para elegir qué segmentos de un material largo se convierten en
short o resumen: se puntúa cada candidato con una rúbrica ponderada de 5
dimensiones y se seleccionan los mejores.

## Procedimiento

1. Listar 8–12 segmentos candidatos de la transcripción (cada uno con timestamp
   de inicio y fin, 15–55s; el pico de engagement está en 25–40s).
2. Puntuar cada uno de 0 a 100 en las 5 dimensiones.
3. Calcular: `score = hook*0.30 + coherencia*0.25 + emoción*0.20 + valor*0.15 + payoff*0.10`.
4. Presentar la tabla al usuario; él elige/ajusta. Solo entonces renderizar
   (receta "shorts con review-gate" en `modos-rapidos.md`).

## Las 5 dimensiones

### 1. Hook (peso 0.30)
Los primeros 3 segundos deciden si el espectador se queda. Puntuar por arquetipo:

| Arquetipo | Rango |
|---|---|
| Contrarian ("todo lo que sabes de {tema} está mal") | 80–100 |
| Curiosity gap ("hay algo que nadie te cuenta sobre…") | 75–95 |
| Promesa de valor ("el framework exacto que usé para…") | 70–90 |
| Pattern interrupt ("espera, mira esto") | 70–90 |
| Vista previa del payoff ("al final sabrás cómo…") | 65–85 |
| Inicio en plena acción (entra a mitad de frase, con energía) | 60–80 |
| Conocimiento oculto ("el secreto que {autoridad} no comparte") | 60–80 |
| Genérico ("hoy quiero hablarles de…") | 10–40 |

Boosters (+5–10 cada uno, máx. +20 total por boosters): número específico ("3 pasos", "$50K", "en 30 días");
entidad reconocible (persona, empresa, herramienta); experiencia propia
("probé", "pasé 6 meses en esto").

### 2. Coherencia standalone (peso 0.25)
El segmento debe entenderse sin haber visto el resto.

| Criterio | Rango |
|---|---|
| Arco completo autónomo (setup → desarrollo → resolución) | 85–100 |
| Idea completa con huecos menores inferibles | 65–84 |
| Mayormente standalone pero referencia contenido previo | 40–64 |
| Requiere contexto previo para entenderse | 10–39 |
| Fragmento: empieza o termina a mitad de idea | 0–9 |

Banderas rojas (puntaje bajo automático): "como mencioné antes…", "volviendo a
lo que discutíamos…", pronombres sin referente claro, corte a mitad de frase.

### 3. Intensidad emocional (peso 0.20)

| Señal | Rango |
|---|---|
| Opinión fuerte / rant con convicción | 80–100 |
| Revelación sorpresa / giro inesperado | 75–95 |
| Humor genuino / risa | 70–90 |
| Vulnerabilidad / fracaso honesto | 70–90 |
| Explicación entusiasta de algo fascinante | 60–80 |
| Observación calmada pero lúcida | 40–60 |
| Recitado monótono de datos | 10–30 |

### 4. Densidad de valor (peso 0.15)

| Contenido | Rango |
|---|---|
| Proceso paso a paso / método exacto | 80–100 |
| Framework / modelo mental con ejemplos | 75–95 |
| Datos específicos / hallazgos de investigación | 70–90 |
| Insight contraintuitivo con explicación | 65–85 |
| Consejo general con algo de especificidad | 40–60 |
| Platitudes vagas ("trabaja duro", "sé constante") | 10–30 |

Penalizar segmentos donde >30% del tiempo es relleno, repetición o tangentes.

### 5. Calidad del payoff (peso 0.10)

| Cierre | Rango |
|---|---|
| Punchline / revelación satisfactoria | 85–100 |
| CTA claro con paso específico | 75–90 |
| Pensamiento completo, punto de parada natural | 65–80 |
| Se diluye hacia el siguiente tema (pero se puede cortar limpio) | 40–60 |
| Se corta a mitad de idea / sin resolución | 10–30 |

## Reglas de selección

- Umbral mínimo: 60. Debajo, se descarta.
- Diversidad: no elegir 5 segmentos sobre el mismo subtema.
- Espaciado: preferir segmentos a ≥2 min de distancia en el original.
- Fronteras naturales: alinear inicio/fin con bordes de frase, nunca a mitad
  de palabra.
- El texto del hook en pantalla NO repite las primeras palabras habladas:
  línea 1 (4–8 palabras, la afirmación que atrapa) + línea 2 (3–6 palabras,
  contexto) en la tipografía de titulares (del brand pack o del modo libre).

---

→ Canónico: `references/formatos.md` · Dominio: produccion · Vecinos: `references/pipeline-resumen.md`, `references/video-real.md`, `references/modos-rapidos.md`
