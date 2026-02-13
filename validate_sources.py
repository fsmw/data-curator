#!/usr/bin/env python3
"""
Valida qué fuentes de datos están operativas para búsqueda y descarga.
Ejecutar desde la raíz del proyecto: python validate_sources.py
"""
import sys
from pathlib import Path

# Asegurar imports desde src
sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

def main():
    from config import Config
    from ingestion import DataIngestionManager

    config = Config()
    manager = DataIngestionManager(config)
    results = {}

    # --- OWID ---
    try:
        df = manager.ingest(source="owid", slug="gdp-per-capita-worldbank")
        results["OWID"] = ("OK", len(df), None)
    except Exception as e:
        results["OWID"] = ("ERROR", 0, str(e))

    # --- ILOSTAT ---
    try:
        df = manager.ingest(source="ilostat", indicator="UNE_DEUC_SEX_AGE_NB")
        results["ILOSTAT"] = ("OK", len(df), None)
    except Exception as e:
        results["ILOSTAT"] = ("ERROR", 0, str(e))

    # --- OECD ---
    try:
        df = manager.ingest(source="oecd", dataset="REV", indicator="1100_1200_1300")
        results["OECD"] = ("OK", len(df), None)
    except Exception as e:
        results["OECD"] = ("ERROR", 0, str(e))

    # --- IMF ---
    try:
        df = manager.ingest(source="imf", database="WEO", indicator="NGDP_RPCH")
        results["IMF"] = ("OK", len(df), None)
    except Exception as e:
        results["IMF"] = ("ERROR", 0, str(e))

    # --- World Bank ---
    try:
        df = manager.ingest(source="worldbank", indicator="SI.POV.GINI")
        results["World Bank"] = ("OK", len(df), None)
    except Exception as e:
        results["World Bank"] = ("ERROR", 0, str(e))

    # --- ECLAC ---
    try:
        df = manager.ingest(source="eclac", table="INFORMALIDAD")
        results["ECLAC"] = ("OK", len(df), None)
    except Exception as e:
        results["ECLAC"] = ("ERROR", 0, str(e))

    # --- Dynamic search (OWID remote) ---
    try:
        from dynamic_search import DynamicSearcher
        ds = DynamicSearcher(config, cache_ttl_minutes=1)
        out = ds.search("gdp", include_remote=True, source_filter=None)
        total = len(out.get("local_results", [])) + len(out.get("remote_results", []))
        results["Búsqueda (OWID remoto)"] = ("OK", total, None)
    except Exception as e:
        results["Búsqueda (OWID remoto)"] = ("ERROR", 0, str(e))

    # Report: "operativa" solo si hay datos (count > 0) para fuentes de descarga
    download_sources = ["OWID", "ILOSTAT", "OECD", "IMF", "World Bank", "ECLAC"]
    print("\n" + "=" * 60)
    print("VALIDACIÓN DE FUENTES DE DATOS - MISES DATA CURATOR")
    print("=" * 60)
    for source, (status, count, err) in results.items():
        if source in download_sources:
            operativa = status == "OK" and count > 0
            label = "OPERATIVA" if operativa else "NO OPERATIVA"
            detail = f"(registros: {count})" if count else (err or "(sin datos)")
            print(f"  {source:25} {label:12} {detail}")
        else:
            print(f"  {source:25} {'OK' if status == 'OK' else 'ERROR':12} (resultados: {count})")
    print("=" * 60 + "\n")
    return 0

if __name__ == "__main__":
    sys.exit(main())
