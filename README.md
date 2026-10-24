# AI-Pipeline — Detección y análisis de fuego activo en Colombia (VIIRS + MODIS)

Pipeline de Inteligencia Artificial para el **NASA Space Apps 2026** que descarga, unifica, limpia
y analiza registros de anomalías térmicas (fuego activo) en **Colombia** usando el **Area API de FIRMS**
con las fuentes de archivo histórico (Standard Processing):

| sensor local | fuente API señalada |
|---|---|
| `viirs_snpp` | `VIIRS_SNPP_SP` (VIIRS Suomi-NPP) |
| `viirs_noaa20` | `VIIRS_NOAA20_SP` (VIIRS NOAA-20 / JPSS-1) |
| `modis` | `MODIS_SP` (MODIS Terra/Aqua) |

Este proyecto **refactoriza y corrige** el notebook original
[`astra-incendios-ia/Untitled0.ipynb`](https://colab.research.google.com/github/dayannamb2007-ctrl/astra-incendios-ia/blob/main/Untitled0.ipynb).

## ¿Qué corrige respecto al notebook original?

| Problema del original | Solución aquí |
|---|---|
| "Origen_Fuego" (antrópico vs natural) derivado de la **confianza de detección** de FIRMS — concepto erróneo: FIRMS no reporta la causa del fuego | Objetivos **honestos y documentados**: `nivel_impacto` (intensidad térmica por FRP/brillo) y `confianza_deteccion` (homogenizada entre sensores) |
| **Fuga de datos**: el campo que definía la etiqueta (`confidence`) se incluyó como feature (el "100% de accuracy" era falso) | Regla en `config.EXCLUDE_BY_TARGET`: el campo que define la etiqueta se **excluye de las features** |
| Coordenadas "corregidas" a fuerza (`0.0`), resultados geográficamente imposibles (lat 0.6, lon −7.4) | Parser robusto + **validación contra el bbox de Colombia**; los inválidos se descartan reportándolos |
| Desbalance de clases ignorado (accuracy 97% con recall ~0.01 en la clase minoritaria) | `class_weight='balanced'`, split **estratificado**, CV estratificada 5-fold, métricas **por clase** |
| Delimitadores con `try/except` ciegos (`;` vs `,`) | `csv.Sniffer` + validación de columnas mínimas esperadas |
| Esquemas de sensores mezclados ad hoc (`bright_ti5`/`brightness`, `confidence` l/n/h vs 0–100) | Homogenización explícita en `clean.py` → esquema unificado |
| Fechas ambiguas (`1/01/2025`) sin marcar | Fechas parseadas; inválidas descartadas con conteo |

## Estructura

```
AI-Pipeline/
├── src/
│   ├── config.py    # rutas, bbox de Colombia, fuentes FIRMS, umbrales, anti-fuga
│   ├── download.py  # descarga histórica Area API (ventanas de 5 días, reanudable)
│   ├── load.py      # carga robusta (sniffer de delimitador, dtype=str)
│   ├── clean.py     # validación geográfica + homogenización de esquemas
│   ├── targets.py   # etiquetas honestas (nivel_impacto, confianza_deteccion)
│   ├── features.py  # features numéricas (posición, época, hora, día/noche)
│   ├── model.py     # Dummy baseline + RandomForest (balanced/estratificado/CV)
│   ├── evaluate.py  # reportes por clase, matrices de confusión, importancia
│   └── main.py      # orquestador
├── notebooks/demo_pipeline.ipynb  # versión Colab-friendly
├── data/raw/                      # CSV crudos de FIRMS (gitignored)
├── data/processed/                # datasets limpios (gitignored)
└── outputs/                       # métricas y figuras (gitignored)
```

## Requisitos

- Python 3.10+
- Una **MAP_KEY** gratuita de [FIRMS](https://firms.modaps.eosdis.nasa.gov/api/map_key/)

## Uso rápido

```bash
python -m venv .venv
.venv/Scripts/pip install -r requirements.txt   # (Windows) / pip3 en Linux-Mac

# 1) Copia tu clave en .env
#    FIRMS_MAP_KEY=tu_clave

# 2) Descargar el histórico (reanudable; equivalentes al notebook original)
.venv/Scripts/python -m src.download --sensor viirs_snpp   --start 2025-01-01 --end 2025-12-31
.venv/Scripts/python -m src.download --sensor viirs_noaa20 --start 2024-01-01 --end 2024-12-31
.venv/Scripts/python -m src.download --sensor modis        --start 2025-01-01 --end 2025-12-31

# 3) Pipeline completo: limpiar → unificar → entrenar → reportar
.venv/Scripts/python -m src.main
```

Salidas principales: `outputs/reporte_modelo.md` y las matrices de confusión en `outputs/`.

En **Colab**: abre `notebooks/demo_pipeline.ipynb` desde el repo (botón "Open in Colab"), pon tu
MAP_KEY, y ejecuta.

## Contexto científico (importante)

- **FIRMS no informa la causa de los incendios.** La columna `confidence` es la *confianza de que la
  detección sea un fuego real* (producto del sensor), no el origen antrópico vs natural. Por eso aquí:
  - `nivel_impacto` «alto» se define por potencia radiativa `frp ≥ 10 MW` **o** brillo 4 µm ≥ 330 K
    (umbrales en `config.py`, documentados y ajustables).
  - `confianza_deteccion` clasifica la confianza homogenizada VIIRS/MODIS
    (VIIRS l/n/h; MODIS 0–100 con bins: baja <30, nominal 30–80, alta ≥80).
- Los pitch del proyecto debería dirigirse a: distribución espacial-temporal del fuego en Colombia,
  intensidad térmica y calidad de detección multimisión — y, como siguiente fase, **cruzar covariables
  externas reales** (cobertura terrestre ESA WorldCover, cercanía a carreteras/asentamientos,
  precipitación) para estimar riesgo y contextos de ocurrencia con evidencia real.
- El dataset moderno (`MODIS_SP`/`VIIRS_*_SP`) trae una columna adicional `type`
  (0: vegetación, 1: vulcanismo, 2: otra fuente terrestre fija, 3: offshore) que el notebook
  procesaba con esquemas antiguos — disponible para ampliar el análisis.

## Roadmap

1. ✅ MVP honesto (este repo): riesgo térmico + confianza de detección, cross-sensor.
2. ⏳ Unir covariables externas (WorldCover, OSM roads, población).
3. ⏳ Panel de visualización (mapa de calor mensual por departamento).
4. ⏳ Estimación de origen antrópico **solo** con evidencia externa documentada.

## Créditos

Equipo ASTRA — Semillero de Astronomía · NASA Space Apps 2026.
Datos: [NASA FIRMS](https://firms.modaps.eosdis.nasa.gov/) (MODIS C6.1/C7 y VIIRS VNP14IMG/VJ114IMG).
