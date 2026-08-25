#!/usr/bin/env python3
"""Build the localized clickable-map dataset from the current source of truth.

Source of truth (2026-08-20 architecture):
  - Regiones.csv (Latin), Regione.csv (Italian), Régions.csv (French),
    Regions.csv (English): per-zone sovereign / name / terrain / MP / town /
    production, one row per T/C/M/D zone id.
  - Adjacences.json: the single language-neutral adjacency graph (kind,
    parent_id, face, adjacencies) for the same 276 zone ids.

Output: clickable/province-map.json, with each zone's language-neutral
graph fields plus an "i18n" block keyed by la/it/fr/en. move_cost is a
single shared number per zone (already verified identical across all four
CSVs for all 276 ids); if a future edit ever desyncs the four files, this
script raises instead of silently picking one value.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

MAP_DIR = Path(__file__).resolve().parent
LANG_FILES = {
    "la": "Regiones.csv",
    "it": "Regione.csv",
    "fr": "Régions.csv",
    "en": "Regions.csv",
}


def load_region_csv(path: Path) -> dict[str, dict]:
    rows: dict[str, dict] = {}
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.reader(handle, delimiter=";")
        next(reader)  # header
        for row in reader:
            if not row or not row[0]:
                continue
            zid = row[0]
            sovereign, name, terrain, mp, city, production = (row + [""] * 6)[1:7]
            rows[zid] = {
                "sovereign": sovereign or None,
                "name": name or None,
                "terrain": terrain or None,
                "mp": mp or None,
                "city": city or None,
                "production": production or None,
            }
    return rows


def main() -> None:
    lang_rows = {lang: load_region_csv(MAP_DIR / fname) for lang, fname in LANG_FILES.items()}
    ids_per_lang = {lang: set(rows) for lang, rows in lang_rows.items()}
    common_ids = set.intersection(*ids_per_lang.values())
    all_ids = set.union(*ids_per_lang.values())
    if common_ids != all_ids:
        raise SystemExit(f"Region files disagree on zone ids: {all_ids - common_ids}")

    graph = json.loads((MAP_DIR / "Adjacences.json").read_text(encoding="utf-8"))
    graph_zones = {z["id"]: z for z in graph["zones"]}
    if set(graph_zones) != common_ids:
        raise SystemExit(
            "Adjacences.json zone ids do not match region file zone ids: "
            f"only-in-graph={set(graph_zones) - common_ids} "
            f"only-in-regions={common_ids - set(graph_zones)}"
        )

    out_zones = []
    for zid in sorted(common_ids):
        gz = graph_zones[zid]
        mp_values = {rows[zid]["mp"] for rows in lang_rows.values()}
        if len(mp_values) != 1:
            raise SystemExit(f"{zid}: movement cost disagrees across languages: {mp_values}")
        mp_raw = next(iter(mp_values))
        move_cost = int(mp_raw) if mp_raw is not None else None

        i18n = {}
        for lang, rows in lang_rows.items():
            r = rows[zid]
            i18n[lang] = {
                "sovereign": r["sovereign"],
                "name": r["name"],
                "terrain": r["terrain"],
                "city": r["city"],
                "production": r["production"],
            }

        out_zones.append(
            {
                "id": zid,
                "kind": gz["kind"],
                "parent_id": gz["parent_id"],
                "face": gz["face"],
                "move_cost": move_cost,
                "adjacencies": gz["adjacencies"],
                "i18n": i18n,
            }
        )

    output = {
        "version": "2026-08-20",
        "source": "Regiones.csv + Regione.csv + Régions.csv + Regions.csv + Adjacences.json",
        "languages": ["la", "it", "fr", "en"],
        "id_scheme": graph["id_scheme"],
        "movement": graph["movement"],
        "counts": graph["counts"],
        "zones": out_zones,
    }

    dest = MAP_DIR / "clickable" / "province-map.json"
    dest.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {dest} with {len(out_zones)} zones.")


if __name__ == "__main__":
    main()
