
import asyncio
import json
import io
from contextlib import redirect_stdout
from mcp_client_test import get_all_tools, tavily_mcp_search


if __name__ == "__main__":

    user_question = input("Enter your search query: ")

    captured_output = io.StringIO()

    with redirect_stdout(captured_output):
        result = asyncio.run(
            tavily_mcp_search(query=user_question)
        )

    print("\n========== FORMATTED SEARCH RESULTS ==========\n")

    if isinstance(result, list):
        response_blocks = result
    else:
        response_blocks = [result]

    for response_block in response_blocks:

        if isinstance(response_block, dict):
            response_text = response_block.get("text", "")
        elif hasattr(response_block, "text"):
            response_text = response_block.text
        else:
            response_text = str(response_block)

        try:
            search_data = json.loads(response_text)
        except (json.JSONDecodeError, TypeError):
            print(response_text)
            continue

        if not isinstance(search_data, dict):
            print(search_data)
            continue

        if "error" in search_data:
            print("Search Error:", search_data["error"])
            print("Details:", search_data.get("detail", ""))
            continue

        search_results = search_data.get("results", [])

        if not search_results:
            print("No search results found.")
            continue

        for number, search_item in enumerate(search_results[:3], start=1):

            title = search_item.get("title", "No title")
            url = search_item.get("url", "No URL")
            content = search_item.get("content", "")
            score = search_item.get("score", "N/A")

            clean_content = " ".join(str(content).split())

            print(f"\n{number}. Title: {title}")
            print(f"   URL: {url}")
            print(f"   Content: {clean_content[:200]}...")
            print(f"   Score: {score}")
            print("-" * 60)
