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
    "I":   "#28a745",  # 緑 : 健全
    "II":  "#ffc107",  # 黄 : 予防保全段階
    "III": "#fd7e14",  # 橙 : 早期措置段階
    "IV":  "#dc3545",  # 赤 : 緊急措置段階
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


def gmaps_url(lat, lon) -> str | None:
    """緯度経度からGoogleマップURLを生成する"""
    if lat and lon:
        return f"https://www.google.com/maps?q={lat},{lon}&z=17"
    return None


# ──────────────────────────────────────────────────────────
# DB ユーティリティ
# ──────────────────────────────────────────────────────────
@st.cache_resource
def get_connection():
    if not DB_PATH.exists():
        st.error(f"データベースが見つかりません: {DB_PATH}\n"
                 "先に `python scripts/generate_dummy_data.py` を実行してください。")
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
    """ファイル名からパス区切りなどの危険文字を除去する"""
    return Path(name).name.replace("..", "").replace("/", "").replace("\\", "")


def _insp_options(bridge_id: int) -> list[str]:
    df = query_df(
        "SELECT inspection_id, inspection_date, inspection_type FROM inspections "
        "WHERE bridge_id=? ORDER BY inspection_date DESC",
        (bridge_id,),
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
    """📁 ファイル管理タブの描画"""
    con = get_connection()

    st.caption(
        f"📂 ストレージ: `storage/bridges/{bridge_code}/`　"
        f"（photos/ と forms/ に直接ファイルを置くことも可能です）"
    )

    sec_photo, sec_form = st.columns(2)

    # ── 写真データ ──────────────────────────────────────────
    with sec_photo:
        st.subheader("📷 写真データ")

        with st.expander("＋ 写真を追加", expanded=False):
            up_photo = st.file_uploader(
                "写真ファイル（JPG/PNG）",
                type=["jpg", "jpeg", "png", "webp"],
                accept_multiple_files=True,
                key=f"up_photo_{bridge_id}",
            )
            p_type = st.selectbox("写真種別", PHOTO_TYPES_LIST, key=f"pt_{bridge_id}")
            p_desc = st.text_input("説明（任意）", key=f"pd_{bridge_id}")
            p_date = st.date_input("撮影日", key=f"pdate_{bridge_id}")
            insp_opts = _insp_options(bridge_id)
            p_insp = st.selectbox("関連点検（任意）", ["なし"] + insp_opts, key=f"pi_{bridge_id}")

            if st.button("写真を保存", key=f"pbtn_{bridge_id}") and up_photo:
                for uf in up_photo:
                    safe_name = _safe_filename(uf.name)
                    (photos_dir / safe_name).write_bytes(uf.getvalue())
                    rel_path = f"bridges/{bridge_code}/photos/{safe_name}"
                    iid = _insp_id_from_label(bridge_id, p_insp)
                    con.execute(
                        "INSERT INTO photos (bridge_id, inspection_id, photo_path, "
                        "file_name, photo_type, description, taken_at) "
                        "VALUES (?,?,?,?,?,?,?)",
                        (bridge_id, iid, rel_path, safe_name, p_type, p_desc or None, str(p_date)),
                    )
                con.commit()
                st.success(f"{len(up_photo)}件の写真を保存しました")
                st.rerun()

        db_photos = query_df(
            "SELECT photo_id, photo_path, file_name, photo_type, description, taken_at "
            "FROM photos WHERE bridge_id=? ORDER BY taken_at DESC",
            (bridge_id,),
        )
        disk_photos = [p for p in sorted(photos_dir.glob("*"))
                       if p.suffix.lower() in PHOTO_EXTS]

        if not db_photos.empty:
            st.markdown(f"**登録済み写真: {len(db_photos)}件**")
            cols = st.columns(3)
            for i, (_, row) in enumerate(db_photos.iterrows()):
                img_path = STORAGE_ROOT / bridge_code / "photos" / row["file_name"]
                with cols[i % 3]:
                    if img_path.exists():
                        st.image(str(img_path), use_container_width=True)
                    else:
                        st.warning("ファイルなし")
                    st.caption(
                        f"**{row['photo_type'] or '-'}**　{row['taken_at'] or ''}\n\n"
                        f"{row['description'] or ''}"
                    )
                    if img_path.exists():
                        st.download_button(
                            "⬇ DL", img_path.read_bytes(),
                            file_name=row["file_name"], key=f"dphoto_{row['photo_id']}",
                        )
        elif disk_photos:
            st.markdown(f"**フォルダ内の写真: {len(disk_photos)}件**（DB未登録）")
            cols = st.columns(3)
            for i, p in enumerate(disk_photos):
                with cols[i % 3]:
                    st.image(str(p), use_container_width=True)
                    st.caption(p.name)
        else:
            st.info("写真はまだ登録されていません。")

    # ── 調査様式・帳票 ─────────────────────────────────────
    with sec_form:
        st.subheader("📄 調査様式・帳票")
        FILE_ICONS = {
            ".pdf": "📕", ".xlsx": "📗", ".xls": "📗",
            ".docx": "📘", ".doc": "📘", ".csv": "📊",
        }

        with st.expander("＋ ファイルを追加", expanded=False):
            up_doc = st.file_uploader(
                "ファイル（PDF/Excel/Word）",
                type=["pdf", "xlsx", "xls", "docx", "doc", "csv"],
                accept_multiple_files=True,
                key=f"up_doc_{bridge_id}",
            )
            d_type = st.selectbox("種別", DOC_TYPES_LIST, key=f"dt_{bridge_id}")
            d_desc = st.text_input("説明（任意）", key=f"dd_{bridge_id}")
            insp_opts2 = _insp_options(bridge_id)
            d_insp = st.selectbox("関連点検（任意）", ["なし"] + insp_opts2, key=f"di_{bridge_id}")

            if st.button("ファイルを保存", key=f"dbtn_{bridge_id}") and up_doc:
                for uf in up_doc:
                    safe_name = _safe_filename(uf.name)
                    data = uf.getvalue()
                    (forms_dir / safe_name).write_bytes(data)
                    rel_path = f"bridges/{bridge_code}/forms/{safe_name}"
                    iid = _insp_id_from_label(bridge_id, d_insp)
                    con.execute(
                        "INSERT INTO documents (bridge_id, inspection_id, doc_path, "
                        "file_name, doc_type, file_size, description, uploaded_at) "
                        "VALUES (?,?,?,?,?,?,?,datetime('now','localtime'))",
                        (bridge_id, iid, rel_path, safe_name, d_type, len(data), d_desc or None),
                    )
                con.commit()
                st.success(f"{len(up_doc)}件のファイルを保存しました")
                st.rerun()

        db_docs = query_df(
            "SELECT doc_id, doc_path, file_name, doc_type, file_size, description, uploaded_at "
            "FROM documents WHERE bridge_id=? ORDER BY uploaded_at DESC",
            (bridge_id,),
        )
        disk_docs = [p for p in sorted(forms_dir.glob("*"))
                     if p.suffix.lower() in DOC_EXTS]

        if not db_docs.empty:
            st.markdown(f"**登録済みファイル: {len(db_docs)}件**")
            for _, row in db_docs.iterrows():
                f_path = STORAGE_ROOT / bridge_code / "forms" / row["file_name"]
                icon = FILE_ICONS.get(Path(row["file_name"]).suffix.lower(), "📎")
                size_kb = f"{row['file_size'] // 1024} KB" if row["file_size"] else "-"
                c1, c2 = st.columns([4, 1])
                with c1:
                    st.markdown(
                        f"{icon} **{row['file_name']}**　"
                        f"`{row['doc_type'] or '-'}`　{size_kb}　"
                        f"_{row['uploaded_at'] or ''}_"
                    )
                    if row["description"]:
                        st.caption(row["description"])
                with c2:
                    if f_path.exists():
                        st.download_button(
                            "⬇ DL", f_path.read_bytes(),
                            file_name=row["file_name"], key=f"ddoc_{row['doc_id']}",
                        )
                    else:
                        st.caption("⚠ファイルなし")
                st.divider()
        elif disk_docs:
            st.markdown(f"**フォルダ内のファイル: {len(disk_docs)}件**（DB未登録）")
            for p in disk_docs:
                icon = FILE_ICONS.get(p.suffix.lower(), "📎")
                c1, c2 = st.columns([4, 1])
                c1.markdown(f"{icon} {p.name}")
                c2.download_button("⬇ DL", p.read_bytes(), file_name=p.name,
                                   key=f"ddisk_{p.name}")
        else:
            st.info("帳票・調査様式はまだ登録されていません。")


# ──────────────────────────────────────────────────────────
# サイドバー ナビゲーション
# ──────────────────────────────────────────────────────────
st.sidebar.title("🌉 橋梁管理システム")
page = st.sidebar.radio(
    "メニュー",
    ["📊 ダッシュボード", "🗺️ 地図・一覧", "🔍 橋梁詳細", "📋 点検記録入力"],
)

# ──────────────────────────────────────────────────────────
# 1. ダッシュボード
# ──────────────────────────────────────────────────────────
if page == "📊 ダッシュボード":
    st.title("📊 橋梁管理 ダッシュボード")

    df_summary = query_df(
        "SELECT current_health_rank, COUNT(*) as cnt FROM bridges WHERE is_active=1 "
        "GROUP BY current_health_rank ORDER BY current_health_rank"
    )
    total = df_summary["cnt"].sum()

    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("管理橋梁数（総計）", f"{total} 橋")
    for _, row in df_summary.iterrows():
        rank = row["current_health_rank"]
        label = RANK_LABEL.get(rank, rank)
        col = {"I": col2, "II": col3, "III": col4, "IV": col5}.get(rank)
        if col:
            col.metric(label, f"{row['cnt']} 橋")

    st.divider()

    col_l, col_r = st.columns([1, 2])

    with col_l:
        st.subheader("健全性ランク分布")
        chart_data = df_summary.set_index("current_health_rank")["cnt"]
        st.bar_chart(chart_data)

    with col_r:
        st.subheader("緊急・早期措置が必要な橋梁")
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
            st.dataframe(
                df_urgent.rename(columns={
                    "bridge_code": "管理番号",
                    "bridge_name": "橋名",
                    "route_name": "路線名",
                    "current_health_rank": "ランク",
                    "last_inspection_date": "最終点検日",
                    "last_countermeasure": "措置区分",
                }),
                hide_index=True,
                use_container_width=True,
            )

    st.divider()
    st.subheader("直近の点検記録（最新10件）")
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
        hide_index=True,
        use_container_width=True,
    )


