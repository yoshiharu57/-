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

echo ブラウザで自動的に開きます...
echo 終了するにはこのウィンドウを閉じるか Ctrl+C を押してください。
echo.

streamlit run app.py --server.port 8501 --browser.gatherUsageStats false
