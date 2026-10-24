# AGENTS.md — AI-Pipeline (Incendios Colombia)

Módulo de datos y Machine Learning del equipo ASTRA para el reto NASA Space Apps
Challenge 2026 **Harmonization of MODIS and VIIRS Hot Spots**. Descarga, unifica, limpia
y analiza registros de anomalías térmicas (focos de calor) en Colombia usando el Area
API de NASA FIRMS, y produce datasets y resultados de modelos que el repositorio
hermano `../Backend-API` integra y expone (ver su `docs/api-contracts.md`).

Corrige un notebook antecedente (`astra-incendios-ia/Untitled0.ipynb`) que derivaba un
"origen del fuego" de la confianza de detección, tenía fuga de datos y coordenadas
corruptas. Historial completo: README.md → “¿Qué corrige respecto al notebook original?”.

## Stack y estructura

### Tecnologías y versiones clave

- **Python:** 3.13 (entorno actual 3.13.17), en `.venv` del repo (gitignored).
- **Pandas / NumPy:** manipulación de datos; todo se lee como `dtype=str` y se
  convierte solo en `clean.py`.
- **scikit-learn:** RandomForest, baseline DummyClassifier, CV estratificada,
  permutación de importancias.
- **matplotlib:** figuras con backend forzado `Agg` (archivos en `outputs/`, sin display).
- **requests:** cliente del Area API FIRMS (sin SDK).
- **Sin base de datos, sin Docker, sin CI.** No añadir infraestructura sin autorización.

### Estructura

``` text
AI-Pipeline/
├── src/
│   ├── config.py     # rutas, bbox Colombia, fuentes FIRMS, umbrales, anti-fuga
│   ├── download.py   # Area API FIRMS por ventanas de 5 días (reanudable)
│   ├── load.py       # sniffing delimitador; dtype=str; CSV vacíos tolerados
│   ├── clean.py      # validación geográfica + esquema unificado
│   ├── targets.py    # etiquetas honestas (nivel_impacto, confianza_deteccion)
│   ├── features.py   # features numéricas + regla anti-fuga (make_X)
│   ├── model.py      # Dummy baseline + RandomForest + CV estratificada
│   ├── evaluate.py   # métricas por clase, matrices PNG, importancias
│   └── main.py       # orquestador (requiere ≥2 sensores en data/raw/)
├── notebooks/demo_pipeline.ipynb   # versión Colab (descarga reanudable)
├── data/raw/<sensor>/              # CSV FIRMS crudos (gitignored, ~45 MB)
├── data/processed/                 # datasets limpios (gitignored; unificado ~140 MB)
├── outputs/                        # reporte_modelo.md + PNG (gitignored)
└── tests/                          # (F5 del roadmap, aún no existe)
```

- `config.py` es la única fuente de verdad para: bbox de Colombia, ids de fuente FIRMS
  (`SOURCES` = fuentes SP históricas), umbrales de etiquetas y `EXCLUDE_BY_TARGET`.
- `clean.py::UNIFIED_COLUMNS` define el contrato interno del dataset; cambiarlo es un
  cambio de contrato: plan y coordinación antes.
- Los artefactos para Backend-API (F9/HU-A09 del roadmap) se crearán en
  `src/export.py` → `data/releases/<version>/` con contrato en `docs/export-contract.md`.

## Comandos

Ejecutar desde la raíz del repo (la carpeta con `src/` y `requirements.txt`).
Los módulos usan imports relativos: **SIEMPRE** `python -m src.<modulo>`, nunca
`python src/main.py` (falla). En Windows/Git Bash:

``` bash
python -m venv .venv
.venv/Scripts/python.exe -m pip install -r requirements.txt

# Descarga histórica (reanudable: archivos existentes se saltan)
.venv/Scripts/python.exe -m src.download --sensor {all|viirs_snpp|viirs_noaa20|modis} \
    --start 2025-01-01 --end 2025-12-31

# Pipeline completo: limpiar → unificar → entrenar → reportar
.venv/Scripts/python.exe -m src.main
```

