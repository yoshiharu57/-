#!/bin/bash
# 橋梁管理システム 起動スクリプト（Mac用）
# ダブルクリックで起動できます

export LANG=ja_JP.UTF-8
cd "$(dirname "$0")"

echo ""
echo "========================================"
echo "  橋梁管理システム 起動中..."
echo "========================================"
echo ""

# データベース確認
if [ ! -f "data/bridges.db" ]; then
    echo "[エラー] データベースが見つかりません。"
    echo "         先に setup.command を実行してください。"
    echo ""
    read -p "Enterキーを押して終了..."
    exit 1
fi

# Streamlit インストール確認
if ! python3 -m streamlit --version &> /dev/null; then
    echo "[エラー] Streamlit が見つかりません。"
    echo "         先に setup.command を実行してください。"
    echo ""
    read -p "Enterキーを押して終了..."
    exit 1
fi

# このMacのIPアドレスを取得（Wi-Fi / 有線LAN）
LOCAL_IP=$(ipconfig getifaddr en0 2>/dev/null || ipconfig getifaddr en1 2>/dev/null)

echo ""
echo " ┌──────────────────────────────────────────────┐"
echo " │                                              │"
echo " │  このMacから開く場合:                         │"
echo " │    http://localhost:8501                     │"
echo " │                                              │"
if [ -n "$LOCAL_IP" ]; then
echo " │  iPad・スマホ・他のPCから開く場合:             │"
echo " │    http://$LOCAL_IP:8501              │"
echo " │                                              │"
fi
echo " │  ※ 同じWi-Fi（社内LAN）に接続している必要あり  │"
echo " │                                              │"
echo " │  終了: このウィンドウを閉じる か Ctrl+C        │"
echo " └──────────────────────────────────────────────┘"
echo ""

# 3秒後にブラウザを自動で開く
sleep 3 && open http://localhost:8501 &

# Streamlit 起動（全ネットワーク待ち受け）
python3 -m streamlit run app.py \
    --server.port 8501 \
    --server.address 0.0.0.0 \
    --browser.gatherUsageStats false \
    --server.headless true
