"""Utilities for logging operation durations."""

from __future__ import annotations

import logging
import time
from collections.abc import Iterator
from contextlib import contextmanager

from tagmania import telemetry


@contextmanager
def log_duration(logger: logging.Logger, label: str) -> Iterator[None]:
    """Log the wall-clock duration of the wrapped block at INFO level.

    Emits the duration even if the wrapped block raises, so partial runs
    still produce a timing line. Inside a CLI run the block is also recorded
    as a telemetry operation (tagmania.telemetry.measure).
    """
    start = time.perf_counter()
    try:
        with telemetry.measure(label):
            yield
    finally:
        elapsed = time.perf_counter() - start
        logger.info(f"{label} took {elapsed:.1f}s")
