# InsightFlow Backend Deployment on Ubuntu

This guide deploys the backend as a single Ubuntu LTS host using pyenv, uv,
systemd, Nginx, and HTTPS.

## Runtime Layout

- Service user: `ubuntu`
- Code: `~/InsightFlow`
- Virtualenv: `~/InsightFlow/.venv`
- Environment file: `~/InsightFlow/backend.env`
- SQLite data: `~/InsightFlow/data`
- Status store: `~/InsightFlow/status_store`
- Uploaded files: `~/InsightFlow/upload_file`
- Logs: `~/InsightFlow/logs`

## Provision Host

```bash
sudo apt update
sudo apt install -y git curl build-essential nginx certbot python3-certbot-nginx \
  libssl-dev zlib1g-dev libbz2-dev libreadline-dev libsqlite3-dev wget llvm \
  libncursesw5-dev xz-utils tk-dev libxml2-dev libxmlsec1-dev libffi-dev liblzma-dev

# Create runtime directories under the ubuntu user's home
mkdir -p ~/InsightFlow/data ~/InsightFlow/status_store ~/InsightFlow/upload_file ~/InsightFlow/completed ~/InsightFlow/logs
```

## Install Python and Dependencies

```bash
curl https://pyenv.run | bash
export PYENV_ROOT=~/.pyenv
export PATH="$PYENV_ROOT/bin:$PATH"
eval "$(pyenv init -)"
PYTHON_VERSION="$(pyenv install --list | sed 's/^  //' | grep -E '^3\.14\.[0-9]+$' | tail -1)"
pyenv install "$PYTHON_VERSION"
pyenv global "$PYTHON_VERSION"
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Deploy code to `~/InsightFlow`, then install dependencies:

```bash
cd ~/InsightFlow
uv venv .venv --python ~/.pyenv/shims/python
uv pip sync requirements-server.txt
uv pip check
# Offline import / dependency smoke test (no DB or network needed):
PYTHONPATH=src INSIGHTFLOW_LOG_DIR=~/InsightFlow/logs .venv/bin/python -c "import server.main"
```

`requirements-server.txt` is the minimal backend runtime lock (compiled from
`requirements-server.in`). The repo-root `requirements.txt` is the full
dev/experimental superset and is not needed on the server.

The runtime lock intentionally excludes test tooling. To run the offline unit
tests, install pytest separately:

```bash
cd ~/InsightFlow
uv pip install pytest pytest-asyncio
PYTHONPATH=src .venv/bin/python -m pytest tests -q
```

## Configure Backend

```bash
cp deploy/env/backend.env.example ~/InsightFlow/backend.env
chmod 0640 ~/InsightFlow/backend.env
editor ~/InsightFlow/backend.env
```

Set `LLM_API_KEY` only in `~/InsightFlow/backend.env`. Do not commit
production secrets to `src/.env`.

## Install systemd Service

```bash
sudo cp deploy/systemd/insightflow-backend.service /etc/systemd/system/insightflow-backend.service
sudo systemctl daemon-reload
sudo systemctl enable --now insightflow-backend
sudo systemctl status insightflow-backend
curl -f http://127.0.0.1:8080/healthz
curl -f http://127.0.0.1:8080/openapi.json
ss -ltnp | grep 8080
```

## Configure Nginx and HTTPS

Replace `api.<your-domain>` in `deploy/nginx/insightflow-backend.conf`, then:

```bash
sudo cp deploy/nginx/insightflow-backend.conf /etc/nginx/sites-available/insightflow-backend
sudo ln -s /etc/nginx/sites-available/insightflow-backend /etc/nginx/sites-enabled/insightflow-backend
sudo nginx -t
sudo certbot --nginx -d api.<your-domain>
sudo systemctl reload nginx
curl -f https://api.<your-domain>/healthz
curl -f https://api.<your-domain>/openapi.json
```

Build the browser extension with `VITE_API_BASE_URL=https://api.<your-domain>`.

## Operations

```bash
tail -f ~/InsightFlow/logs/api_services.log
journalctl -u insightflow-backend -n 100
sqlite3 ~/InsightFlow/data/insight_flow.sqlite3 ".backup '/backup/path/insight_flow.sqlite3'"
```

Back up SQLite, the status store, uploaded files, and the completed archive
daily. Keep one Uvicorn worker until status storage and background task tracking
move out of process memory.