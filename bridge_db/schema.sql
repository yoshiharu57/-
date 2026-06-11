-- 橋梁データベース スキーマ定義
-- 国土交通省「橋梁定期点検要領」準拠
-- SQLite 3.x

PRAGMA foreign_keys = ON;
PRAGMA journal_mode = WAL;

-- =========================================================
-- 1. 路線マスタ
-- =========================================================
CREATE TABLE IF NOT EXISTS routes (
    route_id    INTEGER PRIMARY KEY AUTOINCREMENT,
    route_name  TEXT NOT NULL UNIQUE,   -- 路線名（例: 町道1号線）
    route_type  TEXT NOT NULL           -- 国道/県道/町道/農道
);

-- =========================================================
-- 2. 橋梁基本情報
-- =========================================================
CREATE TABLE IF NOT EXISTS bridges (
    bridge_id           INTEGER PRIMARY KEY AUTOINCREMENT,
    bridge_code         TEXT NOT NULL UNIQUE,   -- 橋梁管理番号（例: T-001）
    bridge_name         TEXT NOT NULL,          -- 橋名（漢字）
    bridge_name_kana    TEXT,                   -- 橋名（カナ）
    route_id            INTEGER REFERENCES routes(route_id),
    manager_name        TEXT NOT NULL,          -- 管理者名

    -- 位置情報
    location_name       TEXT,                   -- 所在地（字名）
    latitude            REAL,                   -- 緯度（WGS84）
    longitude           REAL,                   -- 経度（WGS84）

    -- 仕様
    built_year          INTEGER,                -- 架設年（西暦）
    bridge_length       REAL,                   -- 橋長（m）
    bridge_width        REAL,                   -- 幅員（m）
    superstructure_type TEXT,                   -- 上部工形式（例: RC床版橋）
    substructure_type   TEXT,                   -- 下部工形式（例: 逆T式橋台）
    span_count          INTEGER DEFAULT 1,      -- 径間数
    material            TEXT,                   -- 主要材料（RC/PC/鋼/木）

    -- 管理状態
    current_health_rank TEXT DEFAULT 'I',       -- 現況健全性ランク（I/II/III/IV）
    is_active           INTEGER DEFAULT 1,      -- 1=現役, 0=廃橋

    created_at          TEXT DEFAULT (datetime('now', 'localtime')),
    updated_at          TEXT DEFAULT (datetime('now', 'localtime'))
);

CREATE INDEX IF NOT EXISTS idx_bridges_route    ON bridges(route_id);
CREATE INDEX IF NOT EXISTS idx_bridges_health   ON bridges(current_health_rank);
CREATE INDEX IF NOT EXISTS idx_bridges_location ON bridges(latitude, longitude);

-- =========================================================
-- 3. 点検履歴
-- =========================================================
CREATE TABLE IF NOT EXISTS inspections (
    inspection_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    bridge_id           INTEGER NOT NULL REFERENCES bridges(bridge_id) ON DELETE CASCADE,

    -- 点検情報
    inspection_date     TEXT NOT NULL,          -- 点検年月日（YYYY-MM-DD）
    inspection_type     TEXT NOT NULL,          -- 点検種別（定期/緊急/初回）
    inspector_name      TEXT,                   -- 点検者氏名
    inspector_org       TEXT,                   -- 点検機関名

    -- 判定
    health_rank         TEXT NOT NULL,          -- 健全性ランク（I/II/III/IV）
    -- I:健全  II:予防保全段階  III:早期措置段階  IV:緊急措置段階
    overall_judgment    TEXT,                   -- 総合所見

    -- 損傷状況（部位別）
    damage_superstructure   TEXT,               -- 上部工損傷状況
    damage_substructure     TEXT,               -- 下部工損傷状況
    damage_bearing          TEXT,               -- 支承損傷状況
    damage_road_surface     TEXT,               -- 路面・排水損傷状況

    -- 対策区分
    countermeasure_type TEXT,                   -- 措置区分（A/B/C/D/E）
    -- A:措置不要 B:監視 C:予防保全 D:早期措置 E:緊急措置
    next_inspection_year INTEGER,               -- 次回点検推奨年

    -- 費用（概算）
    estimated_cost      INTEGER,                -- 補修概算費用（千円）

    created_at          TEXT DEFAULT (datetime('now', 'localtime'))
);

