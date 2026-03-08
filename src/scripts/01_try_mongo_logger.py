import asyncio
import logging
from contextlib import asynccontextmanager

from pyutils import configure_loggers, AsyncMongoHandler

mongo_logger = logging.getLogger("mongo_logger")


@asynccontextmanager
async def initialize_mongo_handler(logger: logging.Logger):

    configure_loggers(directory="configurations")
    # Find the first handler that is an AsyncMongoHandler
    async_handler = next(
        (h for h in logger.handlers if isinstance(h, AsyncMongoHandler)),
        None
    )
    if not async_handler:
        raise RuntimeError(
            "AsyncMongoHandler was not found in the logger handlers. "
            "Check your 'configurations' directory and ensure the YAML "
            "properly attaches the TestMongoHandler."
        )
    try:
        await async_handler.start()
        yield
    finally:
        await async_handler.stop()


async def main():
    async with initialize_mongo_handler(mongo_logger):
        for i in range(1101):
            if i < 100:
                mongo_logger.info(f"Info message {i}")
            else:
                mongo_logger.error(f"Error message {i}")


if __name__ == "__main__":
    asyncio.run(main())
