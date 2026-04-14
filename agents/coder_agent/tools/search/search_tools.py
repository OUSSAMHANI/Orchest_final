"""Web-search tools — SRP: external search only."""
from langchain_community.tools import DuckDuckGoSearchRun


def get_search_tools() -> list:
    """Return DuckDuckGo search tool for documentation / error lookup."""
    return [DuckDuckGoSearchRun()]
