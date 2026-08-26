#!/usr/bin/env python3
"""
csv_to_adjacences_json.py

Converts map/adjacencies.csv into map/adjacencies.json, the language-neutral
adjacency graph consumed by build_i18n_province_map.py.

CSV format (semicolon-delimited, UTF-8 with BOM, one header row "Index"):
    <zone_id>;<neighbor_id>;<extra_cost>;<neighbor_id>;<extra_cost>;...
  - <zone_id> is one of: Tnnn (land), Cnnn / Cnnns (coastal, "s" suffix =
    south face), Mnnn (sea / high seas), Dnnn (great desert).
  - Each row lists ALL of that zone's neighbors explicitly (the table is
    symmetric/redundant by design: if A lists B, B's row also lists A).
  - <extra_cost> is blank for 0, or an integer (1 = river, 3 = strait).
    Trailing columns are blank padding and are ignored.

Derivation rules (must match the existing hand-built adjacencies.json):
  - kind:      T -> "land", C -> "coastal", M -> "sea", D -> "great_desert"
  - parent_id: coastal Cnnn[s] -> Tnnn (strip "C"/"s", prefix "T"); else null
  - face:      "south" if the id ends in "s", else null
  - feature:   from extra_cost via EXTRA_COST_FEATURES (0->None, 1->"river",
               3->"strait"). Unknown non-zero costs abort the build so new
               terrain features get an explicit mapping decision instead of
               silently passing through.
  - edge:      T<->T = "land", T<->D or D<->T = "desert", C<->C = "cabotage",
               anything touching M = "high_seas". Any other pairing
               (e.g. C<->T, the same location's land/sea layers, or D<->C)
               aborts the build since it should not exist per the "overlap
               is not an adjacency" rule.

Usage:
    python3 csv_to_adjacences_json.py [--csv adjacencies.csv] [--out adjacencies.json] [--check]

    --check   Build in-memory and diff against the existing Adjacences.json
              instead of writing (used to validate this script against the
              current source of truth).
"""
import argparse
import csv
import json
import sys
from pathlib import Path

KIND_BY_PREFIX = {
    "T": "land",
    "C": "coastal",
    "M": "sea",
    "D": "great_desert",
}

EXTRA_COST_FEATURES = {
    0: None,
    1: "river",
    3: "strait",
}

ID_SCHEME = {
    "T": "land territory",
    "C": "coastal area (Cnnn belongs to Tnnn; suffix s = south face)",
    "M": "sea / high seas",
    "D": "great desert",
}

MOVEMENT = {
    "edge_type": "implied by endpoints: T\u2013T land, C\u2013C cabotage 1, C\u2013M high seas, T\u2013D desert",
    "extra_cost": {
        "0": "no extra",
        "1": "river",
        "3": "strait (encoded in table; rulebook still +2 until confirmed)",
    },
    "overlap": "same number is one place, two layers: T land units, C ships and ports. Not an adjacency.",
    "high_seas_mp": {
        "smaller": 3,
        "bigger": 4,
    },
}


def kind_of(zone_id: str) -> str:
    prefix = zone_id[0]
    if prefix not in KIND_BY_PREFIX:
        raise SystemExit(f"Unknown zone id prefix in '{zone_id}' (expected T/C/M/D)")
    return KIND_BY_PREFIX[prefix]


def parent_and_face(zone_id: str, kind: str):
    if kind != "coastal":
        return None, None
    face = "south" if zone_id.endswith("s") else None
    base = zone_id[:-1] if face else zone_id
    parent_id = "T" + base[1:]
    return parent_id, face


def edge_type(a_kind: str, b_kind: str) -> str:
    kinds = {a_kind, b_kind}
    if kinds == {"land"}:
        return "land"
    if kinds == {"land", "great_desert"}:
        return "desert"
    if kinds == {"coastal"}:
        return "cabotage"
    if "sea" in kinds and kinds <= {"sea", "coastal"}:
        return "high_seas"
    raise SystemExit(
        f"No edge-type rule for kind pair {a_kind!r}/{b_kind!r} "
        f"(check for a same-location land/sea overlap or an unexpected pairing)"
    )


def parse_row(row):
    zone_id = row[0].strip()
    if not zone_id:
        return None
    rest = row[1:]
    neighbors = []
    for i in range(0, len(rest), 2):
        nb_id = rest[i].strip() if i < len(rest) else ""
        if not nb_id:
            continue
        cost_raw = rest[i + 1].strip() if i + 1 < len(rest) else ""
        cost = int(cost_raw) if cost_raw else 0
        neighbors.append((nb_id, cost))
    return zone_id, neighbors


