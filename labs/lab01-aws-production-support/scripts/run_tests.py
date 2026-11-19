#!/usr/bin/env python3
"""LAB 01 - Pruebas automatizadas para analizar_logs.py."""
import json
import subprocess
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
SCRIPT = BASE / "scripts" / "analizar_logs.py"
TESTS = BASE / "data" / "test"
EVIDENCE = BASE / "evidence"
PY = "C:\\Users\\juan\\AppData\\Local\\Programs\\Python\\Python312\\python.exe"


def run(args):
    return subprocess.run([PY, str(SCRIPT)] + args, capture_output=True, text=True, cwd=str(BASE))


def test_normal():
    out = EVIDENCE / "normal.json"
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
    out = EVIDENCE / "multi_event.json"
    r = run(["-i", str(TESTS / "multi_event.log"), "-j", str(out)])
    assert r.returncode == 0, f"multi_event failed: {r.stderr}"
    data = json.loads(out.read_text())
    assert data["total_eventos_parseados"] == 9
    assert data["operaciones_unicas"] == 5
    assert data["conteo_por_estado"]["OK"] == 3
    assert data["conteo_por_estado"]["ERROR"] == 3
    assert data["conteo_por_estado"]["PENDIENTE"] == 3
    return True


def main():
    tests = [
        ("normal", test_normal),
        ("empty", test_empty),
        ("missing_file", test_missing_file),
        ("invalid_lines", test_invalid_lines),
        ("missing_ids", test_missing_ids),
        ("invalid_imports", test_invalid_imports),
        ("unknown_states", test_unknown_states),
        ("multi_event", test_multi_event),
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
    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()