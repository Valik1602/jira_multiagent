"""
HTTP MCP Client with SSE support
Connects to StreamableHTTP MCP Server
"""
import requests
import json
import sseclient
import threading
import asyncio
from typing import Optional, Dict, Any

class HTTPMCPClient:
    def __init__(self, server_url: str = "http://localhost:8001"):
        self.server_url = server_url
        self.session_id: Optional[str] = None
        self.sse_thread: Optional[threading.Thread] = None
        self.progress_callback = None
        self.connected = False
    
    async def connect(self):
        """Create session and connect to SSE stream"""
        print(f"🔌 Connecting to MCP Server at {self.server_url}")
        
        # Create session
        response = requests.post(f"{self.server_url}/session")
        if response.status_code != 200:
            raise Exception(f"Failed to create session: {response.status_code}")
        
        session_data = response.json()
        self.session_id = session_data["session_id"]
        
        print(f"✅ Session created: {self.session_id}")
        
        # Start SSE listener in background
        self.sse_thread = threading.Thread(
            target=self._listen_sse,
            daemon=True
        )
        self.sse_thread.start()
        
        # Wait for connection
        await asyncio.sleep(0.5)
        self.connected = True
        
        print(f"✅ Connected to SSE stream")
    
    def _listen_sse(self):
        """Listen to SSE stream in background thread"""
        sse_url = f"{self.server_url}/sse/{self.session_id}"
        response = requests.get(sse_url, stream=True)
        client = sseclient.SSEClient(response)
        
        for event in client.events():
            if event.event == "connected":
                print(f"📡 SSE: {event.data}")
            elif event.event == "progress":
                try:
                    data = json.loads(event.data)
                    progress = int(data['progress'] * 100)
                    message = data['message']
                    print(f"   🔄 {progress}% - {message}")
                    
                    # Call progress callback if set
                    if self.progress_callback:
                        self.progress_callback(progress, message)
                except json.JSONDecodeError:
                    pass
    
    async def call_tool(
        self,
        tool_name: str,
        arguments: Dict[str, Any]
    ) -> Any:
        """Call an MCP tool via HTTP"""
        if not self.connected:
            raise Exception("Not connected. Call connect() first.")
        
        # JSON-RPC 2.0 request
        payload = {
            "jsonrpc": "2.0",
            "id": f"call-{tool_name}",
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments
            }
        }
        
        # Make HTTP request
        response = requests.post(
            f"{self.server_url}/mcp/{self.session_id}",
            json=payload,
            timeout=60
        )
        
        if response.status_code != 200:
            raise Exception(f"Tool call failed: {response.status_code}")
        
        result = response.json()
        
        if "error" in result:
            raise Exception(f"Tool error: {result['error']}")
        
        # Extract result content
        content = result.get("result", {}).get("content", [])
        if content and len(content) > 0:
            return content[0].get("text", "")
        
        return result.get("result")
    
    async def list_tools(self):
        """List available tools"""
        response = requests.get(f"{self.server_url}/tools")
        if response.status_code == 200:
            return response.json()["tools"]
        return []
    
    async def disconnect(self):
        """Disconnect from server"""
        self.connected = False
        print("🔌 Disconnected from MCP Server")