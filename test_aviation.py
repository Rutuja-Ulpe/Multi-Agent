import asyncio
import os
from dotenv import load_dotenv
from langchain_mcp_adapters.client import MultiServerMCPClient

load_dotenv()

client = MultiServerMCPClient({
    "aviationstack": {
        "transport": "stdio",
        "command": r"C:\Users\Rutuja\.local\bin\uvx.exe",
        "args": ["aviationstack-mcp"],
        "env": {
            "AVIATION_STACK_API_KEY": os.getenv("AVIATIONSTACK_API_KEY")
        }
    }
})

async def main():
    print("Connecting to AviationStack MCP...", flush=True)

    tools = await client.get_tools()

    print("\nCONNECTED!", flush=True)

    for tool in tools:
        print("-", tool.name, flush=True)

if __name__ == "__main__":
    asyncio.run(main())