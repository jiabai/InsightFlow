from pathlib import Path


def test_systemd_unit_matches_backend_deployment_contract():
    unit = Path("deploy/systemd/insightflow-backend.service").read_text(encoding="utf-8")

    assert "User=ubuntu" in unit
    assert "Group=ubuntu" in unit
    assert "WorkingDirectory=/home/ubuntu/InsightFlow" in unit
    assert "EnvironmentFile=/home/ubuntu/InsightFlow/backend.env" in unit
    assert "--host 127.0.0.1" in unit
    assert "--port 8080" in unit
    assert "--workers 1" in unit
    assert "--proxy-headers" in unit
    assert "--forwarded-allow-ips=127.0.0.1" in unit
    assert "--log-level warning" in unit
    assert "--no-access-log" in unit
    assert "LimitNOFILE=65535" in unit
    assert "NoNewPrivileges=true" in unit
    assert "ProtectSystem=full" in unit
    assert "ReadWritePaths=/home/ubuntu/InsightFlow" in unit


def test_nginx_template_supports_https_sse_and_rate_limit():
    nginx = Path("deploy/nginx/insightflow-backend.conf").read_text(encoding="utf-8")

    assert "server_name api.<your-domain>" in nginx
    assert "return 301 https://$host$request_uri" in nginx
    assert "ssl_certificate" in nginx
    assert "proxy_pass http://127.0.0.1:8080" in nginx
    assert "client_max_body_size 20m" in nginx
    assert "proxy_read_timeout 300s" in nginx
    assert "location /llm/query/stream" in nginx
    assert "proxy_buffering off" in nginx
    assert "limit_req_zone $binary_remote_addr zone=insightflow_api:10m rate=5r/s" in nginx


def test_backend_env_example_uses_home_directory():
    env_example = Path("deploy/env/backend.env.example").read_text(encoding="utf-8")

    assert "SERVER_HOST=127.0.0.1" in env_example
    assert "SERVER_PORT=8080" in env_example
    assert "SQLITE_DB_PATH=~/InsightFlow/data/insight_flow.sqlite3" in env_example
    assert "LOCAL_STATUS_STORE_DIR=~/InsightFlow/status_store" in env_example
    assert "LOCAL_STORAGE_BASE_DIR=~/InsightFlow/upload_file" in env_example
    assert "STORAGE_TYPE=local" in env_example
    assert "INSIGHTFLOW_LOG_LEVEL=INFO" in env_example
    assert "INSIGHTFLOW_LOG_CONSOLE=0" in env_example
    assert "INSIGHTFLOW_LOG_DIR=~/InsightFlow/logs" in env_example
    assert "INSIGHTFLOW_MAX_CONCURRENT_TASKS=10" in env_example
    assert "LLM_API_KEY=" in env_example