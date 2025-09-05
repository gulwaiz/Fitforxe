# backend/deps.py
import os
from pymongo import MongoClient

MONGO_URI = os.getenv("MONGODB_URI")  # set on Render
DB_NAME   = os.getenv("MONGODB_DB", "fitforxe_prod")

_client = MongoClient(MONGO_URI)
_db = _client[DB_NAME]

def get_db():
    """Return a PyMongo database handle."""
    return _db
