# Configuration management
"""Configuration using SQLAlchemy DATABASE_URI"""

import os
from dotenv import load_dotenv

load_dotenv()


class Config:

    DATABASE_URI = os.getenv("DATABASE_URI")

    if not DATABASE_URI:
        raise ValueError("DATABASE_URI must be set in .env")

    AZURE_OPENAI_KEY = os.getenv("AZURE_OPENAI_API_KEY")
    AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
    AZURE_OPENAI_DEPLOYMENT = os.getenv("AZURE_OPENAI_DEPLOYMENT")
    AZURE_OPENAI_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION")