"""
Test Multi-Agent System with HTTP MCP Transport
Connects to StreamableHTTP server with real-time progress
"""
import asyncio
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from orchestrator import Orchestrator
from mcp_client_http import HTTPMCPClient
from dotenv import load_dotenv

load_dotenv()

async def test_http_multiagent():
    print("🧪 Testing Multi-Agent System with HTTP Transport\n")
    print("="*60)
    
    # Step 1: Connect to HTTP MCP Server
    print("STEP 1: Connecting to StreamableHTTP MCP Server")
    print("="*60)
    
    mcp_client = HTTPMCPClient(server_url="http://localhost:8001")
    await mcp_client.connect()
    
    print()
    
    # Step 2: Create Orchestrator with HTTP client
    print("="*60)
    print("STEP 2: Creating Orchestrator")
    print("="*60)
    
    orchestrator = Orchestrator(
        api_key=os.getenv("ANTHROPIC_API_KEY"),
        mcp_client=mcp_client
    )
    
    print("✅ Orchestrator ready with HTTP MCP Client")
    print()
    
    # Step 3: Execute task with real Jira changes
    print("="*60)
    print("STEP 3: Executing Task (Watch for SSE progress!)")
    print("="*60)
    
    # Task: Move SCRUM-1 to Done status
    user_query = "Change status of SCRUM-1 to Done"
    
    print(f"Task: {user_query}")
    print("\n🚀 Starting execution...\n")
    
    result = await orchestrator.execute(user_query)
    
    print("\n" + "="*60)
    print("✅ EXECUTION COMPLETE")
    print("="*60)
    
    print(f"\nResult preview:\n{result[:500]}...")
    
    print("\n" + "="*60)
    print("🎯 NOW CHECK JIRA UI!")
    print("="*60)
    print("Go to: https://your-domain.atlassian.net/jira/software/projects/SCRUM/boards/...")
    print("SCRUM-1 should now be in 'Done' status!")
    print()
    
    await mcp_client.disconnect()

if __name__ == "__main__":
    asyncio.run(test_http_multiagent())