import os

from dotenv import load_dotenv
from icecream import ic

load_dotenv()
ic_enabled = os.getenv("IC_ENABLED", False)

if not ic_enabled:
    ic.disable()

mongo_user = ic(os.getenv("MONGO_INITDB_ROOT_USERNAME"))
mongo_password = ic(os.getenv("MONGO_INITDB_ROOT_PASSWORD"))
mongo_host = ic(os.getenv("MONGO_INITDB_ROOT_HOSTNAME", "localhost"))
mongo_port = ic(os.getenv("MONGO_INITDB_ROOT_PORT", "27017"))


__all__ = ["mongo_user", "mongo_password", "mongo_host", "mongo_port"]
