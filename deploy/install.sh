#!/usr/bin/env bash
#
# 橋梁管理システム 自動インストーラ（Ubuntu 22.04 / 24.04）
#
#   sudo bash install.sh
#
# 何度実行しても安全です（再実行で最新版に更新されます）。
#
# 環境変数で挙動を変えられます:
#   APP_DIR=/opt/bridge-app   インストール先
#   PORT=8501                 待ち受けポート
#   BRANCH=メイン             取得するブランチ
#   EMPTY_DB=1                サンプルデータを入れず空のDBで開始する
#   SKIP_SYSTEM=1             apt / systemd / ufw を行わない（動作確認用）
#
set -euo pipefail

APP_DIR="${APP_DIR:-/opt/bridge-app}"
PORT="${PORT:-8501}"
BRANCH="${BRANCH:-メイン}"
REPO="${REPO:-https://github.com/yoshiharu57/-.git}"
SERVICE="${SERVICE:-bridge}"
EMPTY_DB="${EMPTY_DB:-0}"
SKIP_SYSTEM="${SKIP_SYSTEM:-0}"

APP_HOME="$APP_DIR/bridge_db"
VENV="$APP_HOME/venv"

say()  { printf '\n\033[1;36m▶ %s\033[0m\n' "$*"; }
ok()   { printf '  \033[1;32m✓\033[0m %s\n' "$*"; }
warn() { printf '  \033[1;33m!\033[0m %s\n' "$*"; }
die()  { printf '\n\033[1;31m✗ %s\033[0m\n' "$*" >&2; exit 1; }

# ── 0. 事前確認 ────────────────────────────────────────────
if [ "$SKIP_SYSTEM" != "1" ] && [ "$(id -u)" -ne 0 ]; then
  die "root権限が必要です。  sudo bash install.sh  で実行してください。"
fi

# ── 1. 必要なパッケージ ────────────────────────────────────
if [ "$SKIP_SYSTEM" = "1" ]; then
  say "システムパッケージの導入をスキップします"
else
  say "システムパッケージを導入します（数分かかります）"
  export DEBIAN_FRONTEND=noninteractive
  apt-get update -qq
  apt-get install -y -qq python3 python3-pip python3-venv git >/dev/null
  ok "python3 / git を導入しました"
  timedatectl set-timezone Asia/Tokyo 2>/dev/null && ok "タイムゾーンを Asia/Tokyo にしました" || true
fi

command -v git >/dev/null     || die "git が見つかりません"
command -v python3 >/dev/null || die "python3 が見つかりません"

# ── 2. ソースコードの取得 ──────────────────────────────────
say "システム本体を取得します"
if [ -d "$APP_DIR/.git" ]; then
  git -C "$APP_DIR" fetch --quiet origin "$BRANCH"
  git -C "$APP_DIR" checkout --quiet "$BRANCH"
  git -C "$APP_DIR" reset --hard --quiet "origin/$BRANCH"
  ok "既存のインストールを最新版に更新しました"
else
  mkdir -p "$(dirname "$APP_DIR")"
  git clone --quiet --branch "$BRANCH" --depth 1 "$REPO" "$APP_DIR"
  ok "$APP_DIR に取得しました"
fi
[ -f "$APP_HOME/app.py" ] || die "app.py が見つかりません: $APP_HOME"

# ── 3. Python 環境 ─────────────────────────────────────────
say "Python環境を構築します（2〜4分かかります）"
[ -d "$VENV" ] || python3 -m venv "$VENV"
"$VENV/bin/pip" install --quiet --upgrade pip
"$VENV/bin/pip" install --quiet -r "$APP_HOME/requirements.txt"
ok "依存パッケージを導入しました"

# ── 4. データベース初期化 ──────────────────────────────────
say "データベースを準備します"
mkdir -p "$APP_HOME/data" "$APP_HOME/storage"
DB="$APP_HOME/data/bridges.db"

if [ -f "$DB" ]; then
  ok "既存のデータベースをそのまま使用します（データは消えません）"
elif [ "$EMPTY_DB" = "1" ]; then
  "$VENV/bin/python" - "$APP_HOME" <<'PY'
import sqlite3, sys, pathlib
home = pathlib.Path(sys.argv[1])
db = home / "data" / "bridges.db"
with sqlite3.connect(db) as con:
    con.executescript((home / "schema.sql").read_text(encoding="utf-8"))
    con.commit()
sys.path.insert(0, str(home / "scripts"))
import init_storage
init_storage.init_storage()
print("  空のデータベースを作成しました")
PY
  ok "空のデータベースを作成しました（本番向け）"
else
  ( cd "$APP_HOME" && "$VENV/bin/python" -c "import app" >/dev/null 2>&1 ) || true
  if [ -f "$DB" ]; then
    ok "サンプルデータ入りのデータベースを作成しました（練習向け）"
  else
    warn "初回起動時に自動作成されます"
  fi
fi

# ── 5. サービス登録（自動起動） ────────────────────────────
if [ "$SKIP_SYSTEM" = "1" ]; then
  say "サービス登録をスキップします"
else
  say "自動起動サービスを登録します"
  cat > "/etc/systemd/system/${SERVICE}.service" <<EOF
[Unit]
Description=Bridge Management System (Streamlit)
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=$APP_HOME
ExecStart=$VENV/bin/streamlit run app.py \\
  --server.port $PORT \\
  --server.address 0.0.0.0 \\
  --server.headless true \\
  --browser.gatherUsageStats false
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF
  systemctl daemon-reload
  systemctl enable --quiet "$SERVICE"
  systemctl restart "$SERVICE"
  ok "サービス '$SERVICE' を登録・起動しました"

  # ── 6. ファイアウォール ──────────────────────────────────
  if command -v ufw >/dev/null; then
    say "ファイアウォールを設定します"
    ufw allow 22/tcp    >/dev/null 2>&1 || true
    ufw allow "$PORT"/tcp >/dev/null 2>&1 || true
    ok "22番（SSH）と ${PORT}番 を開放しました"
    warn "ufw が無効の場合は  ufw enable  で有効化してください"
  fi

  # ── 7. 起動確認 ──────────────────────────────────────────
  say "起動を確認します"
  for i in $(seq 1 30); do
    if curl -fsS -o /dev/null "http://127.0.0.1:$PORT" 2>/dev/null; then
      ok "システムが応答しました"
      break
    fi
    [ "$i" -eq 30 ] && warn "応答がありません。 journalctl -u $SERVICE -n 50  で確認してください"
    sleep 2
  done
fi

IP="$(hostname -I 2>/dev/null | awk '{print $1}')"
cat <<EOF

────────────────────────────────────────────
 ✅ 導入が完了しました
────────────────────────────────────────────

  アクセス先   http://${IP:-<サーバーのIP>}:$PORT
  インストール先 $APP_HOME

  よく使うコマンド
    systemctl status $SERVICE      状態を確認
    systemctl restart $SERVICE     再起動
    journalctl -u $SERVICE -f      ログを見る
    sudo bash install.sh           最新版に更新

EOF
