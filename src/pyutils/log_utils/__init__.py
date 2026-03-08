# src/pyutils/log_utils/__init__.py
import logging
import logging.config
from pathlib import Path

from yaml import safe_load

from .formatters import DictFormatter
from .handlers import AsyncMongoHandler, TestMongoHandler

__all__ = ["AsyncMongoHandler", "TestMongoHandler", "DictFormatter", "configure_loggers"]


def configure_loggers(directory: str | None = None, filename: str = "logger_config.yaml") -> dict:
    try:
        parents = Path(__file__).resolve().parents
    except NameError:
        parents = Path.cwd().resolve().parents

    for path in parents:
        if directory is not None:
            path = path / directory

        candidate = path / filename

        if candidate.exists():
            with open(candidate, encoding="utf-8") as f:
                config = safe_load(f)

            logging.config.dictConfig(config)
            return config

    raise FileNotFoundError(f"{filename} not found")
