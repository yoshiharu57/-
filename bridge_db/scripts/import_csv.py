"""
橋梁データ CSVインポートスクリプト
既存のExcel/CSVデータを橋梁データベースに一括登録します。

使い方:
    python import_csv.py --csv bridges.csv [--db ../data/bridges.db]

CSVフォーマット（1行目はヘッダ）:
    bridge_code, bridge_name, bridge_name_kana, route_name, route_type,
    location_name, latitude, longitude, built_year, bridge_length,
    bridge_width, superstructure_type, substructure_type, span_count,
    material, current_health_rank
"""

import argparse
import csv
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "data" / "bridges.db"

REQUIRED_COLS = {
    "bridge_code", "bridge_name", "route_name", "built_year",
    "bridge_length", "current_health_rank",
}

FLOAT_COLS  = {"latitude", "longitude", "bridge_length", "bridge_width"}
INT_COLS    = {"built_year", "span_count"}
VALID_RANKS = {"I", "II", "III", "IV"}


def import_csv(csv_path: Path, db_path: Path) -> None:
    if not csv_path.exists():
        raise FileNotFoundError(f"CSVファイルが見つかりません: {csv_path}")

    con = sqlite3.connect(db_path)
    cur = con.cursor()

    ok, skipped, errors = 0, 0, 0

    with open(csv_path, encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        headers = set(reader.fieldnames or [])
        missing = REQUIRED_COLS - headers
        if missing:
            raise ValueError(f"必須列が不足しています: {missing}")

        for lineno, row in enumerate(reader, start=2):
            try:
                row = {k: (v.strip() if v else None) for k, v in row.items()}

                # 型変換
                for col in FLOAT_COLS:
                    if row.get(col):
                        row[col] = float(row[col])
                for col in INT_COLS:
                    if row.get(col):
                        row[col] = int(row[col])

                rank = (row.get("current_health_rank") or "I").upper()
                if rank not in VALID_RANKS:
                    raise ValueError(f"不正な健全性ランク: {rank}")
                row["current_health_rank"] = rank

                # 路線マスタ登録（未登録の場合）
                route_name = row.get("route_name", "不明")
                route_type = row.get("route_type", "町道")
                cur.execute(
                    "INSERT OR IGNORE INTO routes(route_name, route_type) VALUES (?,?)",
                    (route_name, route_type),
                )
                route_id = cur.execute(
                    "SELECT route_id FROM routes WHERE route_name=?", (route_name,)
                ).fetchone()[0]

                # 橋梁登録（bridge_code が重複する場合は UPDATE）
                cur.execute(
                    """INSERT INTO bridges
                       (bridge_code, bridge_name, bridge_name_kana, route_id, manager_name,
                        location_name, latitude, longitude, built_year,
                        bridge_length, bridge_width, superstructure_type, substructure_type,
                        span_count, material, current_health_rank)
                       VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                       ON CONFLICT(bridge_code) DO UPDATE SET
                           bridge_name         = excluded.bridge_name,
                           bridge_name_kana    = excluded.bridge_name_kana,
                           route_id            = excluded.route_id,
                           location_name       = excluded.location_name,
                           latitude            = excluded.latitude,
                           longitude           = excluded.longitude,
                           built_year          = excluded.built_year,
                           bridge_length       = excluded.bridge_length,
                           bridge_width        = excluded.bridge_width,
                           superstructure_type = excluded.superstructure_type,
                           substructure_type   = excluded.substructure_type,
                           span_count          = excluded.span_count,
                           material            = excluded.material,
                           current_health_rank = excluded.current_health_rank,
                           updated_at          = datetime('now', 'localtime')
                    """,
                    (
                        row.get("bridge_code"),
                        row.get("bridge_name"),
                        row.get("bridge_name_kana"),
                        route_id,
                        row.get("manager_name", "○○町役場 建設課"),
                        row.get("location_name"),
                        row.get("latitude"),
                        row.get("longitude"),
                        row.get("built_year"),
                        row.get("bridge_length"),
                        row.get("bridge_width"),
                        row.get("superstructure_type"),
                        row.get("substructure_type"),
                        row.get("span_count", 1),
                        row.get("material"),
                        rank,
                    ),
                )
                ok += 1
            except Exception as e:
                print(f"[SKIP] 行{lineno}: {e} / データ: {row.get('bridge_code','?')}")
                errors += 1

    con.commit()
    con.close()
    print(f"\n[完了] 登録:{ok}件 / エラー:{errors}件 / スキップ:{skipped}件")


def main():
    parser = argparse.ArgumentParser(description="橋梁CSVインポート")
    parser.add_argument("--csv", required=True, help="入力CSVファイルパス")
    parser.add_argument("--db",  default=str(DB_PATH), help="データベースパス")
    args = parser.parse_args()

    import_csv(Path(args.csv), Path(args.db))


if __name__ == "__main__":
    main()