# ──────────────────────────────────────────────────────────
# 2. 地図・一覧
# ──────────────────────────────────────────────────────────
elif page == "🗺️ 地図・一覧":
    st.title("🗺️ 橋梁位置図・一覧")

    col_f1, col_f2, col_f3 = st.columns(3)
    with col_f1:
        rank_filter = st.multiselect(
            "健全性ランクで絞り込み",
            ["I", "II", "III", "IV"],
            default=["I", "II", "III", "IV"],
        )
    with col_f2:
        routes = query_df("SELECT route_name FROM routes ORDER BY route_name")["route_name"].tolist()
        route_filter = st.selectbox("路線で絞り込み", ["（すべて）"] + routes)
    with col_f3:
        keyword = st.text_input("橋名で検索", placeholder="例: 桜橋")

    placeholders = ", ".join("?" * len(rank_filter)) if rank_filter else "''"
    params: list = list(rank_filter)
    sql = f"""
        SELECT * FROM v_bridges_latest
        WHERE current_health_rank IN ({placeholders})
    """
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
        center_lat = df["latitude"].dropna().mean()
        center_lon = df["longitude"].dropna().mean()
        m = folium.Map(location=[center_lat, center_lon], zoom_start=14)

        for _, r in df.iterrows():
            if pd.isna(r["latitude"]):
                continue
            color = RANK_COLOR.get(r["current_health_rank"], "#6c757d")
            gmap = gmaps_url(r["latitude"], r["longitude"])
            gmap_link = f'<a href="{gmap}" target="_blank">📍 Googleマップで開く</a>' if gmap else ""
            popup_html = f"""
            <b>{r['bridge_code']} {r['bridge_name']}</b><br>
            所在地: {r['location_name'] or '-'}<br>
            路線: {r['route_name'] or '-'}<br>
            架設: {r['built_year'] or '-'} 年　橋長: {r['bridge_length'] or '-'} m<br>
            ランク: {RANK_LABEL.get(r['current_health_rank'], r['current_health_rank'])}<br>
            最終点検: {r['last_inspection_date'] or '未点検'}<br>
            {gmap_link}
            """
            folium.CircleMarker(
                location=[r["latitude"], r["longitude"]],
                radius=10,
                color=color,
                fill=True,
                fill_color=color,
                fill_opacity=0.9,
                popup=folium.Popup(popup_html, max_width=250),
                tooltip=f"{r['bridge_code']} {r['bridge_name']} (ランク{r['current_health_rank']})",
            ).add_to(m)

        legend_html = """
        <div style="position:fixed;bottom:30px;left:30px;z-index:1000;
                    background:white;padding:10px;border-radius:5px;
                    border:1px solid #aaa;font-size:13px;">
        <b>健全性ランク</b><br>
        <span style="color:#28a745">●</span> I : 健全<br>
        <span style="color:#ffc107">●</span> II : 予防保全<br>
        <span style="color:#fd7e14">●</span> III : 早期措置<br>
        <span style="color:#dc3545">●</span> IV : 緊急措置
        </div>
        """
        m.get_root().html.add_child(folium.Element(legend_html))
        st_folium(m, width=None, height=500, use_container_width=True)
    else:
        st.info("表示できる位置情報のある橋梁がありません。")

    st.divider()
    st.subheader(f"橋梁一覧（{len(df)}件）")

    df_list = df.copy()
    df_list["googleマップ"] = df_list.apply(
        lambda r: gmaps_url(r["latitude"], r["longitude"]), axis=1
    )
    display_cols = {
        "bridge_code": "管理番号", "bridge_name": "橋名", "route_name": "路線名",
        "location_name": "所在地", "built_year": "架設年",
        "bridge_length": "橋長(m)", "bridge_width": "幅員(m)",
        "superstructure_type": "上部工", "current_health_rank": "ランク",
        "last_inspection_date": "最終点検日", "googleマップ": "Googleマップ",
    }
    st.dataframe(
        df_list[list(display_cols.keys())].rename(columns=display_cols),
        column_config={
            "Googleマップ": st.column_config.LinkColumn(
                "Googleマップ",
                display_text="地図で開く",
            ),
        },
        hide_index=True,
        use_container_width=True,
    )

    csv_data = df.to_csv(index=False).encode("utf-8-sig")
    st.download_button("CSVダウンロード", csv_data, "bridges.csv", "text/csv")


