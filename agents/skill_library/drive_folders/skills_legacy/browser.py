"""
Browser Skill
Allows the agent to navigate websites, extract content, and interact with pages.
Uses subprocess to call curl and basic HTML parsing.
"""

import subprocess
import json
from typing import Dict, Any
from html.parser import HTMLParser


class LinkExtractor(HTMLParser):
    """Extract links from HTML."""

    def __init__(self):
        super().__init__()
        self.links = []

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            for attr, value in attrs:
                if attr == "href":
                    self.links.append(value)


def skill(action: str, url: str = "", selector: str = "", **kwargs) -> Dict[str, Any]:
    """
    Browse the web and extract information.

    Args:
        action: 'fetch', 'extract_links', 'search_text'
        url: URL to fetch
        selector: Text to search for in page content
    """
    try:
        if action == "fetch":
            # Fetch the page content using curl
            result = subprocess.run(
                ["curl", "-s", "-L", url],
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode != 0:
                return {"error": f"Failed to fetch {url}"}

            # Extract plain text (basic approach)
            html_content = result.stdout
            text_content = html_content.replace("<", "\n<").replace(">", ">\n")
            # Remove HTML tags
            import re

            text_content = re.sub(r"<[^>]+>", "", text_content)
            text_content = "\n".join(
                line.strip() for line in text_content.split("\n") if line.strip()
            )

            return {
                "status": "success",
                "url": url,
                "content": text_content[:5000],  # First 5000 chars
                "full_length": len(text_content),
            }

        elif action == "extract_links":
            # Fetch and extract all links
            result = subprocess.run(
                ["curl", "-s", "-L", url],
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode != 0:
                return {"error": f"Failed to fetch {url}"}

            parser = LinkExtractor()
            parser.feed(result.stdout)

            return {
                "status": "success",
                "url": url,
                "links": list(set(parser.links))[:20],  # Top 20 unique links
                "count": len(parser.links),
            }

        elif action == "search_text":
            # Fetch page and search for text
            result = subprocess.run(
                ["curl", "-s", "-L", url],
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode != 0:
                return {"error": f"Failed to fetch {url}"}

            html_content = result.stdout
            import re

            text_content = re.sub(r"<[^>]+>", "", html_content)

            if selector.lower() in text_content.lower():
                # Find context around the match
                idx = text_content.lower().find(selector.lower())
                context = text_content[max(0, idx - 200) : idx + 200 + len(selector)]
                return {
                    "status": "success",
                    "found": True,
                    "url": url,
                    "context": context,
                }
            else:
                return {
                    "status": "success",
                    "found": False,
                    "url": url,
                    "query": selector,
                }

        else:
            return {"error": f"Unknown action: {action}"}

    except subprocess.TimeoutExpired:
        return {"error": "Request timeout"}
    except Exception as e:
        return {"error": f"Browser skill failed: {str(e)}"}
