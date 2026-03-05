# SQLAlchemy adapter (MySQL, PostgreSQL, SQLite)
import asyncio
from typing import List, Dict

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

try:
    # Optional async imports
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
    from sqlalchemy import inspect as sa_inspect
    HAS_ASYNC = True
except Exception:
    create_async_engine = None
    async_sessionmaker = None
    AsyncSession = None
    sa_inspect = None
    HAS_ASYNC = False

from sqlalchemy import create_engine, inspect as sync_inspect


class SQLAlchemyAdapter:
    """Adapter that supports both async and sync DB drivers.

    Present an async API while using a sync engine in a thread when the
    database driver is synchronous (e.g. `pymysql`). If the URI references an
    async driver (e.g. `+aiomysql`, `+asyncpg`, `+aiosqlite`), it will use an
    async SQLAlchemy engine.
    """

    def __init__(self, database_uri: str):
        self.database_uri = database_uri
        self._uses_async_driver = any(tok in (database_uri or "") for tok in ("+aiomysql", "+asyncpg", "+aiosqlite", "+asyncmy"))

        self._async_engine = None
        self._async_session_maker = None

        self._sync_engine = None

    async def connect(self):
        """Create engine(s)."""
        if self._uses_async_driver:
            if not HAS_ASYNC:
                raise RuntimeError("Async SQLAlchemy support is not available in this environment.")

            self._async_engine = create_async_engine(self.database_uri, pool_pre_ping=True, echo=False)
            self._async_session_maker = async_sessionmaker(self._async_engine, class_=AsyncSession, expire_on_commit=False)
        else:
            def _create():
                return create_engine(self.database_uri, echo=False)

            self._sync_engine = await asyncio.to_thread(_create)

    async def execute(self, query: str) -> List[Dict]:
        """Execute SQL and return list of dict rows."""
        if self._uses_async_driver:
            if not self._async_session_maker:
                raise Exception("Database not connected. Call connect() first.")

            try:
                async with self._async_session_maker() as session:
                    result = await session.execute(text(query))
                    rows = result.mappings().all()
                    return [dict(r) for r in rows]
            except SQLAlchemyError as e:
                raise Exception(f"Database execution error: {e}")
        else:
            if not self._sync_engine:
                raise Exception("Database not connected. Call connect() first.")

            def _exec_sync(q):
                try:
                    with self._sync_engine.connect() as conn:
                        res = conn.execute(text(q))
                        return [dict(row._mapping) for row in res.fetchall()]
                except SQLAlchemyError:
                    raise

            try:
                return await asyncio.to_thread(_exec_sync, query)
            except SQLAlchemyError as e:
                raise Exception(f"Database execution error: {e}")

    async def get_schema(self) -> Dict[str, List[Dict[str, str]]]:
        """Return schema mapping asynchronously."""
        if self._uses_async_driver:
            if not self._async_engine:
                raise Exception("Database not connected. Call connect() first.")

            async with self._async_engine.begin() as conn:
                def _get(sync_conn):
                    inspector = sa_inspect(sync_conn)
                    schema = {}
                    for table_name in inspector.get_table_names():
                        columns = inspector.get_columns(table_name)
                        schema[table_name] = [{"column": col["name"], "type": str(col["type"])} for col in columns]
                    return schema

                schema = await conn.run_sync(_get)
                return schema
        else:
            if not self._sync_engine:
                raise Exception("Database not connected. Call connect() first.")

            def _get_sync():
                inspector = sync_inspect(self._sync_engine)
                schema = {}
                for table_name in inspector.get_table_names():
                    columns = inspector.get_columns(table_name)
                    schema[table_name] = [{"column": col["name"], "type": str(col["type"])} for col in columns]
                return schema

            return await asyncio.to_thread(_get_sync)

    async def close(self):
        if self._uses_async_driver and self._async_engine:
            await self._async_engine.dispose()
            self._async_engine = None
        if self._sync_engine:
            self._sync_engine.dispose()
            self._sync_engine = None