# ──────────────────────────────────────────────────────────
# 3. 橋梁詳細
# ──────────────────────────────────────────────────────────
elif page == "🔍 橋梁詳細":
    st.title("🔍 橋梁詳細情報")

    codes = query_df(
        "SELECT bridge_code || ' ' || bridge_name AS label, bridge_id FROM bridges WHERE is_active=1 ORDER BY bridge_code"
    )
    if codes.empty:
        st.warning("橋梁データがありません。")
        st.stop()

    selected_label = st.selectbox("橋梁を選択", codes["label"].tolist())
    bridge_id = int(codes.loc[codes["label"] == selected_label, "bridge_id"].values[0])

    df_b = query_df("SELECT * FROM v_bridges_latest WHERE bridge_id=?", (bridge_id,))
    if df_b.empty:
        st.error("橋梁情報が見つかりません。")
        st.stop()
    b = df_b.iloc[0]

    rank_color = RANK_COLOR.get(b["current_health_rank"], "#6c757d")
    st.markdown(
        f"## {b['bridge_code']}　{b['bridge_name']} "
        f"<span style='background:{rank_color};color:white;padding:2px 10px;"
        f"border-radius:12px;font-size:0.85em;'>"
        f"ランク {b['current_health_rank']}</span>",
        unsafe_allow_html=True,
    )

    bridge_code = b["bridge_code"]
    bridge_dir  = STORAGE_ROOT / bridge_code
    photos_dir  = bridge_dir / "photos"
    forms_dir   = bridge_dir / "forms"
    photos_dir.mkdir(parents=True, exist_ok=True)
    forms_dir.mkdir(parents=True, exist_ok=True)

    tab1, tab2, tab3, tab4 = st.tabs(["基本情報", "点検履歴", "補修履歴", "📁 ファイル管理"])

    with tab1:
        col_a, col_b = st.columns(2)
        with col_a:
            st.markdown("**基本情報**")
            loc_text = b["location_name"] or "-"
            gmap = gmaps_url(b["latitude"], b["longitude"])
            if gmap:
                loc_text += f'　[📍 地図]({gmap})'
            st.table(pd.DataFrame({
                "項目": ["路線名", "管理者", "所在地", "架設年", "上部工形式", "下部工形式"],
                "内容": [
                    b["route_name"] or "-",
                    b["manager_name"] or "-",
                    b["location_name"] or "-",
                    f"{b['built_year']} 年" if b["built_year"] else "-",
                    b["superstructure_type"] or "-",
                    b["substructure_type"] or "-",
                ],
            }))
            if gmap:
                st.markdown(
                    f"📍 所在地: **{b['location_name'] or ''}**　"
                    f"[Googleマップで開く]({gmap}){{target='_blank'}}",
                    unsafe_allow_html=False,
                )
                st.link_button("🗺️ Googleマップで現地確認", gmap)
        with col_b:
            st.markdown("**諸元**")
            st.table(pd.DataFrame({
                "項目": ["橋長", "幅員", "径間数", "主要材料"],
                "内容": [
                    f"{b['bridge_length']} m" if b["bridge_length"] else "-",
                    f"{b['bridge_width']} m" if b["bridge_width"] else "-",
                    "-",
                    "-",
                ],
            }))
            if b["latitude"] and b["longitude"]:
                st.markdown(f"**緯度**: {b['latitude']}　**経度**: {b['longitude']}")
        if b["latitude"] and b["longitude"]:
            m2 = folium.Map(location=[b["latitude"], b["longitude"]], zoom_start=16)
            folium.Marker(
                [b["latitude"], b["longitude"]],
                popup=folium.Popup(
                    f"<b>{b['bridge_name']}</b><br>{b['location_name'] or ''}<br>"
                    f'<a href="{gmap}" target="_blank">Googleマップで開く</a>',
                    max_width=200,
                ),
                tooltip=f"{b['bridge_name']}（クリックで詳細）",
                icon=folium.Icon(color="red", icon="info-sign"),
            ).add_to(m2)
            st_folium(m2, width=None, height=320, use_container_width=True)

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
                with st.expander(
                    f"📅 {row['inspection_date']}　"
                    f"ランク {row['health_rank']}　"
                    f"措置: {COUNTERMEASURE_LABEL.get(row['countermeasure_type'], row['countermeasure_type'] or '-')}"
                ):
                    st.write(f"**点検種別**: {row['inspection_type']}")
                    st.write(f"**点検機関**: {row['inspector_org'] or '-'}")
                    st.write(f"**点検者**: {row['inspector_name'] or '-'}")
                    st.write(f"**総合所見**: {row['overall_judgment'] or '-'}")
                    if row["estimated_cost"]:
                        st.write(f"**補修概算費用**: {row['estimated_cost']:,} 千円")

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
                hide_index=True,
                use_container_width=True,
            )

    with tab4:
        _tab_files(bridge_id, bridge_code, photos_dir, forms_dir)


