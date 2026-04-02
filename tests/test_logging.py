from __future__ import annotations

import json

import pytest
import structlog

from src.infrastructure.logging import get_logger, setup_logging


@pytest.fixture(autouse=True)
def reset_structlog():
    """Prevent structlog global state from leaking between tests."""
    yield
    structlog.reset_defaults()


class TestSetupLogging:
    def test_json_format_does_not_raise(self):
        setup_logging(log_level="INFO", log_format="json")

    def test_console_format_does_not_raise(self):
        setup_logging(log_level="DEBUG", log_format="console")

    def test_debug_level_accepted(self):
        setup_logging(log_level="DEBUG", log_format="json")

    def test_warning_level_accepted(self):
        setup_logging(log_level="WARNING", log_format="json")

    def test_error_level_accepted(self):
        setup_logging(log_level="ERROR", log_format="json")

    def test_critical_level_accepted(self):
        setup_logging(log_level="CRITICAL", log_format="json")

    def test_unknown_level_falls_back_to_info(self):
        # getattr(logging, "NOTAREAL", logging.INFO) returns logging.INFO silently
        setup_logging(log_level="NOTAREAL", log_format="json")

    def test_json_output_is_parseable(self, capsys):
        setup_logging(log_level="DEBUG", log_format="json")
        logger = get_logger("test.json")
        logger.info("hello_world", answer=42)
        captured = capsys.readouterr()
        record = json.loads(captured.out.strip())
        assert record["event"] == "hello_world"
        assert record["answer"] == 42
        assert record["level"] == "info"
        assert "timestamp" in record

    def test_json_output_includes_log_level(self, capsys):
        setup_logging(log_level="DEBUG", log_format="json")
        logger = get_logger("test.levels")
        logger.warning("watch_out", code=99)
        captured = capsys.readouterr()
        record = json.loads(captured.out.strip())
        assert record["level"] == "warning"

    def test_debug_messages_suppressed_at_info_level(self, capsys):
        setup_logging(log_level="INFO", log_format="json")
        logger = get_logger("test.suppress")
        logger.debug("this_should_not_appear")
        captured = capsys.readouterr()
        assert captured.out.strip() == ""

    def test_console_format_produces_output(self, capsys):
        setup_logging(log_level="DEBUG", log_format="console")
        logger = get_logger("test.console")
        logger.info("hello_console", key="value")
        captured = capsys.readouterr()
        assert "hello_console" in captured.out


class TestGetLogger:
    def test_returns_usable_logger(self):
        setup_logging(log_level="INFO", log_format="json")
        logger = get_logger("mymodule")
        assert logger is not None

    def test_multiple_loggers_produce_output(self, capsys):
        setup_logging(log_level="DEBUG", log_format="json")
        logger_a = get_logger("module.a")
        logger_b = get_logger("module.b")
        logger_a.info("from_a")
        logger_b.info("from_b")
        lines = [l for l in capsys.readouterr().out.strip().splitlines() if l]
        events = [json.loads(l)["event"] for l in lines]
        assert "from_a" in events
        assert "from_b" in events
