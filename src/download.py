"""Descarga histórica desde el Area API de FIRMS.

La API admite ventanas de hasta 5 días por petición, así que un rango largo
(dividido en ventanas de 5 días). Soporta reanudación: los archivos ya
descargados se saltan.

Uso:
    python -m src.download --sensor all --start 2025-01-01 --end 2025-12-31
"""
from __future__ import annotations

import argparse
import datetime as dt
import time
from pathlib import Path

import requests

from . import config

DAY_RANGE = 5          # máximo permitido por la API
PAUSA_ENTRE_LLAMADAS = 0.8  # segundos; amable con el servidor
MAX_REINTENTOS = 4


# ------------------------------------------------------------- helpers ----
def _url(source: str, fecha_desde: dt.date | None = None) -> str:
    base = (
        f"{config.FIRMS_API_BASE}/area/csv/"
        f"{config.FIRMS_MAP_KEY}/{source}/{config.AREA_COORDS}/{DAY_RANGE}"
    )
    if fecha_desde is not None:
        base += f"/{fecha_desde:%Y-%m-%d}"
    return base


def _ventanas(desde: dt.date, hasta: dt.date, dias: int):
    """Genera ventanas [inicio, fin] inclusive, de a 'dias' días."""
    actual = desde
    while actual <= hasta:
        fin = min(actual + dt.timedelta(days=dias - 1), hasta)
        yield actual, fin
        actual = fin + dt.timedelta(days=1)


def _descargar(session: requests.Session, url: str) -> str | None:
    for intento in range(1, MAX_REINTENTOS + 1):
        try:
            resp = session.get(url, timeout=180)
            if resp.status_code == 429:
                espera = 30 * intento
                print(f"  429 (límite). Esperando {espera}s...")
                time.sleep(espera)
                continue
            resp.raise_for_status()
            return resp.text
        except requests.RequestException as exc:  # noqa: BLE001
            if intento == MAX_REINTENTOS:
                print(f"  X Falló tras {MAX_REINTENTOS} intentos: {url} -> {exc}")
                return None
            time.sleep(10 * intento)
    return None


def _texto_valido(texto: str) -> bool:
    """Respuesta válida: encabezado CSV de FIRMS (puede tener 0 filas)."""
    if not texto or not texto.strip():
        return False
    return texto.strip().lower().startswith("latitude")


# --------------------------------------------------------- descarga -------
def descargar_sensor(
    sensor: str,
    source_id: str,
    desde: dt.date,
    hasta: dt.date,
    out_dir: Path,
    forzar: bool = False,
) -> int:
    """Descarga todas las ventanas de un sensor. Devuelve # de archivos nuevos."""
    out_dir.mkdir(parents=True, exist_ok=True)
    session = requests.Session()
    nuevos = 0
    total = sum(1 for _ in _ventanas(desde, hasta, DAY_RANGE))
    for i, (ini, fin) in enumerate(_ventanas(desde, hasta, DAY_RANGE), start=1):
        destino = out_dir / f"{source_id}_{ini:%Y%m%d}_{fin:%Y%m%d}.csv"
        if destino.exists() and destino.stat().st_size > 0 and not forzar:
            continue
        texto = _descargar(session, _url(source_id, ini))
        if texto is None:
            continue
        if not _texto_valido(texto):
            print(f"  ! Respuesta inválida en {ini:%Y-%m-%d}: {texto[:120]!r}")
            continue
        destino.write_text(texto, encoding="utf-8")
        nuevos += 1
        if i % 10 == 0 or i == total:
            print(f"  [{sensor}] {i}/{total} ventanas ({ini:%Y-%m-%d} → {fin:%Y-%m-%d})")
        time.sleep(PAUSA_ENTRE_LLAMADAS)
    print(f"  [{sensor}] descargas nuevas: {nuevos}")
    return nuevos


def verificar_clave() -> bool:
    ok = bool(config.FIRMS_MAP_KEY)
    if not ok:
        print("ERROR: FIRMS_MAP_KEY vacía. Crea .env con tu clave (ver .env.example).")
    return ok


# ------------------------------------------------------------- status -----
def disponibilidad(sensor_id: str) -> str:
    """Consulta /api/data_availability para ver fechas disponibles."""
    url = f"{config.FIRMS_API_BASE}/data_availability/csv/{config.FIRMS_MAP_KEY}/{sensor_id}"
    txt = requests.get(url, timeout=60).text
    path = config.OUTPUTS_DIR / f"disponibilidad_{sensor_id}.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(txt, encoding="utf-8")
    return str(path)


# ---------------------------------------------------------------- CLI -----
def main() -> None:
    ap = argparse.ArgumentParser(description="Descarga histórica FIRMS para Colombia")
    ap.add_argument("--sensor", default="all", choices=[*config.SOURCES.keys(), "all"])
    ap.add_argument("--start", required=True, help="YYYY-MM-DD")
    ap.add_argument("--end", required=True, help="YYYY-MM-DD")
    args = ap.parse_args()

    if not verificar_clave():
        return
    desde = dt.date.fromisoformat(args.start)
    hasta = dt.date.fromisoformat(args.end)
    sensores = config.SOURCES.items() if args.sensor == "all" else [(args.sensor, config.SOURCES[args.sensor])]

    for sensor, source_id in sensores:
        print(f"== Descargando {sensor} ({source_id}) {desde} → {hasta} ==")
        descargar_sensor(sensor, source_id, desde, hasta, config.RAW_DIR / sensor)


if __name__ == "__main__":
    main()
