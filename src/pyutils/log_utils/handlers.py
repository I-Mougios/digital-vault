# src/pyutils/log_utils/handlers.py
import asyncio
import logging
import sys

from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.errors import ConnectionFailure, OperationFailure, PyMongoError

from configurations import mongo_host, mongo_password, mongo_port, mongo_user


class AsyncHandler(logging.Handler):
    def __init__(self, queue_max_size: int = 1000):
        super().__init__()
        self.logs_queue: asyncio.Queue = asyncio.Queue(queue_max_size)

    def emit(self, record: logging.LogRecord):
        try:
            formatted_record = self.format(record)
            try:
                self.logs_queue.put_nowait(formatted_record)
            except asyncio.QueueFull:
                # Queue is full, drop to prevent blocking the main app
                sys.stderr.write(f"Log queue full, record {formatted_record} ignore")
            except asyncio.QueueShutDown:
                # Application is closing, just drop the log
                sys.stderr.write(f"Log queue was shut down, record {formatted_record} ignored")
        except Exception:
            # Fallback to prevent logging from crashing the app
            pass


class AsyncMongoHandler(AsyncHandler):
    def __init__(
        self,
        uri: str,
        database_name: str,
        collection_name: str,
        queue_max_size: int = 1000,
        batch_size: int = 50,
        **kwargs,
    ):
        super().__init__(queue_max_size)
        client = AsyncIOMotorClient(uri, **kwargs)
        db = client[database_name]
        self.collection = db[collection_name]
        self.batch_size = batch_size
        self.batch: list[logging.LogRecord] = []
        self.log_listener: asyncio.Task | None = None
        self._mongo_ready_event = asyncio.Event()

    async def _consumer_loop(self) -> None:
        # Signal that the task has started
        self._mongo_ready_event.set()
        try:
            while True:
                # This will raise asyncio.QueueShutDown when the queue
                # is empty AFTER shutdown() is called in the stop() method.
                record = await self.logs_queue.get()

                self.batch.append(record)
                if len(self.batch) >= self.batch_size:
                    await self._flush_batch()

        except (asyncio.QueueShutDown, EOFError):
            pass
        finally:
            # This catches any partial batch (e.g., 2 logs when batch_size is 3)
            await self._flush_batch()

    async def _flush_batch(self) -> None:
        if not self.batch:
            return

        try:
            await self.collection.insert_many(self.batch)
        except PyMongoError as e:
            sys.stderr.write(f"[Logging] error insert batch of logs: {e}")
        finally:
            for _ in range(len(self.batch)):
                self.logs_queue.task_done()
            self.batch.clear()

    async def start(self) -> None:
        # Schedule the logs consumer in the event loop
        self.log_listener = asyncio.create_task(self._consumer_loop())

        # Start the log consumer and reassure that is actually running
        await self._mongo_ready_event.wait()

        try:
            await self.collection.database.command("ping")
        except (ConnectionFailure, OperationFailure) as e:
            sys.stderr.write(f"[Logging] Failed to connect to MongoDB server: {e}\n")

    async def stop(self):
        self.logs_queue.shutdown()

        await self.logs_queue.join()

        if self.log_listener and not self.log_listener.done():
            self.log_listener.cancel()
            try:
                await self.log_listener
            except asyncio.CancelledError:
                pass


class TestMongoHandler(AsyncMongoHandler):
    def __init__(
        self,
        uri: str = f"mongodb://{mongo_user}:{mongo_password}@{mongo_host}:{mongo_port}/admin?authSource=admin",
        database_name: str = "dv-notes",
        collection_name: str = "test_logs",
        queue_max_size: int = 1000,
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
