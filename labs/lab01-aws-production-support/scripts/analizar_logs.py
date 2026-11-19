#!/usr/bin/env python3
"""LAB 01 - Analisis local de logs de operaciones (Production Support)."""
import argparse
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

LINE_RE = re.compile(
    r"(?P<ts>\S+)\s+level=(?P<level>\w+)\s+id_operacion=(?P<id_operacion>\S+)\s+"
    r"cliente=(?P<cliente>\S+)\s+estado=(?P<estado>\S+)\s+importe=(?P<importe>[0-9.]+)\s+"
    r'causa="(?P<causa>[^"]*)"'
)
ESTADOS_VALIDOS = {"OK", "ERROR", "PENDIENTE"}


def parse_line(line):
    m = LINE_RE.search(line.strip())
    if not m:
        return None
    d = m.groupdict()
    try:
        d["importe"] = float(d["importe"])
    except ValueError:
        return None
    if d["estado"] not in ESTADOS_VALIDOS:
        return None
    return d


def analyze(path):
    events = []
    parse_errors = []
    with path.open("r", encoding="utf-8") as f:
        for lineno, raw in enumerate(f, start=1):
            if not raw.strip():
                continue
            ev = parse_line(raw)
            if ev:
                ev["linea"] = lineno
                events.append(ev)
            else:
                parse_errors.append({"linea": lineno, "contenido": raw.strip()})

    by_estado = Counter(e["estado"] for e in events)
    by_operacion = defaultdict(list)
    for e in events:
        by_operacion[e["id_operacion"]].append(e)

    error_ops = {}
    pendiente_ops = {}
    for op, evs in by_operacion.items():
        for e in evs:
            if e["estado"] == "ERROR":
                error_ops.setdefault(op, {"eventos": 0, "causas": [], "cliente": e["cliente"], "importe": e["importe"]})
                error_ops[op]["eventos"] += 1
                if e["causa"] not in error_ops[op]["causas"]:
                    error_ops[op]["causas"].append(e["causa"])
            if e["estado"] == "PENDIENTE":
                pendiente_ops.setdefault(op, {"eventos": 0, "causas": [], "cliente": e["cliente"], "importe": e["importe"]})
                pendiente_ops[op]["eventos"] += 1
                if e["causa"] not in pendiente_ops[op]["causas"]:
                    pendiente_ops[op]["causas"].append(e["causa"])

    importe_error = round(sum(e["importe"] for e in events if e["estado"] == "ERROR"), 2)
    importe_pendiente = round(sum(e["importe"] for e in events if e["estado"] == "PENDIENTE"), 2)

    resumen = {
        "archivo": str(path),
        "total_eventos_parseados": len(events),
        "lineas_no_parseadas": len(parse_errors),
        "conteo_por_estado": dict(by_estado),
        "operaciones_unicas": len(by_operacion),
        "operaciones_error": error_ops,
        "operaciones_pendiente": pendiente_ops,
        "importe_total_eventos_error": importe_error,
        "importe_total_eventos_pendiente": importe_pendiente,
        "alerta": {"hay_errores": len(error_ops) > 0, "hay_pendientes": len(pendiente_ops) > 0},
    }
    if parse_errors:
        resumen["detalle_no_parseadas"] = parse_errors
    return resumen


def print_summary(resumen):
    print("=== LAB 01: Resumen de analisis de logs ===")
    print(f"Archivo: {resumen['archivo']}")
    print(f"Eventos parseados: {resumen['total_eventos_parseados']}")
    print(f"Operaciones unicas: {resumen['operaciones_unicas']}")
    print(f"Lineas no parseadas: {resumen['lineas_no_parseadas']}")
    print("\nConteo por estado:")
    for estado, cnt in sorted(resumen["conteo_por_estado"].items()):
        print(f"  - {estado}: {cnt}")
    print("\nOperaciones en ERROR:")
    if resumen["operaciones_error"]:
        for op, info in sorted(resumen["operaciones_error"].items()):
            causas = "; ".join(info["causas"])
            print(f"  - {op} (cliente={info['cliente']}, importe={info['importe']}, eventos={info['eventos']}): {causas}")
    else:
        print("  (ninguna)")
    print("\nOperaciones en PENDIENTE:")
    if resumen["operaciones_pendiente"]:
        for op, info in sorted(resumen["operaciones_pendiente"].items()):
            causas = "; ".join(info["causas"])
            print(f"  - {op} (cliente={info['cliente']}, importe={info['importe']}, eventos={info['eventos']}): {causas}")
    else:
        print("  (ninguna)")
    print("\nImportes totales (eventos):")
    print(f"  - ERROR: {resumen['importe_total_eventos_error']}")
    print(f"  - PENDIENTE: {resumen['importe_total_eventos_pendiente']}")
    print(f"\nAlerta: hay_errores={resumen['alerta']['hay_errores']} hay_pendientes={resumen['alerta']['hay_pendientes']}")


def main():
    parser = argparse.ArgumentParser(description="Analiza logs de operaciones (LAB 01).")
    parser.add_argument("--input", "-i", required=True, help="Ruta al archivo de log")
    parser.add_argument("--json", "-j", help="Ruta de salida JSON (opcional)")
    args = parser.parse_args()
    path = Path(args.input)
    if not path.exists():
        raise SystemExit(f"ERROR: no existe el archivo de entrada: {path}")
    resumen = analyze(path)
    print_summary(resumen)
    if args.json:
        out = Path(args.json)
        out.parent.mkdir(parents=True, exist_ok=True)
        with out.open("w", encoding="utf-8") as f:
            json.dump(resumen, f, ensure_ascii=False, indent=2)
        print(f"\nJSON guardado en: {out}")


if __name__ == "__main__":
    main()