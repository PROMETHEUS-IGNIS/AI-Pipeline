# ROADMAP.md — AI-Pipeline (Incendios Colombia)

## 1. Propósito

Este roadmap organiza el desarrollo del módulo de datos/ML del equipo ASTRA para el reto NASA Space Apps Challenge 2026 **Harmonization of MODIS and VIIRS Hot Spots**. Divide el trabajo en fases, historias de usuario (HU), criterios de aceptación y tareas pequeñas que pueden delegarse a agentes de código.

`AI-Pipeline` es el módulo **datos/ML** del mismo proyecto cuyo backend/API vive en el repositorio hermano `../Backend-API` (con su propio `ROADMAP.md`, `PROJECT_CONTEXT.md` y `MEMORY.md`). La coordinación entre ambos repos es un contrato de integración explícito (ver F9): este repo produce datasets procesados y resultados de modelos; el backend los expone vía endpoints; el frontend los visualiza.

Este documento es un plan de ejecución: no reemplaza `PROJECT_CONTEXT.md`, `AGENTS.md` ni las decisiones científicas del equipo.

## 2. Cómo utilizar este roadmap

- Trabaja en orden de dependencias. Las fases marcadas ✅ solo necesitan mantenimiento (tests y documentación).
- Cada tarea delegable debe tener objetivo claro, archivos esperados, criterios de aceptación y verificación.
- Antes de asignar una tarea a un agente, proporciónele `AGENTS.md`, `PROJECT_CONTEXT.md` y la HU correspondiente.
- Asigna una HU por agente. Evita que dos agentes toquen simultáneamente `config.py` o `clean.py` (fuentes de verdad del pipeline).
- **No inventes datos, campos FIRMS, fórmulas científicas ni métricas.** Si falta una decisión de dominio, registra el bloqueo y trabaja en tareas independientes.
- Integra cambios mediante revisión humana; ningún agente hace commits, pushes ni despliegues sin autorización explícita.

### Prioridad

- **P0 — Imprescindible:** necesario para la demo del equipo.
- **P1 — Importante:** aporta el análisis principal robusto.
- **P2 — Opcional:** solo con tiempo, datos y contratos a mano.

### Definition of Ready (DoR)
1. Objetivo y resultado esperado claros.
2. Dependencias y datos disponibles, o indicando explícitamente qué está simulado.
3. Criterios de aceptación verificables.
4. No depende de una decisión científica pendiente sin alternativa provisional autorizada.

### Definition of Done (DoD)
1. Cumple los criterios de aceptación.
2. Incluye pruebas o verificación pertinente; los resultados reales se reportan con honestidad.
3. Documentación (`README.md`, `AGENTS.md`, `MEMORY.md`) actualizada si corresponde.
4. No introduce secretos, datos sintéticos presentados como reales, ni cambios ajenos a la HU.
5. El cambio fue revisado por la persona responsable.

---

## 3. Resumen de fases

| Fase | Objetivo | Prioridad | Estado | Entregable |
|---|---|---:|---|---|
| F0. Alineación y contratos | Esquema unificado, umbrales, reglas anti-fuga | P0 | ✅ Completada | `config.py`, `clean.py`, `targets.py` |
| F1. Descarga histórica FIRMS | Datos reales VIIRS/MODIS de Colombia vía API | P0 | ✅ Completada | `data/raw/` (73–74 ventanas por sensor) |
| F2. Limpieza y homogenización | Coordenadas válidas + esquema común entre sensores | P0 | ✅ Completada | `data/processed/dataset_unificado.csv` |
| F3. Objetivos honestos y modelo base | Etiquetas sin fuga de datos + RandomForest estratificado | P0 | ✅ Completada | `outputs/reporte_modelo.md` |
| F4. Validación cruzada entre sensores | Entrenar SNPP → evaluar NOAA-20 y MODIS | P0 | ✅ Completada | Sección cross-sensor del reporte |
| F5. Pruebas y reproducibilidad | Suite pytest local y dependencias fijadas | P1 | ⬜ | `tests/` |
| F6. Covariables externas | Cobertura real (ESA WorldCover), caminos/población (OSM), clima | P1 | ⬜ | Features adicionales + re-entrenamiento |
| F7. Contexto de origen | Aproximación honesta al origen con evidencia externa real | P2 | ⬜ | Bloqueada hasta decisión científica |
| F8. Analítica y visualización | Mapas de calor, series mensuales, estadísticas por región | P1 | ⬜ | Figuras y dataset analítico |
| F9. Contrato con Backend-API | Exportar datasets/resultados con esquema estable | P0 (integración) | ⬜ | Contrato `docs/export-contract.md` |
| F10. Demo para jueces | Notebook demo pulida + checklist de presentación | P0 | ⬜ | `notebooks/demo_pipeline.ipynb` |

