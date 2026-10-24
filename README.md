# AI-Pipeline — Detección y análisis de fuego activo en Colombia (VIIRS + MODIS)

Pipeline de Machine Learning para el **NASA Space Apps Challenge 2026** (reto
*Harmonization of MODIS and VIIRS Hot Spots*) que descarga, unifica, limpia y analiza
registros de anomalías térmicas (focos de calor) en **Colombia** usando el **Area API de
NASA FIRMS** con las fuentes de archivo histórico (Standard Processing):

| sensor local | fuente API FIRMS | período descargado | registros (post-limpieza) |
|---|---|---|---:|
| `viirs_snpp` | `VIIRS_SNPP_SP` (VIIRS Suomi-NPP, 375 m) | 2025 | 235.287 |
| `viirs_noaa20` | `VIIRS_NOAA20_SP` (VIIRS NOAA-20 / JPSS-1, 375 m) | 2024 | 608.329 |
| `modis` | `MODIS_SP` (MODIS Terra, 1 km) | 2025 | 51.971 |

> `AI-Pipeline` es el **módulo de datos/ML** del equipo. El backend/API del mismo proyecto
> vive en el repositorio hermano [`PROMETHEUS-IGNIS/Backend-API`](https://github.com/PROMETHEUS-IGNIS/Backend-API):
> este repo produce datasets y resultados; el backend los expone vía endpoints y el
> frontend los visualiza (contrato de export: F9 del `ROADMAP.md`).

---

## Origen: qué corrige respecto al notebook original

Este proyecto nació corrigiendo [`astra-incendios-ia/Untitled0.ipynb`](https://colab.research.google.com/github/dayannamb2007-ctrl/astra-incendios-ia/blob/main/Untitled0.ipynb), un
primer borrador con fallas de fondo:

| Problema del original | Solución aquí |
|---|---|
| "Origen_Fuego" (antrópico vs natural) derivado de la **confianza de detección** de FIRMS — concepto erróneo: FIRMS no reporta la causa del fuego | Objetivos **honestos y documentados**: `nivel_impacto` (intensidad térmica por FRP/brillo) y `confianza_deteccion` (homogenizada entre sensores). El análisis de origen real quedó en F7 del roadmap, **bloqueado** hasta tener evidencia externa o metodología aprobada |
| **Fuga de datos**: el campo que definía la etiqueta (`confidence`) se incluyó como feature → "100 % de accuracy" falso | Regla en `config.EXCLUDE_BY_TARGET`: el campo que define una etiqueta se **excluye de las features**, y toda métrica se reporta con su **baseline** |
| Coordenadas "corregidas" a la fuerza (`0.0`), con resultados geográficamente imposibles (lat 0.6, lon −7.4) | Parser robusto + **validación contra el bbox de Colombia**; los inválidos se descartan y **se contabilizan** en el reporte de calidad |
| Desbalance ignorado (accuracy 97 % con recall ~0.01 en la clase minoritaria) | `class_weight='balanced'`, split **estratificado**, CV estratificada 5-fold, métricas **por clase** |
| Delimitadores con `try/except` ciegos (`;` vs `,`) | `csv.Sniffer` + validación de columnas mínimas esperadas |
| Esquemas de sensores mezclados ad hoc (`bright_ti5`/`brightness`, `confidence` l/n/h vs 0–100) | Homogenización explícita en `clean.py` → esquema unificado |
| Uploads manuales de CSV al Colab | **Descarga reproducible** vía API FIRMS (reanudable, ventanas de 5 días) |

---

## Resultados del MVP (ejecución real, `outputs/reporte_modelo.md`)

Calidad de datos tras la limpieza (ingesta de años completos por sensor):

| sensor | entrada → salida | fuera de bbox | térmicas inválidas | duplicados quitados | fechas inválidas |
|---|---|---:|---:|---:|---:|
| viirs_snpp 2025 | 235.287 → 235.287 | 0 | 0 | 0 | 0 |
| viirs_noaa20 2024 | 609.777 → 608.329 | 0 | 0 | 1.448 | 0 |
| modis 2025 | 51.978 → 51.971 | 0 | 7 | 0 | 0 |

### Objetivo 1 — `nivel_impacto` (fuego de intensidad térmica alta)

Modelo entrenado con VIIRS SNPP 2025; CV estratificada 5 folds; `class_weight='balanced'`.

| Evaluación | accuracy | f1 (weighted) | Detalle |
|---|---:|---:|---|
| CV 5-fold (SNPP) | **0.946** | 0.947 | vs baseline mayoritaria **0.826** → señal real |
| *Test* SNPP (n=47.058) | 0.94 | 0.95 | recall balanceado: 0.95 (alto) / **0.90** (bajo) |
| Cross-sensor NOAA-20 2024 (n=608.329) | 0.94 | 0.94 | generaliza entre satélites VIIRS |
| Cross-sensor MODIS 2025 (n=51.971) | 0.70 | 0.69 | degradación esperable: resolución ~1 km vs 375 m |

Recall de **0.90 en la clase minoritaria** — opuesto exacto al notebook original
(que reportaba 97 % de accuracy con recall 0.01–0.02 en su clase minoritaria).

Features más influyentes (permutación): `acq_hour` (0.19) y `is_noche` (0.04) —
la hora del pase nocturno marca la diferencia de intensidad detectada.

### Objetivo 2 — `confianza_deteccion` (fiabilidad de detección de FIRMS)

| Evaluación | accuracy | f1 (weighted) | vs baseline |
|---|---:|---:|---|
| CV 5-fold (SNPP) | 0.868 | 0.896 | baseline: **0.896** → **sin señal** |
| Cross-sensor NOAA-20 | 0.87 | 0.89 | idem |
| Cross-sensor MODIS | 0.69 | 0.61 | muy degradado |

**Hallazgo honesto y valioso:** con features de posición/estación/horario, los niveles de
confianza de FIRMS dan f1 ≈ baseline (el modelo casi siempre predice "nominal"). Esto
confirma que el "97–100 %" del notebook original era artefacto de fuga de datos, no señal.
Única feature con aporte real: `brightness_k` (0.17) — la temperatura de brillo sí guía la
confianza de detección, como documenta el algoritmo de FIRMS.

Matrices de confusión: `outputs/matriz_nivel_impacto_snpp.png` y
`outputs/matriz_confianza_deteccion_snpp.png`.

---

## Objetivos del modelo (etiquetas honestas)

| etiqueta | definición (umbrales en `config.py`) | features excluidas (anti-fuga) |
|---|---|---|
| `nivel_impacto` | `alto` si `frp ≥ 10 MW` **o** `brightness_k ≥ 330 K`; si no `bajo_moderado` | `frp`, `brightness_k` |
| `confianza_deteccion` | nivel de confianza homogenizado: VIIRS `l/n/h`; MODIS 0–100 → `baja` (<30) / `nominal` (30–80) / `alta` (≥80) | `confidence_*` |

Regla del repo: **si una etiqueta proviene de un campo, ese campo nunca entra como feature**
(`config.EXCLUDE_BY_TARGET`) y **nunca se reporta una métrica sin su baseline**.

---

## Estructura

``` text
AI-Pipeline/
├── src/
│   ├── config.py    # rutas, bbox de Colombia, fuentes FIRMS, umbrales, anti-fuga
│   ├── download.py  # descarga histórica Area API (ventanas de 5 días, reanudable)
│   ├── load.py      # carga robusta (sniffer de delimitador, dtype=str)
│   ├── clean.py     # validación geográfica + homogenización de esquemas
│   ├── targets.py   # etiquetas honestas (sin fuga de datos)
│   ├── features.py  # features numéricas + regla anti-fuga (make_X)
│   ├── model.py     # Dummy baseline + RandomForest (balanced, estratificado, CV)
│   ├── evaluate.py  # métricas por clase, matrices de confusión, importancia
│   └── main.py      # orquestador: load → clean → unify → train → report
├── notebooks/demo_pipeline.ipynb   # versión Colab del pipeline completo
├── data/raw/<sensor>/              # CSV crudos FIRMS (gitignored, ~45 MB)
├── data/processed/                 # datasets limpios (gitignored; unificado ~140 MB)
├── outputs/                        # reporte_modelo.md, matrices PNG (gitignored)
├── ROADMAP.md / PROJECT_CONTEXT.md / AGENTS.md / MEMORY.md   # docs del equipo
└── requirements.txt, .env.example, .gitignore
```

---

## Instalación

**Requisitos:** Python 3.10+ (desarrollado con 3.13) y una **MAP_KEY gratuita de FIRMS**.

1. **MAP_KEY (1 minuto):** registrarse gratis en
   [`firms.modaps.eosdis.nasa.gov/api/map_key/`](https://firms.modaps.eosdis.nasa.gov/api/map_key/).
   Límite: 5.000 transacciones / 10 min (suficiente de sobra; cada ventana de 5 días cuenta como pocas).
2. Entorno y dependencias (Windows / Git Bash):

``` bash
git clone https://github.com/PROMETHEUS-IGNIS/AI-Pipeline.git
cd AI-Pipeline
python -m venv .venv
.venv/Scripts/python.exe -m pip install -r requirements.txt       # Linux/Mac: .venv/bin/python
cp .env.example .env                                              # y pega tu clave en FIRMS_MAP_KEY=
```

---

## Uso rápido

Los módulos usan imports relativos: **siempre** ejecutar `python -m src.<modulo>` desde la raíz.

``` bash
# 1) Descargar el histórico (reanudable: lo ya descargado se salta)
#    Períodos equivalentes al notebook original:
.venv/Scripts/python.exe -m src.download --sensor viirs_snpp   --start 2025-01-01 --end 2025-12-31
.venv/Scripts/python.exe -m src.download --sensor viirs_noaa20 --start 2024-01-01 --end 2024-12-31
.venv/Scripts/python.exe -m src.download --sensor modis        --start 2025-01-01 --end 2025-12-31
#    (año completo ≈ 73 ventanas de 5 días por sensor; unos minutos por sensor)

# 2) Pipeline completo: limpiar → unificar → entrenar → reportar
.venv/Scripts/python.exe -m src.main
#    → data/processed/dataset_unificado.csv
#    → outputs/reporte_modelo.md + outputs/matriz_*.png
```

### En Google Colab

Tras el merge de `feature/steve` a `main`, abre directo:

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/PROMETHEUS-IGNIS/AI-Pipeline/blob/main/notebooks/demo_pipeline.ipynb)

La notebook hace todo: instalación, descarga reanudable por API, limpieza, métricas y
figuras (necesita tu MAP_KEY como secret de Colab `FIRMS_MAP_KEY` o en una celda).

---

## Documentación del equipo

| archivo | contenido |
|---|---|
| [`ROADMAP.md`](ROADMAP.md) | plan de trabajo: fases F0–F10, HUs delegables a agentes, dependencias y criterio de éxito |
| [`PROJECT_CONTEXT.md`](PROJECT_CONTEXT.md) | rol del agente, arquitectura conceptual, reglas de dominio y formato de entrega |
| [`AGENTS.md`](AGENTS.md) | instrucciones para sesiones de código: comandos, convenciones, límites, verificación |
| [`MEMORY.md`](MEMORY.md) | memoria entre sesiones: estado, decisiones (con su porqué) y aprendizajes |

Convención de commits: **Conventional Commits** (`feat(...)`, `docs(...)`, `test(...)`,
`fix(...)`, `chore(...)`) con asunto en español y cuerpo explicando el porqué.

---

## Contexto científico y limitaciones (léelo antes de presentar)

- **FIRMS no informa la causa de los incendios.** La columna `confidence` es la
  *confiabilidad de que la detección sea un fuego real* (producto del sensor), no el
  origen antrópico vs natural. Por eso:
  - `nivel_impacto::alto` es una **heurística documentada** (umbral FRP/brillo), no una
    clasificación oficial de FIRMS.
  - La clasificación de origen real requiere datos externos (cobertura, caminos,
    asentamientos, o registros de causa de IDEAM/CIMA): roadmap F6–F7.
- MODIS y VIIRS **no son intercambiables**: resolución (~1 km vs 375 m), horario de
  pases, campos y escala de confianza difieren. Las agregaciones conservan el sensor;
  no se "suman conteos armonizados" sin metodología aprobada.
- El proxy de "bosque" del notebook original (`bright_ti5`/`brightness` > 330 K) es
  crudo; se reemplazará con cobertura terrestre real (ESA WorldCover, F6).
- Las fuentes SP modernas traen la columna `type` (0 vegetación, 1 vulcanismo,
  2 fuente terrestre fija, 3 offshore) — disponible para ampliar el análisis.
- Las pruebas de software **no** validan ciencia: los resultados del modelo describen
  correlaciones de detección con contexto, no causalidad.

---

## Roadmap (post-MVP)

Detalle completo con historias de usuario y criterios: [`ROADMAP.md`](ROADMAP.md).

| Fase | Objetivo | Estado |
|---|---|---|
| F0–F4 | contratos, datos FIRMS, limpieza, modelos honestos, cross-sensor | ✅ Completada |
| F5 | suite pytest (fixtures sintéticos, anti-fuga) + lock de dependencias | ⬜ |
| F6 | covariables externas (ESA WorldCover, OSM caminos/población, clima) | ⬜ |
| F7 | contexto de origen con evidencia externa (**bloqueada a decisión científica**) | ⬜ |
| F8 | mapa de calor y series mensuales por sensor | ⬜ |
| F9 | contrato de export hacia Backend-API (`docs/export-contract.md`) | ⬜ |
| F10 | notebook demo pulida para jueces | ⬜ |

**Fases recomendadas ahora:** HU-A01 (tests) → HU-A09 (contrato con Backend-API) →
HU-A10 (demo) → HU-A03 (WorldCover).

---

## Créditos

**Equipo ASTRA — Semillero de Astronomía** (repo [`PROMETHEUS-IGNIS/AI-Pipeline`](https://github.com/PROMETHEUS-IGNIS/AI-Pipeline)) · NASA Space Apps Challenge 2026.

- Notebook antecedente: [`astra-incendios-ia`](https://github.com/dayannamb2007-ctrl/astra-incendios-ia)
- Datos: [NASA FIRMS](https://firms.modaps.eosdis.nasa.gov/) — producto MODIS C6.1/C7 y
  VIIRS VNP14IMG / VJ114IMG, vía Area API con fuentes Standard Processing (SP).
