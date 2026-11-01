
import os 
import asyncio
import certifi 
from dotenv import load_dotenv
from langchain_mcp_adapters.client import MultiServerMCPClient

os.environ["SSL_CERT_FILE"]= certifi.where()
os.environ["REQUESTS_CA_BUNDLE"]= certifi.where()

load_dotenv()

TAVILY_API_KEY= os.getenv("TAVILY_API_KEY")

if not TAVILY_API_KEY or not TAVILY_API_KEY.startswith("tvly-"):
    raise ValueError("Please check your TAVILY_API_KEY in .env file")


client = MultiServerMCPClient(
    {
       "tavily": {
            "transport": "streamable_http",
            "url": f"https://mcp.tavily.com/mcp/?tavilyApiKey={TAVILY_API_KEY}"
        },
  
    }
)

# this func will return all the tools i have for mcp right now
# to implement one mcp server, i need to create one mcp cient.
# then need to create mcp server. then inside mcp server, i will be having mcp tools.
# to implement this tool, i need api. these four steps need to follow to develop one mcp.


async def get_all_tools():
    tools = await client.get_tools()

    print("\nAvailable MCP Tools:\n")

    for number, tool in enumerate(tools, start=1):
        print(f"{number}. {tool.name}")


# This retuns tavily_search tool object
tavily_search_tool = None

async def get_tavily_search_tool():
    global tavily_search_tool
    if tavily_search_tool is not None:
        return tavily_search_tool

    tools = await client.get_tools()
    print("\nAvailable MCP Tools:")

    for tool in tools:
        print(tool.name)

    tavily_search_tool = next(
        tool
        for tool in tools
        if tool.name == "tavily_search"
    )

    return tavily_search_tool


# This function can be used to call the tavily_search tool with a query in backend.py
async def tavily_mcp_search(query: str):
    await get_tavily_search_tool()
    result = await tavily_search_tool.ainvoke(
        {
            "query": query
        }
    )
    # print(result)
    return result