Las fases F5, F6, F8 y F9 pueden avanzar en paralelo si cada agente respeta módulos separados.

---

# 4. Fases, historias de usuario y tareas delegables

## F0–F4 — Completadas (estado del MVP)

- Esquema unificado en `clean.py::UNIFIED_COLUMNS`; umbrales y bbox documentados en `config.py`.
- Datos reales descargados con fuentes **SP** (`VIIRS_SNPP_SP` 2025, `VIIRS_NOAA20_SP` 2024, `MODIS_SP` 2025).
- Modelos entrenados con VIIRS SNPP: CV 5-fold estratificada, `class_weight='balanced'`; validación cruzada contra NOAA-20 y MODIS.
- Regla permanente: **nunca se reporta accuracy sin baseline**; el DummyClassifier (mayoritaria) siempre acompaña al reporte.

---

## F5 — Pruebas y reproducibilidad

**Objetivo:** proteger el MVP de regresiones con pruebas rápidas, sin red ni credenciales.

### HU-A01 — Suite de pruebas del pipeline

**Como** responsable del módulo, **quiero** una suite pytest que valide limpieza, etiquetas y entrenamiento, **para** detectar regresiones antes de ampliar features.

**Prioridad:** P1.

**Criterios de aceptación**
- `python -m pytest -v` pasa sin red, sin `FIRMS_MAP_KEY` y sin datos grandes.
- Los fixtures reproducen las columnas de la API real (incluida `type`) y están identificados como sintéticos de prueba.
- Pruebas cubren: detección de delimitador (`;` y `,`), coordenadas fuera del bbox descartadas (jamás `0.0`), homogenización de `confidence` (VIIRS l/n/h y MODIS 0–100 → baja/nominal/alta), fechas ambiguas.
- Prueba anti-fuga: `make_X(target)` excluye los campos definidos en `config.EXCLUDE_BY_TARGET`.
- Smoke-test de ML con un dataset diminuto (~200 filas) que verifica fit/predict.

**Tareas delegables**
- **T-A01.1** — Crear `tests/fixtures/` con CSV sintéticos pequeños (VIIRS-like y MODIS-like) y su documentación.
- **T-A01.2** — Tests para `load.detect_delimiter` y `load.load_raw` (columnas mínimas, archivo vacío).
- **T-A01.3** — Tests para `clean.clean_dataset` (bbox, duplicados, térmicas inválidas).
- **T-A01.4** — Tests para `targets` + `features.make_X` (exclusiones anti-fuga, relleno de NaN con mediana).
- **T-A01.5** — Smoke-test del RandomForest con `config.SEED`.

**Convención:** si una prueba necesitara datos reales grandes, no se versionan; se usan los fixtures sintéticos.

### HU-A02 — Bloqueo de dependencias

**Prioridad:** P1.

**Criterios de aceptación**
- Versiones exactas del venv registradas en un archivo de lock.
- Semillas (`config.SEED`) usadas en todos los componentes aleatorios; reproducibilidad documentada en README.

**Tareas delegables**
- **T-A02.1** — Generar `requirements-lock.txt` a partir del venv actual (`pip freeze`).
- **T-A02.2** — Documentar instalación reproducible (Windows y Linux/Mac).

---

## F6 — Covariables externas

**Objetivo:** pasar de features puramente posicionales a contexto físico real, sin fusionar datos mal interpretados.

### HU-A03 — Cobertura terrestre real (ESA WorldCover)

**Como** analista, **quiero** la clase de cobertura (bosque/sabana/agricultura) de cada detección, **para** analizar el comportamiento del fuego sin depender del proxy crudo del brillo térmico (el `Es_Forestal` del notebook original).

**Prioridad:** P1.

**Criterios de aceptación**
- Fuente elegida (ESA WorldCover 10 m u otra) documentada con su licencia y resolución.
- Función `landcover(lat, lon)` determinística con cache local; no re-descargar en cada ejecución de `src.main`.
- Columna integrada como campo adicional sin romper `UNIFIED_COLUMNS` existente.
- Pruebas con fixtures; los CSV externos crudos van a `data/raw/` (gitignored).

**Tareas delegables**
- **T-A03.1** — Investigar proveedores (AppEEARS, tiles públicos S3 de ESA) y registrar la decisión de acceso.
- **T-A03.2** — Implementar `src/context/landcover.py` con cache.
- **T-A03.3** — Integrar la variable a `config.BASE_FEATURES` y `EXCLUDE_BY_TARGET` si aplica.
- **T-A03.4** — Re-entrenar `nivel_impacto` con la nueva variable y actualizar el reporte.

