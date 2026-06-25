"""
橋梁管理システム - Streamlit Webアプリ
国土交通省「橋梁定期点検要領」準拠
"""

import sqlite3
import shutil
import sys
from pathlib import Path

import folium
import pandas as pd
import streamlit as st
from streamlit_folium import st_folium

DB_PATH      = Path(__file__).parent / "data" / "bridges.db"
STORAGE_ROOT = Path(__file__).parent / "storage" / "bridges"

PHOTO_EXTS = {".jpg", ".jpeg", ".png", ".heic", ".webp"}
DOC_EXTS   = {".pdf", ".xlsx", ".xls", ".docx", ".doc", ".csv"}
PHOTO_TYPES_LIST  = ["全景", "損傷", "補修後", "その他"]
DOC_TYPES_LIST    = ["点検調書", "損傷図", "補修設計書", "その他"]
ACCESS_METHOD_LIST = ["橋梁点検車", "リフト車（高所作業車）", "梯子", "目視のみ", "渡り板", "その他"]

# ──────────────────────────────────────────────────────────
# ページ設定
# ──────────────────────────────────────────────────────────
st.set_page_config(
    page_title="橋梁管理システム",
    page_icon="🌉",
    layout="wide",
)

RANK_COLOR = {
    "I":   "#16a34a",
    "II":  "#d97706",
    "III": "#ea580c",
    "IV":  "#dc2626",
}
RANK_BG = {
    "I":   "#f0fdf4",
    "II":  "#fffbeb",
    "III": "#fff7ed",
    "IV":  "#fef2f2",
}
RANK_LABEL = {
    "I":   "I : 健全",
    "II":  "II : 予防保全段階",
    "III": "III : 早期措置段階",
    "IV":  "IV : 緊急措置段階",
}
COUNTERMEASURE_LABEL = {
    "A": "A : 措置不要",
    "B": "B : 監視",
    "C": "C : 予防保全",
    "D": "D : 早期措置",
    "E": "E : 緊急措置",
}


# ──────────────────────────────────────────────────────────
# カスタム CSS
# ──────────────────────────────────────────────────────────
def inject_css():
    st.markdown("""
<style>
/* ── フォント & ベース ─────────────────────────── */
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@400;500;700&display=swap');
html, body, [class*="css"] { font-family: 'Noto Sans JP', sans-serif; }

/* ── メイン背景 ─────────────────────────────────── */
.stApp { background-color: #f0f4f8; }
.block-container { padding-top: 1.8rem; padding-bottom: 2rem; }

/* ── サイドバー ─────────────────────────────────── */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #1e3a5f 0%, #14304f 100%);
    min-width: 240px !important;
}
[data-testid="stSidebar"] * { color: #e2e8f0 !important; }

/* メニュー項目を大きく・余白を広く */
[data-testid="stSidebar"] .stRadio > div {
    display: flex !important;
    flex-direction: column !important;
    gap: 0.2rem !important;
}
[data-testid="stSidebar"] .stRadio label {
    padding: 0.7rem 1rem !important;
    border-radius: 10px !important;
    transition: background 0.15s !important;
    cursor: pointer !important;
}
[data-testid="stSidebar"] .stRadio label:hover {
    background: rgba(255,255,255,0.12) !important;
}
[data-testid="stSidebar"] .stRadio label p {
    font-size: 1.05rem !important;
    font-weight: 600 !important;
    color: #e2e8f0 !important;
    letter-spacing: 0.01em !important;
    line-height: 1.4 !important;
}

[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p {
    color: #94a3b8 !important; font-size: 0.78rem;
}

/* ── ページタイトル ─────────────────────────────── */
.page-header {
    background: linear-gradient(135deg, #1e3a5f 0%, #2563eb 100%);
    border-radius: 12px;
    padding: 1.2rem 1.8rem;
    margin-bottom: 1.5rem;
    color: white;
}
.page-header h1 {
    margin: 0; font-size: 1.6rem; font-weight: 700; color: white;
    letter-spacing: 0.02em;
}
.page-header p { margin: 0.3rem 0 0; font-size: 0.85rem; opacity: 0.75; color: white; }

/* ── カード（全面カラー）────────────────────────── */
.metric-card {
    border-radius: 16px;
    padding: 1.2rem 1.4rem;
    display: flex; align-items: center; gap: 1rem;
    box-shadow: 0 6px 20px rgba(0,0,0,0.15);
    transition: transform 0.12s, box-shadow 0.12s;
    height: 100%;
    min-height: 100px;
}
.metric-card:hover {
    transform: translateY(-3px);
    box-shadow: 0 10px 28px rgba(0,0,0,0.20);
}
.metric-card .mc-icon-wrap {
    background: rgba(255,255,255,0.22);
    border-radius: 12px;
    width: 54px; height: 54px; flex-shrink: 0;
    display: flex; align-items: center; justify-content: center;
    font-size: 1.9rem;
}
.metric-card .mc-body { flex: 1; min-width: 0; }
.metric-card .mc-value {
    font-size: 2.5rem; font-weight: 900; line-height: 1.0;
    color: white;
}
.metric-card .mc-label {
    font-size: 0.82rem; font-weight: 600;
    color: rgba(255,255,255,0.88); margin-top: 0.25rem;
}
.metric-card .mc-sub {
    font-size: 0.75rem; color: rgba(255,255,255,0.65);
}

/* ── 橋梁一覧テーブル ───────────────────────────── */
.bridge-table-wrap {
    overflow-x: auto;
    border-radius: 14px;
    box-shadow: 0 2px 16px rgba(0,0,0,0.10);
    margin-bottom: 0.8rem;
}
.bridge-list-table {
    width: 100%; border-collapse: collapse;
    background: white; font-size: 0.92rem;
}
.bridge-list-table thead tr {
    background: linear-gradient(90deg, #1e3a5f 0%, #2563eb 100%);
}
.bridge-list-table th {
    color: white; padding: 0.85rem 0.9rem;
    font-weight: 700; font-size: 0.86rem;
    white-space: nowrap; text-align: left;
}
.bridge-list-table td {
    padding: 0.75rem 0.9rem;
    border-bottom: 1px solid #e2e8f0;
    white-space: nowrap; color: #334155;
}
.bridge-list-table tbody tr:hover { background: #eff6ff; }
.bridge-list-table .bridge-code {
    color: #dc2626; font-weight: 700; font-size: 0.9rem;
}
.map-link {
    display: inline-block;
    background: #eff6ff; border: 1px solid #bfdbfe;
    border-radius: 6px; padding: 3px 10px;
    color: #2563eb; text-decoration: none;
    font-size: 0.82rem; font-weight: 600;
}
.map-link:hover { background: #dbeafe; }

/* ── ランク凡例 ─────────────────────────────────── */
.rank-legend {
    display: flex; gap: 1.2rem; flex-wrap: wrap;
    background: white; border-radius: 10px;
    padding: 0.7rem 1.2rem;
    border: 1px solid #e2e8f0;
    margin-top: 0.5rem;
}
.rank-legend .rl-item {
    display: flex; align-items: center; gap: 0.4rem;
    font-size: 0.84rem; color: #475569; font-weight: 600;
}
.rank-legend .rl-dot {
    display: inline-block; width: 12px; height: 12px; border-radius: 50%;
}

/* ── セクションヘッダー ─────────────────────────── */
.section-header {
    display: flex; align-items: center; gap: 0.6rem;
    border-bottom: 3px solid #e2e8f0;
    padding-bottom: 0.6rem; margin-bottom: 1.2rem; margin-top: 0.8rem;
}
.section-header span {
    font-size: 1.15rem; font-weight: 800; color: #1e293b; letter-spacing: 0.01em;
}

/* ── ランクバッジ ────────────────────────────────── */
.rank-badge {
    display: inline-block;
    padding: 3px 12px; border-radius: 20px;
    font-size: 0.78rem; font-weight: 700;
    letter-spacing: 0.03em;
}
.rank-I   { background:#f0fdf4; color:#16a34a; border:1px solid #86efac; }
.rank-II  { background:#fffbeb; color:#d97706; border:1px solid #fcd34d; }
.rank-III { background:#fff7ed; color:#ea580c; border:1px solid #fdba74; }
.rank-IV  { background:#fef2f2; color:#dc2626; border:1px solid #fca5a5; }

/* ── 橋梁詳細ヘッダー ───────────────────────────── */
.bridge-hero {
    background: white;
    border-radius: 12px;
    padding: 1.2rem 1.8rem;
    margin-bottom: 1rem;
    box-shadow: 0 1px 4px rgba(0,0,0,0.08);
    display: flex; align-items: center; gap: 1.2rem;
    border-left: 6px solid #2563eb;
}
.bridge-hero .bh-code {
    font-size: 0.9rem; color: #64748b; font-weight: 500;
}
.bridge-hero .bh-name {
    font-size: 1.5rem; font-weight: 700; color: #1e293b; margin: 0.1rem 0;
}

/* ── 点検カード ─────────────────────────────────── */
.insp-card {
    background: white; border-radius: 10px;
    padding: 1rem 1.2rem; margin-bottom: 0.8rem;
    box-shadow: 0 1px 3px rgba(0,0,0,0.07);
    border-left: 4px solid #e2e8f0;
}
.insp-card.rank-I-border  { border-left-color: #16a34a; }
.insp-card.rank-II-border { border-left-color: #d97706; }
.insp-card.rank-III-border{ border-left-color: #ea580c; }
.insp-card.rank-IV-border { border-left-color: #dc2626; }
.insp-card .ic-date  { font-size:0.8rem; color:#64748b; }
.insp-card .ic-title { font-size:1rem; font-weight:700; color:#1e293b; margin:0.2rem 0; }
.insp-card .ic-body  { font-size:0.85rem; color:#475569; margin-top:0.5rem; line-height:1.6; }
.insp-card .ic-meta  { font-size:0.78rem; color:#94a3b8; margin-top:0.5rem; }

/* ── 緊急アラートカード ─────────────────────────── */
.alert-card {
    background: #fef2f2; border: 1px solid #fca5a5;
    border-radius: 10px; padding: 0.8rem 1rem;
    margin-bottom: 0.5rem; display:flex; align-items:center; gap:0.8rem;
}
.alert-card.warn {
    background: #fff7ed; border-color: #fdba74;
}
.alert-card .ac-icon { font-size: 1.4rem; }
.alert-card .ac-name { font-weight:700; color:#1e293b; font-size:0.95rem; }
.alert-card .ac-sub  { font-size:0.78rem; color:#64748b; margin-top:0.1rem; }

/* ── テーブル（見やすく大きく）──────────────────── */
[data-testid="stDataFrame"] th {
    background: #1e3a5f !important; color: #e2e8f0 !important;
    font-size: 0.92rem !important; font-weight: 700 !important;
    padding: 0.7rem 0.9rem !important;
}
[data-testid="stDataFrame"] td {
    font-size: 0.95rem !important;
    padding: 0.6rem 0.9rem !important;
}
[data-testid="stDataFrame"] tr:nth-child(even) td {
    background: #f8fafc !important;
}

/* ── ボタン ─────────────────────────────────────── */
.stButton > button[kind="primary"], .stFormSubmitButton > button[kind="primary"] {
    background: linear-gradient(135deg, #1e3a5f, #2563eb) !important;
    border: none !important; border-radius: 8px !important;
    font-weight: 600 !important;
}
.stLinkButton a {
    background: #f1f5f9 !important; border: 1px solid #cbd5e1 !important;
    border-radius: 8px !important; color: #1e3a5f !important;
    font-weight: 600 !important;
}

/* ── タブ ────────────────────────────────────────── */
.stTabs [data-baseweb="tab-list"] {
    border-bottom: 2px solid #e2e8f0;
}
.stTabs [data-baseweb="tab"] {
    font-weight: 600; color: #64748b !important;
    padding: 0.5rem 1rem;
}
.stTabs [aria-selected="true"] {
    color: #2563eb !important;
    border-bottom: 2px solid #2563eb !important;
}

/* ── 入力フォーム ────────────────────────────────── */
.stTextInput input, .stSelectbox select, .stTextArea textarea,
.stDateInput input, .stNumberInput input {
    border-radius: 8px !important; border-color: #cbd5e1 !important;
}
.stForm {
    background: white; border-radius: 12px;
    padding: 1.5rem; box-shadow: 0 1px 4px rgba(0,0,0,0.08);
    border: 1px solid #e2e8f0;
}

/* ── フィルターバー ─────────────────────────────── */
.filter-bar {
    background: white; border-radius: 10px;
    padding: 1rem 1.2rem; margin-bottom: 1rem;
    box-shadow: 0 1px 3px rgba(0,0,0,0.07);
    border: 1px solid #e2e8f0;
}

/* ── info/success/warning ────────────────────────── */
[data-testid="stAlert"] {
    border-radius: 10px !important;
}

/* ══════════════════════════════════════════════════
   タブレット・スマートフォン対応 (iPad 含む)
   ══════════════════════════════════════════════════ */

/* iPad縦向き以下 (max-width: 1024px) */
@media (max-width: 1024px) {
    .block-container {
        padding-left: 1rem !important;
        padding-right: 1rem !important;
        padding-top: 1.2rem !important;
        max-width: 100% !important;
    }
    .page-header h1 { font-size: 1.3rem !important; }
    .page-header p  { font-size: 0.8rem !important; }

    /* メトリクスカード: 横並び → スクロール */
    .metric-card { padding: 0.8rem 1rem; }
    .metric-card .mc-value { font-size: 1.6rem; }
    .metric-card .mc-label { font-size: 0.7rem; }

    /* テーブルを横スクロール可能に */
    [data-testid="stDataFrame"] {
        overflow-x: auto !important;
    }
}

/* iPad縦向き以下 (max-width: 768px) */
@media (max-width: 768px) {
    /* ページヘッダー */
    .page-header {
        padding: 1rem 1.2rem;
        border-radius: 8px;
    }
    .page-header h1 { font-size: 1.1rem !important; }

    /* 橋梁ヒーロー */
    .bridge-hero { padding: 0.8rem 1rem; gap: 0.6rem; }
    .bridge-hero .bh-name { font-size: 1.2rem; }

    /* アラートカード */
    .alert-card { flex-wrap: wrap; }

    /* 点検カード */
    .insp-card { padding: 0.8rem 1rem; }

    /* フォームの余白調整 */
    .stForm { padding: 1rem; }

    /* セクションヘッダーのフォント */
    .section-header span { font-size: 0.92rem; }

    /* ボタンを大きめに（タッチ操作しやすく） */
    .stButton > button, .stFormSubmitButton > button,
    .stLinkButton a, .stDownloadButton > button {
        min-height: 2.6rem !important;
        font-size: 0.9rem !important;
    }

    /* 数値入力の +/- ボタンを大きく */
    [data-testid="stNumberInput"] button {
        min-width: 2.2rem !important;
        min-height: 2.2rem !important;
    }
}

/* スマートフォン (max-width: 480px) */
@media (max-width: 480px) {
    .page-header h1 { font-size: 1rem !important; }
    .mc-value { font-size: 1.4rem !important; }
    .bridge-hero .bh-name { font-size: 1rem; }
    .rank-badge { font-size: 0.72rem; padding: 2px 8px; }
}
</style>
""", unsafe_allow_html=True)


