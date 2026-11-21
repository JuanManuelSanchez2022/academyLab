#!/usr/bin/env python3
"""LAB 01 - Pruebas automatizadas para analizar_logs.py.

Por defecto los JSON de las pruebas se escriben en una carpeta temporal para no
modificar la evidencia versionada. Con --guardar-evidencia se escriben en
evidence/ como evidencia del laboratorio.
"""
import csv
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
SCRIPT = BASE / "scripts" / "analizar_logs.py"
TESTS = BASE / "data" / "test"
SAMPLE_LOG = BASE / "data" / "sample_logs" / "operaciones.log"
SYNTHETIC_CSV = BASE / "data" / "synthetic" / "operaciones_sinteticas.csv"
EVIDENCE = BASE / "evidence"
PY = os.environ.get("ACADEMYLAB_PYTHON") or sys.executable
OUTPUT_DIR = EVIDENCE


def run(args):
    return subprocess.run([PY, str(SCRIPT)] + args, capture_output=True, text=True, cwd=str(BASE))


def test_normal():
    out = OUTPUT_DIR / "normal.json"
    r = run(["-i", str(TESTS / "normal.log"), "-j", str(out)])
    assert r.returncode == 0, f"normal failed: {r.stderr}"
    data = json.loads(out.read_text())
    assert data["total_eventos_parseados"] == 10
    assert data["operaciones_unicas"] == 8
    assert data["conteo_por_estado"]["OK"] == 4
    assert data["conteo_por_estado"]["ERROR"] == 3
    assert data["conteo_por_estado"]["PENDIENTE"] == 3
    assert data["lineas_no_parseadas"] == 0
    assert data["alerta"]["hay_errores"] is True
    assert data["alerta"]["hay_pendientes"] is True
    # Estado actual: el último evento de cada operación.
    assert data["conteo_operaciones_por_estado_actual"] == {"ERROR": 2, "OK": 4, "PENDIENTE": 2}
    assert data["importe_operaciones_por_estado_actual"] == {"ERROR": 1760.0, "OK": 480.25, "PENDIENTE": 1281.25}
    assert data["estado_actual_por_operacion"]["OP-1002"]["estado"] == "PENDIENTE"
    assert data["estado_actual_por_operacion"]["OP-1003"]["estado"] == "OK"
    assert data["archivo"] == "data/test/normal.log", data["archivo"]
    return True


def test_empty():
    r = run(["-i", str(TESTS / "empty.log")])
    assert r.returncode == 0
    assert "Eventos parseados: 0" in r.stdout
    return True


def test_missing_file():
    r = run(["-i", str(TESTS / "does_not_exist.log")])
    assert r.returncode != 0
    assert "no existe" in r.stderr
    return True


def test_invalid_lines():
    r = run(["-i", str(TESTS / "invalid.log")])
    assert r.returncode == 0
    assert "Lineas no parseadas: 2" in r.stdout
    return True


def test_missing_ids():
    r = run(["-i", str(TESTS / "missing_ids.log")])
    assert r.returncode == 0
    assert "Lineas no parseadas: 2" in r.stdout
    return True


def test_invalid_imports():
    r = run(["-i", str(TESTS / "invalid_imports.log")])
    assert r.returncode == 0
    assert "Lineas no parseadas: 2" in r.stdout
    return True


def test_unknown_states():
    r = run(["-i", str(TESTS / "unknown_states.log")])
    assert r.returncode == 0
    assert "Lineas no parseadas: 1" in r.stdout
    return True


def test_multi_event():
    out = OUTPUT_DIR / "multi_event.json"
    r = run(["-i", str(TESTS / "multi_event.log"), "-j", str(out)])
    assert r.returncode == 0, f"multi_event failed: {r.stderr}"
    data = json.loads(out.read_text())
    assert data["total_eventos_parseados"] == 9
    assert data["operaciones_unicas"] == 5
    assert data["conteo_por_estado"]["OK"] == 3
    assert data["conteo_por_estado"]["ERROR"] == 3
    assert data["conteo_por_estado"]["PENDIENTE"] == 3
    assert data["conteo_operaciones_por_estado_actual"] == {"ERROR": 1, "OK": 2, "PENDIENTE": 2}
    assert data["estado_actual_por_operacion"]["OP-1005"]["importe"] == 1200.0
    return True


def test_csv_matches_log_current_state():
    """La tabla CSV de operaciones debe reflejar el último evento de cada operación del log."""
    # JSON auxiliar: siempre en una carpeta temporal, no es evidencia del laboratorio.
    with tempfile.TemporaryDirectory(prefix="lab01-csv-check-") as temporary_dir:
        out = Path(temporary_dir) / "sample_current_state.json"
        r = run(["-i", str(SAMPLE_LOG), "-j", str(out)])
        assert r.returncode == 0, f"sample log failed: {r.stderr}"
        actual = {
            op: (info["estado"], info["importe"])
            for op, info in json.loads(out.read_text(encoding="utf-8"))["estado_actual_por_operacion"].items()
        }
    with SYNTHETIC_CSV.open(encoding="utf-8-sig", newline="") as stream:
        table = {
            row["id_operacion"]: (row["estado"], float(row["importe"]))
            for row in csv.DictReader(stream)
        }
    assert table == actual, f"CSV {table} distinto del estado actual del log {actual}"
    return True


def run_all():
    tests = [
        ("normal", test_normal),
        ("empty", test_empty),
        ("missing_file", test_missing_file),
        ("invalid_lines", test_invalid_lines),
        ("missing_ids", test_missing_ids),
        ("invalid_imports", test_invalid_imports),
        ("unknown_states", test_unknown_states),
        ("multi_event", test_multi_event),
        ("csv_matches_log_current_state", test_csv_matches_log_current_state),
    ]
    passed = 0
    failed = 0
    for name, fn in tests:
        try:
            fn()
            print(f"PASS: {name}")
            passed += 1
        except Exception as e:
            print(f"FAIL: {name} -> {e}")
            failed += 1
    print(f"\nResultados: {passed} pasaron, {failed} fallaron")
    return failed


def main():
    global OUTPUT_DIR
    if "--guardar-evidencia" in sys.argv[1:]:
        OUTPUT_DIR = EVIDENCE
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        failed = run_all()
    else:
        with tempfile.TemporaryDirectory(prefix="lab01-run-tests-") as temporary_dir:
            OUTPUT_DIR = Path(temporary_dir)
            failed = run_all()
    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()
