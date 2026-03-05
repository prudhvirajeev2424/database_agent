# MySQL-specific
"""MySQL Database Adapter"""
import mysql.connector
from mysql.connector import Error
from app.infrastructure.db_adapters.base_adapter import BaseDatabaseAdapter
from app.infrastructure.logger import AppLogger


class MySQLAdapter(BaseDatabaseAdapter):

    def __init__(self, config):
        self.config = config
        self.connection = None

    def connect(self):
        try:
            cfg = dict(self.config)
            # ensure numeric port when provided as a string
            if "port" in cfg and isinstance(cfg["port"], str) and cfg["port"].isdigit():
                cfg["port"] = int(cfg["port"])

            self.connection = mysql.connector.connect(**cfg)
            AppLogger.info(f"MySQL connected to {cfg.get('host')}:{cfg.get('port', '')}")
        except Error as e:
            AppLogger.error(f"MySQL connection failed: {e}")
            raise

    def get_schema(self):
        query = """
        SELECT TABLE_NAME, COLUMN_NAME, DATA_TYPE
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
        ORDER BY TABLE_NAME, ORDINAL_POSITION
        """

        cursor = self.connection.cursor(dictionary=True)
        cursor.execute(query)
        rows = cursor.fetchall()
        cursor.close()

        schema = {}
        for row in rows:
            table = row["TABLE_NAME"]
            if table not in schema:
                schema[table] = []
            schema[table].append({
                "column": row["COLUMN_NAME"],
                "type": row["DATA_TYPE"]
            })

        return schema

    def execute(self, query):
        cursor = self.connection.cursor(dictionary=True)
        cursor.execute(query)
        rows = cursor.fetchall()
        cursor.close()
        return rows