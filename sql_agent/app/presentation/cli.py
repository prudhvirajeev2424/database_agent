# Command-line interface
"""Command Line Interface"""
from app.application.orchestrator import Orchestrator
import asyncio


class CLI:

    def __init__(self):
        self.orchestrator = Orchestrator()

    async def main_async(self):
        """Main async loop - keeps event loop alive for all queries"""
        print("Universal SQL AI Assistant")

        try:
            while True:
                question = input("\nAsk (exit to quit): ")

                if question.lower() == "exit":
                    break

                try:
                    response = await self.orchestrator.handle(question)
                    print("\nResult:\n")
                    print(response)
                except Exception as e:
                    print("Error:", str(e))
        finally:
            # Cleanup database connection when exiting
            if hasattr(self.orchestrator, 'adapter') and hasattr(self.orchestrator.adapter, 'close'):
                await self.orchestrator.adapter.close()

    def run(self):
        """Run CLI with single event loop"""
        asyncio.run(self.main_async())