# ──────────────────────────────────────────────────────────
# UIヘルパー
# ──────────────────────────────────────────────────────────
def page_header(title: str, subtitle: str = ""):
    sub = f"<p>{subtitle}</p>" if subtitle else ""
    st.markdown(f"""
<div class="page-header">
  <h1>{title}</h1>
  {sub}
</div>
""", unsafe_allow_html=True)


def section_header(icon: str, text: str):
    st.markdown(f"""
<div class="section-header">
  <span>{icon} {text}</span>
</div>
""", unsafe_allow_html=True)


def rank_badge(rank: str) -> str:
    label = {"I": "ランク I", "II": "ランク II", "III": "ランク III", "IV": "ランク IV"}.get(rank, rank)
    return f'<span class="rank-badge rank-{rank}">{label}</span>'


def metric_card(label: str, value: str, sub: str = "", color: str = "#2563eb", icon: str = "🌉") -> str:
    return f"""
<div class="metric-card" style="background:linear-gradient(135deg,{color} 0%,{color}cc 100%)">
  <div class="mc-icon-wrap">{icon}</div>
  <div class="mc-body">
    <div class="mc-value">{value}</div>
    <div class="mc-label">{label}</div>
    <div class="mc-sub">{sub}</div>
  </div>
</div>"""


def _width_category(w) -> str:
    """写真の診断歩掛調査表に基づく幅員分類"""
    if w is None or w == 0:
        return "-"
    w = float(w)
    if w <= 6:   return "4m程度"
    if w <= 10:  return "8m程度"
    if w <= 14:  return "12m程度"
    if w <= 18:  return "16m程度"
    if w <= 22:  return "20m程度"
    if w <= 26:  return "24m程度"
    return "30m程度"


def _length_category(l) -> str:
    """橋長による規模分類"""
    if l is None or l == 0:
        return "-"
    l = float(l)
    if l < 15:  return "小橋"
    if l < 50:  return "中橋"
    if l < 100: return "大橋"
    return "大規模橋"


def render_bridge_table(df) -> str:
    """橋梁一覧をHTML表で描画する（管理番号赤字・地図ボタン・健全度ドット付き）"""
    RANK_DOT = {
        "I":   "#16a34a",
        "II":  "#d97706",
        "III": "#ea580c",
        "IV":  "#dc2626",
    }
    rows = []
    for _, r in df.iterrows():
        rank     = str(r.get("current_health_rank") or "-")
        dot_color = RANK_DOT.get(rank, "#94a3b8")
        dot      = (f'<span style="display:inline-block;width:13px;height:13px;'
                    f'border-radius:50%;background:{dot_color};'
                    f'vertical-align:middle;margin-right:5px;"></span>')

        lat, lon = r.get("latitude"), r.get("longitude")
        if lat and lon:
            url = f"https://www.google.com/maps?q={lat},{lon}&z=17"
            map_cell = f'<a href="{url}" target="_blank" class="map-link">📍 地図</a>'
        else:
            map_cell = '<span style="color:#94a3b8">-</span>'

        last_date = r.get("last_inspection_date") or "-"
        last_cell = (f'<span style="color:#475569">📅 {last_date}</span>'
                     if last_date != "-" else "-")
        next_yr   = r.get("next_inspection_year")
        next_cell = (f'<span style="color:#475569">📅 {next_yr}年</span>'
                     if next_yr else "-")
        access    = str(r.get("access_method") or "-")
        insp_cnt  = int(r.get("insp_count") or 0)

        bwidth = r.get("bridge_width")
        blength = r.get("bridge_length")

        rows.append(f"""<tr>
          <td><span class="bridge-code">{r['bridge_code']}</span></td>
          <td><strong>{r['bridge_name']}</strong></td>
          <td>{r.get('route_name') or '-'}</td>
          <td>{r.get('location_name') or '-'}</td>
          <td>{map_cell}</td>
          <td>{last_cell}</td>
          <td>{next_cell}</td>
          <td>{dot}{rank}</td>
          <td>{access}</td>
          <td style="text-align:center;color:#64748b">{insp_cnt}</td>
          <td>{_width_category(bwidth)}</td>
          <td>{_length_category(blength)}</td>
        </tr>""")

    rows_html = "\n".join(rows) if rows else "<tr><td colspan='12' style='text-align:center;padding:2rem;color:#94a3b8'>該当する橋梁がありません</td></tr>"
    return f"""<div class="bridge-table-wrap"><table class="bridge-list-table">
  <thead><tr>
    <th>管理番号</th><th>橋梁名</th><th>路線名</th><th>所在地</th>
    <th>地図</th><th>前回点検</th><th>次回点検予定</th>
    <th>健全性</th><th>点検足場</th><th>点検数</th>
    <th>幅員分類</th><th>規模</th>
  </tr></thead>
  <tbody>{rows_html}</tbody>
</table></div>"""


def gmaps_url(lat, lon) -> str | None:
    if lat and lon:
        return f"https://www.google.com/maps?q={lat},{lon}&z=17"
    return None


