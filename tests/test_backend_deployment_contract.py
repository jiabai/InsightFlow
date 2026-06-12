import logging

from fastapi import FastAPI
from fastapi.testclient import TestClient

from server.api_services.insight_logger import setup_logging
from server.api_services import question_routes
from server.main import app as main_app


def test_insight_logger_uses_configured_log_dir(monkeypatch, tmp_path):
    monkeypatch.setenv("INSIGHTFLOW_LOG_DIR", str(tmp_path))
    app = FastAPI()

    logger = setup_logging(app, log_file="api_services.log", level=logging.INFO)
    logger.info("deployment log directory probe")

    assert (tmp_path / "api_services.log").exists()


def test_max_concurrent_tasks_is_configurable(monkeypatch):
    monkeypatch.setenv("INSIGHTFLOW_MAX_CONCURRENT_TASKS", "3")
    assert question_routes.get_max_concurrent_tasks() == 3

    monkeypatch.setenv("INSIGHTFLOW_MAX_CONCURRENT_TASKS", "not-a-number")
    assert question_routes.get_max_concurrent_tasks() == 10


def test_healthz_endpoint_is_lifespan_independent():
    client = TestClient(main_app)

    response = client.get("/healthz")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
