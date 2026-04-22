import logging

import pytest

from tagmania.iac_tools.timing import log_duration


class TestLogDuration:
    def test_logs_label_and_duration_on_success(self, caplog):
        logger = logging.getLogger("tagmania.test")
        with caplog.at_level(logging.INFO, logger="tagmania.test"):
            with log_duration(logger, "my_op"):
                pass
        assert len(caplog.records) == 1
        record = caplog.records[0]
        assert record.levelno == logging.INFO
        assert record.message.startswith("my_op took ")
        assert record.message.endswith("s")

    def test_logs_duration_when_block_raises(self, caplog):
        logger = logging.getLogger("tagmania.test")
        with caplog.at_level(logging.INFO, logger="tagmania.test"):
            with pytest.raises(RuntimeError, match="boom"):
                with log_duration(logger, "failing_op"):
                    raise RuntimeError("boom")
        assert len(caplog.records) == 1
        assert caplog.records[0].message.startswith("failing_op took ")

    def test_duration_reflects_elapsed_time(self, caplog):
        logger = logging.getLogger("tagmania.test")
        with caplog.at_level(logging.INFO, logger="tagmania.test"):
            with log_duration(logger, "quick"):
                pass
        # Extract the duration value from "quick took 0.0s" (format is f"{elapsed:.1f}s")
        message = caplog.records[0].message
        duration_str = message.removeprefix("quick took ").removesuffix("s")
        assert float(duration_str) >= 0.0
        assert float(duration_str) < 1.0  # trivial block should take well under a second