# ──────────────────────────────────────────────────────────
# DB ユーティリティ
# ──────────────────────────────────────────────────────────
def _ensure_db():
    """初回起動時にDBとサンプルデータを自動生成する（Replit等クラウド環境向け）"""
    if DB_PATH.exists():
        return
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    scripts_dir = Path(__file__).parent / "scripts"
    sys.path.insert(0, str(scripts_dir))
    import generate_dummy_data as _gdd  # noqa: PLC0415
    con = _gdd.create_database()
    _gdd.insert_dummy_data(con)
    con.close()
    # ストレージフォルダも作成
    import init_storage as _is  # noqa: PLC0415
    _is.init_storage()


_ensure_db()

# DB マイグレーション: access_method 列がなければ追加
with sqlite3.connect(DB_PATH) as _mc:
    try:
        _mc.execute("ALTER TABLE inspections ADD COLUMN access_method TEXT")
        _mc.commit()
    except sqlite3.OperationalError:
        pass


@st.cache_resource
def get_connection():
    con = sqlite3.connect(DB_PATH, check_same_thread=False)
    con.row_factory = sqlite3.Row
    return con


def query_df(sql: str, params=()) -> pd.DataFrame:
    return pd.read_sql_query(sql, get_connection(), params=params)


# ──────────────────────────────────────────────────────────
# ファイル管理ヘルパー
# ──────────────────────────────────────────────────────────
def _safe_filename(name: str) -> str:
    return Path(name).name.replace("..", "").replace("/", "").replace("\\", "")


def _insp_options(bridge_id: int) -> list[str]:
    df = query_df(
        "SELECT inspection_id, inspection_date, inspection_type FROM inspections "
        "WHERE bridge_id=? ORDER BY inspection_date DESC", (bridge_id,),
    )
    return [f"{r['inspection_date']} {r['inspection_type']} (id={r['inspection_id']})"
            for _, r in df.iterrows()]


def _insp_id_from_label(bridge_id: int, label: str):
    if label == "なし" or not label:
        return None
    try:
        return int(label.split("id=")[1].rstrip(")"))
    except Exception:
        return None


def _tab_files(bridge_id: int, bridge_code: str, photos_dir: Path, forms_dir: Path, drawings_dir: Path):
    con = get_connection()
    st.caption(f"📂 `storage/bridges/{bridge_code}/`　（photos/ / forms/ / drawings/ に直接置くことも可能）")

    sec_photo, sec_form = st.columns(2)

    with sec_photo:
        section_header("📷", "写真データ")
        with st.expander("＋ 写真を追加"):
            up_photo = st.file_uploader("写真ファイル（JPG/PNG）",
                type=["jpg","jpeg","png","webp"], accept_multiple_files=True,
                key=f"up_photo_{bridge_id}")
            p_type = st.selectbox("写真種別", PHOTO_TYPES_LIST, key=f"pt_{bridge_id}")
            p_desc = st.text_input("説明（任意）", key=f"pd_{bridge_id}")
            p_date = st.date_input("撮影日", key=f"pdate_{bridge_id}")
            p_insp = st.selectbox("関連点検（任意）", ["なし"] + _insp_options(bridge_id), key=f"pi_{bridge_id}")
            if st.button("写真を保存", key=f"pbtn_{bridge_id}", type="primary") and up_photo:
                for uf in up_photo:
                    safe_name = _safe_filename(uf.name)
                    (photos_dir / safe_name).write_bytes(uf.getvalue())
                    rel_path = f"bridges/{bridge_code}/photos/{safe_name}"
                    con.execute(
                        "INSERT INTO photos (bridge_id, inspection_id, photo_path, "
                        "file_name, photo_type, description, taken_at) VALUES (?,?,?,?,?,?,?)",
                        (bridge_id, _insp_id_from_label(bridge_id, p_insp),
                         rel_path, safe_name, p_type, p_desc or None, str(p_date)),
                    )
                con.commit()
                st.success(f"{len(up_photo)}件の写真を保存しました")
                st.rerun()

        db_photos = query_df(
            "SELECT photo_id, photo_path, file_name, photo_type, description, taken_at "
            "FROM photos WHERE bridge_id=? ORDER BY taken_at DESC", (bridge_id,))
        disk_photos = [p for p in sorted(photos_dir.glob("*")) if p.suffix.lower() in PHOTO_EXTS]

        if not db_photos.empty:
            st.caption(f"登録済み: {len(db_photos)}件")
            cols = st.columns(3)
            for i, (_, row) in enumerate(db_photos.iterrows()):
                img_path = STORAGE_ROOT / bridge_code / "photos" / row["file_name"]
                with cols[i % 3]:
                    if img_path.exists():
                        st.image(str(img_path), use_container_width=True)
                    else:
                        st.warning("ファイルなし")
                    st.caption(f"**{row['photo_type'] or '-'}**　{row['taken_at'] or ''}\n\n{row['description'] or ''}")
                    if img_path.exists():
                        st.download_button("⬇ DL", img_path.read_bytes(),
                            file_name=row["file_name"], key=f"dphoto_{row['photo_id']}")
        elif disk_photos:
            st.caption(f"フォルダ内: {len(disk_photos)}件（DB未登録）")
            cols = st.columns(3)
            for i, p in enumerate(disk_photos):
                with cols[i % 3]:
                    st.image(str(p), use_container_width=True)
                    st.caption(p.name)
        else:
            st.info("写真はまだ登録されていません。")

    with sec_form:
        section_header("📄", "調査様式・帳票")
        FILE_ICONS = {".pdf":"📕",".xlsx":"📗",".xls":"📗",".docx":"📘",".doc":"📘",".csv":"📊"}
        with st.expander("＋ ファイルを追加"):
            up_doc = st.file_uploader("ファイル（PDF/Excel/Word）",
                type=["pdf","xlsx","xls","docx","doc","csv"], accept_multiple_files=True,
                key=f"up_doc_{bridge_id}")
            d_type = st.selectbox("種別", DOC_TYPES_LIST, key=f"dt_{bridge_id}")
            d_desc = st.text_input("説明（任意）", key=f"dd_{bridge_id}")
            d_insp = st.selectbox("関連点検（任意）", ["なし"] + _insp_options(bridge_id), key=f"di_{bridge_id}")
            if st.button("ファイルを保存", key=f"dbtn_{bridge_id}", type="primary") and up_doc:
                for uf in up_doc:
                    safe_name = _safe_filename(uf.name)
                    data = uf.getvalue()
                    (forms_dir / safe_name).write_bytes(data)
                    rel_path = f"bridges/{bridge_code}/forms/{safe_name}"
                    con.execute(
                        "INSERT INTO documents (bridge_id, inspection_id, doc_path, "
                        "file_name, doc_type, file_size, description, uploaded_at) "
                        "VALUES (?,?,?,?,?,?,?,datetime('now','localtime'))",
                        (bridge_id, _insp_id_from_label(bridge_id, d_insp),
                         rel_path, safe_name, d_type, len(data), d_desc or None),
                    )
                con.commit()
                st.success(f"{len(up_doc)}件のファイルを保存しました")
                st.rerun()

        db_docs = query_df(
            "SELECT doc_id, doc_path, file_name, doc_type, file_size, description, uploaded_at "
            "FROM documents WHERE bridge_id=? AND doc_path LIKE ? ORDER BY uploaded_at DESC",
            (bridge_id, f"bridges/{bridge_code}/forms/%"))
        disk_docs = [p for p in sorted(forms_dir.glob("*")) if p.suffix.lower() in DOC_EXTS]

        if not db_docs.empty:
            st.caption(f"登録済み: {len(db_docs)}件")
            for _, row in db_docs.iterrows():
                f_path = STORAGE_ROOT / bridge_code / "forms" / row["file_name"]
                icon = FILE_ICONS.get(Path(row["file_name"]).suffix.lower(), "📎")
                size_kb = f"{row['file_size'] // 1024} KB" if row["file_size"] else "-"
                c1, c2 = st.columns([4, 1])
                with c1:
                    st.markdown(f"{icon} **{row['file_name']}**　`{row['doc_type'] or '-'}`　{size_kb}　_{row['uploaded_at'] or ''}_")
                    if row["description"]:
                        st.caption(row["description"])
                with c2:
                    if f_path.exists():
                        st.download_button("⬇ DL", f_path.read_bytes(),
                            file_name=row["file_name"], key=f"ddoc_{row['doc_id']}")
                    else:
                        st.caption("⚠なし")
                st.divider()
        elif disk_docs:
            st.caption(f"フォルダ内: {len(disk_docs)}件（DB未登録）")
            for p in disk_docs:
                icon = FILE_ICONS.get(p.suffix.lower(), "📎")
                c1, c2 = st.columns([4, 1])
                c1.markdown(f"{icon} {p.name}")
                c2.download_button("⬇ DL", p.read_bytes(), file_name=p.name, key=f"ddisk_{p.name}")
        else:
            st.info("帳票・調査様式はまだ登録されていません。")

    # ── 一般図・図面 ─────────────────────────────────
    st.markdown("<br>", unsafe_allow_html=True)
    section_header("📐", "一般図・図面")
    drawings_dir.mkdir(parents=True, exist_ok=True)
    DRAW_TYPES = ["一般図", "平面図", "側面図", "断面図", "構造図", "その他"]
    with st.expander("＋ 図面ファイルを追加"):
        up_draw = st.file_uploader(
            "図面ファイル（PDF/DWG/画像）",
            type=["pdf", "jpg", "jpeg", "png", "xlsx", "xls", "docx"],
            accept_multiple_files=True,
            key=f"up_draw_{bridge_id}",
        )
        dr_type = st.selectbox("図面種別", DRAW_TYPES, key=f"drt_{bridge_id}")
        dr_desc = st.text_input("説明（任意）", key=f"drd_{bridge_id}")
        if st.button("図面を保存", key=f"drbtn_{bridge_id}", type="primary") and up_draw:
            for uf in up_draw:
                safe_name = _safe_filename(uf.name)
                data = uf.getvalue()
                (drawings_dir / safe_name).write_bytes(data)
                rel_path = f"bridges/{bridge_code}/drawings/{safe_name}"
                con.execute(
                    "INSERT INTO documents (bridge_id, inspection_id, doc_path, "
                    "file_name, doc_type, file_size, description, uploaded_at) "
                    "VALUES (?,?,?,?,?,?,?,datetime('now','localtime'))",
                    (bridge_id, None, rel_path, safe_name, dr_type, len(data), dr_desc or None),
                )
            con.commit()
            st.success(f"{len(up_draw)}件の図面を保存しました")
            st.rerun()

    db_draws = query_df(
        "SELECT doc_id, doc_path, file_name, doc_type, file_size, description, uploaded_at "
        "FROM documents WHERE bridge_id=? AND doc_path LIKE ? ORDER BY uploaded_at DESC",
        (bridge_id, f"bridges/{bridge_code}/drawings/%"))
    disk_draws = [p for p in sorted(drawings_dir.glob("*")) if p.suffix.lower() in DOC_EXTS | {".jpg",".jpeg",".png"}]

    if not db_draws.empty:
        st.caption(f"登録済み: {len(db_draws)}件")
        for _, row in db_draws.iterrows():
            f_path = drawings_dir / row["file_name"]
            icon = FILE_ICONS.get(Path(row["file_name"]).suffix.lower(), "📐")
            size_kb = f"{row['file_size'] // 1024} KB" if row["file_size"] else "-"
            c1, c2 = st.columns([4, 1])
            with c1:
                st.markdown(f"{icon} **{row['file_name']}**　`{row['doc_type'] or '-'}`　{size_kb}　_{row['uploaded_at'] or ''}_")
                if row["description"]:
                    st.caption(row["description"])
            with c2:
                if f_path.exists():
                    st.download_button("⬇ DL", f_path.read_bytes(),
                        file_name=row["file_name"], key=f"ddraw_{row['doc_id']}")
                else:
                    st.caption("⚠なし")
            st.divider()
    elif disk_draws:
        st.caption(f"フォルダ内: {len(disk_draws)}件（DB未登録）")
        for p in disk_draws:
            icon = FILE_ICONS.get(p.suffix.lower(), "📐")
            c1, c2 = st.columns([4, 1])
            c1.markdown(f"{icon} {p.name}")
            c2.download_button("⬇ DL", p.read_bytes(), file_name=p.name, key=f"ddrawdisk_{p.name}")
    else:
        st.info("一般図・図面はまだ登録されていません。")