### HU-A04 — Proximidad humana (OSM / caminos)

**Como** analista, **quiero** la distancia aproximada de cada foco a carreteras y asentamientos, **para** construir (en F7) un contexto de origen con evidencia real, no con la columna `confidence` interpretada erróneamente como "origen" en el notebook original.

**Prioridad:** P1.

**Criterios de aceptación**
- Fuente (Overpass API o fragmentos pre-extraídos) documentada con sus límites de uso.
- Cálculo aproximado y barato (p. ej. grid de distancias precalculado), no una llamada por registro.
- Columna `dist_roads_km` documentada en el esquema; decisiones registradas en `MEMORY.md`.

**Tareas delegables**
- **T-A04.1** — Diseñar el almacenamiento de puntos OSM pre-procesados (bbox Colombia).
- **T-A04.2** — Implementar el cálculo de distancia por grid.
- **T-A04.3** — Re-entrenar y analizar importancia de features.

### HU-A05 — Precipitación y clima

**Prioridad:** P2. Siguiendo el patrón de HU-A03, con una fuente climática documentada (p. ej. CHIRPS mensual) para contexto estacional. No se inicia hasta terminar F6.

---

## F7 — Contexto de origen con evidencia externa

### HU-A06 — Etiqueta de contexto de origen (BLOQUEADA)

**Como** equipo, **queremos** construir, con evidencia externa (HU-A03 + HU-A04), un análisis de probabilidad de origen antrópico vs natural, **para** dar el paso que el notebook original planteó de forma incorrecta (derivar "origen" de la confianza de detección).

**Prioridad:** P2.

**Bloqueos explícitos (no simular)**
- **Regla científica no definida:** el equipo (ciencia + datos) debe aprobar el criterio que combina cobertura y distancia humana como proxy de contexto. Mientras tanto, cualquier aproximación es etiqueta provisional y ninguna salida pública la presenta sin la nota "contexto heurístico, no causa validada".
- Si el equipo consigue una fuente real de causas (p. ej. registros de IDEAM/CIMA por departamento), esa fuente reemplaza al proxy y redefine esta HU.

**Tareas delegables**
- **T-A06.1** — Redactar una propuesta de criterio (documento de una página) y someterla a revisión del equipo.
- **T-A06.2** — Solo si hay aprobación: implementar la etiqueta y el modelo. Sin aprobación, no avanzar.

---

## F8 — Analítica y visualización

### HU-A07 — Mapa de calor y serie mensual

**Como** usuario del frontend (vía Backend-API), **quiero** la distribución de focos por mes y zona, **para** explorar la estacionalidad del fuego en Colombia.

**Prioridad:** P1.

**Criterios de aceptación**
- Figuras PNG por año/sensor en `outputs/`.
- Dataset agregado mensual por celda de grid, con esquema definido para el backend, **conservando siempre el sensor** (no se suma MODIS+VIIRS como "total" indistinto).
- La agregación es reproducible (script versionado, no cálculos manuales).

**Tareas delegables**
- **T-A07.1** — Agregación mensual por grid (`src/analytics/`).
- **T-A07.2** — Mapa de calor con matplotlib (añadir geopandas solo si una tarea real lo exige).
- **T-A07.3** — Serie temporal por sensor.

### HU-A08 — Estadísticas por región administrativa

**Prioridad:** P2. Requiere un shapefile/GeoJSON departamental con licencia libre acordada por el equipo. Fuera del MVP si no es indispensable.

---

## F9 — Contrato de resultados para Backend-API

### HU-A09 — Publicar el contrato de export

**Como** responsable de Backend-API, **quiero** un contrato documentado de los datasets y resultados que este módulo produce, **para** integrarlos y exponerlos sin conocer los internos del pipeline.

**Prioridad:** P0 para la integración del equipo (puede iniciarse en paralelo; la integración completa depende de F6/F8).

**Criterios de aceptación**
- Documento de contrato en `docs/export-contract.md` (o unificado con `docs/api-contracts.md` del repo hermano) con: nombre del artefacto, esquema de columnas (unidades, rangos, nulos), período cubierto, versión/semilla del modelo y fecha de generación.
- Exportación reproducible desde `src/main.py` (flag `--export`) que escribe `data/releases/<version>/`.
- Los artefactos nunca contienen la `MAP_KEY` ni credenciales.
- Los cambios de esquema se coordinan y documentan; nunca cambios silenciosos.

**Tareas delegables**
- **T-A09.1** — Inventario de datasets/outputs actuales y propuesta de esquema, validada con muestras reales.
- **T-A09.2** — Implementar `src/export.py` con versionado simple (`v1`).
- **T-A09.3** — Coordinar el contrato con el responsable de Backend-API; registrar la decisión en este roadmap y en `MEMORY.md`.
- **T-A09.4** — Verificar correspondencia con los modelos del backend (`app/schemas/observation.py` del repo hermano) y documentar mapeos de campos (p. ej. `acq_date`+`acq_time` → `acquired_at` UTC).

