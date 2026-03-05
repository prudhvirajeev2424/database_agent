# Instantiation tests
import os
os.environ['DATABASE_URI'] = 'sqlite:///:memory:'
# Provide dummy Azure vars so LLMClient doesn't raise during instantiation
os.environ['AZURE_OPENAI_API_KEY'] = os.environ.get('AZURE_OPENAI_API_KEY', 'testkey')
os.environ['AZURE_OPENAI_DEPLOYMENT'] = os.environ.get('AZURE_OPENAI_DEPLOYMENT', 'test')

from app.agents.orchestrator_agent import Orchestrator
import asyncio

o = Orchestrator()
print('OK instantiated')
print(o.rightshoring.decide('Show top 10 customers by balance', 'DATABASE_QUERY'))

async def run_repeat_test():
	await o.memory.add_user('Show top 10 customers by balance')
	await o.memory.add_assistant('Here are the top 10 customers by balance: ...')
	res = await o.handle('Show top 10 customers by balance')
	print('Handle returned:', res)

asyncio.run(run_repeat_test())