# ──────────────────────────────────────────────────────────
# CSS 注入 & サイドバー
# ──────────────────────────────────────────────────────────
inject_css()

st.sidebar.markdown("""
<div style="padding:1.2rem 0.8rem 0.6rem;">
  <div style="font-size:1.6rem; font-weight:900; color:#f1f5f9; letter-spacing:0.02em; line-height:1.2;">
    🌉 橋梁管理
  </div>
  <div style="font-size:0.78rem; color:#94a3b8; margin-top:0.3rem; font-weight:500; letter-spacing:0.04em;">
    Bridge Inspection System
  </div>
</div>
<hr style="border-color:#2d4a6b; margin:0.4rem 0 0.8rem;">
<div style="padding:0 0.5rem 0.5rem; font-size:0.72rem; color:#64748b; font-weight:600; letter-spacing:0.08em; text-transform:uppercase;">
  ナビゲーション
</div>
""", unsafe_allow_html=True)

page = st.sidebar.radio(
    "メニュー",
    ["📊 ダッシュボード", "📋 橋梁一覧", "➕ 橋梁追加", "✏️ 情報変更", "🗑️ 橋梁削除", "🔍 橋梁詳細", "📋 点検記録入力", "🗺️ 地図"],
    label_visibility="collapsed",
)

st.sidebar.markdown("""
<hr style="border-color:#2d4a6b; margin:1.5rem 0 0.8rem;">
<div style="font-size:0.76rem; color:#475569; padding:0 0.8rem 1.2rem; line-height:1.8;">
  📋 国土交通省<br>
  　橋梁定期点検要領 準拠<br>
  🗄️ SQLite + Streamlit
</div>
""", unsafe_allow_html=True)


# ──────────────────────────────────────────────────────────
# 橋梁管理フォーム共通ヘルパー（複数ページで共有）
# ──────────────────────────────────────────────────────────
SUPER_TYPES = [
    "RC中空床版橋", "RC単純桁橋", "RC単純スラブ橋",
    "PC単純T桁橋", "PC連続桁橋", "PC連続箱桁橋",
    "鋼単純桁橋", "鋼連続桁橋", "石造りアーチ橋", "木橋", "その他",
]
SUB_TYPES = [
    "逆T式橋台", "重力式橋台", "一体式橋台",
    "張出し式橋脚", "壁式橋脚", "ラーメン式橋脚", "その他",
]
MATERIALS = ["RC", "PC", "鋼", "石", "木", "その他"]


def _idx(lst, val):
    return lst.index(val) if val in lst else 0


def _bridge_form(prefix: str, defaults: dict = {}):
    """橋梁入力フォームの共通部品。dict を返す。"""
    c1, c2 = st.columns(2)
    with c1:
        section_header("🔑", "識別情報")
        code = st.text_input("管理番号 *", value=defaults.get("bridge_code", ""),
                             key=f"{prefix}_code", placeholder="例: T-013")
        name = st.text_input("橋名 *", value=defaults.get("bridge_name", ""),
                             key=f"{prefix}_name")
        kana = st.text_input("橋名（カナ）", value=defaults.get("bridge_name_kana", "") or "",
                             key=f"{prefix}_kana")
        mgr  = st.text_input("管理者名", value=defaults.get("manager_name", "○○町役場 建設課"),
                             key=f"{prefix}_mgr")

        st.markdown("<br>", unsafe_allow_html=True)
        section_header("🛣️", "路線情報")
        existing_routes = query_df("SELECT route_name, route_type FROM routes ORDER BY route_name")
        route_opts = existing_routes["route_name"].tolist() + ["── 新規路線を入力 ──"]
        default_route = defaults.get("route_name", route_opts[0])
        if default_route not in route_opts:
            default_route = route_opts[0]
        route_sel = st.selectbox("路線名", route_opts, index=route_opts.index(default_route),
                                 key=f"{prefix}_route_sel")
        if route_sel == "── 新規路線を入力 ──":
            route_name = st.text_input("新規路線名", key=f"{prefix}_route_new")
            route_type = st.selectbox("路線種別", ["町道", "県道", "国道", "農道", "林道", "その他"],
                                      key=f"{prefix}_rtype")
        else:
            route_name = route_sel
            matched = existing_routes.loc[existing_routes["route_name"] == route_sel, "route_type"]
            route_type = matched.values[0] if not matched.empty else "町道"

    with c2:
        section_header("📍", "位置情報")
        loc  = st.text_input("所在地（字名）", value=defaults.get("location_name", "") or "",
                             key=f"{prefix}_loc")
        lc1, lc2 = st.columns(2)
        lat  = lc1.number_input("緯度", value=float(defaults.get("latitude") or 35.0),
                                format="%.6f", key=f"{prefix}_lat")
        lon  = lc2.number_input("経度", value=float(defaults.get("longitude") or 136.0),
                                format="%.6f", key=f"{prefix}_lon")

        st.markdown("<br>", unsafe_allow_html=True)
        section_header("📐", "諸元")
        sc1, sc2 = st.columns(2)
        year   = sc1.number_input("架設年（西暦）", min_value=1800, max_value=2100,
                                  value=int(defaults.get("built_year") or 2000),
                                  key=f"{prefix}_year")
        spans  = sc2.number_input("径間数", min_value=1, max_value=99,
                                  value=int(defaults.get("span_count") or 1),
                                  key=f"{prefix}_spans")
        bc1, bc2 = st.columns(2)
        blen   = bc1.number_input("橋長 (m)", min_value=0.0,
                                  value=float(defaults.get("bridge_length") or 0.0),
                                  key=f"{prefix}_blen")
        bwid   = bc2.number_input("幅員 (m)", min_value=0.0,
                                  value=float(defaults.get("bridge_width") or 0.0),
                                  key=f"{prefix}_bwid")

        sup_type = st.selectbox("上部工形式",  SUPER_TYPES,
                                index=_idx(SUPER_TYPES, defaults.get("superstructure_type")),
                                key=f"{prefix}_sup")
        sub_type = st.selectbox("下部工形式",  SUB_TYPES,
                                index=_idx(SUB_TYPES,   defaults.get("substructure_type")),
                                key=f"{prefix}_sub")
        mat      = st.selectbox("主要材料",    MATERIALS,
                                index=_idx(MATERIALS,   defaults.get("material")),
                                key=f"{prefix}_mat")
        rank     = st.selectbox("健全性ランク", ["I", "II", "III", "IV"],
                                index=["I","II","III","IV"].index(
                                    defaults.get("current_health_rank", "I")),
                                format_func=lambda x: RANK_LABEL[x],
                                key=f"{prefix}_rank")

    return dict(
        bridge_code=code.strip(), bridge_name=name.strip(), bridge_name_kana=kana.strip(),
        manager_name=mgr.strip(), route_name=route_name, route_type=route_type,
        location_name=loc.strip(), latitude=lat, longitude=lon,
        built_year=year, span_count=spans,
        bridge_length=blen, bridge_width=bwid,
        superstructure_type=sup_type, substructure_type=sub_type,
        material=mat, current_health_rank=rank,
    )


def _upsert_route(con, route_name: str, route_type: str) -> int:
    con.execute("INSERT OR IGNORE INTO routes(route_name,route_type) VALUES(?,?)",
                (route_name, route_type))
    con.commit()
    return con.execute("SELECT route_id FROM routes WHERE route_name=?",
                       (route_name,)).fetchone()[0]


