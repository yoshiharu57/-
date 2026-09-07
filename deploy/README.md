# 橋梁管理システム 導入キット

自社サーバー・お客様サーバーへ導入するための一式です。

## 収録内容

| ファイル | 用途 |
|---|---|
| `install.sh` | 自動インストーラ。何度実行しても安全（再実行＝最新版へ更新） |
| `backup.sh` | データベースと添付ファイルのバックアップ |

## 動作環境

- Ubuntu 22.04 LTS または 24.04 LTS（64bit）
- メモリ 1GB 以上（橋梁200件の場合）
- インターネット接続（地図表示に必要）

## 導入手順

サーバーにSSHで接続し、次の3行を実行するだけです。

```bash
git clone -b メイン https://github.com/yoshiharu57/-.git /opt/bridge-app
cd /opt/bridge-app/deploy
sudo bash install.sh
```

完了すると `http://<サーバーのIP>:8501` でアクセスできます。

### 本番導入（サンプルデータを入れない）

お客様へ納品する場合は空のデータベースで開始します。

```bash
sudo EMPTY_DB=1 bash install.sh
```

### 設定を変える

```bash
sudo PORT=8080 bash install.sh      # ポートを変更
sudo APP_DIR=/srv/bridge bash install.sh   # 導入先を変更
```

## 運用コマンド

```bash
systemctl status bridge      # 状態を確認
systemctl restart bridge     # 再起動
journalctl -u bridge -f      # ログを見る
sudo bash install.sh         # 最新版へ更新（データは保持）
```

## バックアップ

```bash
sudo bash backup.sh                  # /var/backups/bridge に保存
sudo bash backup.sh /mnt/usb         # 保存先を指定
```

毎日自動で取得する場合は cron に登録します。

```bash
sudo crontab -e
# 以下の1行を追加（毎日 深夜2時）
0 2 * * * bash /opt/bridge-app/deploy/backup.sh
```

## 注意点

- **地図表示にはインターネット接続が必要です。** OpenStreetMapのタイルと
  Leaflet.js を外部から取得するため、閉域網（LGWAN等）では地図が表示されません。
- 個人情報を扱う場合は、国内データセンターのサーバーをご利用ください。
- 外部公開する場合は HTTPS 化（Nginx + Let's Encrypt）をご検討ください。
