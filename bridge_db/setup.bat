@echo off
chcp 65001 > nul
echo.
echo ========================================
echo  橋梁管理システム セットアップ
echo ========================================
echo.

:: Python確認
python --version > nul 2>&1
if %errorlevel% neq 0 (
    echo [エラー] Python が見つかりません。
    echo https://www.python.org/downloads/ からインストールしてください。
    echo インストール時に「Add Python to PATH」にチェックを入れてください。
    pause
    exit /b 1
)
for /f "tokens=*" %%i in ('python --version') do echo [OK] %%i を検出

:: ライブラリインストール
echo.
echo [1/3] 必要なライブラリをインストールしています...
pip install -r requirements.txt -q
if %errorlevel% neq 0 (
    echo [エラー] インストールに失敗しました。
    pause
    exit /b 1
)
echo [OK] ライブラリのインストール完了

:: データベース作成
echo.
echo [2/3] データベースを初期化しています...
if not exist "data\bridges.db" (
    python scripts\generate_dummy_data.py
    if %errorlevel% neq 0 (
        echo [エラー] データベースの作成に失敗しました。
        pause
        exit /b 1
    )
    echo [OK] データベースを作成しました
) else (
    echo [スキップ] データベースは既に存在します
)

:: ストレージフォルダ作成
echo.
echo [3/3] ストレージフォルダを初期化しています...
python scripts\init_storage.py
echo [OK] フォルダ構造を作成しました

echo.
echo ========================================
echo  セットアップ完了！
echo  start.bat でシステムを起動できます
echo ========================================
echo.
pause
