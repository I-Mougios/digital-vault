# src/backend/__main__.py
import logging
from contextlib import asynccontextmanager

import uvicorn
from fastapi import Depends, FastAPI
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorCollection

from configurations import mongo_host, mongo_password, mongo_port, mongo_user
from shared_utils.dependencies.database import get_collection

# logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
BlogCollection = Depends(get_collection("backend", "blogs"))


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"Connecting to MongoDB at {mongo_host}:{mongo_port}")
    mongo_client = AsyncIOMotorClient(
        f"mongodb://{mongo_user}:{mongo_password}@{mongo_host}:{mongo_port}/admin?authSource=admin"
    )
    app.state.mongo_client = mongo_client
    yield
    mongo_client.close()
    logger.info("MongoDB connection closed")


app = FastAPI(lifespan=lifespan)


@app.get("/")
def root():
    return {"message": "Hello, World!"}


@app.get("/blogs")
async def count_documents(collection: AsyncIOMotorCollection = BlogCollection):
    count = await collection.count_documents({})
    return {"count": count}


if __name__ == "__main__":
    uvicorn.run("backend.__main__:app", host="0.0.0.0", port=8000, reload=True)
