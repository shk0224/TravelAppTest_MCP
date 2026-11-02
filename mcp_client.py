import os
import sys
from pathlib import Path

import certifi
from dotenv import load_dotenv
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_groq import ChatGroq


# ==========================================
# Environment configuration
# ==========================================

os.environ["SSL_CERT_FILE"] = certifi.where()
os.environ["REQUESTS_CA_BUNDLE"] = certifi.where()

load_dotenv()

# Environment variable names must match the keys in your .env file.
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
AVIATION_STACK_API_KEY = os.getenv("AVIATIONSTACK_API_KEY")
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# Local variables: these names can be changed if references are updated.
PROJECT_DIR = Path(__file__).resolve().parent
WEATHER_SERVER_PATH = PROJECT_DIR / "custom_weather_mcp_server.py"

# Keep the Windows environment when starting local MCP servers.
AVIATION_ENV = os.environ.copy()
AVIATION_ENV["AVIATION_STACK_API_KEY"] = AVIATION_STACK_API_KEY or ""

WEATHER_ENV = os.environ.copy()
WEATHER_ENV["OPENWEATHER_API_KEY"] = OPENWEATHER_API_KEY or ""


# ==========================================
# LLM
# ==========================================

# llm is an object variable; ChatGroq is an imported class.
llm = ChatGroq(
    model="openai/gpt-oss-20b",
    api_key=GROQ_API_KEY
)


# ==========================================
# MCP client configuration
# ==========================================

# Server names below must match the names used in MCP calls.
client = MultiServerMCPClient(
    {
        "tavily": {
            "transport": "streamable_http",
            "url": (
                "https://mcp.tavily.com/mcp/"
                f"?tavilyApiKey={TAVILY_API_KEY}"
            )
        },
        "aviationstack": {
            "transport": "stdio",
            "command": "uvx",
            "args": ["aviationstack-mcp"],
            "env": AVIATION_ENV
        },
        "weather": {
            "transport": "stdio",
            "command": sys.executable,
            "args": [str(WEATHER_SERVER_PATH)],
            "env": WEATHER_ENV
        }
    }
)


# ==========================================
# Diagnostic function
# ==========================================

async def get_all_tools():
    """Print available tools from each MCP server independently."""
    all_tools = []  # Local list variable; renameable.

    for server_name in ("tavily", "aviationstack", "weather"):
        try:
            tools = await client.get_tools(server_name=server_name)
            all_tools.extend(tools)

            print(f"\nAvailable tools from {server_name} MCP:\n")
            for tool in tools:
                print(tool.name)

        except Exception as error:
            print(f"\nCould not connect to {server_name} MCP:\n{error}\n")

    return all_tools


# ==========================================
# Tavily MCP tool
# ==========================================

search_tool = None  # Global variable holding the selected tool object.


async def initialize_mcp():
    """Load only Tavily and select its registered search tool."""
    global search_tool

    if search_tool is not None:
        return

    tools = await client.get_tools(server_name="tavily")
    tools_by_name = {tool.name: tool for tool in tools}

    # Registered tool name: do not rename unless the server changes it.
    search_tool = tools_by_name.get("tavily_search")

    if search_tool is None:
        available_tools = ", ".join(tools_by_name.keys())
        raise RuntimeError(
            "Tavily MCP connected, but the "
            "'tavily_search' tool was not found. "
            f"Available tools: {available_tools or 'none'}"
        )


async def tavily_mcp_search(query: str):
    """Run the Tavily search tool using a search query."""
    await initialize_mcp()
    result = await search_tool.ainvoke({"query": query})
    return result


# ==========================================
# AviationStack MCP tools
# ==========================================

aviation_tools = {}  # Global dictionary: tool name -> tool object.


async def initialize_aviation_tools():
    """Load AviationStack tools without starting other MCP servers."""
    global aviation_tools

    if aviation_tools:
        return

    tools = await client.get_tools(server_name="aviationstack")
    aviation_tools = {tool.name: tool for tool in tools}

    if not aviation_tools:
        raise RuntimeError(
            "AviationStack MCP connected but returned no tools."
        )


async def aviation_mcp_call(tool_name: str, tool_args: dict = None):
    """Call an AviationStack tool by its registered name."""
    await initialize_aviation_tools()

    tool = aviation_tools.get(tool_name)
    if tool is None:
        available_tools = ", ".join(sorted(aviation_tools.keys()))
        raise ValueError(
            f"AviationStack tool '{tool_name}' was not found. "
            f"Available tools: {available_tools or 'none'}"
        )

    result = await tool.ainvoke(tool_args or {})
    return result


# ==========================================
# Common MCP calling pattern (NEW)
# ==========================================

async def mcp_call(server_name: str, tool_name: str, tool_args: dict = None):
    """Call a selected MCP tool using server name, tool name, and inputs."""
    # Parameter names here are user-defined and can be renamed consistently.
    # Server and tool name VALUES must match the MCP configuration/server.
    if server_name == "aviationstack":
        return await aviation_mcp_call(tool_name, tool_args)

    if server_name == "tavily":
        if tool_name != "tavily_search":
            raise ValueError(f"Unsupported Tavily tool: {tool_name}")
        await initialize_mcp()
        return await search_tool.ainvoke(tool_args or {})

    raise ValueError(f"Unsupported MCP server: {server_name}")


# ==========================================
# Weather MCP tools
# ==========================================

weather_tool = None
forecast_tool = None


async def initialize_weather_tools():
    """Load the current-weather and forecast tools from the local server."""
    global weather_tool
    global forecast_tool

    if weather_tool is not None and forecast_tool is not None:
        return

    if not WEATHER_SERVER_PATH.exists():
        raise FileNotFoundError(
            "Weather MCP server file was not found: "
            f"{WEATHER_SERVER_PATH}"
        )

    tools = await client.get_tools(server_name="weather")
    tools_by_name = {tool.name: tool for tool in tools}

    weather_tool = tools_by_name.get("get_current_weather")
    forecast_tool = tools_by_name.get("get_forecast")

    missing_tools = []
    if weather_tool is None:
        missing_tools.append("get_current_weather")
    if forecast_tool is None:
        missing_tools.append("get_forecast")

    if missing_tools:
        available_tools = ", ".join(tools_by_name.keys())
        raise RuntimeError(
            "Missing Weather MCP tools: "
            f"{', '.join(missing_tools)}. "
            f"Available tools: {available_tools or 'none'}"
        )


async def weather_mcp_search(city: str):
    """Fetch current weather for the provided destination city."""
    await initialize_weather_tools()
    result = await weather_tool.ainvoke({"city": city})
    return result


async def forecast_mcp_search(city: str):
    """Fetch a forecast for the provided destination city."""
    await initialize_weather_tools()
    result = await forecast_tool.ainvoke({"city": city})
    return result


# ==========================================
# Destination extractor
# ==========================================

def extract_destination(query: str):
    """Ask the LLM to extract the destination from the user request."""
    prompt = f"""
    Extract only the destination city or country.

    Query:
    {query}

    Return only destination name.
    """

    response = llm.invoke(prompt)
    return response.content.strip()