En Linux/Mac usar `.venv/bin/python`. Pruebas: cuando exista la suite (F5/HU-A01),
`python -m pytest -v` debe pasar sin red ni MAP_KEY; hasta entonces la verificación
rápida es el smoke-test de imports:

``` bash
.venv/Scripts/python.exe -c "from src import config, load, clean, targets, features, model, evaluate; print('OK')"
```

Requisitos de entorno:

- `FIRMS_MAP_KEY` en `.env` (cargado manualmente por `config.py`, sin python-dotenv);
  vacía → `src.download` aborta.
- La consola Windows usa cp1252: `src/__init__.py` reconfigura stdout/stderr a UTF-8.
  No eliminar ese bloque (los prints con acentos/`→` lanzan `UnicodeEncodeError`).
- `data/`, `outputs/`, `.env` y `.venv` están gitignored; no forzar su commit.

## Convenciones

- Documentación de equipo, comentarios de apoyo y explicaciones al responsable:
  **español**. Identificadores: columnas del dataset en inglés (esquema FIRMS),
  objetivos de dominio en español (`nivel_impacto`, `confianza_deteccion`,
  `is_noche`); mantener ese estado al ampliar.
- `snake_case` en módulos/funciones/variables; constantes `UPPER_SNAKE_CASE` en `config.py`.
- Commits en formato **Conventional Commits**: `type(ámbito): asunto corto en español`
  — tipos habituales `feat`, `fix`, `docs`, `test`, `refactor`, `chore` (ej.
  `feat(cleaning): bin de confianza para MODIS`); asunto ≤ ~72 caracteres, cuerpo
  opcional con líneas cortas y justificación (el porqué, no repite el diff).
- Todo umbral, bin o ROADMAP-decisión vive en `config.py` con justificación en su docstring.
- Semilla única: `config.SEED`.
- No devolver métricas sin su baseline DummyClassifier ni sin CV estratificada.
- Docstrings cortos en español que expliquen el porqué, no el qué.

## Reglas de dominio / trampas conocidas

- `confidence` de FIRMS es la **confiabilidad de la detección**, no la causa del fuego.
  Nunca presentarla como origen antrópico/natural. La clasificación de origen real
  (roadmap F7/HU-A06) está bloqueada hasta tener evidencia externa o metodología
  aprobada; no simular.
- MODIS y VIIRS no son intercambiables: resolución (~1 km vs 375 m), frecuencia,
  campos (`brightness`/`bright_t31` vs `bright_ti4`/`bright_ti5`) y confianza
  (0–100 vs l/n/h) difieren. No sumar conteos de sensores como "total" indistinto.
- Anti-fuga: si una etiqueta viene de un campo, ese campo se excluye de las features
  vía `config.EXCLUDE_BY_TARGET` (hoy: `frp`/`brightness_k` para `nivel_impacto`).
  El notebook antecedente reportaba 97–100 % de accuracy falsa por incluir el campo
  del label como feature.
- Coordenadas: grados decimales validadas contra el bbox de Colombia (`config.py`).
  Fuera de rango se descartan y se contabilizan en el reporte de calidad; jamás
  valores inventados como `0.0`.
- FIRMS: fuentes `*_SP` para histórico (NRT solo días recientes); el Area API acepta
  **máx. 5 días por petición** (`DAY_RANGE=5`, no ampliarlo); MAP_KEY con límite de
  5000 transacciones/10 min; las fuentes SP modernas traen columna extra `type`
  (no presente en las export antiguas del notebook).
- Fechas: FIRMS usa `YYYY-MM-DD`; la limpieza tolera formatos regionales (`1/01/2025`)
  con parseo dayfirst y descarta inválidas contabilizándolas.
- No inventar datos, campos, métricas ni disponibilidad; fixtures sintéticos solo
  para tests e identificados como demostrativos.

