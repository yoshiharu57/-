"""
橋梁データベース ダミーデータ生成スクリプト
国土交通省「橋梁定期点検要領」準拠の10件のサンプルデータを生成します。
"""

import sqlite3
import random
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "data" / "bridges.db"
SCHEMA_PATH = Path(__file__).parent.parent / "schema.sql"


ROUTES = [
    ("町道1号線", "町道"),
    ("町道2号線", "町道"),
    ("県道45号線", "県道"),
    ("農道A線",   "農道"),
    ("町道3号線", "町道"),
]

BRIDGES = [
    # (管理番号, 橋名, カナ, 路線idx, 字名, 緯度, 経度, 架設年, 橋長, 幅員, 上部工, 下部工, 径間, 材料, ランク)
    ("T-001", "桜橋",     "サクラバシ",   0, "大字桜町",   35.1234, 136.9012, 1965, 18.5, 5.5, "RC中空床版橋",   "逆T式橋台",     1, "RC",  "II"),
    ("T-002", "松川橋",   "マツカワバシ", 0, "大字松川",   35.1289, 136.9078, 1978, 32.0, 6.0, "PC単純T桁橋",    "重力式橋台",     1, "PC",  "I"),
    ("T-003", "新橋",     "シンバシ",     1, "大字新田",   35.1301, 136.8950, 1992, 24.5, 7.5, "鋼単純桁橋",     "逆T式橋台",     1, "鋼",  "II"),
    ("T-004", "梅ノ木橋", "ウメノキバシ", 2, "大字梅ノ木", 35.1198, 136.9145, 1958, 12.0, 4.0, "RC単純桁橋",     "重力式橋台",     1, "RC",  "III"),
    ("T-005", "西川橋",   "ニシカワバシ", 1, "大字西川",   35.1356, 136.8880, 1985, 45.0, 8.0, "PC連続桁橋",     "張出し式橋脚",  3, "PC",  "I"),
    ("T-006", "田中橋",   "タナカバシ",   3, "大字田中",   35.1267, 136.9234, 1971, 15.0, 4.5, "RC単純スラブ橋", "逆T式橋台",     1, "RC",  "III"),
    ("T-007", "大正橋",   "タイショウバシ",2,"大字上町",   35.1412, 136.9001, 1923, 28.0, 5.0, "石造りアーチ橋", "一体式橋台",    1, "石",  "II"),
    ("T-008", "若葉橋",   "ワカババシ",   4, "大字若葉",   35.1145, 136.8923, 2005, 38.5, 9.5, "PC単純T桁橋",    "逆T式橋台",     2, "PC",  "I"),
    ("T-009", "谷口橋",   "タニグチバシ", 3, "大字谷口",   35.1389, 136.9167, 1968, 10.0, 3.5, "RC中空床版橋",   "重力式橋台",     1, "RC",  "IV"),
    ("T-010", "緑橋",     "ミドリバシ",   4, "大字緑ケ丘", 35.1234, 136.8834, 1999, 52.0, 10.0,"PC連続箱桁橋",   "壁式橋脚",      4, "PC",  "I"),
]

INSPECTIONS = [
    # bridge_idx, date, type, inspector, org, rank, countermeasure, overall_judgment
    (0, "2021-10-15", "定期", "田中 一郎", "○○建設コンサルタント", "II", "C",
     "主桁にひびわれ・漏水が確認された。予防保全措置が必要。"),
    (0, "2016-06-20", "定期", "鈴木 次郎", "○○建設コンサルタント", "II", "B",
     "軽微なひびわれを確認。経過観察とする。"),
    (1, "2023-05-10", "定期", "田中 一郎", "○○建設コンサルタント", "I",  "A",
     "損傷は認められず、健全な状態。"),
    (2, "2022-09-01", "定期", "佐藤 三郎", "△△技術事務所",       "II", "B",
     "塗装劣化が進行中。次回点検時に要確認。"),
    (3, "2020-11-25", "定期", "田中 一郎", "○○建設コンサルタント", "III","D",
     "床版の断面欠損・鉄筋露出あり。早期補修が必要。"),
    (3, "2015-08-10", "定期", "鈴木 次郎", "○○建設コンサルタント", "II", "C",
     "床版にひびわれ・剥離を確認。"),
    (4, "2023-07-20", "定期", "佐藤 三郎", "△△技術事務所",       "I",  "A",
     "全体的に良好な状態を維持している。"),
    (5, "2019-04-15", "定期", "田中 一郎", "○○建設コンサルタント", "III","D",
     "支承の機能障害、桁端部の腐食を確認。早期措置が必要。"),
    (6, "2022-03-08", "定期", "高橋 四郎", "□□エンジニアリング",  "II", "B",
     "石積み部に軽微なひびわれあり。歴史的構造物として慎重な対応が必要。"),
    (7, "2023-10-30", "定期", "佐藤 三郎", "△△技術事務所",       "I",  "A",
     "竣工後18年経過も損傷なし。良好な状態。"),
    (8, "2018-06-01", "定期", "田中 一郎", "○○建設コンサルタント", "IV", "E",
     "床版貫通ひびわれ・鉄筋破断を確認。緊急措置が必要。通行規制を推奨。"),
    (9, "2023-08-22", "定期", "高橋 四郎", "□□エンジニアリング",  "I",  "A",
     "新設橋梁につき健全。"),
]

