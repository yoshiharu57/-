# 橋梁管理システム

町役場向け橋梁台帳・点検管理システム  
国土交通省「橋梁定期点検要領」準拠 | Python + SQLite + Streamlit

---

## 機能一覧

| 画面 | 機能 |
|---|---|
| 📊 ダッシュボード | 健全性ランク集計・緊急橋梁アラート・直近点検記録 |
| 🗺️ 地図・一覧 | Folium地図（ランク別色分け）・条件検索・Googleマップ連携・CSV出力 |
| 🔍 橋梁詳細 | 基本情報・点検履歴・補修履歴・写真/帳票ファイル管理 |
| 📋 点検記録入力 | 健全性ランク・損傷状況・措置区分の入力・登録 |
| 🏗️ 橋梁管理 | 橋梁の新規追加・情報変更・アーカイブ・完全削除 |

---

## セットアップ手順（Windows）

### 1. Python のインストール（初回のみ）

1. https://www.python.org/downloads/ を開く
2. 「Download Python 3.x.x」をクリック
3. **インストール画面で「Add Python to PATH」に必ずチェック**を入れてインストール

### 2. このフォルダを PC に保存する

GitHubからダウンロードするか、USB等でコピーしてください。  
例: `C:\Users\yourname\Documents\bridge_db\`

### 3. セットアップの実行（初回のみ）

`bridge_db` フォルダの中にある **`setup.bat`** をダブルクリックしてください。

- 必要なライブラリが自動でインストールされます
- データベース（`data/bridges.db`）が作成されます
- 橋梁ごとのフォルダ（`storage/`）が作成されます

### 4. システムの起動

**`start.bat`** をダブルクリックするとブラウザが自動で開きます。

```
http://localhost:8501
```

---

## 既存データの移行（ExcelやCSVから）

### CSVインポート

```bash
python scripts\import_csv.py --csv 既存データ.csv --db data\bridges.db
```

**CSVの列名（1行目）:**

```
bridge_code, bridge_name, bridge_name_kana, route_name, route_type,
location_name, latitude, longitude, built_year, bridge_length,
bridge_width, superstructure_type, substructure_type, span_count,
material, current_health_rank
```

サンプルは `sample_import.csv` を参照してください。

---

## ファイル構成

```
bridge_db/
├── app.py                  ← Streamlit アプリ本体
├── schema.sql              ← データベース定義
├── requirements.txt        ← 依存ライブラリ
├── setup.bat               ← 初回セットアップ（Windows）
├── start.bat               ← 起動スクリプト（Windows）
├── sample_import.csv       ← CSVインポートのサンプル
├── data/
│   └── bridges.db          ← SQLiteデータベース（自動生成）
├── scripts/
│   ├── generate_dummy_data.py  ← サンプルデータ生成
│   ├── import_csv.py           ← CSV一括インポート
│   └── init_storage.py         ← ストレージフォルダ初期化
└── storage/
    └── bridges/
        ├── T-001/
        │   ├── photos/     ← 写真データ（JPG/PNG）
        │   └── forms/      ← 調査様式・帳票（PDF/Excel）
        ├── T-002/
        ...
```

---

## データのバックアップ

定期的に以下の2箇所をコピーして保存してください。

| バックアップ対象 | パス |
|---|---|
| データベース | `data/bridges.db` |
| 写真・帳票 | `storage/` フォルダ全体 |

---

## 健全性ランクについて

国土交通省「橋梁定期点検要領」に基づく4段階評価：

| ランク | 状態 | 対応 |
|---|---|---|
| I | 健全 | 措置不要 |
| II | 予防保全段階 | 監視・予防保全措置 |
| III | 早期措置段階 | 早期補修が必要 |
| IV | 緊急措置段階 | 緊急補修・通行規制を検討 |

---

## 動作環境

- **OS**: Windows 10 / 11（Mac/Linux でも動作可）
- **Python**: 3.10 以上
- **ブラウザ**: Chrome / Edge / Firefox
- **インターネット**: 地図タイル・Googleマップリンクに使用（オフラインでも基本機能は動作）
