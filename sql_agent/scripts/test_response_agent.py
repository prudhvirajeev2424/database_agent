# Response formatting tests
import os
import sys
import asyncio

# ensure package import works
os.environ['DATABASE_URI'] = 'sqlite:///:memory:'
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.agents.response_agent import ResponseAgent

agent = ResponseAgent(llm=None)

record = {
  "account_id": 13,
  "customer_id": 13,
  "account_number": "ACC10013",
  "account_type": "CURRENT",
  "branch_name": "Kochi Aluva",
  "balance": "210000.00",
  "status": "ACTIVE",
  "opened_date": "2018-05-22"
}

async def run():
    out = await agent.generate_response(
        question="Summarize this account",
        result=record,
        query=None,
        intent={"output_format":"AUTO","operation_type":"DATASET"},
        detailed=False
    )
    print(out)

if __name__ == '__main__':
    asyncio.run(run())
