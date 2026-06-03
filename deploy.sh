#!/usr/bin/env bash

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
GENERATED_DIR="$PROJECT_ROOT/.deploy/generated"
GRAFANA_DIR="$GENERATED_DIR/grafana"
RUNTIME_ENV_FILE="$GENERATED_DIR/movie-kite.env"
GRAFANA_COMPOSE="$GRAFANA_DIR/docker-compose.grafana.yml"
GRAFANA_PROVISIONING_DS="$GRAFANA_DIR/provisioning/datasources/datasource.yml"
GRAFANA_PROVISIONING_DASHBOARDS="$GRAFANA_DIR/provisioning/dashboards/dashboards.yml"
GRAFANA_DASHBOARD="$GRAFANA_DIR/dashboards/movie-kite-dashboard.json"
SYSTEMD_UNIT_PATH="/etc/systemd/system/movie-kite.service"
NGINX_SITE_AVAILABLE="/etc/nginx/sites-available/movie-kite.conf"
NGINX_SITE_ENABLED="/etc/nginx/sites-enabled/movie-kite.conf"
APP_HOST="127.0.0.1"
APP_PORT="5000"
GRAFANA_HOST_PORT="3000"
APP_USER="${APP_USER:-$(id -un)}"
GRAFANA_ADMIN_USER="${GRAFANA_ADMIN_USER:-admin}"
GRAFANA_ADMIN_PASSWORD="${GRAFANA_ADMIN_PASSWORD:-change-me-now}"

usage() {
  cat <<'EOF'
Usage: ./deploy.sh [up|down|restart|status|logs]

Commands:
  up       Prepare and start the Flask app, Grafana, systemd service, and Nginx.
  down     Stop the Grafana stack and the systemd service.
  restart  Recreate everything by running down then up.
  status   Show systemd, Nginx, and Grafana status.
  logs     Tail the systemd app logs and Grafana container logs.

Environment variables:
  GRAFANA_ADMIN_USER
  GRAFANA_ADMIN_PASSWORD
  APP_USER
EOF
}

log() {
  printf '[deploy] %s\n' "$*"
}

ensure_venv() {
  if [[ ! -x "$PROJECT_ROOT/.venv/bin/python" ]]; then
    log "Python virtual environment not found at .venv"
    exit 1
  fi
}

ensure_movies_db() {
  if [[ ! -f "$PROJECT_ROOT/movies.db" ]]; then
    log "Creating empty SQLite database file at movies.db"
    : > "$PROJECT_ROOT/movies.db"
  fi
}

write_runtime_env() {
  log "Writing sanitized runtime env file"
  mkdir -p "$GENERATED_DIR"
  : > "$RUNTIME_ENV_FILE"

  if [[ -f "$PROJECT_ROOT/.env" ]]; then
    grep -E '^[A-Za-z_][A-Za-z0-9_]*=.*$' "$PROJECT_ROOT/.env" >> "$RUNTIME_ENV_FILE" || true
  fi

  for line in \
    "SECRET_KEY=${SECRET_KEY:-dev-secret-change-me}" \
    "SESSION_COOKIE_SECURE=${SESSION_COOKIE_SECURE:-false}" \
    "DATABASE_URL=${DATABASE_URL:-sqlite:///movies.db}" \
    "MONGO_URI=${MONGO_URI:-mongodb://localhost:27017/movieDB}" \
    "API_KEY=${API_KEY:-}" \
    "minio_endpoint=${minio_endpoint:-}" \
    "minio_access_key=${minio_access_key:-}" \
    "minio_secret_key=${minio_secret_key:-}"; do
    key="${line%%=*}"
    if ! grep -q "^${key}=" "$RUNTIME_ENV_FILE"; then
      printf '%s\n' "$line" >> "$RUNTIME_ENV_FILE"
    fi
  done
}

install_python_deps() {
  log "Installing/updating Python dependency gunicorn"
  "$PROJECT_ROOT/.venv/bin/python" -m pip install --quiet gunicorn
}

