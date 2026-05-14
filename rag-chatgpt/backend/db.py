# db.py - MongoDB Chat History Storage

import os
from datetime import datetime, timezone
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError


def get_collection():
    uri = os.getenv("MONGO_URI", "mongodb://localhost:27017")
    client = MongoClient(uri, serverSelectionTimeoutMS=3000)
    return client["rag_chatbot"]["chat_history"]


def save_chat(question: str, answer: str, sources: list = None) -> str:
    try:
        collection = get_collection()
        doc = {
            "question": question,
            "answer": answer,
            "sources": sources or [],
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        result = collection.insert_one(doc)
        print(f"[DB] Chat saved: {result.inserted_id}")
        return str(result.inserted_id)
    except (ConnectionFailure, ServerSelectionTimeoutError):
        print("[DB] MongoDB not available - chat not saved (app still works)")
        return "unavailable"
    except Exception as e:
        print(f"[DB] Error: {e}")
        return "error"


def get_recent_chats(limit: int = 20) -> list:
    try:
        collection = get_collection()
        chats = list(
            collection.find({}, {"_id": 0}).sort("timestamp", -1).limit(limit)
        )
        return chats
    except Exception:
        return []


def get_chat_count() -> int:
    try:
        return get_collection().count_documents({})
    except Exception:
        return -1
