import os
import asyncio
from dotenv import load_dotenv
from orchestrator import Orchestrator
from mcp_client import MCPClient

load_dotenv()

async def main():
    api_key = os.getenv("ANTHROPIC_API_KEY")
    
    if not api_key:
        print("❌ ANTHROPIC_API_KEY not found in .env")
        return
    
    print("🔌 Connecting to Jira MCP Server...\n")
    
    # Подключаемся к MCP серверу
    mcp_client = MCPClient(
        command="uv",
        args=[
            "--directory",
            "C:\\Users\\ValentynZelinskyi\\Desktop\\jira-mcp",
            "run",
            "mcp",
            "run",
            "mcp_server.py"
        ]
    )
    
    try:
        await mcp_client.connect()
        print("✅ Connected to MCP Server\n")
        
        # Создаём оркестратор с MCP клиентом
        orchestrator = Orchestrator(api_key=api_key, mcp_client=mcp_client)
        
        # Тестовый запрос
        user_query = "Execute: Change status of all Valentyn Zelinskyi's In Progress issues to Done"
        
        print(f"🎯 User Query: {user_query}\n")
        print("=" * 60 + "\n")
        
        # Выполняем задачу
        final_result = await orchestrator.execute(user_query)
        
        print("=" * 60)
        print("\n📊 FINAL RESULT:\n")
        print(final_result)
        
    finally:
        await mcp_client.cleanup()
        print("\n🔌 Disconnected from MCP Server")

if __name__ == "__main__":
    asyncio.run(main())