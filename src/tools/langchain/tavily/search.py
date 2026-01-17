"""
=============================================================================
TAVILY SEARCH TOOL - AI-Optimized Web Search
=============================================================================

Tavily is a search engine purpose-built for AI agents with:
- Optimized result formatting for LLM consumption
- Built-in answer synthesis
- Superior relevance ranking
- Structured results with content snippets

WHEN TO USE:
- General web searches for current information
- Research questions requiring multiple sources
- Fact-checking and verification
- When you need AI-optimized search results

=============================================================================
"""

import os
from typing import Any, Dict
from datetime import datetime
from langchain_core.tools import tool

from tools.langchain.base import LangChainTool


# Configuration
TAVILY_DEFAULT_MAX_RESULTS = int(os.getenv("TAVILY_MAX_RESULTS", "5"))
TAVILY_DEFAULT_SEARCH_DEPTH = os.getenv("TAVILY_SEARCH_DEPTH", "basic")


class TavilySearchTool(LangChainTool):
    """
    Web search tool using Tavily API.

    Tavily provides search results optimized for AI agents with:
    - Direct answers when available
    - Structured results with content snippets
    - Optional raw content and images
    - Superior relevance ranking

    Environment Variables:
        TAVILY_API_KEY: Your Tavily API key (required)
        TAVILY_MAX_RESULTS: Default max results (default: 5)
        TAVILY_SEARCH_DEPTH: Default search depth (default: "basic")

    Example Usage:
        ```python
        tool = TavilySearchTool()
        result = await tool.execute(
            query="python asyncio tutorial",
            max_results=5,
            search_depth="basic"
        )
        ```
    """

    # -------------------------------------------------------------------------
    # Tool Configuration
    # -------------------------------------------------------------------------

    name = "tavily_search"
    """Tool name - must match the function name in get_langchain_tool()."""

    description = (
        "Search the web using Tavily, an AI-optimized search engine. "
        "Returns comprehensive, accurate, and trusted results with snippets. "
        "Use for questions about current events, facts, or any web research."
    )
    """Description shown to the LLM when selecting tools."""

    # -------------------------------------------------------------------------
    # Schema Definition
    # -------------------------------------------------------------------------

    def get_schema(self) -> Dict[str, Dict[str, Any]]:
        """Define the parameters for the Tavily search tool."""
        return {
            "query": {
                "type": "string",
                "required": True,
                "description": "The search query string."
            },
            "max_results": {
                "type": "integer",
                "required": False,
                "default": TAVILY_DEFAULT_MAX_RESULTS,
                "description": f"Maximum number of results (1-10). Default: {TAVILY_DEFAULT_MAX_RESULTS}"
            },
            "search_depth": {
                "type": "string",
                "required": False,
                "default": TAVILY_DEFAULT_SEARCH_DEPTH,
                "description": "Search depth: 'basic' for speed, 'advanced' for thoroughness. Default: 'basic'"
            },
            "include_answer": {
                "type": "boolean",
                "required": False,
                "default": True,
                "description": "Include AI-generated answer from Tavily. Default: True"
            }
        }

    # -------------------------------------------------------------------------
    # LangChain Tool Definition
    # -------------------------------------------------------------------------

    def get_langchain_tool(self):
        """Return the LangChain @tool decorated function."""
        @tool
        def tavily_search(
            query: str,
            max_results: int = TAVILY_DEFAULT_MAX_RESULTS,
            search_depth: str = TAVILY_DEFAULT_SEARCH_DEPTH,
            include_answer: bool = True
        ) -> str:
            """
            Search the web using Tavily AI-optimized search engine.

            Use this tool for web searches when you need current, accurate information.
            Tavily provides AI-optimized results with comprehensive snippets.

            Args:
                query: The search query string
                max_results: Number of results to return (1-10, default: 5)
                search_depth: 'basic' for speed, 'advanced' for thoroughness
                include_answer: Include AI-generated answer (default: True)

            Returns:
                Formatted search results with titles, URLs, snippets, and optional answer
            """
            return "LANGCHAIN_TOOL_PLACEHOLDER"

        return tavily_search

    # -------------------------------------------------------------------------
    # Execution
    # -------------------------------------------------------------------------

    async def execute(
        self,
        query: str,
        max_results: int = TAVILY_DEFAULT_MAX_RESULTS,
        search_depth: str = TAVILY_DEFAULT_SEARCH_DEPTH,
        include_answer: bool = True
    ) -> str:
        """
        Execute the Tavily search and return formatted results.

        Uses langchain-community's TavilySearchResults or direct API.
        Results are formatted as markdown for easy LLM consumption.

        Args:
            query: Search query string
            max_results: Maximum number of results to return
            search_depth: 'basic' or 'advanced'
            include_answer: Include AI-generated answer

        Returns:
            Formatted markdown string with search results
        """
        print(f"\n{'#'*80}")
        print(f"# TAVILY SEARCH EXECUTE")
        print(f"# Query: {query}")
        print(f"# Max Results: {max_results}")
        print(f"# Search Depth: {search_depth}")
        print(f"# Include Answer: {include_answer}")
        print(f"{'#'*80}")

        # Validate API key
        api_key = os.getenv("TAVILY_API_KEY")
        if not api_key:
            error_msg = (
                "Tavily Search Error: TAVILY_API_KEY environment variable not set. "
                "Get your key at https://tavily.com"
            )
            print(f"\n❌ {error_msg}")
            return error_msg

        try:
            from langchain_community.tools.tavily_search import TavilySearchResults

            # Initialize the Tavily search tool
            tavily_tool = TavilySearchResults(
                max_results=max_results,
                search_depth=search_depth,
                include_answer=include_answer,
                include_raw_content=False,
                include_images=False,
            )

            # Execute the search
            results = tavily_tool.invoke({"query": query})

            print(f"\n✅ Tavily returned {len(results)} results")

            if not results:
                return "No search results found for the query."

            # Format results for LLM consumption
            formatted_output = f"## Tavily Search Results for: \"{query}\"\n\n"
            formatted_output += f"*Found {len(results)} results*\n\n"

            for idx, result in enumerate(results, 1):
                title = result.get('title', 'No Title')
                url = result.get('url', '')
                content = result.get('content', 'No content available')

                # Format each result as a structured block
                formatted_output += f"### Result {idx}: {title}\n"
                formatted_output += f"**URL:** {url}\n"
                formatted_output += f"**Content:** {content}\n\n"
                formatted_output += "---\n\n"

            print(f"\n📄 Formatted output preview (first 500 chars):\n{formatted_output[:500]}")

            return formatted_output

        except ImportError as e:
            error_msg = (
                "Tavily Search Error: langchain_community or tavily-python not installed. "
                "Install with: pip install langchain-community tavily-python"
            )
            print(f"\n❌ {error_msg}")
            return error_msg
        except Exception as e:
            error_msg = f"Tavily Search Error: {type(e).__name__}: {str(e)}"
            print(f"\n❌ {error_msg}")
            return error_msg

    # -------------------------------------------------------------------------
    # Custom Citation Extraction
    # -------------------------------------------------------------------------

    def get_citation_metadata(
        self,
        tool_args: Dict[str, Any],
        tool_result: Any
    ) -> Dict[str, Any]:
        """
        Extract citation metadata from Tavily search results.

        Returns metadata about the search including query, result count,
        and search depth used.
        """
        return {
            "tool": self.name,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "source_type": "web_search",
            "search_engine": "tavily",
            "query": tool_args.get("query", ""),
            "max_results": tool_args.get("max_results", TAVILY_DEFAULT_MAX_RESULTS),
            "search_depth": tool_args.get("search_depth", TAVILY_DEFAULT_SEARCH_DEPTH),
            "description": f"Web search results for: {tool_args.get('query', 'web search')}",
        }
