import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from orchestrator import Orchestrator
from mcp_client_http import HTTPMCPClient
from dotenv import load_dotenv

load_dotenv()

async def main():
    if len(sys.argv) < 2:
        print("Usage: python jira_agent.py \"your task\"")
        print("\nExamples:")
        print('  python jira_agent.py "Change status of SCRUM-1 to Done"')
        return
    
    task = " ".join(sys.argv[1:])
    print(f"🎯 Task: {task}\n")
    
    mcp_client = HTTPMCPClient(server_url="http://localhost:8001")
    await mcp_client.connect()
    
    orchestrator = Orchestrator(
        api_key=os.getenv("ANTHROPIC_API_KEY"),
        mcp_client=mcp_client
    )
    
    print("🚀 Executing...\n")
    result = await orchestrator.execute(task)
    
    print("\n" + "="*60)
    print("✅ RESULT:")
    print("="*60)
    print(result)
    
    await mcp_client.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
