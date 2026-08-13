"""
Web Search Skill
Allows the agent to search the web and return results.
"""

import os
import json
from typing import List, Dict, Any

try:
    import requests
except ImportError:
    print("Error: requests library not found. Install with: pip install requests")
    requests = None


def skill(query: str, num_results: int = 5) -> Dict[str, Any]:
    """
    Search the web for information.

    Args:
        query: The search query
        num_results: Number of results to return (default: 5)

    Returns:
        Dictionary with search results
    """
    if not requests:
        return {"error": "requests library not installed"}

    try:
        # Using DuckDuckGo API (no key required)
        url = "https://api.duckduckgo.com/"
        params = {
            "q": query,
            "format": "json",
            "no_redirect": 1,
            "no_html": 1,
        }

        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        results = []

        # Extract results from DuckDuckGo response
        if data.get("RelatedTopics"):
            for item in data["RelatedTopics"][: num_results]:
                if "Text" in item:
                    results.append(
                        {
                            "title": item.get("FirstURL", "").split("/")[-1],
                            "url": item.get("FirstURL", ""),
                            "snippet": item.get("Text", ""),
                        }
                    )

        return {
            "query": query,
            "results": results,
            "count": len(results),
        }

    except Exception as e:
        return {"error": f"Web search failed: {str(e)}"}