write_grafana_files() {
  mkdir -p "$GRAFANA_DIR/provisioning/datasources" "$GRAFANA_DIR/provisioning/dashboards" "$GRAFANA_DIR/dashboards"

  cat > "$GRAFANA_COMPOSE" <<EOF
services:
  grafana:
    image: grafana/grafana-oss:latest
    container_name: movie-kite-grafana
    ports:
      - "$GRAFANA_HOST_PORT:3000"
    environment:
      GF_SECURITY_ADMIN_USER: $GRAFANA_ADMIN_USER
      GF_SECURITY_ADMIN_PASSWORD: $GRAFANA_ADMIN_PASSWORD
      GF_PLUGINS_PREINSTALL_SYNC: frser-sqlite-datasource
      GF_USERS_ALLOW_SIGN_UP: "false"
      GF_AUTH_ANONYMOUS_ENABLED: "false"
    volumes:
      - grafana-data:/var/lib/grafana
      - ./provisioning:/etc/grafana/provisioning:ro
      - ./dashboards:/var/lib/grafana/dashboards:ro
      - $PROJECT_ROOT/movies.db:/var/lib/grafana/db/movies.db:ro
    restart: unless-stopped

volumes:
  grafana-data:
EOF

  cat > "$GRAFANA_PROVISIONING_DS" <<'EOF'
apiVersion: 1

datasources:
  - name: Movie Kite SQLite
    uid: moviekite-sqlite
    type: frser-sqlite-datasource
    access: proxy
    isDefault: true
    editable: false
    jsonData:
      pathPrefix: "file:"
      path: /var/lib/grafana/db/movies.db
      pathOptions: mode=ro
      attachLimit: 0
EOF

  cat > "$GRAFANA_PROVISIONING_DASHBOARDS" <<'EOF'
apiVersion: 1

providers:
  - name: Movie Kite
    folder: Movie Kite
    type: file
    disableDeletion: false
    allowUiUpdates: true
    options:
      path: /var/lib/grafana/dashboards
EOF

  cat > "$GRAFANA_DASHBOARD" <<'EOF'
{
  "title": "Movie Kite Overview",
  "tags": ["movie-kite", "analytics"],
  "timezone": "browser",
  "schemaVersion": 39,
  "version": 1,
  "refresh": "30s",
  "panels": [
    {
      "type": "table",
      "title": "Movies in Library by Title",
      "datasource": { "type": "frser-sqlite-datasource", "uid": "moviekite-sqlite" },
      "targets": [
        {
          "refId": "A",
          "format": "table",
          "rawSql": "SELECT title, COUNT(*) AS users_in_library FROM movie WHERE library = 1 GROUP BY title ORDER BY users_in_library DESC, title ASC;"
        }
      ],
      "gridPos": { "h": 10, "w": 12, "x": 0, "y": 0 },
      "options": { "showHeader": true }
    },
    {
      "type": "table",
      "title": "Movies in Watchlist by Title",
      "datasource": { "type": "frser-sqlite-datasource", "uid": "moviekite-sqlite" },
      "targets": [
        {
          "refId": "A",
          "format": "table",
          "rawSql": "SELECT title, COUNT(*) AS users_in_watchlist FROM movie WHERE watch_list = 1 GROUP BY title ORDER BY users_in_watchlist DESC, title ASC;"
        }
      ],
      "gridPos": { "h": 10, "w": 12, "x": 12, "y": 0 },
      "options": { "showHeader": true }
    },
    {
      "type": "table",
      "title": "Total Movies Per Status",
      "datasource": { "type": "frser-sqlite-datasource", "uid": "moviekite-sqlite" },
      "targets": [
        {
          "refId": "A",
          "format": "table",
          "rawSql": "SELECT 'library' AS list_type, COUNT(*) AS total_rows FROM movie WHERE library = 1 UNION ALL SELECT 'watchlist' AS list_type, COUNT(*) AS total_rows FROM movie WHERE watch_list = 1;"
        }
      ],
      "gridPos": { "h": 8, "w": 12, "x": 0, "y": 10 },
      "options": { "showHeader": true }
    },
    {
      "type": "table",
      "title": "Top Users by Library Size",
      "datasource": { "type": "frser-sqlite-datasource", "uid": "moviekite-sqlite" },
      "targets": [
        {
          "refId": "A",
          "format": "table",
          "rawSql": "SELECT u.username, COUNT(*) AS library_count FROM user u JOIN movie m ON m.user_id = u.id WHERE m.library = 1 GROUP BY u.id, u.username ORDER BY library_count DESC LIMIT 10;"
        }
      ],
      "gridPos": { "h": 8, "w": 12, "x": 12, "y": 10 },
      "options": { "showHeader": true }
    },
    {
      "type": "table",
      "title": "Movie Actions Over Time",
      "datasource": { "type": "frser-sqlite-datasource", "uid": "moviekite-sqlite" },
      "targets": [
        {
          "refId": "A",
          "format": "table",
          "rawSql": "SELECT date(created_at) AS day, event_type, COUNT(*) AS event_count FROM movie_event GROUP BY date(created_at), event_type ORDER BY day ASC, event_type ASC;"
        }
      ],
      "gridPos": { "h": 10, "w": 12, "x": 0, "y": 18 },
      "options": { "showHeader": true }
    },
    {
      "type": "table",
      "title": "Recent User Interactions",
      "datasource": { "type": "frser-sqlite-datasource", "uid": "moviekite-sqlite" },
      "targets": [
        {
          "refId": "A",
          "format": "table",
          "rawSql": "SELECT created_at, username, movie_title, event_type, details FROM movie_event e JOIN user u ON u.id = e.user_id ORDER BY created_at DESC LIMIT 100;"
        }
      ],
      "gridPos": { "h": 10, "w": 12, "x": 12, "y": 18 },
      "options": { "showHeader": true }
    }
  ]
}
EOF
}

