# Abstract base adapter
"""Base Database Adapter"""
from abc import ABC, abstractmethod

class BaseDatabaseAdapter(ABC):

    @abstractmethod
    async def connect(self):
        """Establish async connection to database"""
        pass

    @abstractmethod
    async def get_schema(self):
        """Get database schema asynchronously"""
        pass

    @abstractmethod
    async def execute(self, query: str):
        """Execute query asynchronously"""
        pass

    @abstractmethod
    async def close(self):
        """Close async connection"""
        pass