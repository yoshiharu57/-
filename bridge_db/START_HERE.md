# 橋梁管理アプリ 完成版

## 起動方法

Windowsでは、このフォルダ内の `setup.bat` を初回だけ実行し、その後 `start.bat` を実行してください。

手動で起動する場合:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m streamlit run app.py
```

起動後、ブラウザで以下を開きます。

```text
http://localhost:8501
```

## 反映済み内容

- 橋梁管理ダッシュボード
- 橋梁一覧、詳細、地図表示
- 点検記録入力
- 第三者被害の入力項目
- 点検方法への表記変更
- 点検方法プルダウンへの「高所作業者」追加
- SQLiteデータベース同梱