install_systemd_unit() {
  local tmp_unit
  tmp_unit="$(mktemp)"
  cat > "$tmp_unit" <<EOF
[Unit]
Description=Movie Kite Flask app via Gunicorn
After=network.target

[Service]
Type=simple
User=$APP_USER
WorkingDirectory=$PROJECT_ROOT
EnvironmentFile=$RUNTIME_ENV_FILE
Environment=DOTENV_FILE=$RUNTIME_ENV_FILE
Environment=PYTHONUNBUFFERED=1
ExecStart=$PROJECT_ROOT/.venv/bin/gunicorn --workers 3 --bind $APP_HOST:$APP_PORT wsgi:app
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

  sudo cp "$tmp_unit" "$SYSTEMD_UNIT_PATH"
  rm -f "$tmp_unit"
  sudo systemctl daemon-reload
  sudo systemctl enable --now movie-kite.service
}

install_nginx_site() {
  local tmp_nginx
  tmp_nginx="$(mktemp)"
  cat > "$tmp_nginx" <<'EOF'
server {
    listen 80;
    listen [::]:80;
    server_name movie-kite.top www.movie-kite.top;

    client_max_body_size 20m;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
EOF

  sudo cp "$tmp_nginx" "$NGINX_SITE_AVAILABLE"
  rm -f "$tmp_nginx"
  sudo ln -sf "$NGINX_SITE_AVAILABLE" "$NGINX_SITE_ENABLED"
  sudo nginx -t
  sudo systemctl reload nginx
}

start_grafana() {
  mkdir -p "$GENERATED_DIR"
  pushd "$GRAFANA_DIR" >/dev/null
  docker compose -f docker-compose.grafana.yml up -d
  popd >/dev/null
}

start_app() {
  log "Starting/restarting Gunicorn through systemd"
  sudo systemctl restart movie-kite.service
}

stop_all() {
  if [[ -f "$GRAFANA_COMPOSE" ]]; then
    pushd "$GRAFANA_DIR" >/dev/null
    docker compose -f docker-compose.grafana.yml down || true
    popd >/dev/null
  fi
  sudo systemctl stop movie-kite.service || true
}

status_all() {
  systemctl status movie-kite.service --no-pager || true
  systemctl status nginx --no-pager || true
  if [[ -f "$GRAFANA_COMPOSE" ]]; then
    pushd "$GRAFANA_DIR" >/dev/null
    docker compose -f docker-compose.grafana.yml ps || true
    popd >/dev/null
  fi
}

logs_all() {
  sudo journalctl -u movie-kite.service -n 50 --no-pager || true
  if [[ -f "$GRAFANA_COMPOSE" ]]; then
    pushd "$GRAFANA_DIR" >/dev/null
    docker compose -f docker-compose.grafana.yml logs --tail=50 grafana || true
    popd >/dev/null
  fi
}

main() {
  local command="${1:-up}"

  case "$command" in
    up)
      ensure_venv
      ensure_movies_db
      write_runtime_env
      install_python_deps
      write_grafana_files
      install_systemd_unit
      install_nginx_site
      start_app
      start_grafana
      log "Deployment completed."
      log "App: http://$APP_HOST:$APP_PORT"
      log "Grafana: http://127.0.0.1:$GRAFANA_HOST_PORT"
      ;;
    down)
      stop_all
      ;;
    restart)
      stop_all
      "$0" up
      ;;
    status)
      status_all
      ;;
    logs)
      logs_all
      ;;
    -h|--help|help)
      usage
      ;;
    *)
      echo "Unknown command: $command" >&2
      usage >&2
      exit 1
      ;;
  esac
}

main "$@"
