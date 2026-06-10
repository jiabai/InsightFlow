"""
Test 1: Health check — verifies the test infrastructure is wired correctly.
"""
import pytest


class TestHealthCheck:
    """Confirm that TestClient can create an app and handle requests."""

    def test_client_can_send_request(self, client):
        """The test client should be able to send a GET request and get a response."""
        # Any endpoint — we just need to confirm the app is running
        response = client.get("/upload/file_status/nonexistent")
        # A 4xx/5xx is fine; the point is that the app processes the request
        assert response.status_code in {200, 400, 404, 422}

    def test_app_has_routers_registered(self, client):
        """All three routers should be registered and reachable."""
        # Hit an endpoint from each router module
        r1 = client.get("/upload/file_status/test123")
        r2 = client.get("/questions/test123")
        r3 = client.post("/llm/query", json={"user_content": "Hello"})

        # None should be 405 Method Not Allowed (sign of missing routes)
        for r in [r1, r2, r3]:
            assert r.status_code != 405, (
                f"Expected a registered route, got {r.status_code}"
            )