---

## F10 — Demo para jueces

### HU-A10 — Notebook demo ejecutable

**Como** equipo, **quiero** una notebook Colab ejecutable de punta a punta, **para** demostrar el pipeline en vivo.

**Prioridad:** P0.

**Criterios de aceptación**
- `notebooks/demo_pipeline.ipynb` corre de arriba a abajo en Colab con una `FIRMS_MAP_KEY` válida.
- Incluye aviso de los límites de transacción de la API y descarga reanudable.
- Muestra figuras y métricas del MVP, con la explicación honesta de por qué el "clasificador de origen" del original no tenía señal.
- Checklist previa a la presentación escrita.

**Tareas delegables**
- **T-A10.1** — Ejecutar la notebook completa localmente y corregir cualquier error.
- **T-A10.2** — Pulir textos, figuras y referencias a `outputs/`.
- **T-A10.3** — Checklist de demo (datos, MAP_KEY, entorno limpio).

---

# 5. Orden recomendado de delegación

1. **Agente A — Pruebas:** HU-A01 y HU-A02 (protege lo construido; máxima prioridad ahora).
2. **Agente B — Contrato Backend:** HU-A09, coordinado con el responsable de Backend-API.
3. **Agente C — Covariables:** HU-A03 (después de B, para no tocar `config.py` a la vez).
4. **Agente D — Contexto:** HU-A04 y, con aprobación científica, HU-A06.
5. **Agente E — Visualización:** HU-A07 cuando el esquema exportable esté estable, o en paralelo si no lo afecta.
6. **Agente F — Demo:** HU-A10 al final, sobre el pipeline estable.

Una sola persona es responsable de los cambios que afectan `config.py`, `clean.py` o el esquema exportado al backend.

## 6. Plantilla para asignar tareas a un agente

```text
Lee AGENTS.md, PROJECT_CONTEXT.md, MEMORY.md y la HU asignada en ROADMAP.md.

Tarea: [ID y título de la HU/tarea]
Objetivo: [resultado concreto]
Contexto existente: [archivos y contratos relevantes]
Alcance permitido: [archivos o componentes que puede modificar]
Fuera de alcance: [qué no debe cambiar]
Criterios de aceptación:
- [criterio 1]
- [criterio 2]

Pruebas/verificación requeridas:
- [comandos y casos]

Antes de implementar:
- Inspecciona el estado real del repositorio (incluye data/raw/ si aplica).
- Si falta una decisión científica o el cambio afecta el esquema exportado,
  detente y solicita aclaración.
- Para cambios amplios, presenta un plan breve antes de editar.

Al terminar:
- Resume los cambios.
- Enumera los archivos modificados.
- Indica comandos ejecutados y resultados reales.
- Señala pendientes, riesgos y pruebas no ejecutadas.
- No hagas commit, push ni despliegue.
```

## 7. Dependencias críticas y bloqueos

| Decisión o insumo | Responsable principal | Bloquea |
|---|---|---|
| MAP_KEY FIRMS vigente (límite: 5000 transacciones/10 min) | Steve/Dayanna (responsable AI-Pipeline) | Re-descargas y actualizaciones de F1 |
| Definición del criterio de origen antrópico | Science Lead + Datos | HU-A06 (queda P2/bloqueada sin esto) |
| Contrato de export consumido por Backend-API | Responsables de ambos repos | HU-A09 y toda la integración frontend |
| Elección de proveedores externos (WorldCover, OSM) y su licencia | Equipo | HU-A03 / HU-A04 |
| Shapefile departamental con licencia libre | Equipo | HU-A08 |

## 8. Criterio de éxito del MVP avanzado

El proyecto está listo para la demostración cuando:

- Una persona nueva puede ejecutar el pipeline tras leer el README (instalación limpia de venv + MAP_KEY).
- La suite de pruebas (F5) pasa sin red y protege las reglas anti-fuga.
- El contrato de export (F9) está acordado con Backend-API y los artefactos se generan con `--export`.
- Las covariables externas (F6) están integradas con procedencia documentada.
- La notebook demo (F10) corre en Colab de punta a punta.
- El equipo puede explicar con honestidad: qué es dato observado, qué es criterio heurístico documentado y qué proviene de otro repositorio (Backend-API).

**Regla final:** prioriza un flujo pequeño, trazable y reproducible de FIRMS → datos limpios → modelo honesto → artefactos exportables a Backend-API, antes de añadir más endpoints, más modelos o más infraestructura.
