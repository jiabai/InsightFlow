# InsightFlow Backend Deployment on Ubuntu

This guide deploys the backend as a single Ubuntu LTS host using pyenv, uv,
systemd, Nginx, and HTTPS.

## Runtime Layout

- Service user: `insightflow`
- Code: `/opt/insightflow/current`
- Virtualenv: `/opt/insightflow/current/.venv`
- Environment file: `/etc/insightflow/backend.env`
- SQLite data: `/var/lib/insightflow/data`
- Status store: `/var/lib/insightflow/status_store`
- Uploaded files: `/var/lib/insightflow/upload_file`
- Logs: `/var/log/insightflow`

## Provision Host

```bash
sudo apt update
sudo apt install -y git curl build-essential nginx certbot python3-certbot-nginx \
  libssl-dev zlib1g-dev libbz2-dev libreadline-dev libsqlite3-dev wget llvm \
  libncursesw5-dev xz-utils tk-dev libxml2-dev libxmlsec1-dev libffi-dev liblzma-dev

sudo useradd --system --create-home --home-dir /opt/insightflow --shell /bin/bash insightflow
sudo install -d -o insightflow -g insightflow /opt/insightflow
sudo install -d -o insightflow -g insightflow /var/lib/insightflow/data
sudo install -d -o insightflow -g insightflow /var/lib/insightflow/status_store
sudo install -d -o insightflow -g insightflow /var/lib/insightflow/upload_file
sudo install -d -o insightflow -g insightflow /var/log/insightflow
sudo install -d -o root -g insightflow -m 0750 /etc/insightflow
```

## Install Python and Dependencies

```bash
sudo -iu insightflow
curl https://pyenv.run | bash
export PYENV_ROOT=/opt/insightflow/.pyenv
export PATH="$PYENV_ROOT/bin:$PATH"
eval "$(pyenv init -)"
PYTHON_VERSION="$(pyenv install --list | sed 's/^  //' | grep -E '^3\.12\.[0-9]+$' | tail -1)"
pyenv install "$PYTHON_VERSION"
pyenv global "$PYTHON_VERSION"
curl -LsSf https://astral.sh/uv/install.sh | sh
exit
```

Deploy code to `/opt/insightflow/current`, then install dependencies:

```bash
sudo -iu insightflow
cd /opt/insightflow/current
uv venv .venv --python /opt/insightflow/.pyenv/shims/python
uv pip sync requirements.txt
uv pip check
PYTHONPATH=src .venv/bin/python -m pytest tests -q
exit
```

## Configure Backend

```bash
sudo cp deploy/env/backend.env.example /etc/insightflow/backend.env
sudo chown root:insightflow /etc/insightflow/backend.env
sudo chmod 0640 /etc/insightflow/backend.env
sudo editor /etc/insightflow/backend.env
```

Set `LLM_API_KEY` only in `/etc/insightflow/backend.env`. Do not commit
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
tail -f /var/log/insightflow/api_services.log
journalctl -u insightflow-backend -n 100
sqlite3 /var/lib/insightflow/data/insight_flow.sqlite3 ".backup '/backup/path/insight_flow.sqlite3'"
```

Back up SQLite, status store, and uploaded files daily. Keep one Uvicorn worker
until status storage and background task tracking move out of process memory.
