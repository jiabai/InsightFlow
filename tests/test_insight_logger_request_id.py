import logging

from fastapi import FastAPI
from fastapi.testclient import TestClient

from server.api_services.insight_logger import request_id_var, setup_logging


def test_request_id_header_is_used_for_context_and_response_header():
    app = FastAPI()
    setup_logging(app, log_file="test_request_id.log", level=logging.DEBUG)

    @app.get("/probe")
    async def probe():
        return {"request_id": request_id_var.get()}

    client = TestClient(app)

    response = client.get(
        "/probe",
        headers={"X-InsightFlow-Request-Id": "frontend-trace-123"},
    )

    assert response.status_code == 200
    assert response.json() == {"request_id": "frontend-trace-123"}
    assert response.headers["X-InsightFlow-Request-Id"] == "frontend-trace-123"
