# Database adapter tests
"""Simple DB connection tester for the project.

Run from the project venv to validate `.env` / `Config` settings.
Usage:
    python scripts/test_db.py
"""
import sys
from dotenv import load_dotenv
load_dotenv()

from app.config import Config
import mysql.connector


def main():
    cfg = dict(Config.DB_CONFIG)
    print("Using DB config:", cfg)

    try:
        # ensure port type
        if "port" in cfg and isinstance(cfg["port"], str) and cfg["port"].isdigit():
            cfg["port"] = int(cfg["port"])

        conn = mysql.connector.connect(**cfg)
        print("OK - connected to MySQL server")
        conn.close()
    except Exception as e:
        print("CONNECT ERROR:", e)
        sys.exit(1)


if __name__ == '__main__':
    main()
