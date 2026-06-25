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

# Streamlit Cloud は /mount/src/ が読み取り専用のため書き込み可能パスを選択
def _resolve_db_path() -> Path:
    candidate = Path(__file__).parent / "data" / "bridges.db"
    try:
        candidate.parent.mkdir(parents=True, exist_ok=True)
        _t = candidate.parent / ".write_test"
        _t.write_text("x", encoding="utf-8")
        _t.unlink()
        return candidate
    except (PermissionError, OSError):
        p = Path("/tmp") / "bridge_db" / "bridges.db"
        p.parent.mkdir(parents=True, exist_ok=True)
        return p


DB_PATH      = _resolve_db_path()
STORAGE_ROOT = Path(__file__).parent / "storage" / "bridges"