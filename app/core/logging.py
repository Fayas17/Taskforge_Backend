import logging
import os
import sys
from logging.handlers import TimedRotatingFileHandler

import structlog


def setup_logging() -> None:
    log_dir = "logs"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    # 1. Base Formatter
    formatter = logging.Formatter("%(message)s")

    # 2. Daily Rotation Handlers
    # All logs (INFO+)
    info_handler = TimedRotatingFileHandler(
        os.path.join(log_dir, "app.log"), when="midnight", interval=1, backupCount=30
    )
    info_handler.setLevel(logging.INFO)
    info_handler.setFormatter(formatter)

    # Error logs only (WARNING+)
    error_handler = TimedRotatingFileHandler(
        os.path.join(log_dir, "error.log"), when="midnight", interval=1, backupCount=90
    )
    error_handler.setLevel(logging.WARNING)
    error_handler.setFormatter(formatter)

    # Security/Audit logs (Specialized)
    security_handler = TimedRotatingFileHandler(
        os.path.join(log_dir, "security.log"), when="midnight", interval=1, backupCount=365
    )
    security_handler.setLevel(logging.INFO)
    security_handler.setFormatter(formatter)

    # 3. Standard Library Logging Config
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(logging.StreamHandler(sys.stdout))
    root_logger.addHandler(info_handler)
    root_logger.addHandler(error_handler)

    # Define a dedicated Security Logger
    security_logger = logging.getLogger("security")
    security_logger.setLevel(logging.INFO)
    security_logger.addHandler(security_handler)
    security_logger.addHandler(error_handler)  # High-priority security issues in error.log too
    security_logger.propagate = False  # Don't duplicate in app.log

    # 4. Structlog Configuration
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer(),
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
