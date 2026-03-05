# MongoDB-specific
"""MongoDB Database Adapter"""
import json
from typing import Any, Dict, Optional
from pymongo import MongoClient
from pymongo.errors import PyMongoError
from app.infrastructure.db_adapters.base_adapter import BaseDatabaseAdapter


class MongoDBAdapter(BaseDatabaseAdapter):

    def __init__(self, uri: str, database: str = None):
        self.uri = uri
        self.client: Optional[MongoClient] = None
        self.database_name = database

    def connect(self):
        try:
            self.client = MongoClient(self.uri)
            # lazily set database name from URI if not provided
            if not self.database_name:
                # try to parse from uri path
                parts = self.uri.split('/')
                if len(parts) > 3 and parts[-1]:
                    self.database_name = parts[-1].split('?')[0]
        except PyMongoError as e:
            raise Exception(f"MongoDB connection error: {e}")

    def execute(self, query: str):
        """
        Execute a simple MongoDB textual command.

        Supported formats (string input):
        - find <collection> <json_filter> [<limit>]
          Example: 'find customers {"age": {"$gt": 30}} 10'
        - aggregate <collection> <json_pipeline>
          Example: 'aggregate sales [{"$match": {"amt": {"$gt": 100}}}, {"$limit": 5}]'

        Alternatively, `query` can be a JSON string representing an object
        with explicit action keys: {"action":"find", "collection":"x", "filter":{...}}
        """
        if not self.client:
            raise Exception("MongoDB client not connected")

        db = self.client[self.database_name] if self.database_name else None
        if db is None:
            raise Exception("No MongoDB database selected")

        # try parsing JSON object first
        try:
            payload = json.loads(query)
        except Exception:
            payload = None

        try:
            if isinstance(payload, dict):
                action = payload.get("action", "find")
                collection = payload["collection"]
                if action == "find":
                    filt = payload.get("filter", {})
                    limit = int(payload.get("limit", 0))
                    cursor = db[collection].find(filt)
                    if limit > 0:
                        cursor = cursor.limit(limit)
                    return [doc for doc in cursor]
                if action == "aggregate":
                    pipeline = payload.get("pipeline", [])
                    cursor = db[collection].aggregate(pipeline)
                    return [doc for doc in cursor]

            # fallback: textual command parsing
            parts = query.strip().split(None, 2)
            if len(parts) < 2:
                raise ValueError("Invalid MongoDB query string")

            cmd = parts[0].lower()
            collection = parts[1]

            if cmd == "find":
                filt = {}
                limit = 0
                if len(parts) >= 3:
                    # try to split filter and optional limit
                    rest = parts[2].rsplit(None, 1)
                    try:
                        maybe_limit = int(rest[-1])
                        limit = maybe_limit
                        filt_text = rest[0]
                    except Exception:
                        filt_text = parts[2]

                    try:
                        filt = json.loads(filt_text)
                    except Exception:
                        filt = {}

                cursor = db[collection].find(filt)
                if limit > 0:
                    cursor = cursor.limit(limit)
                return [doc for doc in cursor]

            if cmd == "aggregate":
                if len(parts) < 3:
                    raise ValueError("aggregate requires a pipeline JSON")
                pipeline = json.loads(parts[2])
                cursor = db[collection].aggregate(pipeline)
                return [doc for doc in cursor]

            raise ValueError(f"Unknown Mongo command: {cmd}")

        except PyMongoError as e:
            raise Exception(f"MongoDB execution error: {e}")

    def get_schema(self):
        """
        Return a lightweight schema: collections and sample keys from first document.
        """
        if not self.client:
            raise Exception("MongoDB client not connected")

        db = self.client[self.database_name] if self.database_name else None
        if db is None:
            raise Exception("No MongoDB database selected")

        schema: Dict[str, Any] = {}
        for coll_name in db.list_collection_names():
            coll = db[coll_name]
            sample = coll.find_one()
            if sample:
                keys = [{"column": k, "type": type(v).__name__} for k, v in sample.items()]
            else:
                keys = []
            schema[coll_name] = keys

        return schema
