#!/bin/bash
# 橋梁管理システム セットアップ（Mac用）
# ダブルクリックで実行できます

export LANG=ja_JP.UTF-8
cd "$(dirname "$0")"

echo ""
echo "========================================"
echo "  橋梁管理システム セットアップ"
echo "========================================"
echo ""

# Python3 確認
if ! command -v python3 &> /dev/null; then
    echo "[エラー] Python3 が見つかりません。"
    echo "https://www.python.org/downloads/ からインストールしてください。"
    echo ""
    read -p "Enterキーを押して終了..."
    exit 1
fi
echo "[OK] $(python3 --version) を検出しました"

# ライブラリインストール
echo ""
echo "[1/2] 必要なライブラリをインストールしています..."
echo "      （数分かかる場合があります）"
python3 -m pip install -r requirements.txt -q
if [ $? -ne 0 ]; then
    echo "[エラー] ライブラリのインストールに失敗しました。"
    echo "         インターネット接続を確認してください。"
    read -p "Enterキーを押して終了..."
    exit 1
fi
echo "[OK] ライブラリのインストール完了"

# データベース作成
echo ""
echo "[2/2] データベースを初期化しています..."
if [ ! -f "data/bridges.db" ]; then
    python3 scripts/generate_dummy_data.py
    if [ $? -ne 0 ]; then
        echo "[エラー] データベースの作成に失敗しました。"
        read -p "Enterキーを押して終了..."
        exit 1
    fi
    echo "[OK] データベースを作成しました"
    python3 scripts/init_storage.py > /dev/null 2>&1
    echo "[OK] ストレージフォルダを作成しました"
else
    echo "[スキップ] データベースは既に存在します"
fi

echo ""
echo "========================================"
echo "  セットアップ完了！"
echo "  start.command でシステムを起動できます"
echo "========================================"
echo ""
read -p "Enterキーを押して終了..."