def build_graph(csv_path: Path) -> dict:
    with csv_path.open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.reader(f, delimiter=";"))
    if not rows:
        raise SystemExit(f"{csv_path} is empty")
    data_rows = rows[1:]  # skip "Index" header

    parsed = []
    for row in data_rows:
        result = parse_row(row)
        if result is None:
            continue
        parsed.append(result)

    zone_ids = {zid for zid, _ in parsed}

    zones = []
    kind_counts = {"land": 0, "coastal": 0, "coastal_south": 0, "sea": 0, "great_desert": 0}
    for zone_id, neighbors in parsed:
        kind = kind_of(zone_id)
        parent_id, face = parent_and_face(zone_id, kind)

        kind_counts[kind] += 1
        if face == "south":
            kind_counts["coastal_south"] += 1

        adjacencies = []
        for nb_id, cost in neighbors:
            if nb_id not in zone_ids:
                raise SystemExit(f"{zone_id} references unknown neighbor {nb_id}")
            if cost not in EXTRA_COST_FEATURES:
                raise SystemExit(
                    f"{zone_id}->{nb_id}: extra_cost {cost} has no feature mapping "
                    f"in EXTRA_COST_FEATURES; add one before building"
                )
            nb_kind = kind_of(nb_id)
            adjacencies.append({
                "id": nb_id,
                "extra_cost": cost,
                "feature": EXTRA_COST_FEATURES[cost],
                "edge": edge_type(kind, nb_kind),
            })

        zones.append({
            "id": zone_id,
            "kind": kind,
            "parent_id": parent_id,
            "face": face,
            "adjacencies": adjacencies,
        })

    # Sort for stable, deterministic output (Tnnn, then Cnnn[s], Mnnn, Dnnn).
    zones.sort(key=lambda z: z["id"])

    graph = {
        "source": "adjacencies.csv",
        "id_scheme": ID_SCHEME,
        "movement": MOVEMENT,
        "counts": {
            "zones": len(zones),
            "land": kind_counts["land"],
            "coastal": kind_counts["coastal"],
            "coastal_south": kind_counts["coastal_south"],
            "seas": kind_counts["sea"],
            "great_deserts": kind_counts["great_desert"],
        },
        "zones": zones,
    }
    return graph


def check_symmetry(graph: dict):
    """Warn (non-fatal) about one-way or cost-mismatched adjacency pairs."""
    by_id = {z["id"]: z for z in graph["zones"]}
    problems = []
    for zone in graph["zones"]:
        for adj in zone["adjacencies"]:
            back = by_id.get(adj["id"])
            if back is None:
                continue
            back_adj = next((a for a in back["adjacencies"] if a["id"] == zone["id"]), None)
            if back_adj is None:
                problems.append(f"{zone['id']} -> {adj['id']} has no reverse entry")
            elif back_adj["extra_cost"] != adj["extra_cost"]:
                problems.append(
                    f"{zone['id']} <-> {adj['id']} cost mismatch: "
                    f"{adj['extra_cost']} vs {back_adj['extra_cost']}"
                )
    return problems


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--csv", default="adjacencies.csv", type=Path)
    ap.add_argument("--out", default="adjacencies.json", type=Path)
    ap.add_argument("--check", action="store_true", help="validate against existing --out instead of writing")
    args = ap.parse_args()

    graph = build_graph(args.csv)

    problems = check_symmetry(graph)
    for p in problems:
        print(f"WARNING: {p}", file=sys.stderr)

    if args.check:
        if not args.out.exists():
            raise SystemExit(f"{args.out} does not exist to check against")
        existing = json.loads(args.out.read_text(encoding="utf-8"))
        existing_sorted = dict(existing)
        existing_sorted["zones"] = sorted(existing["zones"], key=lambda z: z["id"])
        if graph == existing_sorted:
            print(f"OK: rebuilt graph from {args.csv} matches {args.out} exactly.")
        else:
            print(f"DIFF: rebuilt graph from {args.csv} does NOT match {args.out}.")
            sys.exit(1)
        return

    args.out.write_text(json.dumps(graph, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {args.out} ({len(graph['zones'])} zones).")
    if problems:
        print(f"{len(problems)} symmetry warning(s) above \u2014 review before treating the output as final.")


if __name__ == "__main__":
    main()
