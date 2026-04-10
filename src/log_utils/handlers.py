# src/pyutils/log_utils/handlers.py
import asyncio
import logging
import sys
import typing

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorCollection
from pymongo.errors import ConnectionFailure, OperationFailure, PyMongoError


class AsyncHandler(logging.Handler):
    def __init__(self, queue_max_size: int = 1000):
        super().__init__()
        self._logs_queue: asyncio.Queue = asyncio.Queue(queue_max_size)

    def emit(self, record: logging.LogRecord):
        try:
            formatted_record = self.format(record)
            try:
                self._logs_queue.put_nowait(formatted_record)
            except asyncio.QueueFull:
                # Queue is full, drop to prevent blocking the main app
                sys.stderr.write(f"[Logging]: Log queue full, record {formatted_record} ignore\n")
            except asyncio.QueueShutDown:
                # Application is closing, just drop the log
                sys.stderr.write(
                    f"[Logging]: Log queue was shut down, record {formatted_record} ignored\n"
                )
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
        flush_interval: int | float = 5,
        **kwargs,
    ):
        super().__init__(queue_max_size)
        self.uri = uri
        self.database_name = database_name
        self.collection_name = collection_name
        self.batch_size = batch_size
        self.flush_interval = flush_interval
        self.kwargs = kwargs

        self.client: AsyncIOMotorClient | None = None
        self.collection: None | AsyncIOMotorCollection = None
        self._batch: list[typing.Mapping] = []
        self._log_listener: asyncio.Task | None = None
        self._mongo_ready_event = asyncio.Event()

    async def _consumer_loop(self) -> None:
        self._mongo_ready_event.set()
        try:
            while True:
                try:
                    record = await asyncio.wait_for(
                        self._logs_queue.get(), timeout=self.flush_interval
                    )
                    self._batch.append(record)
                except asyncio.TimeoutError:
                    pass

                if len(self._batch) >= self.batch_size or (
                    self._batch and self._logs_queue.empty()
                ):
                    await self._flush_batch()

        except (asyncio.QueueShutDown, EOFError):
            # This is the expected exit path when stop() is called
            pass
        except Exception as e:
            sys.stderr.write(f"[Logging]: Unexpected error in consumer: {e}\n")
        finally:
            # 4. Final cleanup for whatever is left in self._batch
            await self._flush_batch()

    async def _flush_batch(self) -> None:
        if not self._batch:
            return

        try:
            await self.collection.insert_many(self._batch)  # type: ignore[union-attr]
        except PyMongoError as e:
            sys.stderr.write(f"[Logging]: error insert batch of logs: {e}\n")
        finally:
            n_remaining = len(self._batch)
            for _ in range(n_remaining):
                self._logs_queue.task_done()
            self._batch.clear()

    async def start(self) -> None:
        self.client = AsyncIOMotorClient(self.uri, **self.kwargs)
        self.collection = self.client[self.database_name][self.collection_name]

        try:
            await self.collection.database.command("ping")
        except (ConnectionFailure, OperationFailure) as e:
            sys.stderr.write(f"[Logging]: Failed to connect to MongoDB server: {e}\n")

        # Schedule the log consumer in the event loop
        self._log_listener = asyncio.create_task(self._consumer_loop())

        # Start the log consumer and reassure that is actually running
        await self._mongo_ready_event.wait()

    async def stop(self):
        self._logs_queue.shutdown()

        try:
            await asyncio.wait_for(self._logs_queue.join(), timeout=2.0)
        except asyncio.TimeoutError:
            pass

        if self.client:
            self.client.close()

        if self._log_listener and not self._log_listener.done():
            self._log_listener.cancel()
            try:
                await self._log_listener
            except asyncio.CancelledError:
                pass