# ──────────────────────────────────────────────────────────
# 1. ダッシュボード
# ──────────────────────────────────────────────────────────
if page == "📊 ダッシュボード":
    page_header("📊 橋梁管理 ダッシュボード")

    df_summary = query_df(
        "SELECT current_health_rank, COUNT(*) as cnt FROM bridges WHERE is_active=1 "
        "GROUP BY current_health_rank ORDER BY current_health_rank"
    )
    rank_counts = dict(zip(df_summary["current_health_rank"], df_summary["cnt"]))
    total = sum(rank_counts.values())

    # ── メトリクスカード（全面カラー）────────────────────
    cols = st.columns(5)
    cards = [
        ("管理橋梁数（総計）", f"{total}",                     "全管理橋梁",         "#2563eb", "🌉"),
        ("I : 健全",           f"{rank_counts.get('I', 0)}",   "措置不要",           RANK_COLOR["I"],   "✅"),
        ("II : 予防保全",      f"{rank_counts.get('II', 0)}",  "監視・予防保全措置", RANK_COLOR["II"],  "🔔"),
        ("III : 早期措置",     f"{rank_counts.get('III', 0)}", "早期補修が必要",     RANK_COLOR["III"], "⚠️"),
        ("IV : 緊急措置",      f"{rank_counts.get('IV', 0)}",  "緊急補修・通行規制検討", RANK_COLOR["IV"], "🚨"),
    ]
    for col, (label, val, sub, color, icon) in zip(cols, cards):
        with col:
            st.markdown(metric_card(label, val + " 橋", sub, color, icon), unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    section_header("⚠️", "緊急・早期措置が必要な橋梁")
    df_urgent = query_df(
        """SELECT bridge_code, bridge_name, route_name,
                  current_health_rank, last_inspection_date, last_countermeasure
           FROM v_bridges_latest
           WHERE current_health_rank IN ('III','IV')
           ORDER BY current_health_rank DESC"""
    )
    if df_urgent.empty:
        st.success("現在、緊急・早期措置が必要な橋梁はありません。")
    else:
        cols_alert = st.columns(2)
        for i, (_, r) in enumerate(df_urgent.iterrows()):
            is_iv = r["current_health_rank"] == "IV"
            cls   = "" if is_iv else "warn"
            icon  = "🚨" if is_iv else "⚠️"
            cm    = COUNTERMEASURE_LABEL.get(r["last_countermeasure"], r["last_countermeasure"] or "-")
            date  = r["last_inspection_date"] or "未点検"
            with cols_alert[i % 2]:
                st.markdown(f"""
<div class="alert-card {cls}">
  <div class="ac-icon">{icon}</div>
  <div>
    <div class="ac-name">{r['bridge_code']}　{r['bridge_name']}
      {rank_badge(r['current_health_rank'])}
    </div>
    <div class="ac-sub">{r['route_name'] or '-'}　｜　最終点検: {date}　｜　措置: {cm}</div>
  </div>
</div>
""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── 橋梁一覧テーブル ──────────────────────────────────
    section_header("🌉", "橋梁一覧")

    # 検索バー
    col_kw, _ = st.columns([3, 1])
    with col_kw:
        kw = st.text_input(
            "", placeholder="🔍 橋梁名・管理番号・場所で検索...",
            label_visibility="collapsed",
        )

    df_list = query_df(
        """SELECT
               b.bridge_code, b.bridge_name,
               r.route_name, b.location_name,
               b.latitude, b.longitude,
               b.bridge_width, b.bridge_length,
               i.inspection_date          AS last_inspection_date,
               i.next_inspection_year,
               COALESCE(i.access_method, '未記録') AS access_method,
               b.current_health_rank,
               (SELECT COUNT(*) FROM inspections WHERE bridge_id = b.bridge_id) AS insp_count
           FROM bridges b
           LEFT JOIN routes r ON b.route_id = r.route_id
           LEFT JOIN inspections i ON i.inspection_id = (
               SELECT inspection_id FROM inspections
               WHERE bridge_id = b.bridge_id
               ORDER BY inspection_date DESC LIMIT 1
           )
           WHERE b.is_active = 1
           ORDER BY b.bridge_code"""
    )

    if kw:
        mask = (
            df_list["bridge_code"].str.contains(kw, case=False, na=False) |
            df_list["bridge_name"].str.contains(kw, case=False, na=False) |
            df_list["location_name"].fillna("").str.contains(kw, case=False, na=False)
        )
        df_list = df_list[mask]

    st.markdown(
        f'<p style="color:#64748b;font-size:0.86rem;margin-bottom:0.5rem;">'
        f'管理橋梁数: <strong>{len(df_list)}</strong>件</p>',
        unsafe_allow_html=True,
    )
    st.markdown(render_bridge_table(df_list), unsafe_allow_html=True)

    # 凡例
    st.markdown("""
<div class="rank-legend">
  <span class="rl-item"><span class="rl-dot" style="background:#16a34a"></span>I : 健全</span>
  <span class="rl-item"><span class="rl-dot" style="background:#d97706"></span>II : 予防保全段階</span>
  <span class="rl-item"><span class="rl-dot" style="background:#ea580c"></span>III : 早期措置段階</span>
  <span class="rl-item"><span class="rl-dot" style="background:#dc2626"></span>IV : 緊急措置段階</span>
</div>
""", unsafe_allow_html=True)


# ──────────────────────────────────────────────────────────
# 2. 橋梁一覧
# ──────────────────────────────────────────────────────────
elif page == "📋 橋梁一覧":
    page_header("📋 橋梁一覧", "管理橋梁の一覧・検索・地図表示")

    # フィルター
    st.markdown('<div class="filter-bar">', unsafe_allow_html=True)
    col_f1, col_f2, col_f3 = st.columns(3)
    with col_f1:
        rank_filter_l = st.multiselect("健全性ランクで絞り込み",
            ["I", "II", "III", "IV"], default=["I", "II", "III", "IV"], key="list_rank")
    with col_f2:
        routes_l = query_df("SELECT route_name FROM routes ORDER BY route_name")["route_name"].tolist()
        route_filter_l = st.selectbox("路線で絞り込み", ["（すべて）"] + routes_l, key="list_route")
    with col_f3:
        keyword_l = st.text_input("橋名で検索", placeholder="例: 桜橋", key="list_kw")
    st.markdown('</div>', unsafe_allow_html=True)

    placeholders_l = ", ".join("?" * len(rank_filter_l)) if rank_filter_l else "''"
    params_l: list = list(rank_filter_l)
    sql_l = f"SELECT b.*, r.route_name, b.bridge_width, b.bridge_length FROM v_bridges_latest b LEFT JOIN routes r ON b.route_id = r.route_id WHERE b.current_health_rank IN ({placeholders_l})"
    # v_bridges_latest already has route_name, rebuild simpler
    sql_l = f"""SELECT
        b.bridge_code, b.bridge_name,
        r.route_name, b.location_name,
        b.latitude, b.longitude,
        b.bridge_width, b.bridge_length,
        i.inspection_date AS last_inspection_date,
        i.next_inspection_year,
        COALESCE(i.access_method, '未記録') AS access_method,
        b.current_health_rank,
        (SELECT COUNT(*) FROM inspections WHERE bridge_id = b.bridge_id) AS insp_count
    FROM bridges b
    LEFT JOIN routes r ON b.route_id = r.route_id
    LEFT JOIN inspections i ON i.inspection_id = (
        SELECT inspection_id FROM inspections
        WHERE bridge_id = b.bridge_id
        ORDER BY inspection_date DESC LIMIT 1
    )
    WHERE b.is_active = 1
    AND b.current_health_rank IN ({placeholders_l})"""
    if route_filter_l != "（すべて）":
        sql_l += " AND r.route_name = ?"
        params_l.append(route_filter_l)
    if keyword_l:
        sql_l += " AND (b.bridge_name LIKE ? OR b.bridge_code LIKE ?)"
        params_l += [f"%{keyword_l}%", f"%{keyword_l}%"]
    sql_l += " ORDER BY b.bridge_code"
    df_list_l = query_df(sql_l, tuple(params_l))

    # 地図
    if not df_list_l.empty and df_list_l["latitude"].notna().any():
        section_header("📍", "橋梁位置図")
        center_lat_l = df_list_l["latitude"].dropna().mean()
        center_lon_l = df_list_l["longitude"].dropna().mean()
        m_l = folium.Map(location=[center_lat_l, center_lon_l], zoom_start=14,
                         tiles="CartoDB positron")
        for _, r_l in df_list_l.iterrows():
            if pd.isna(r_l["latitude"]):
                continue
            color_l = RANK_COLOR.get(r_l["current_health_rank"], "#6c757d")
            gmap_l  = gmaps_url(r_l["latitude"], r_l["longitude"])
            gmap_link_l = f'<a href="{gmap_l}" target="_blank">📍 Googleマップで開く</a>' if gmap_l else ""
            popup_html_l = f"""
<div style="font-family:sans-serif;font-size:13px;line-height:1.6">
<b style="font-size:14px">{r_l['bridge_code']} {r_l['bridge_name']}</b><br>
<span style="color:#666">所在地:</span> {r_l['location_name'] or '-'}<br>
<span style="color:#666">路線:</span> {r_l['route_name'] or '-'}<br>
{gmap_link_l}
</div>"""
            folium.CircleMarker(
                location=[r_l["latitude"], r_l["longitude"]],
                radius=11, color=color_l, fill=True,
                fill_color=color_l, fill_opacity=0.85,
                popup=folium.Popup(popup_html_l, max_width=260),
                tooltip=f"{r_l['bridge_code']} {r_l['bridge_name']}（ランク{r_l['current_health_rank']}）",
            ).add_to(m_l)
        st_folium(m_l, width=None, height=420, use_container_width=True)

    st.markdown("<br>", unsafe_allow_html=True)
    section_header("🌉", f"橋梁一覧（{len(df_list_l)}件）")
    st.markdown(render_bridge_table(df_list_l), unsafe_allow_html=True)
    st.markdown("""
<div class="rank-legend">
  <span class="rl-item"><span class="rl-dot" style="background:#16a34a"></span>I : 健全</span>
  <span class="rl-item"><span class="rl-dot" style="background:#d97706"></span>II : 予防保全段階</span>
  <span class="rl-item"><span class="rl-dot" style="background:#ea580c"></span>III : 早期措置段階</span>
  <span class="rl-item"><span class="rl-dot" style="background:#dc2626"></span>IV : 緊急措置段階</span>
</div>
""", unsafe_allow_html=True)


# ──────────────────────────────────────────────────────────
# 3. 橋梁追加
# ──────────────────────────────────────────────────────────
elif page == "➕ 橋梁追加":
    page_header("➕ 橋梁追加", "新しい橋梁をデータベースに登録します")

    con = get_connection()
    st.markdown("<br>", unsafe_allow_html=True)
    with st.form("form_add"):
        fields = _bridge_form("add")
        st.markdown("<br>", unsafe_allow_html=True)
        submitted_add = st.form_submit_button(
            "✅ 橋梁を登録する", type="primary", use_container_width=True)

    if submitted_add:
        if not fields["bridge_code"] or not fields["bridge_name"]:
            st.error("管理番号と橋名は必須です。")
        else:
            try:
                route_id = _upsert_route(con, fields["route_name"], fields["route_type"])
                con.execute(
                    """INSERT INTO bridges
                       (bridge_code, bridge_name, bridge_name_kana, route_id, manager_name,
                        location_name, latitude, longitude, built_year,
                        bridge_length, bridge_width, superstructure_type, substructure_type,
                        span_count, material, current_health_rank)
                       VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (fields["bridge_code"], fields["bridge_name"], fields["bridge_name_kana"] or None,
                     route_id, fields["manager_name"], fields["location_name"] or None,
                     fields["latitude"], fields["longitude"], fields["built_year"],
                     fields["bridge_length"], fields["bridge_width"],
                     fields["superstructure_type"], fields["substructure_type"],
                     fields["span_count"], fields["material"], fields["current_health_rank"]),
                )
                con.commit()
                # ストレージフォルダ作成
                bd = STORAGE_ROOT / fields["bridge_code"]
                (bd / "photos").mkdir(parents=True, exist_ok=True)
                (bd / "forms").mkdir(parents=True, exist_ok=True)
                st.success(f"✅ 橋梁「{fields['bridge_name']}（{fields['bridge_code']}）」を登録しました。")
                st.balloons()
            except Exception as e:
                if "UNIQUE constraint" in str(e):
                    st.error(f"管理番号「{fields['bridge_code']}」は既に使用されています。")
                else:
                    st.error(f"登録に失敗しました: {e}")


# ──────────────────────────────────────────────────────────
# 4. 情報変更
# ──────────────────────────────────────────────────────────
elif page == "✏️ 情報変更":
    page_header("✏️ 情報変更", "橋梁の基本情報を変更します")

    con = get_connection()
    st.markdown("<br>", unsafe_allow_html=True)
    all_bridges = query_df(
        "SELECT bridge_code || ' ' || bridge_name AS label, bridge_id "
        "FROM bridges WHERE is_active=1 ORDER BY bridge_code"
    )
    if all_bridges.empty:
        st.info("橋梁データがありません。")
    else:
        edit_label = st.selectbox("変更する橋梁を選択", all_bridges["label"].tolist(),
                                  key="edit_sel")
        edit_id = int(all_bridges.loc[all_bridges["label"] == edit_label, "bridge_id"].values[0])
        df_cur = query_df(
            """SELECT b.*, r.route_name, r.route_type
               FROM bridges b LEFT JOIN routes r ON b.route_id=r.route_id
               WHERE b.bridge_id=?""", (edit_id,))
        if df_cur.empty:
            st.error("橋梁情報が取得できません。")
        else:
            cur = df_cur.iloc[0].to_dict()
            with st.form("form_edit"):
                fields_e = _bridge_form("edit", defaults=cur)
                st.markdown("<br>", unsafe_allow_html=True)
                submitted_edit = st.form_submit_button(
                    "💾 変更を保存する", type="primary", use_container_width=True)

            if submitted_edit:
                if not fields_e["bridge_name"]:
                    st.error("橋名は必須です。")
                else:
                    try:
                        route_id_e = _upsert_route(con, fields_e["route_name"], fields_e["route_type"])
                        old_code = cur["bridge_code"]
                        new_code = fields_e["bridge_code"]
                        con.execute(
                            """UPDATE bridges SET
                               bridge_code=?, bridge_name=?, bridge_name_kana=?, route_id=?, manager_name=?,
                               location_name=?, latitude=?, longitude=?, built_year=?,
                               bridge_length=?, bridge_width=?, superstructure_type=?,
                               substructure_type=?, span_count=?, material=?,
                               current_health_rank=?,
                               updated_at=datetime('now','localtime')
                               WHERE bridge_id=?""",
                            (new_code,
                             fields_e["bridge_name"], fields_e["bridge_name_kana"] or None,
                             route_id_e, fields_e["manager_name"],
                             fields_e["location_name"] or None,
                             fields_e["latitude"], fields_e["longitude"],
                             fields_e["built_year"], fields_e["bridge_length"],
                             fields_e["bridge_width"], fields_e["superstructure_type"],
                             fields_e["substructure_type"], fields_e["span_count"],
                             fields_e["material"], fields_e["current_health_rank"],
                             edit_id),
                        )
                        con.commit()
                        if old_code != new_code:
                            old_dir = STORAGE_ROOT / old_code
                            new_dir = STORAGE_ROOT / new_code
                            if old_dir.exists():
                                import shutil as _shutil
                                _shutil.move(str(old_dir), str(new_dir))
                        st.success(f"✅「{fields_e['bridge_name']}」の情報を更新しました。")
                    except Exception as e:
                        st.error(f"更新に失敗しました: {e}")


# ──────────────────────────────────────────────────────────
# 5. 橋梁削除
# ──────────────────────────────────────────────────────────
elif page == "🗑️ 橋梁削除":
    page_header("🗑️ 橋梁削除", "橋梁のアーカイブ（非表示）または完全削除を行います")

    con = get_connection()
    st.markdown("<br>", unsafe_allow_html=True)

    # アーカイブ済みも含めて表示
    all_for_del = query_df(
        """SELECT b.bridge_code || ' ' || b.bridge_name
                  || CASE WHEN b.is_active=0 THEN ' [アーカイブ済]' ELSE '' END AS label,
                  b.bridge_id, b.is_active
           FROM bridges b ORDER BY b.bridge_code"""
    )
    if all_for_del.empty:
        st.info("橋梁データがありません。")
    else:
        del_label = st.selectbox("対象橋梁を選択", all_for_del["label"].tolist(), key="del_sel")
        row_del   = all_for_del.loc[all_for_del["label"] == del_label].iloc[0]
        del_id    = int(row_del["bridge_id"])
        is_active = int(row_del["is_active"])

        df_del = query_df("SELECT * FROM v_bridges_latest WHERE bridge_id=?", (del_id,))
        if df_del.empty:
            df_del = query_df(
                "SELECT b.bridge_code, b.bridge_name, b.built_year, b.bridge_length "
                "FROM bridges b WHERE b.bridge_id=?", (del_id,))
        b_del = df_del.iloc[0]

        # 橋梁プレビュー
        st.markdown(f"""
<div style="background:white;border-radius:10px;padding:1rem 1.4rem;
            border-left:5px solid #dc2626;box-shadow:0 1px 4px rgba(0,0,0,0.08);
            margin-bottom:1rem">
  <div style="font-size:0.8rem;color:#64748b">{b_del.get('bridge_code','-')}</div>
  <div style="font-size:1.2rem;font-weight:700;color:#1e293b">{b_del.get('bridge_name','-')}</div>
  <div style="font-size:0.82rem;color:#64748b;margin-top:0.3rem">
    架設 {b_del.get('built_year','-')} 年　橋長 {b_del.get('bridge_length','-')} m
  </div>
</div>
""", unsafe_allow_html=True)

        # 関連データ件数
        insp_cnt = query_df("SELECT COUNT(*) as c FROM inspections WHERE bridge_id=?", (del_id,))["c"].values[0]
        rep_cnt  = query_df("SELECT COUNT(*) as c FROM repairs      WHERE bridge_id=?", (del_id,))["c"].values[0]
        ph_cnt   = query_df("SELECT COUNT(*) as c FROM photos        WHERE bridge_id=?", (del_id,))["c"].values[0]
        doc_cnt  = query_df("SELECT COUNT(*) as c FROM documents     WHERE bridge_id=?", (del_id,))["c"].values[0]

        st.markdown(f"""
<div style="background:#f8fafc;border-radius:8px;padding:0.8rem 1rem;
            border:1px solid #e2e8f0;font-size:0.82rem;color:#475569;margin-bottom:1rem">
  関連データ：点検 {insp_cnt} 件　補修 {rep_cnt} 件　写真 {ph_cnt} 件　帳票 {doc_cnt} 件
</div>
""", unsafe_allow_html=True)

        col_arch, col_del = st.columns(2)

        # ── アーカイブ（論理削除）─────────────────────
        with col_arch:
            st.markdown("#### 📦 アーカイブ")
            st.caption("is_active を 0 にします。データは保持され、一覧から非表示になります。")
            if is_active == 1:
                if st.button("📦 アーカイブする", key="btn_archive", use_container_width=True):
                    con.execute("UPDATE bridges SET is_active=0, updated_at=datetime('now','localtime') WHERE bridge_id=?", (del_id,))
                    con.commit()
                    st.success(f"「{b_del.get('bridge_name')}」をアーカイブしました。")
                    st.rerun()
            else:
                if st.button("♻️ アーカイブを解除する", key="btn_restore", use_container_width=True):
                    con.execute("UPDATE bridges SET is_active=1, updated_at=datetime('now','localtime') WHERE bridge_id=?", (del_id,))
                    con.commit()
                    st.success(f"「{b_del.get('bridge_name')}」を復元しました。")
                    st.rerun()

        # ── 完全削除（物理削除）──────────────────────
        with col_del:
            st.markdown("#### ⛔ 完全削除")
            st.caption("橋梁と関連する点検・補修・写真・帳票データをすべて削除します。この操作は取り消せません。")
            confirm = st.text_input(
                f"確認のため管理番号「{b_del.get('bridge_code')}」を入力",
                key="del_confirm", placeholder="管理番号を入力")
            del_files = st.checkbox("ストレージフォルダも削除する", key="del_files")
            if st.button("⛔ 完全削除を実行", key="btn_delete",
                         use_container_width=True, type="primary"):
                if confirm.strip() != str(b_del.get("bridge_code", "")):
                    st.error("管理番号が一致しません。")
                else:
                    try:
                        con.execute("DELETE FROM bridges WHERE bridge_id=?", (del_id,))
                        con.commit()
                        if del_files:
                            import shutil as _shutil
                            bd_path = STORAGE_ROOT / str(b_del.get("bridge_code", ""))
                            if bd_path.exists():
                                _shutil.rmtree(bd_path)
                        st.success(f"「{b_del.get('bridge_name')}」を完全削除しました。")
                        st.rerun()
                    except Exception as e:
                        st.error(f"削除に失敗しました: {e}")


# ──────────────────────────────────────────────────────────
# 6. 地図（旧: 地図・一覧）
# ──────────────────────────────────────────────────────────
elif page == "🗺️ 地図":
    page_header("🗺️ 橋梁位置図", "地図上の位置確認と橋梁の検索・ダウンロード")

    # フィルター
    st.markdown('<div class="filter-bar">', unsafe_allow_html=True)
    col_f1, col_f2, col_f3 = st.columns(3)
    with col_f1:
        rank_filter = st.multiselect("健全性ランクで絞り込み",
            ["I", "II", "III", "IV"], default=["I", "II", "III", "IV"])
    with col_f2:
        routes = query_df("SELECT route_name FROM routes ORDER BY route_name")["route_name"].tolist()
        route_filter = st.selectbox("路線で絞り込み", ["（すべて）"] + routes)
    with col_f3:
        keyword = st.text_input("橋名で検索", placeholder="例: 桜橋")
    st.markdown('</div>', unsafe_allow_html=True)

    placeholders = ", ".join("?" * len(rank_filter)) if rank_filter else "''"
    params: list = list(rank_filter)
    sql = f"SELECT * FROM v_bridges_latest WHERE current_health_rank IN ({placeholders})"
    if route_filter != "（すべて）":
        sql += " AND route_name = ?"
        params.append(route_filter)
    if keyword:
        sql += " AND (bridge_name LIKE ? OR bridge_name_kana LIKE ?)"
        params += [f"%{keyword}%", f"%{keyword}%"]
    sql += " ORDER BY bridge_code"
    df = query_df(sql, tuple(params))

    # 地図
    if not df.empty and df["latitude"].notna().any():
        section_header("📍", "橋梁位置図")
        center_lat = df["latitude"].dropna().mean()
        center_lon = df["longitude"].dropna().mean()
        m = folium.Map(location=[center_lat, center_lon], zoom_start=14,
                       tiles="CartoDB positron")
        for _, r in df.iterrows():
            if pd.isna(r["latitude"]):
                continue
            color = RANK_COLOR.get(r["current_health_rank"], "#6c757d")
            gmap  = gmaps_url(r["latitude"], r["longitude"])
            gmap_link = f'<a href="{gmap}" target="_blank">📍 Googleマップで開く</a>' if gmap else ""
            popup_html = f"""
<div style="font-family:sans-serif;font-size:13px;line-height:1.6">
<b style="font-size:14px">{r['bridge_code']} {r['bridge_name']}</b><br>
<span style="color:#666">所在地:</span> {r['location_name'] or '-'}<br>
<span style="color:#666">路線:</span> {r['route_name'] or '-'}<br>
<span style="color:#666">架設:</span> {r['built_year'] or '-'} 年
<span style="color:#666">橋長:</span> {r['bridge_length'] or '-'} m<br>
<span style="color:#666">最終点検:</span> {r['last_inspection_date'] or '未点検'}<br>
{gmap_link}
</div>"""
            folium.CircleMarker(
                location=[r["latitude"], r["longitude"]],
                radius=11, color=color, fill=True,
                fill_color=color, fill_opacity=0.85,
                popup=folium.Popup(popup_html, max_width=260),
                tooltip=f"{r['bridge_code']} {r['bridge_name']}（ランク{r['current_health_rank']}）",
            ).add_to(m)
        legend_html = """
<div style="position:fixed;bottom:30px;left:30px;z-index:1000;
            background:white;padding:10px 14px;border-radius:8px;
            border:1px solid #e2e8f0;font-size:12px;font-family:sans-serif;
            box-shadow:0 2px 8px rgba(0,0,0,0.12);">
<b style="color:#1e293b">健全性ランク</b><br>
<span style="color:#16a34a">●</span> I : 健全<br>
<span style="color:#d97706">●</span> II : 予防保全<br>
<span style="color:#ea580c">●</span> III : 早期措置<br>
<span style="color:#dc2626">●</span> IV : 緊急措置
</div>"""
        m.get_root().html.add_child(folium.Element(legend_html))
        st_folium(m, width=None, height=480, use_container_width=True)
    else:
        st.info("表示できる位置情報のある橋梁がありません。")

    st.markdown("<br>", unsafe_allow_html=True)
    section_header("📋", f"橋梁一覧（{len(df)}件）")
    df_list = df.copy()
    df_list["googleマップ"] = df_list.apply(lambda r: gmaps_url(r["latitude"], r["longitude"]), axis=1)
    display_cols = {
        "bridge_code": "管理番号", "bridge_name": "橋名", "route_name": "路線名",
        "location_name": "所在地", "built_year": "架設年",
        "bridge_length": "橋長(m)", "bridge_width": "幅員(m)",
        "superstructure_type": "上部工", "current_health_rank": "ランク",
        "last_inspection_date": "最終点検日", "googleマップ": "Googleマップ",
    }
    st.dataframe(
        df_list[list(display_cols.keys())].rename(columns=display_cols),
        column_config={"Googleマップ": st.column_config.LinkColumn("Googleマップ", display_text="地図で開く")},
        hide_index=True, use_container_width=True,
    )
    st.download_button("⬇ CSVダウンロード", df.to_csv(index=False).encode("utf-8-sig"),
                       "bridges.csv", "text/csv")


# ──────────────────────────────────────────────────────────
# 3. 橋梁詳細
# ──────────────────────────────────────────────────────────
elif page == "🔍 橋梁詳細":
    page_header("🔍 橋梁詳細情報", "橋梁を選択して基本情報・点検・補修・ファイルを確認")

    codes = query_df(
        "SELECT bridge_code || ' ' || bridge_name AS label, bridge_id "
        "FROM bridges WHERE is_active=1 ORDER BY bridge_code"
    )
    if codes.empty:
        st.warning("橋梁データがありません。")
        st.stop()

    selected_label = st.selectbox("橋梁を選択", codes["label"].tolist(),
                                  label_visibility="collapsed")
    bridge_id = int(codes.loc[codes["label"] == selected_label, "bridge_id"].values[0])

    df_b = query_df("SELECT * FROM v_bridges_latest WHERE bridge_id=?", (bridge_id,))
    if df_b.empty:
        st.error("橋梁情報が見つかりません。")
        st.stop()
    b = df_b.iloc[0]

    # 橋梁ヒーロー
    rank_color  = RANK_COLOR.get(b["current_health_rank"], "#6c757d")
    rank_bg     = RANK_BG.get(b["current_health_rank"], "#f8fafc")
    gmap        = gmaps_url(b["latitude"], b["longitude"])
    gmap_btn    = f'<a href="{gmap}" target="_blank" style="font-size:0.8rem;color:#2563eb;text-decoration:none;border:1px solid #bfdbfe;border-radius:6px;padding:3px 10px;background:#eff6ff;">🗺️ Googleマップ</a>' if gmap else ""
    st.markdown(f"""
<div class="bridge-hero">
  <div style="font-size:2.2rem">🌉</div>
  <div style="flex:1">
    <div class="bh-code">{b['bridge_code']}　{b['route_name'] or ''}</div>
    <div class="bh-name">{b['bridge_name']}</div>
    <div style="margin-top:0.4rem;display:flex;align-items:center;gap:0.6rem;flex-wrap:wrap">
      {rank_badge(b['current_health_rank'])}
      <span style="font-size:0.8rem;color:#64748b">📍 {b['location_name'] or '-'}</span>
      <span style="font-size:0.8rem;color:#64748b">🏗 {b['built_year'] or '-'} 年架設</span>
      {gmap_btn}
    </div>
  </div>
</div>
""", unsafe_allow_html=True)

    bridge_code  = b["bridge_code"]
    photos_dir   = STORAGE_ROOT / bridge_code / "photos"
    forms_dir    = STORAGE_ROOT / bridge_code / "forms"
    drawings_dir = STORAGE_ROOT / bridge_code / "drawings"
    photos_dir.mkdir(parents=True, exist_ok=True)
    forms_dir.mkdir(parents=True, exist_ok=True)
    drawings_dir.mkdir(parents=True, exist_ok=True)

    tab1, tab2, tab3, tab4 = st.tabs(["📋 基本情報", "🔬 点検履歴", "🔧 補修履歴", "📁 ファイル管理"])

    with tab1:
        col_a, col_b = st.columns(2)
        with col_a:
            section_header("📌", "基本情報")
            rows_a = [
                ("路線名", b["route_name"] or "-"),
                ("管理者", b["manager_name"] or "-"),
                ("所在地", b["location_name"] or "-"),
                ("架設年", f"{b['built_year']} 年" if b["built_year"] else "-"),
                ("上部工形式", b["superstructure_type"] or "-"),
                ("下部工形式", b["substructure_type"] or "-"),
            ]
            rows_html = "".join(
                f'<tr><td style="padding:6px 10px;color:#64748b;font-size:0.82rem;white-space:nowrap">{k}</td>'
                f'<td style="padding:6px 10px;color:#1e293b;font-size:0.85rem;font-weight:500">{v}</td></tr>'
                for k, v in rows_a
            )
            st.markdown(f'<table style="width:100%;border-collapse:collapse;background:white;border-radius:8px;overflow:hidden;box-shadow:0 1px 3px rgba(0,0,0,0.07)">{rows_html}</table>', unsafe_allow_html=True)
            if gmap:
                st.markdown("<br>", unsafe_allow_html=True)
                st.link_button("🗺️ Googleマップで現地確認", gmap)

        with col_b:
            section_header("📐", "諸元")
            rows_b = [
                ("橋長", f"{b['bridge_length']} m" if b["bridge_length"] else "-"),
                ("幅員", f"{b['bridge_width']} m" if b["bridge_width"] else "-"),
                ("径間数", str(b["span_count"]) if b.get("span_count") else "-"),
                ("主要材料", b["material"] if b.get("material") else "-"),
            ]
            if b["latitude"] and b["longitude"]:
                rows_b += [
                    ("緯度", str(b["latitude"])),
                    ("経度", str(b["longitude"])),
                ]
            rows_html2 = "".join(
                f'<tr><td style="padding:6px 10px;color:#64748b;font-size:0.82rem;white-space:nowrap">{k}</td>'
                f'<td style="padding:6px 10px;color:#1e293b;font-size:0.85rem;font-weight:500">{v}</td></tr>'
                for k, v in rows_b
            )
            st.markdown(f'<table style="width:100%;border-collapse:collapse;background:white;border-radius:8px;overflow:hidden;box-shadow:0 1px 3px rgba(0,0,0,0.07)">{rows_html2}</table>', unsafe_allow_html=True)

        if b["latitude"] and b["longitude"]:
            st.markdown("<br>", unsafe_allow_html=True)
            m2 = folium.Map(location=[b["latitude"], b["longitude"]], zoom_start=16,
                            tiles="CartoDB positron")
            folium.Marker(
                [b["latitude"], b["longitude"]],
                popup=folium.Popup(
                    f'<b>{b["bridge_name"]}</b><br>{b["location_name"] or ""}<br>'
                    f'<a href="{gmap}" target="_blank">Googleマップで開く</a>',
                    max_width=200),
                tooltip=f"{b['bridge_name']}",
                icon=folium.Icon(color="blue", icon="info-sign"),
            ).add_to(m2)
            st_folium(m2, width=None, height=300, use_container_width=True)

    with tab2:
        df_insp = query_df(
            """SELECT inspection_date, inspection_type, health_rank,
                      countermeasure_type, overall_judgment, inspector_name,
                      inspector_org, estimated_cost
               FROM inspections WHERE bridge_id=? ORDER BY inspection_date DESC""",
            (bridge_id,),
        )
        if df_insp.empty:
            st.info("点検履歴がありません。")
        else:
            for _, row in df_insp.iterrows():
                rank   = row["health_rank"]
                cm     = COUNTERMEASURE_LABEL.get(row["countermeasure_type"], row["countermeasure_type"] or "-")
                cost   = f"補修概算: {row['estimated_cost']:,} 千円" if row["estimated_cost"] else ""
                st.markdown(f"""
<div class="insp-card rank-{rank}-border">
  <div class="ic-date">📅 {row['inspection_date']}　{row['inspection_type']}</div>
  <div class="ic-title" style="display:flex;align-items:center;gap:0.5rem">
    {rank_badge(rank)}
    <span style="font-size:0.85rem;color:#475569">{cm}</span>
  </div>
  <div class="ic-body">{row['overall_judgment'] or '-'}</div>
  <div class="ic-meta">
    点検機関: {row['inspector_org'] or '-'}　｜
    点検者: {row['inspector_name'] or '-'}
    {'　｜　' + cost if cost else ''}
  </div>
</div>
""", unsafe_allow_html=True)

    with tab3:
        df_rep = query_df(
            """SELECT repair_date, repair_type, description,
                      contractor_name, cost, warranty_until
               FROM repairs WHERE bridge_id=? ORDER BY repair_date DESC""",
            (bridge_id,),
        )
        if df_rep.empty:
            st.info("補修履歴がありません。")
        else:
            st.dataframe(
                df_rep.rename(columns={
                    "repair_date": "補修日", "repair_type": "補修種別",
                    "description": "内容", "contractor_name": "施工業者",
                    "cost": "費用(千円)", "warranty_until": "保証期限",
                }),
                hide_index=True, use_container_width=True,
            )

    with tab4:
        _tab_files(bridge_id, bridge_code, photos_dir, forms_dir, drawings_dir)


# ──────────────────────────────────────────────────────────
# 4. 点検記録入力
# ──────────────────────────────────────────────────────────
elif page == "📋 点検記録入力":
    page_header("📋 点検記録入力", "点検結果を入力してデータベースに登録します")

    con = get_connection()
    codes = query_df(
        "SELECT bridge_code || ' ' || bridge_name AS label, bridge_id "
        "FROM bridges WHERE is_active=1 ORDER BY bridge_code"
    )
    selected = st.selectbox("対象橋梁を選択", codes["label"].tolist())
    bridge_id = int(codes.loc[codes["label"] == selected, "bridge_id"].values[0])

    st.markdown("<br>", unsafe_allow_html=True)
    with st.form("inspection_form"):
        section_header("📝", "点検基本情報")
        col1, col2 = st.columns(2)
        with col1:
            insp_date      = st.date_input("点検年月日")
            insp_type      = st.selectbox("点検種別", ["定期", "緊急", "初回"])
            health_rank    = st.selectbox("健全性ランク", ["I", "II", "III", "IV"],
                                          format_func=lambda x: RANK_LABEL[x])
            countermeasure = st.selectbox("措置区分", ["A", "B", "C", "D", "E"],
                                          format_func=lambda x: COUNTERMEASURE_LABEL[x])
            access_method  = st.selectbox("点検足場", ACCESS_METHOD_LIST)
        with col2:
            inspector_name = st.text_input("点検者氏名")
            inspector_org  = st.text_input("点検機関名")
            next_year      = st.number_input("次回点検推奨年", min_value=2020, max_value=2100, value=2029)
            est_cost       = st.number_input("補修概算費用（千円）", min_value=0, value=0)

        st.markdown("<br>", unsafe_allow_html=True)
        section_header("💬", "所見・損傷状況")
        overall = st.text_area("総合所見", height=100)
        dmg_sub = st.text_area("下部工損傷状況", height=80)

        st.markdown("<br>", unsafe_allow_html=True)
        submitted = st.form_submit_button("✅ 点検記録を登録する", type="primary", use_container_width=True)

    if submitted:
        try:
            con.execute(
                """INSERT INTO inspections
                   (bridge_id, inspection_date, inspection_type, inspector_name,
                    inspector_org, health_rank, overall_judgment,
                    damage_superstructure, damage_substructure,
                    countermeasure_type, next_inspection_year, estimated_cost,
                    access_method)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (bridge_id, str(insp_date), insp_type, inspector_name,
                 inspector_org, health_rank, overall, None, dmg_sub,
                 countermeasure, next_year, est_cost, access_method),
            )
            con.execute(
                "UPDATE bridges SET current_health_rank=?, updated_at=datetime('now','localtime') WHERE bridge_id=?",
                (health_rank, bridge_id),
            )
            new_insp_id = con.execute("SELECT last_insert_rowid()").fetchone()[0]
            con.execute(
                "UPDATE bridges SET current_health_rank=?, updated_at=datetime('now','localtime') WHERE bridge_id=?",
                (health_rank, bridge_id),
            )
            con.commit()
            st.session_state["last_insp_id"]        = new_insp_id
            st.session_state["last_insp_bridge_id"] = bridge_id
            st.success(f"✅ 点検記録を登録しました（{selected} / {insp_date}）")
            st.cache_resource.clear()
        except Exception as e:
            st.error(f"登録に失敗しました: {e}")

    # ── 点検調書アップロード（登録直後に表示）─────────────
    if (st.session_state.get("last_insp_bridge_id") == bridge_id
            and "last_insp_id" in st.session_state):
        insp_id       = st.session_state["last_insp_id"]
        b_code_row    = query_df("SELECT bridge_code FROM bridges WHERE bridge_id=?", (bridge_id,))
        b_code        = b_code_row["bridge_code"].values[0] if not b_code_row.empty else "unknown"
        f_dir         = STORAGE_ROOT / b_code / "forms"
        f_dir.mkdir(parents=True, exist_ok=True)

        st.markdown("<br>", unsafe_allow_html=True)
        section_header("📄", "点検調書概要版のアップロード・表示")
        st.caption(f"登録した点検記録（ID: {insp_id}）に点検調書概要版ファイルを添付します")

        FILE_ICONS_INP = {".pdf":"📕",".xlsx":"📗",".xls":"📗",".docx":"📘",".doc":"📘"}
        up_chosho = st.file_uploader(
            "点検調書・添付ファイル（PDF / Excel / Word）",
            type=["pdf","xlsx","xls","docx","doc"],
            accept_multiple_files=True,
            key=f"chosho_{insp_id}",
        )
        chosho_desc = st.text_input("説明（任意）", key=f"chosho_desc_{insp_id}")

        if st.button("📤 点検調書を保存", key=f"chosho_save_{insp_id}", type="primary") and up_chosho:
            saved = 0
            for uf in up_chosho:
                safe_name = _safe_filename(uf.name)
                data = uf.getvalue()
                (f_dir / safe_name).write_bytes(data)
                rel_path = f"bridges/{b_code}/forms/{safe_name}"
                con.execute(
                    "INSERT INTO documents (bridge_id, inspection_id, doc_path, "
                    "file_name, doc_type, file_size, description, uploaded_at) "
                    "VALUES (?,?,?,?,?,?,?,datetime('now','localtime'))",
                    (bridge_id, insp_id, rel_path, safe_name,
                     "点検調書", len(data), chosho_desc or None),
                )
                saved += 1
            con.commit()
            st.success(f"✅ {saved}件の点検調書を保存しました")

        # 登録済み調書一覧
        db_chosho = query_df(
            "SELECT doc_id, file_name, doc_type, file_size, uploaded_at "
            "FROM documents WHERE inspection_id=? ORDER BY uploaded_at DESC", (insp_id,))
        if not db_chosho.empty:
            st.caption(f"この点検に添付済み: {len(db_chosho)}件")
            for _, row in db_chosho.iterrows():
                icon = FILE_ICONS_INP.get(Path(row["file_name"]).suffix.lower(), "📎")
                size_kb = f"{row['file_size'] // 1024} KB" if row["file_size"] else "-"
                fp = f_dir / row["file_name"]
                c1, c2 = st.columns([4, 1])
                c1.markdown(f"{icon} **{row['file_name']}**　{size_kb}　_{row['uploaded_at'] or ''}_")
                if fp.exists():
                    c2.download_button("⬇ DL", fp.read_bytes(),
                        file_name=row["file_name"], key=f"dl_chosho_{row['doc_id']}")
