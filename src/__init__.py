# Pipeline de IA de incendios en Colombia (NASA Space Apps 2026)
# Módulos: config, download, load, clean, targets, features, model, evaluate

import sys

# Consolas Windows (cp1252) no pueden imprimir Unicode como '→' o 'é' seguro.
# Reconfiguramos stdout/stderr a UTF-8 si es posible.
for _stream in (sys.stdout, sys.stderr):
    try:
        if _stream and getattr(_stream, "encoding", "").lower() not in ("utf-8", "utf8"):
            _stream.reconfigure(encoding="utf-8")
    except Exception:
        pass