## Forma de trabajar

1. Lee `PROJECT_CONTEXT.md`, `MEMORY.md` y este archivo antes de actuar.
2. Inspecciona el estado real (`data/raw/`, `data/processed/`, git status). No asumas
   que una fase del roadmap ya está hecha ni que los datos existen.
3. Cambios pequeños y claros: implementa directo. Cambios que afecten `config.py`,
   `clean.py`, el esquema exportado o varios módulos: plan breve y aprobación primero.
4. Ejecuta las verificaciones pertinentes y reporta resultados reales (comandos,
   qué pasa, qué falla). No declares terminado con fallos sin explicar.
5. Actualiza `MEMORY.md` al terminar cada tarea (ver sección Memoria).

## Memoria

- Al empezar, lee `MEMORY.md`: estado del proyecto, decisiones y errores evitados.
- Al terminar una tarea, actualízalo: estado actual, decisiones importantes (con su
  porqué) y aprendizajes. Máximo ~50 líneas: resume o borra lo que ya no aporte.
- Si algo se vuelve regla permanente, muévelo a este `AGENTS.md` en lugar de dejarlo
  en la memoria.
- Nunca almacenar datos sensibles (MAP_KEY, tokens) en la memoria ni en el repo.

## Límites

### ✅ Siempre

- Validar coordenadas contra el bbox y contabilizar descartes.
- Conservar procedencia (`source`, `confidence_raw`, sensor en agregaciones).
- Reportar métricas con baseline y CV; honestidad sobre resultados negativos.
- Mantener el UTF-8 de `src/__init__.py` y el backend `Agg` de matplotlib.
- Mantener secretos y datos grandes fuera del git.
- Actualizar `MEMORY.md` al terminar cada tarea.

### ⚠️ Pregunta antes

- Cambiar umbrales/bins de etiquetas, `UNIFIED_COLUMNS` o `EXCLUDE_BY_TARGET`.
- Modificar `download.py` (rate limits, `DAY_RANGE`, estructura de `data/raw/<sensor>/`).
- Añadir dependencias o herramientas (lint, CI, geopandas, seaborn…).
- Cambiar el esquema exportado hacia Backend-API (coordinar con su responsable).
- Eliminar archivos o hacer refactorizaciones amplias.

Si una de estas es imprescindible, explica necesidad, alternativas e impacto y espera
aprobación antes de actuar.

### 🚫 Nunca

- Presentar métricas infladas o de una fase no ejecutada como reales.
- Derivar "origen del fuego" de `confidence` o de cualquier dato FIRMS sin la
  metodología aprobada de F7.
- Corregir coordenadas con valores inventados (`0.0`).
- Sumar MODIS+VIIRS sin conservar el sensor en cada fila.
- Introducir credenciales en código, pruebas, logs o documentación.
- Hacer commits, pushes o despliegues sin solicitud explícita del responsable.

## Verificación

Antes de declarar terminada una tarea:

1. Confirma los criterios de aceptación de la HU correspondiente (ROADMAP.md).
2. Smoke-test de imports y, si hay datos, `python -m src.main` con la salida completa revisada.
3. Cuando exista `tests/`: `python -m pytest -v` debe pasar sin red.
4. Para cambios en `clean.py`/`targets.py`: inspecciona el reporte de calidad
   (descartes, duplicados) antes/después y confirma que las cantidades razonan.
5. Para cambios del modelo: reporte CV + baseline + validación cross-sensor al día en
   `outputs/reporte_modelo.md`.
6. Para cambios de export: valida muestras contra el esquema del contrato y contra
   `app/schemas/observation.py` del repo hermano cuando aplique.
7. Revisa `git status`/`git diff` por archivos grandes o secretos incluidos por accidente.

Regla de cierre: si algo falló o no se pudo ejecutar, dilo con el error real. Las
pruebas de software no demuestran validez científica de las etiquetas; las etiquetas
son heurísticas documentadas en `config.py`.
