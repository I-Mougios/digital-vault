import asyncio
import logging
import typing

from pymongo import MongoClient
from pymongo.errors import InvalidOperation

import pytest

from log_utils import AsyncMongoHandler, DictFormatter
from configurations import mongo_host, mongo_password, mongo_port, mongo_user


class TestMongoLogger:
    """
    1.QueueFull Test: Verifies that logs are dropped and an error is printed when the queue is saturated.
    2.Error Resilience: Ensures no deadlock occurs in the event of an unexpected error.
    3.Shutdown Integrity: Verifies that no additional logs can be added to the queue after queue.shutdown() is called.
    4.Residual Log Flush: Verifies all pending logs are flushed during cleanup, even if the batch is incomplete.
    """

    @pytest.fixture(autouse=True)
    async def _setup_handler(self) -> typing.AsyncGenerator[None]:
        """
        This fixture replaces setup_method and teardown_method.
        'autouse=True' ensures it runs for every test in this class.
        """
        # --- setup_method ---
        self.logger = logging.getLogger("mongo_logger")
        self.logger.handlers.clear()

        self.async_handler = AsyncMongoHandler(
            uri=f"mongodb://{mongo_user}:{mongo_password}@{mongo_host}:{mongo_port}/admin?authSource=admin",
            database_name="dv-notes",
            collection_name="test_logs",
            queue_max_size=10,
            batch_size=5,
            flush_interval=0.5
        )
        self.async_handler.setFormatter(DictFormatter())
        self.logger.addHandler(self.async_handler)

        self.logger.setLevel(logging.INFO)
        await self.async_handler.start()

        yield

        # --- teardown_method ---
        if hasattr(self, "async_handler") and self.async_handler:
            if self.async_handler.collection is not None:
                try:
                    # there is test where I can drop the collection since client is closed
                    await self.async_handler.collection.drop()
                except InvalidOperation:
                    pass
            await self.async_handler.stop()

        self.logger.handlers.clear()


    async def test_queue_overflow_drops_logs(self, capsys) -> None:
        # We fill the queue (size 10) and go beyond it
        for i in range(11):
            self.logger.info(f"Filling queue {i}")

        captured = capsys.readouterr()
        assert "[Logging]: Log queue full" in captured.err

    async def test_raises_unexpected_error(self, capsys):
        self.async_handler.setFormatter(None)
        for i in range(1):
            self.logger.info(f"Filling queue {i}")
        await asyncio.sleep(0.1)
        captured = capsys.readouterr()
        assert "[Logging]: Unexpected error in consumer" in captured.err

    async def test_log_after_shutdown_is_ignored(self, capsys) -> None:
        await self.async_handler.start()
        await self.async_handler.stop()

        self.logger.info("This log is too late!")

        captured = capsys.readouterr()
        assert "[Logging]: Log queue was shut down" in captured.err


    async def test_flushes_remaining_logs_on_stop(self) -> None:
        self.async_handler.batch_size=5
        # 5 is not a divisor of 7
        for i in range(7):
            self.logger.info(f"Residual log {i}")

        # Stop the handler while there are two remaining logs in the self._batch
        await self.async_handler.stop()

        # 4. Verify the database count
        client = MongoClient(self.async_handler.uri)
        collection = client[self.async_handler.database_name][self.async_handler.collection_name]
        count = collection.count_documents({})
        assert count == 7, f"Expected 7 logs, but found {count}. Finally block might have failed."



