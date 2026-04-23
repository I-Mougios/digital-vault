import logging
import logging.config
from pathlib import Path

from yaml import safe_load

from configurations import mongo_host, mongo_password, mongo_port, mongo_user

from .formatters import DictFormatter
from .handlers import AsyncMongoHandler

__all__ = ["AsyncMongoHandler", "DictFormatter", "configure_loggers"]


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


class MongoLogger(AsyncMongoHandler):
    def __init__(
        self,
        uri: str = f"mongodb://{mongo_user}:{mongo_password}@{mongo_host}:{mongo_port}/admin?authSource=admin",
        database_name: str = "dv-notes",
        collection_name: str = "test-logs",
        queue_max_size: int = 100,
        batch_size: int = 50,
        **kwargs,
    ):
        super().__init__(
            uri=uri,
            database_name=database_name,
            collection_name=collection_name,
            queue_max_size=queue_max_size,
            batch_size=batch_size,
        )