REPAIRS = [
    (3, 0, "2021-03-15", "床版補修", "断面修復材による床版欠損補修、鉄筋防錆処理", "○○建設㈱", 1850, "2026-03-14"),
    (5, 5, "2020-02-10", "支承取替", "固定支承・可動支承の全面取替", "△△橋梁㈱",   3200, "2025-02-09"),
    (8, 10,"2019-05-20", "床版打替", "RC床版の全面打替工事（応急→本格補修）", "○○建設㈱", 8700, "2029-05-19"),
]


def create_database():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB_PATH)
    con.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
    con.commit()
    return con


def insert_dummy_data(con: sqlite3.Connection):
    cur = con.cursor()

    # 路線
    for name, rtype in ROUTES:
        cur.execute(
            "INSERT OR IGNORE INTO routes(route_name, route_type) VALUES (?,?)",
            (name, rtype),
        )
    con.commit()

    # 橋梁
    bridge_ids = []
    for b in BRIDGES:
        (code, name, kana, route_idx, loc, lat, lon,
         year, length, width, super_t, sub_t, spans, mat, rank) = b
        cur.execute(
            """INSERT OR IGNORE INTO bridges
               (bridge_code, bridge_name, bridge_name_kana, route_id, manager_name,
                location_name, latitude, longitude, built_year,
                bridge_length, bridge_width, superstructure_type, substructure_type,
                span_count, material, current_health_rank)
               VALUES (?,?,?,
                       (SELECT route_id FROM routes WHERE route_name=?),
                       '○○町役場 建設課',
                       ?,?,?,?,?,?,?,?,?,?,?)""",
            (code, name, kana, ROUTES[route_idx][0],
             loc, lat, lon, year, length, width, super_t, sub_t, spans, mat, rank),
        )
        bridge_ids.append(cur.lastrowid or cur.execute(
            "SELECT bridge_id FROM bridges WHERE bridge_code=?", (code,)).fetchone()[0])
    con.commit()

    # 点検履歴
    inspection_ids = []
    for insp in INSPECTIONS:
        (bidx, date, itype, inspector, org, rank, cmeasure, judgment) = insp
        bid = bridge_ids[bidx]
        # 損傷テキストは健全性ランクに応じて設定
        dmg_super = {
            "I": "異常なし",
            "II": "軽微なひびわれ・剥離が一部に見られる",
            "III": "断面欠損・鉄筋露出あり",
            "IV": "貫通ひびわれ・鉄筋破断確認",
        }.get(rank, "")
        next_year = {
            "I": 2029, "II": 2026, "III": 2024, "IV": 2019
        }.get(rank, 2025)
        est_cost = {
            "I": 0, "II": random.randint(100, 500),
            "III": random.randint(500, 3000), "IV": random.randint(3000, 10000)
        }.get(rank, 0)
        cur.execute(
            """INSERT INTO inspections
               (bridge_id, inspection_date, inspection_type, inspector_name, inspector_org,
                health_rank, overall_judgment, damage_superstructure,
                countermeasure_type, next_inspection_year, estimated_cost)
               VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            (bid, date, itype, inspector, org, rank, judgment,
             dmg_super, cmeasure, next_year, est_cost),
        )
        inspection_ids.append(cur.lastrowid)
    con.commit()

    # 補修履歴
    for rep in REPAIRS:
        bidx, iidx, date, rtype, desc, contractor, cost, warranty = rep
        cur.execute(
            """INSERT INTO repairs
               (bridge_id, inspection_id, repair_date, repair_type,
                description, contractor_name, cost, warranty_until)
               VALUES (?,?,?,?,?,?,?,?)""",
            (bridge_ids[bidx], inspection_ids[iidx],
             date, rtype, desc, contractor, cost, warranty),
        )
    con.commit()

    print(f"[OK] ダミーデータを挿入しました → {DB_PATH}")
    print(f"     橋梁: {len(BRIDGES)}件 / 点検: {len(INSPECTIONS)}件 / 補修: {len(REPAIRS)}件")


def show_summary(con: sqlite3.Connection):
    print("\n--- 健全性ランク別集計 ---")
    for row in con.execute(
        "SELECT current_health_rank, COUNT(*) FROM bridges GROUP BY current_health_rank ORDER BY current_health_rank"
    ):
        print(f"  ランク {row[0]}: {row[1]}橋")

    print("\n--- 橋梁一覧（最新点検情報付き）---")
    for row in con.execute(
        "SELECT bridge_code, bridge_name, current_health_rank, last_inspection_date FROM v_bridges_latest ORDER BY bridge_code"
    ):
        print(f"  {row[0]}  {row[1]:12s}  ランク:{row[2]}  最終点検:{row[3]}")


if __name__ == "__main__":
    con = create_database()
    insert_dummy_data(con)
    show_summary(con)
    con.close()
