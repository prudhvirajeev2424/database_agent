# Orchestrator integration tests
import asyncio
import json

from app.infrastructure.db_adapters import adapter_factory


class FakeAdapter:
    def connect(self):
        print("FakeAdapter.connect() called")

    def get_schema(self):
        return {
            "customers": [
                {"column": "id", "type": "INT"},
                {"column": "name", "type": "VARCHAR"},
                {"column": "balance", "type": "DECIMAL"},
            ]
        }

    def execute(self, query):
        # return a small static result set
        return [
            {"id": 1, "name": "Alice", "balance": 12500.5},
            {"id": 2, "name": "Bob", "balance": 9800.0},
            {"id": 3, "name": "Carol", "balance": 7200.25},
        ]


# Monkeypatch the AdapterFactory to return our FakeAdapter
adapter_factory.AdapterFactory.create_adapter = staticmethod(lambda db_type, config: FakeAdapter())


class FakeRespMessage:
    def __init__(self, content):
        self.content = content


class FakeChoice:
    def __init__(self, content):
        self.message = FakeRespMessage(content)


class FakeResponse:
    def __init__(self, content):
        self.choices = [FakeChoice(content)]


class FakeLLMClient:
    async def chat_completion(self, *, messages, temperature=0.0, response_format=None):
        # Return a canned JSON SQL response for the QueryGeneratorAgent
        payload = json.dumps({
            "status": "SUCCESS",
            "query": "SELECT id, name, balance FROM customers ORDER BY balance DESC LIMIT 100"
        })
        return FakeResponse(payload)


async def main():
    # Import here so our monkeypatches are in place
    from app.application.orchestrator import Orchestrator

    # Replace the real LLMClient used in the Orchestrator with our fake
    import app.application.orchestrator as orchestrator_module
    orchestrator_module.LLMClient = FakeLLMClient

    orch = Orchestrator()

    # Replace validator and response agent with lightweight mocks to avoid external LLM calls
    class MockValidator:
        async def validate(self, query, schema=None, db_type="mysql"):
            return {"valid": True, "reason": None, "suggested_fix": None}

    class MockResponseAgent:
        async def generate_response(self, question, result, query=None, history=None, detailed=False):
            return "MOCK RESPONSE: found %d rows" % (len(result) if result else 0)

    orch.validator = MockValidator()
    orch.response_agent = MockResponseAgent()

    prompt = "Top 3 customers by balance"
    out = await orch.handle(prompt)
    print("\n--- Orchestrator Output ---\n")
    print(out)


if __name__ == "__main__":
    asyncio.run(main())
