from pathlib import Path


def test_backend_logging_defaults_to_info_file_only():
    source = Path("src/server/api_services/shared_resources.py").read_text(encoding="utf-8")

    assert 'os.getenv("INSIGHTFLOW_LOG_LEVEL", "INFO")' in source
    assert 'os.getenv("INSIGHTFLOW_LOG_CONSOLE", "0")' in source


def test_start_script_defaults_to_quiet_file_logging():
    source = Path("src/server/scripts/start.ps1").read_text(encoding="utf-8")

    assert '$env:INSIGHTFLOW_LOG_LEVEL = "INFO"' in source
    assert '$env:INSIGHTFLOW_LOG_CONSOLE = "0"' in source
    assert '$env:INSIGHTFLOW_LOG_LEVEL = "DEBUG"' not in source
    assert '$env:INSIGHTFLOW_LOG_CONSOLE = "1"' not in source
    assert "--log-level $UvicornLogLevel" in source
    assert "--no-access-log" in source
