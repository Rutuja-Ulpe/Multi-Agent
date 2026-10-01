import asyncio
import os
import sys
from dotenv import load_dotenv
from langchain_mcp_adapters.client import MultiServerMCPClient

load_dotenv()

client = MultiServerMCPClient({
    "weather": {
        "transport": "stdio",
        "command": sys.executable,
        "args": [
            os.path.join(
                os.path.dirname(__file__),
                "custom_weather_mcp_server.py"
            )
        ],
        "env": {
            "OPENWEATHER_API_KEY": os.getenv("OPENWEATHER_API_KEY")
        }
    }
})


async def main():
    print("Connecting to Weather MCP...", flush=True)

    tools = await client.get_tools()

    print("\nCONNECTED!", flush=True)

    print("\nAvailable tools:")

    for tool in tools:
        print("-", tool.name)


if __name__ == "__main__":
    asyncio.run(main())