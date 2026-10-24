# MEMORY.md — AI-Pipeline (Incendios Colombia)
Memoria del proyecto entre sesiones. Máximo ~50 líneas: resume o elimina lo que ya no aporte.

## Estado actual
- MVP (F0–F4 del roadmap) completado y ejecutado end-to-end: descarga FIRMS SP →
  limpieza → esquema unificado → modelos honestos → reporte en `outputs/reporte_modelo.md`
  y matrices de confusión PNG en `outputs/`.
- Datos reales descargados (post-limpieza): VIIRS SNPP 2025 ≈ 47k, VIIRS NOAA-20 2024
  ≈ 608k, MODIS 2025 ≈ 52k registros. `data/processed/dataset_unificado.csv` (~140 MB).
- Resultados: `nivel_impacto` CV acc 0.946 vs baseline 0.826 (recall 0.90 en la clase
  minoritaria); cross-sensor NOAA-20 0.94 / MODIS 0.70. `confianza_deteccion` CV 0.868
  ≤ baseline 0.896 → sin señal real con features posicionales (hallazgo honesto clave).
- Documentación en formato del repo hermano `../Backend-API`: ROADMAP.md,
  PROJECT_CONTEXT.md, AGENTS.md y este MEMORY.md.
## Decisiones (qué cambió y por qué)
- El "Origen_Fuego" del notebook original (falsamente derivado de `confidence`) fue
  reemplazado por etiquetas honestas: `nivel_impacto` (FRP ≥ 10 MW o brillo ≥ 330 K)
  y `confianza_deteccion` (homogenizada). Anti-fuga garantizada por
  `config.EXCLUDE_BY_TARGET` (el campo que define la etiqueta se excluye de features).
- Nunca reportar accuracy sin baseline DummyClassifier (mayoritaria).
- `confidence` homogenizada: VIIRS l/n/h y MODIS 0–100 → baja/nominal/alta
  (bins <30 / 30–80 / ≥80 en `config.py`, decisión documentada y ajustable).
- Coordenadas validadas contra bbox de Colombia; descartes contabilizados, jamás
  "correcciones" a 0.0 (falla crítica del notebook original).
- Solo fuentes **SP** para histórico (NRT solo cubre días recientes); ventanas de
  máx. 5 días (`DAY_RANGE`) por límite del Area API.
- `data/`, `outputs/`, `.env` gitignored (datos grandes + secreto de la MAP_KEY).
## Aprendizajes y errores a evitar
- Consola Windows cp1252: `src/__init__.py` reconfigura stdout/stderr a UTF-8; no
  quitar ese bloque (los prints con acentos/`→` lanzan UnicodeEncodeError).
- No lanzar descargas paralelas con `&` dentro de un shell: los subprocesos mueren al
  cerrar el padre (la descarga 2024 se perdió así y se re-corrió en primer plano).
- `tee` hacia `outputs/` falla si el directorio aún no existe; crearlo antes del log.
- Las fuentes SP modernas traen columna extra `type` (0 vegetación, 1 vulcanismo,
  2 fuente terrestre fija, 3 offshore) — candidato a feature futura; se descarta hoy.
- Ejecutar módulos siempre como `python -m src.<modulo>` desde la raíz (imports
  relativos; `python src/main.py` falla).
## Próximos pasos
- HU-A01/A02: suite pytest sin red (fixtures sintéticos VIIRS-like/MODIS-like y prueba
  anti-fuga) + lock de dependencias.
- HU-A09: contrato de export (`docs/export-contract.md` + `src/export.py --export`)
  coordinado con `../Backend-API` (mapear `acq_date`+`acq_time` → `acquired_at` UTC).
- HU-A03: ESA WorldCover (cobertura real) después del contrato; no tocar `config.py`
  simultáneamente con otro agente.
- HU-A06 (origen con evidencia externa) permanece bloqueada hasta decisión científica;
  no simular aprobación ni usar `confidence` como causa.
- Al terminar: actualiza este archivo y sugiere commit solo con autorización del responsable.
