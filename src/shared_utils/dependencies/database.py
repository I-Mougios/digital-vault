# src/shared_utils/dependencies/database.py
from typing import Callable

from fastapi import Request
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorCollection


def get_collection(
    database_name: str, collection_name: str
) -> Callable[[], AsyncIOMotorCollection]:
    """
    Returns a function that retrieves a specific collection from a pre-defined database.
    """

    # This is the 'dependency' function FastAPI will call
    def _get_collection(request: Request) -> AsyncIOMotorCollection:
        client: AsyncIOMotorClient = request.app.state.mongo_client
        return client[database_name][collection_name]

    return _get_collection
