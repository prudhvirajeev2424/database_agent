class ExecutionEngine:

    def __init__(self, adapter):
        self.adapter = adapter

    async def execute(self, query: str):
        """Execute query asynchronously through adapter"""
        return await self.adapter.execute(query)