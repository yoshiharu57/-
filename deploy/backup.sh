#!/usr/bin/env bash
#
# 橋梁管理システム バックアップ
#
#   sudo bash backup.sh              → /var/backups/bridge に保存
#   sudo bash backup.sh /mnt/usb     → 保存先を指定
#
# データベースと添付ファイル（写真・PDF）をまとめて保存します。
# 古いバックアップは30日で自動削除されます。
#
set -euo pipefail

APP_HOME="${APP_HOME:-/opt/bridge-app/bridge_db}"
DEST="${1:-${DEST:-/var/backups/bridge}}"
KEEP_DAYS="${KEEP_DAYS:-30}"
STAMP="$(date +%Y%m%d_%H%M%S)"
OUT="$DEST/bridge_$STAMP.tar.gz"

ok()  { printf '  \033[1;32m✓\033[0m %s\n' "$*"; }
die() { printf '\033[1;31m✗ %s\033[0m\n' "$*" >&2; exit 1; }

[ -f "$APP_HOME/data/bridges.db" ] || die "データベースが見つかりません: $APP_HOME/data/bridges.db"
mkdir -p "$DEST"

printf '\n\033[1;36m▶ バックアップを作成します\033[0m\n'

# SQLite は書き込み中でも安全にコピーできる .backup を使う
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
sqlite3 "$APP_HOME/data/bridges.db" ".backup '$TMP/bridges.db'" 2>/dev/null \
  || cp "$APP_HOME/data/bridges.db" "$TMP/bridges.db"
ok "データベースを取得しました"

tar -czf "$OUT" -C "$TMP" bridges.db -C "$APP_HOME" storage 2>/dev/null
ok "$OUT に保存しました（$(du -h "$OUT" | cut -f1)）"

DELETED="$(find "$DEST" -name 'bridge_*.tar.gz' -mtime "+$KEEP_DAYS" -print -delete | wc -l)"
[ "$DELETED" -gt 0 ] && ok "${KEEP_DAYS}日より古いバックアップ ${DELETED}件を削除しました"

cat <<EOF

  保存済みバックアップ（新しい順）
$(ls -1t "$DEST"/bridge_*.tar.gz 2>/dev/null | head -5 | sed 's/^/    /')

  復元するには
    systemctl stop bridge
    tar -xzf $OUT -C /tmp
    cp /tmp/bridges.db $APP_HOME/data/bridges.db
    cp -r /tmp/storage $APP_HOME/
    systemctl start bridge

EOF
