// tiempo.mjs — kit de tiempo "seek-safe" de EditorIA para los motores HTML
// (HyperFrames, Canvas/p5, Remotion, una pagina con renderAt(t)).
//
// Una sola regla: TODO es funcion pura de t. Nada de Date.now(),
// performance.now(), Math.random() sin semilla, timers, transiciones CSS ni
// estado entre frames. Asi un frame se puede pintar solo, fuera de orden y
// promediado en sub-frames de motion blur, y da siempre lo mismo.
//
// Es el espejo del motor Python (scripts/render_plan.py): mismo resorte
// `spring`, mismos seis gestos de `MOVIMIENTO`, mismas cuatro curvas de
// animacion.md §3 y mismos sub-frames del obturador. El test
// scripts/_tests/test_tiempo_js.py comprueba que los dos dan los mismos numeros.
// Lee la rejilla de scripts/beat_grid.py (--json) y las palabras de
// scripts/alinear.py sin convertir nada.
//
// Tecnicas adaptadas de: pdoom-video (MIT, Giacomo Magnanini) — frameIdx,
// pulsos que decaen, progreso por palabra; el kit canvas de John Heibel
// (MIT) — ring/onTwos/keys; prompts publicos de motion design reunidos en
// opus-video-prompts — resorte con objetivo cambiante como suma de resortes.
// Creditos completos: references/creditos.md. Autor: Jaime Andres Restrepo (DragonJAR).

// ---------- basicos ----------
export const clamp = (x, a = 0, b = 1) => Math.min(b, Math.max(a, x));
export const lerp = (a, b, p) => a + (b - a) * p;
/** Progreso 0..1 de t dentro de [a, b] (con curva opcional). */
export const seg = (t, a, b, curva = (p) => p) =>
  b <= a ? (t >= b ? 1 : 0) : curva(clamp((t - a) / (b - a)));

// ---------- las cuatro curvas del motor (animacion.md §3) ----------
export const curvas = {
  ease_out: (p) => 1 - (1 - clamp(p)) ** 3,                       // entrada
  ease_in_out: (p) => { p = clamp(p); return p < 0.5 ? 4 * p ** 3 : 1 - (-2 * p + 2) ** 3 / 2; }, // camara
  smoothstep: (p) => { p = clamp(p); return p * p * (3 - 2 * p); }, // transicion
};   // la cuarta "curva" es el resorte (rol pop): entra(t, t0, 'pop')

// ---------- resortes ----------
/** Resorte 0->1 (identico a render_plan.spring). */
export function resorte(t, t0, rigidez = 120, amortiguacion = 13) {
  if (t <= t0) return 0;
  const dt = t - t0, w = Math.sqrt(rigidez), d = amortiguacion / (2 * w);
  if (d >= 1) return 1 - Math.exp(-w * dt) * (1 + w * dt);
  const wd = w * Math.sqrt(1 - d * d);
  return 1 - Math.exp(-d * w * dt) * (Math.cos(wd * dt) + (d * w / wd) * Math.sin(wd * dt));
}

/** Los seis gestos de la casa (render_plan.MOVIMIENTO): [rigidez, amortiguacion]. */
export const MOVIMIENTO = {
  titular: [150, 15], bloque: [120, 15], elemento: [110, 14],
  suave: [130, 16], pop: [150, 13], lento: [70, 12],
};

/** Entrada con el gesto del rol (render_plan.entra). */
export const entra = (t, t0, rol = 'bloque') => resorte(t, t0, ...MOVIMIENTO[rol]);

/** Resorte criticamente amortiguado: 1-(1+w·dt)e^(-w·dt). Nunca pasa del objetivo
 *  (UI seria, datos, wipes). w 12-40: mas alto = mas seco. */
export const critico = (t, t0, w = 20) => resorte(t, t0, w * w, 2 * w);

/** Un valor que cambia de objetivo muchas veces sigue siendo f(t): es la SUMA
 *  de un resorte por cambio. cambios = [[t, valor], ...] ordenados. */
export function retarget(t, v0, cambios, rol = 'bloque') {
  let v = v0, prev = v0;
  for (const [ti, vi] of cambios) { v += (vi - prev) * entra(t, ti, rol); prev = vi; }
  return v;
}

/** Bamboleo amortiguado tras un evento (asentar, follow-through). 0 en reposo. */
export function wobble(t, t0, frecuencia = 3, vidaMedia = 0.12) {
  if (t < t0) return 0;
  const dt = t - t0;
  return Math.sin(2 * Math.PI * frecuencia * dt) * 0.5 ** (dt / vidaMedia);
}
/** Un wobble por evento (impactos, golpes de beat). */
export const ring = (t, eventos, frecuencia, vidaMedia) =>
  eventos.reduce((s, e) => s + wobble(t, e, frecuencia, vidaMedia), 0);

// ---------- llaves ----------
/** Llaves [[t, v, curva?], ...]; v puede ser numero o array. La curva de cada
 *  llave gobierna el tramo que TERMINA en ella. */
export function keys(t, llaves, curvaDef = curvas.ease_in_out) {
  if (!llaves.length) return 0;
  if (t <= llaves[0][0]) return llaves[0][1];
  for (let i = 1; i < llaves.length; i++) {
    const [t1, v1, c] = llaves[i];
    if (t <= t1) {
      const [t0, v0] = llaves[i - 1];
      const p = (c || curvaDef)(clamp((t - t0) / Math.max(1e-9, t1 - t0)));
      return Array.isArray(v0) ? v0.map((x, k) => lerp(x, v1[k], p)) : lerp(v0, v1, p);
    }
  }
  return llaves[llaves.length - 1][1];
}

