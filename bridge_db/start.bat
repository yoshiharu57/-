@echo off
chcp 65001 > nul
echo.
echo ========================================
echo  橋梁管理システム 起動中...
echo ========================================
echo.

:: データベース確認
if not exist "data\bridges.db" (
    echo [エラー] データベースが見つかりません。
    echo 先に setup.bat を実行してください。
    pause
    exit /b 1
)

:: このPCのIPアドレスを取得
for /f "tokens=2 delims=:" %%a in ('ipconfig ^| findstr /C:"IPv4" ^| findstr /V "127.0.0.1"') do (
    set RAW_IP=%%a
)
:: 先頭スペースを除去
set LOCAL_IP=%RAW_IP: =%

echo.
echo  ┌─────────────────────────────────────────────┐
echo  │  このPCから開く場合                          │
echo  │    http://localhost:8501                    │
echo  │                                             │
echo  │  iPad・スマホ・他のPCから開く場合             │
if defined LOCAL_IP (
    echo  │    http://%LOCAL_IP%:8501        │
) else (
    echo  │    ※ ネットワーク未接続                    │
)
echo  │                                             │
echo  │  ※ 同じWi-Fi（社内LAN）に接続している必要あり │
echo  └─────────────────────────────────────────────┘
echo.
echo  終了するにはこのウィンドウを閉じるか Ctrl+C を押してください。
echo.

:: 全ネットワークインターフェースで待ち受け（0.0.0.0）
streamlit run app.py ^
    --server.port 8501 ^
    --server.address 0.0.0.0 ^
    --browser.gatherUsageStats false ^
    --server.headless true
