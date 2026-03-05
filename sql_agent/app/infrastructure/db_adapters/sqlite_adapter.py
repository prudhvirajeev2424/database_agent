# SQLite-specific
"""SQLite Database Adapter"""
import sqlite3
from app.infrastructure.db_adapters.base_adapter import BaseDatabaseAdapter

class SQLiteAdapter(BaseDatabaseAdapter):

    def __init__(self, config):
        self.config = config
        self.connection = None

    def connect(self):
        self.connection = sqlite3.connect(self.config["database"])
        self.connection.row_factory = sqlite3.Row

    def get_schema(self):
        cursor = self.connection.cursor()
        tables = cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table';"
        ).fetchall()

        schema = {}
        for table in tables:
            table_name = table[0]
            columns = cursor.execute(f"PRAGMA table_info({table_name});").fetchall()
            schema[table_name] = [
                {"column": col[1], "type": col[2]} for col in columns
            ]

        return schema

    def execute(self, query):
        cursor = self.connection.cursor()
        cursor.execute(query)
        rows = cursor.fetchall()
        return [dict(row) for row in rows]