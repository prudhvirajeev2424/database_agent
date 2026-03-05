# Factory for creating adapters
"""Database Adapter Factory that picks adapter by URI scheme."""

from urllib.parse import urlparse

from app.config import Config
from app.infrastructure.db_adapters.sqlalchemy_adapter import SQLAlchemyAdapter
from app.infrastructure.db_adapters.mongodb_adapter import MongoDBAdapter


class AdapterFactory:

    @staticmethod
    def create_adapter():
        """Create async database adapter based on URI scheme.
        
        Returns an unconnected adapter instance.
        Call adapter.connect() asynchronously to establish connection.
        """
        uri = Config.DATABASE_URI
        parsed = urlparse(uri)
        scheme = parsed.scheme.lower()

        # mongodb:// or mongodb+srv:// -> MongoDB (keep synchronous for now)
        if scheme.startswith("mongodb"):
            adapter = MongoDBAdapter(uri)
            return adapter

        # All SQL databases (mysql, postgresql, sqlite) use async SQLAlchemy
        # Ensure URI uses async-compatible scheme:
        # - mysql+aiomysql://
        # - postgresql+asyncpg://
        # - sqlite+aiosqlite:///
        adapter = SQLAlchemyAdapter(uri)
        return adapter