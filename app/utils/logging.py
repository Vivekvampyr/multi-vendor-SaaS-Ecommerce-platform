import logging
import sys


def setup_logging(debug: bool = False) -> None:
    """Configure structured logging for the application."""
    log_level = logging.DEBUG if debug else logging.INFO
    log_format = "%(asctime)s | %(levelname)-8s | %(name)s:%(lineno)d - %(message)s"

    logging.basicConfig(
        level=log_level,
        format=log_format,
        handlers=[logging.StreamHandler(sys.stdout)],
        force=True,
    )
