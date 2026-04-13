import json
import re
import sys
from pathlib import Path

import pandas as pd

ID_RE = re.compile(r'^F\d{3}$')


def clean_str(value):
    if pd.isna(value):
        return None
    s = str(value).replace('\xa0', ' ').strip()
    return s if s else None


def parse_bool_oui_non(value):
    s = clean_str(value)
    return s is not None and s.lower() == 'oui'


def parse_int(value, default=None):
    if pd.isna(value):
        return default
    s = clean_str(value)
    if s is None:
        return default
    try:
        return int(float(s))
    except ValueError:
        return default


def looks_like_id(value):
    s = clean_str(value)
    return bool(s and ID_RE.match(s))


def normalize_neighbor_cost(value):
    n = parse_int(value, default=0)
    return n if n in (0, 1, 2) else 0


def detect_neighbor_start(columns):
    normalized = [str(c).replace('\n', ' ').strip().lower() for c in columns]
    for i, c in enumerate(normalized):
        if 'voisin' in c:
            return i
    return 8


def build_neighbors(row_values, start_idx):
    neighbors = []
    i = start_idx
    while i < len(row_values):
        cell = row_values[i]
        if looks_like_id(cell):
            neighbor_id = clean_str(cell)
            extra_cost = 0
            if i + 1 < len(row_values) and not looks_like_id(row_values[i + 1]):
                extra_cost = normalize_neighbor_cost(row_values[i + 1])
                i += 1
            neighbors.append({
                'id': neighbor_id,
                'extra_cost': extra_cost,
            })
        i += 1
    return neighbors


def row_to_province(row, start_idx):
    values = list(row)
    province_id = clean_str(values[0])
    if not looks_like_id(province_id):
        return None

    sovereign = clean_str(values[1])
    name_fr = clean_str(values[2])
    terrain = clean_str(values[3])
    move_cost = parse_int(values[4])
    coastal = parse_bool_oui_non(values[5])
    city = clean_str(values[6])
    production = clean_str(values[7])
    neighbors = build_neighbors(values, start_idx)

    return {
        'id': province_id,
        'sovereign_fr': sovereign,
        'name_fr': name_fr,
        'terrain': terrain,
        'move_cost': move_cost,
        'coastal': coastal,
        'city': city,
        'production': production,
        'neighbors': neighbors,
    }


def convert_excel_to_json(input_path, output_path, sheet_name=0):
    df = pd.read_excel(input_path, sheet_name=sheet_name, dtype=object)
    df = df.dropna(how='all')
    start_idx = detect_neighbor_start(df.columns)

    provinces = []
    seen = set()
    for row in df.itertuples(index=False, name=None):
        p = row_to_province(row, start_idx)
        if p is None:
            continue
        if p['id'] in seen:
            raise ValueError(f"Duplicate province id: {p['id']}")
        seen.add(p['id'])
        provinces.append(p)

    provinces.sort(key=lambda x: x['id'])

    payload = {'provinces': provinces}
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def main():
    if len(sys.argv) < 2:
        print('Usage: python xl2json.py <input.xlsx> [output.json] [sheet_name]')
        sys.exit(1)

    input_path = Path(sys.argv[1]).expanduser()
    if not input_path.exists():
        print(f'Input file not found: {input_path}')
        sys.exit(1)

    output_path = Path(sys.argv[2]).expanduser() if len(sys.argv) >= 3 else input_path.with_name('provinces.json')
    sheet_name = sys.argv[3] if len(sys.argv) >= 4 else 0

    convert_excel_to_json(input_path, output_path, sheet_name)
    print(f'Written {output_path}')


if __name__ == '__main__':
    main()

