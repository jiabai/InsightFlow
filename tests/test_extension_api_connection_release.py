from pathlib import Path


API_SERVICE_SOURCE = Path("src/extension/entrypoints/services/apiService.ts")


def test_fetch_with_timeout_aborts_and_clears_timer():
    source = API_SERVICE_SOURCE.read_text(encoding="utf-8")

    assert "new AbortController()" in source
    assert "controller.abort()" in source
    assert "clearTimeout(timeoutId)" in source
    assert "signal: controller.signal" in source


def test_unused_success_response_body_is_released_after_generate_request():
    source = API_SERVICE_SOURCE.read_text(encoding="utf-8")

    assert "async function releaseResponseBody" in source
    assert "await releaseResponseBody(generateResponse)" in source
    assert "response.body.cancel()" in source