# ──────────────────────────────────────────────────────────
# 4. 点検記録入力
# ──────────────────────────────────────────────────────────
elif page == "📋 点検記録入力":
    st.title("📋 点検記録入力")

    con = get_connection()
    codes = query_df(
        "SELECT bridge_code || ' ' || bridge_name AS label, bridge_id FROM bridges WHERE is_active=1 ORDER BY bridge_code"
    )
    selected = st.selectbox("対象橋梁", codes["label"].tolist())
    bridge_id = int(codes.loc[codes["label"] == selected, "bridge_id"].values[0])

    with st.form("inspection_form"):
        col1, col2 = st.columns(2)
        with col1:
            insp_date   = st.date_input("点検年月日")
            insp_type   = st.selectbox("点検種別", ["定期", "緊急", "初回"])
            health_rank = st.selectbox("健全性ランク", ["I", "II", "III", "IV"],
                                       format_func=lambda x: RANK_LABEL[x])
            countermeasure = st.selectbox("措置区分", ["A", "B", "C", "D", "E"],
                                          format_func=lambda x: COUNTERMEASURE_LABEL[x])
        with col2:
            inspector_name = st.text_input("点検者氏名")
            inspector_org  = st.text_input("点検機関名")
            next_year      = st.number_input("次回点検推奨年", min_value=2020, max_value=2100,
                                             value=2029)
            est_cost       = st.number_input("補修概算費用（千円）", min_value=0, value=0)

        overall = st.text_area("総合所見")

        st.markdown("**損傷状況**")
        c1, c2 = st.columns(2)
        dmg_super = c1.text_area("上部工損傷状況", height=80)
        dmg_sub   = c2.text_area("下部工損傷状況", height=80)

        submitted = st.form_submit_button("登録する", type="primary")

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
            st.success(f"点検記録を登録しました（{selected} / {insp_date}）")
            st.cache_resource.clear()
        except Exception as e:
            st.error(f"登録に失敗しました: {e}")
