import os
import subprocess
import sys
from pathlib import Path


def test_server_main_imports_without_prior_logging_setup():
    repo_root = Path(__file__).resolve().parents[1]
    env = os.environ.copy()
    env["PYTHONPATH"] = str(repo_root / "src")

    result = subprocess.run(
        [sys.executable, "-c", "import server.main; print('ok')"],
        cwd=repo_root,
        env=env,
        text=True,
        capture_output=True,
        timeout=10,
    )

    assert result.returncode == 0, result.stderr
    assert "ok" in result.stdout


def test_server_app_lifespan_starts(tmp_path):
    repo_root = Path(__file__).resolve().parents[1]
    env = os.environ.copy()
    env["PYTHONPATH"] = str(repo_root / "src")
    env["SQLITE_DB_PATH"] = str(tmp_path / "insight_flow.sqlite3")
    env["LOCAL_STATUS_STORE_DIR"] = str(tmp_path / "status_store")
    env["LOCAL_STORAGE_BASE_DIR"] = str(tmp_path / "upload_file")

    code = """
from fastapi.testclient import TestClient
import server.main as m

with TestClient(m.app) as client:
    print(client.get('/docs').status_code)
"""
    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=repo_root,
        env=env,
        text=True,
        capture_output=True,
        timeout=10,
    )

    assert result.returncode == 0, result.stderr
    assert "200" in result.stdout