CREATE INDEX IF NOT EXISTS idx_inspections_bridge ON inspections(bridge_id);
CREATE INDEX IF NOT EXISTS idx_inspections_date   ON inspections(inspection_date);

-- =========================================================
-- 4. 補修・補強履歴
-- =========================================================
CREATE TABLE IF NOT EXISTS repairs (
    repair_id           INTEGER PRIMARY KEY AUTOINCREMENT,
    bridge_id           INTEGER NOT NULL REFERENCES bridges(bridge_id) ON DELETE CASCADE,
    inspection_id       INTEGER REFERENCES inspections(inspection_id),

    repair_date         TEXT NOT NULL,          -- 補修年月日（YYYY-MM-DD）
    repair_type         TEXT NOT NULL,          -- 補修種別（断面修復/塗装/床版補修等）
    description         TEXT,                   -- 補修内容詳細
    contractor_name     TEXT,                   -- 施工業者名
    cost                INTEGER,                -- 補修費用（千円）
    warranty_until      TEXT,                   -- 保証期限

    created_at          TEXT DEFAULT (datetime('now', 'localtime'))
);

CREATE INDEX IF NOT EXISTS idx_repairs_bridge ON repairs(bridge_id);

-- =========================================================
-- 5. 写真データ管理
-- =========================================================
CREATE TABLE IF NOT EXISTS photos (
    photo_id            INTEGER PRIMARY KEY AUTOINCREMENT,
    bridge_id           INTEGER NOT NULL REFERENCES bridges(bridge_id) ON DELETE CASCADE,
    inspection_id       INTEGER REFERENCES inspections(inspection_id),

    photo_path          TEXT NOT NULL,          -- ファイルパス（storage/ からの相対パス）
    file_name           TEXT NOT NULL,          -- 元ファイル名
    photo_type          TEXT,                   -- 写真種別（全景/損傷/補修後/その他）
    description         TEXT,                   -- 説明文
    taken_at            TEXT,                   -- 撮影日時

    created_at          TEXT DEFAULT (datetime('now', 'localtime'))
);

CREATE INDEX IF NOT EXISTS idx_photos_bridge     ON photos(bridge_id);
CREATE INDEX IF NOT EXISTS idx_photos_inspection ON photos(inspection_id);

-- =========================================================
-- 6. 調査様式・帳票ファイル管理
-- =========================================================
CREATE TABLE IF NOT EXISTS documents (
    doc_id              INTEGER PRIMARY KEY AUTOINCREMENT,
    bridge_id           INTEGER NOT NULL REFERENCES bridges(bridge_id) ON DELETE CASCADE,
    inspection_id       INTEGER REFERENCES inspections(inspection_id),

    doc_path            TEXT NOT NULL,          -- ファイルパス（storage/ からの相対パス）
    file_name           TEXT NOT NULL,          -- 元ファイル名
    doc_type            TEXT,                   -- 種別（点検調書/損傷図/補修設計書/その他）
    file_size           INTEGER,                -- ファイルサイズ（バイト）
    description         TEXT,                   -- 説明・備考
    uploaded_at         TEXT DEFAULT (datetime('now', 'localtime'))
);

CREATE INDEX IF NOT EXISTS idx_documents_bridge     ON documents(bridge_id);
CREATE INDEX IF NOT EXISTS idx_documents_inspection ON documents(inspection_id);

-- =========================================================
-- 7. ビュー: 橋梁一覧（最新点検情報付き）
-- =========================================================
CREATE VIEW IF NOT EXISTS v_bridges_latest AS
SELECT
    b.bridge_id,
    b.bridge_code,
    b.bridge_name,
    b.bridge_name_kana,
    r.route_name,
    b.manager_name,
    b.location_name,
    b.latitude,
    b.longitude,
    b.built_year,
    b.bridge_length,
    b.bridge_width,
    b.superstructure_type,
    b.substructure_type,
    b.current_health_rank,
    i.inspection_date     AS last_inspection_date,
    i.health_rank         AS last_health_rank,
    i.countermeasure_type AS last_countermeasure,
    i.next_inspection_year
FROM bridges b
LEFT JOIN routes r ON b.route_id = r.route_id
LEFT JOIN inspections i ON i.inspection_id = (
    SELECT inspection_id FROM inspections
    WHERE bridge_id = b.bridge_id
    ORDER BY inspection_date DESC
    LIMIT 1
)
WHERE b.is_active = 1;
