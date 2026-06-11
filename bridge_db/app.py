"""
橋梁管理システム - Streamlit Webアプリ
国土交通省「橋梁定期点検要領」準拠
"""

import sqlite3
import shutil
from pathlib import Path

import folium
import pandas as pd
import streamlit as st
from streamlit_folium import st_folium

DB_PATH      = Path(__file__).parent / "data" / "bridges.db"
STORAGE_ROOT = Path(__file__).parent / "storage" / "bridges"

PHOTO_EXTS = {".jpg", ".jpeg", ".png", ".heic", ".webp"}
DOC_EXTS   = {".pdf", ".xlsx", ".xls", ".docx", ".doc", ".csv"}
PHOTO_TYPES_LIST = ["全景", "損傷", "補修後", "その他"]
DOC_TYPES_LIST   = ["点検調書", "損傷図", "補修設計書", "その他"]

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
}
[data-testid="stSidebar"] * { color: #e2e8f0 !important; }
[data-testid="stSidebar"] .stRadio label { color: #cbd5e1 !important; }
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

/* ── カード ─────────────────────────────────────── */
.metric-card {
    background: white;
    border-radius: 10px;
    padding: 1rem 1.2rem;
    border-left: 5px solid #2563eb;
    box-shadow: 0 1px 4px rgba(0,0,0,0.08);
    height: 100%;
}
.metric-card .mc-label {
    font-size: 0.75rem; font-weight: 500;
    color: #64748b; text-transform: uppercase; letter-spacing: 0.05em;
    margin-bottom: 0.3rem;
}
.metric-card .mc-value {
    font-size: 2rem; font-weight: 700; color: #1e293b; line-height: 1.1;
}
.metric-card .mc-sub {
    font-size: 0.78rem; color: #94a3b8; margin-top: 0.2rem;
}

/* ── セクションヘッダー ─────────────────────────── */
.section-header {
    display: flex; align-items: center; gap: 0.5rem;
    border-bottom: 2px solid #e2e8f0;
    padding-bottom: 0.5rem; margin-bottom: 1rem; margin-top: 0.5rem;
}
.section-header span {
    font-size: 1rem; font-weight: 700; color: #1e293b;
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

/* ── テーブル微調整 ─────────────────────────────── */
[data-testid="stDataFrame"] th {
    background: #f1f5f9 !important; color: #475569 !important;
    font-size: 0.8rem !important; font-weight: 600 !important;
}
[data-testid="stDataFrame"] td { font-size: 0.85rem !important; }

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


def metric_card(label: str, value: str, sub: str = "", color: str = "#2563eb") -> str:
    return f"""
<div class="metric-card" style="border-left-color:{color}">
  <div class="mc-label">{label}</div>
  <div class="mc-value" style="color:{color}">{value}</div>
  <div class="mc-sub">{sub}</div>
</div>"""


def gmaps_url(lat, lon) -> str | None:
    if lat and lon:
        return f"https://www.google.com/maps?q={lat},{lon}&z=17"
    return None


# ──────────────────────────────────────────────────────────
# DB ユーティリティ
# ──────────────────────────────────────────────────────────
@st.cache_resource
def get_connection():
    if not DB_PATH.exists():
        st.error("データベースが見つかりません。先に `python scripts/generate_dummy_data.py` を実行してください。")
        st.stop()
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


def _tab_files(bridge_id: int, bridge_code: str, photos_dir: Path, forms_dir: Path):
    con = get_connection()
    st.caption(f"📂 `storage/bridges/{bridge_code}/`　（photos/ と forms/ に直接置くことも可能）")

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
            "FROM documents WHERE bridge_id=? ORDER BY uploaded_at DESC", (bridge_id,))
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


# ──────────────────────────────────────────────────────────
# CSS 注入 & サイドバー
# ──────────────────────────────────────────────────────────
inject_css()

st.sidebar.markdown("""
<div style="padding:1rem 0.5rem 0.5rem;">
  <div style="font-size:1.4rem; font-weight:800; color:#f1f5f9; letter-spacing:0.02em;">
    🌉 橋梁管理
  </div>
  <div style="font-size:0.72rem; color:#94a3b8; margin-top:0.2rem;">
    Bridge Inspection System
  </div>
</div>
<hr style="border-color:#334155; margin:0.5rem 0 1rem;">
""", unsafe_allow_html=True)

page = st.sidebar.radio(
    "メニュー",
    ["📊 ダッシュボード", "🗺️ 地図・一覧", "🔍 橋梁詳細", "📋 点検記録入力"],
    label_visibility="collapsed",
)

st.sidebar.markdown("""
<hr style="border-color:#334155; margin:1.5rem 0 0.5rem;">
<div style="font-size:0.72rem; color:#475569; padding:0 0.5rem 1rem;">
  国土交通省「橋梁定期点検要領」準拠<br>
  SQLite + Streamlit
</div>
""", unsafe_allow_html=True)


# ──────────────────────────────────────────────────────────
# 1. ダッシュボード
# ──────────────────────────────────────────────────────────
if page == "📊 ダッシュボード":
    page_header("📊 橋梁管理 ダッシュボード", "管理橋梁の健全性状況と点検記録の概要")

    df_summary = query_df(
        "SELECT current_health_rank, COUNT(*) as cnt FROM bridges WHERE is_active=1 "
        "GROUP BY current_health_rank ORDER BY current_health_rank"
    )
    rank_counts = dict(zip(df_summary["current_health_rank"], df_summary["cnt"]))
    total = sum(rank_counts.values())

    # ── メトリクスカード ──────────────────────────────────
    cols = st.columns(5)
    cards = [
        ("管理橋梁数（総計）", f"{total}", "is_active = 1", "#2563eb"),
        ("I : 健全",           f"{rank_counts.get('I', 0)}",   "定期点検・措置不要", RANK_COLOR["I"]),
        ("II : 予防保全段階",   f"{rank_counts.get('II', 0)}",  "監視・予防保全措置", RANK_COLOR["II"]),
        ("III : 早期措置段階",  f"{rank_counts.get('III', 0)}", "早期補修が必要",     RANK_COLOR["III"]),
        ("IV : 緊急措置段階",   f"{rank_counts.get('IV', 0)}",  "緊急補修・通行規制", RANK_COLOR["IV"]),
    ]
    for col, (label, val, sub, color) in zip(cols, cards):
        with col:
            st.markdown(metric_card(label, val + " 橋", sub, color), unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    col_l, col_r = st.columns([1, 2])

    with col_l:
        section_header("📈", "健全性ランク分布")
        chart_df = (
            df_summary
            .rename(columns={"current_health_rank": "ランク", "cnt": "橋梁数"})
            .set_index("ランク")
        )
        st.bar_chart(chart_df, color="#2563eb", height=260)

    with col_r:
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
            for _, r in df_urgent.iterrows():
                is_iv  = r["current_health_rank"] == "IV"
                cls    = "" if is_iv else "warn"
                icon   = "🚨" if is_iv else "⚠️"
                cm     = COUNTERMEASURE_LABEL.get(r["last_countermeasure"], r["last_countermeasure"] or "-")
                date   = r["last_inspection_date"] or "未点検"
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
    section_header("📋", "直近の点検記録（最新10件）")
    df_recent = query_df(
        """SELECT b.bridge_code, b.bridge_name, i.inspection_date,
                  i.health_rank, i.countermeasure_type, i.inspector_name
           FROM inspections i JOIN bridges b ON i.bridge_id = b.bridge_id
           ORDER BY i.inspection_date DESC LIMIT 10"""
    )
    st.dataframe(
        df_recent.rename(columns={
            "bridge_code": "管理番号", "bridge_name": "橋名",
            "inspection_date": "点検日", "health_rank": "ランク",
            "countermeasure_type": "措置", "inspector_name": "点検者",
        }),
        hide_index=True, use_container_width=True,
    )


# ──────────────────────────────────────────────────────────
# 2. 地図・一覧
# ──────────────────────────────────────────────────────────
elif page == "🗺️ 地図・一覧":
    page_header("🗺️ 橋梁位置図・一覧", "地図上の位置確認と橋梁一覧の検索・ダウンロード")

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

    bridge_code = b["bridge_code"]
    photos_dir  = STORAGE_ROOT / bridge_code / "photos"
    forms_dir   = STORAGE_ROOT / bridge_code / "forms"
    photos_dir.mkdir(parents=True, exist_ok=True)
    forms_dir.mkdir(parents=True, exist_ok=True)

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
        _tab_files(bridge_id, bridge_code, photos_dir, forms_dir)


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
        with col2:
            inspector_name = st.text_input("点検者氏名")
            inspector_org  = st.text_input("点検機関名")
            next_year      = st.number_input("次回点検推奨年", min_value=2020, max_value=2100, value=2029)
            est_cost       = st.number_input("補修概算費用（千円）", min_value=0, value=0)

        st.markdown("<br>", unsafe_allow_html=True)
        section_header("💬", "所見・損傷状況")
        overall = st.text_area("総合所見", height=100)
        c1, c2  = st.columns(2)
        dmg_super = c1.text_area("上部工損傷状況", height=80)
        dmg_sub   = c2.text_area("下部工損傷状況", height=80)

        st.markdown("<br>", unsafe_allow_html=True)
        submitted = st.form_submit_button("✅ 点検記録を登録する", type="primary", use_container_width=True)

    if submitted:
        try:
            con.execute(
                """INSERT INTO inspections
                   (bridge_id, inspection_date, inspection_type, inspector_name,
                    inspector_org, health_rank, overall_judgment,
                    damage_superstructure, damage_substructure,
                    countermeasure_type, next_inspection_year, estimated_cost)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                (bridge_id, str(insp_date), insp_type, inspector_name,
                 inspector_org, health_rank, overall, dmg_super, dmg_sub,
                 countermeasure, next_year, est_cost),
            )
            con.execute(
                "UPDATE bridges SET current_health_rank=?, updated_at=datetime('now','localtime') WHERE bridge_id=?",
                (health_rank, bridge_id),
            )
            con.commit()
            st.success(f"✅ 点検記録を登録しました（{selected} / {insp_date}）")
            st.cache_resource.clear()
        except Exception as e:
            st.error(f"登録に失敗しました: {e}")
