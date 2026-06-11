"""
ストレージフォルダ初期化スクリプト

データベースに登録されている全橋梁のフォルダを生成します。
  storage/bridges/{管理番号}_{橋名}/
      photos/   ← 写真データ（JPG/PNG）
      forms/    ← 調査様式・帳票（PDF/Excel/Word）

既存のフォルダは上書きせず安全にスキップします。
"""

import sqlite3
from pathlib import Path

DB_PATH      = Path(__file__).parent.parent / "data" / "bridges.db"
STORAGE_ROOT = Path(__file__).parent.parent / "storage"

PHOTO_TYPES = ["全景", "損傷", "補修後", "その他"]
DOC_TYPES   = ["点検調書", "損傷図", "補修設計書", "その他"]

README_PHOTOS = """\
# 写真データフォルダ

このフォルダに点検・補修時の写真を保存してください。

## 推奨ファイル名規則
  YYYYMMDD_種別_連番.jpg
  例: 20211015_全景_001.jpg
      20211015_損傷_002.jpg

## 対応フォーマット
  JPG / JPEG / PNG / HEIC
"""

README_FORMS = """\
# 調査様式・帳票フォルダ

このフォルダに点検調書・損傷図・補修設計書などを保存してください。

## 推奨ファイル名規則
  YYYYMMDD_種別.pdf
  例: 20211015_点検調書.pdf
      20211015_損傷図.xlsx

## 対応フォーマット
  PDF / Excel (.xlsx/.xls) / Word (.docx/.doc)
"""

README_BRIDGE = """\
# {bridge_code} {bridge_name}

| 項目       | 内容              |
|------------|-------------------|
| 管理番号   | {bridge_code}     |
| 橋名       | {bridge_name}     |
| 路線名     | {route_name}      |
| 架設年     | {built_year} 年   |
| 健全性ランク | {health_rank}   |

## フォルダ構成
```
{bridge_code}/
  photos/   写真データ（JPG/PNG）
  forms/    調査様式・帳票（PDF/Excel/Word）
```
"""


def init_storage(db_path: Path = DB_PATH, storage_root: Path = STORAGE_ROOT) -> None:
    if not db_path.exists():
        print(f"[ERROR] DBが見つかりません: {db_path}")
        return

    con = sqlite3.connect(db_path)
    bridges = con.execute(
        """SELECT b.bridge_code, b.bridge_name, r.route_name,
                  b.built_year, b.current_health_rank
           FROM bridges b
           LEFT JOIN routes r ON b.route_id = r.route_id
           WHERE b.is_active = 1
           ORDER BY b.bridge_code"""
    ).fetchall()
    con.close()

    storage_root.mkdir(parents=True, exist_ok=True)
    bridges_root = storage_root / "bridges"
    bridges_root.mkdir(exist_ok=True)

    created, skipped = 0, 0
    for code, name, route, year, rank in bridges:
        bridge_dir = bridges_root / code
        photos_dir = bridge_dir / "photos"
        forms_dir  = bridge_dir / "forms"

        existed = bridge_dir.exists()
        photos_dir.mkdir(parents=True, exist_ok=True)
        forms_dir.mkdir(parents=True, exist_ok=True)

        # README を初回のみ作成
        readme_path = bridge_dir / "README.md"
        if not readme_path.exists():
            readme_path.write_text(
                README_BRIDGE.format(
                    bridge_code=code, bridge_name=name,
                    route_name=route or "-", built_year=year or "-",
                    health_rank=rank or "-",
                ),
                encoding="utf-8",
            )
        (photos_dir / "README.md").write_text(README_PHOTOS, encoding="utf-8") if not (photos_dir / "README.md").exists() else None
        (forms_dir  / "README.md").write_text(README_FORMS,  encoding="utf-8") if not (forms_dir  / "README.md").exists() else None

        if existed:
            skipped += 1
        else:
            created += 1
            print(f"  [作成] {bridge_dir.relative_to(storage_root.parent)}/")

    print(f"\n[完了] 作成:{created}橋 / スキップ:{skipped}橋")
    print(f"ストレージルート: {storage_root.resolve()}")

    _print_tree(storage_root)


def _print_tree(root: Path, depth: int = 2, prefix: str = "") -> None:
    print(f"\n--- フォルダ構成 (深さ {depth}) ---")
    _tree(root, depth, "")


def _tree(path: Path, max_depth: int, indent: str) -> None:
    if max_depth < 0:
        return
    entries = sorted(path.iterdir()) if path.is_dir() else []
    for i, entry in enumerate(entries):
        connector = "└── " if i == len(entries) - 1 else "├── "
        print(indent + connector + entry.name + ("/" if entry.is_dir() else ""))
        if entry.is_dir():
            extension = "    " if i == len(entries) - 1 else "│   "
            _tree(entry, max_depth - 1, indent + extension)


if __name__ == "__main__":
    init_storage()