// ---------- frames, obturador, azar con semilla ----------
/** Indice de frame CONSTANTE durante todo el obturador (centrado en el frame).
 *  Usalo para todo lo que "salta" por frame (jitter, boil, grano): con
 *  Math.floor(t*fps) cada frame promediado mezclaria dos estados. */
export function frameIdx(t, fps = 30) {
  // redondeo al par, como int(round(t*fps)) del grano en Python
  const x = t * fps, f = Math.floor(x), d = x - f;
  if (Math.abs(d - 0.5) < 1e-9) return f % 2 === 0 ? f : f + 1;
  return d < 0.5 ? f : f + 1;
}
/** "A doses": sostiene cada dibujo n frames (look cel/stop-motion). La camara no. */
export const enDos = (t, fps = 30, n = 2) => (Math.floor(frameIdx(t, fps) / n) * n) / fps;
/** Instantes de los n sub-frames del obturador (mismos que render_plan). */
export function subframes(t, fps = 30, n = 5, obturador = 0.5) {
  const v = obturador / fps;
  return Array.from({ length: n }, (_, k) => t + v * ((k + 0.5) / n - 0.5));
}
/** PRNG con semilla (mulberry32). */
export function mulberry32(semilla) {
  let a = semilla >>> 0;
  return () => {
    a = (a + 0x6d2b79f5) >>> 0;
    let x = Math.imul(a ^ (a >>> 15), 1 | a);
    x = (x + Math.imul(x ^ (x >>> 7), 61 | x)) ^ x;
    return ((x ^ (x >>> 14)) >>> 0) / 4294967296;
  };
}
/** Hash 0..1 estable de enteros (para "lo que debe quedarse quieto"). */
export function hash(...ns) {
  let h = 2166136261 >>> 0;
  for (const n of ns) { h = Math.imul(h ^ (n | 0), 16777619) >>> 0; h ^= h >>> 13; }
  return (Math.imul(h, 2246822519) >>> 0) / 4294967296;
}

// ---------- ritmo (salida de scripts/beat_grid.py --json) ----------
/** rejilla({bpm, beat0, compas0, picos}) -> utilidades de beat. */
export function rejilla(g) {
  const beat = 60 / g.bpm, b0 = g.beat0 ?? 0, c0 = g.compas0 ?? b0;
  const picos = (g.picos || []).map((p) => (typeof p === 'number' ? { t: p, fuerza: 1 } : p));
  return {
    beat,
    beatAt: (t) => (t - b0) / beat,                       // indice continuo
    tiempoDeBeat: (i) => b0 + i * beat,
    beatCercano: (t) => b0 + Math.round((t - b0) / beat) * beat,
    compasAt: (t) => Math.floor((t - c0) / (4 * beat)),
    faseCompas: (t) => ((((t - c0) / (4 * beat)) % 1) + 1) % 1,
    /** 1 en cada beat y decae (vida media en s): el "golpe" que todo comparte. */
    pulso: (t, vidaMedia = 0.1) => (t < b0 ? 0 : 0.5 ** ((((t - b0) % beat) + beat) % beat / vidaMedia)),
    /** Pulso de los picos medidos (kick, golpe): el de mas fuerza manda. */
    golpe: (t, vidaMedia = 0.11) => golpes(t, picos, vidaMedia),
    /** Un movimiento que debe ATERRIZAR en el beat i empieza `antes` s antes. */
    aterriza: (i, antes = 0.05) => b0 + i * beat - antes,
  };
}
/** Pulsos que decaen desde cada evento [{t, fuerza}] anterior a t. */
export function golpes(t, eventos, vidaMedia = 0.11) {
  let v = 0;
  for (const e of eventos) {
    const dt = t - e.t;
    if (dt < 0 || dt > vidaMedia * 8) continue;
    v = Math.max(v, (e.fuerza ?? 1) * 0.5 ** (dt / vidaMedia));
  }
  return v;
}

// ---------- palabras (salida de scripts/alinear.py) ----------
/** Progreso cantado/dicho de una palabra {inicio, fin} (o {start, end}). Nunca se adelanta a la voz. */
export const progresoPalabra = (w, t) => seg(t, w.inicio ?? w.start, w.fin ?? w.end);
/** Indice de la palabra que suena en t (-1 antes de la primera). */
export function palabraEn(palabras, t) {
  let k = -1;
  for (let i = 0; i < palabras.length; i++) if ((palabras[i].inicio ?? palabras[i].start) <= t) k = i;
  return k;
}
/** Caracteres "dichos" de una linea en t (para barridos por glifo). */
export function caracteresDichos(palabras, t) {
  let n = 0;
  palabras.forEach((w, i) => {
    const txt = w.texto ?? w.w ?? '';
    n += Math.round(txt.length * progresoPalabra(w, t)) + (i < palabras.length - 1 && progresoPalabra(w, t) >= 1 ? 1 : 0);
  });
  return n;
}
/** Anticipacion permitida: mostrar la linea atenuada hasta `antes` s antes de su primera palabra. */
export const lineaVisible = (palabras, t, antes = 0.4) =>
  palabras.length > 0 && t >= (palabras[0].inicio ?? palabras[0].start) - antes;
