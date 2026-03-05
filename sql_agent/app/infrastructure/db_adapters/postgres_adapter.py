# PostgreSQL-specific
"""PostgreSQL Database Adapter"""
import psycopg2
import psycopg2.extras
from app.infrastructure.db_adapters.base_adapter import BaseDatabaseAdapter

class PostgresAdapter(BaseDatabaseAdapter):

    def __init__(self, config):
        self.config = config
        self.connection = None

    def connect(self):
        self.connection = psycopg2.connect(**self.config)

    def get_schema(self):
        query = """
        SELECT table_name, column_name, data_type
        FROM information_schema.columns
        WHERE table_schema = 'public'
        """

        cursor = self.connection.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cursor.execute(query)
        rows = cursor.fetchall()
        cursor.close()

        schema = {}
        for row in rows:
            table = row["table_name"]
            if table not in schema:
                schema[table] = []
            schema[table].append({
                "column": row["column_name"],
                "type": row["data_type"]
            })

        return schema

    def execute(self, query):
        cursor = self.connection.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cursor.execute(query)
        rows = cursor.fetchall()
        cursor.close()
        return [dict(r) for r in rows]