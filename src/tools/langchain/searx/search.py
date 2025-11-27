"""
=============================================================================
SEARXNG SEARCH TOOL - Privacy-Respecting Web Search
=============================================================================

This tool searches the web using SearxNG metasearch engine. It aggregates
results from multiple search engines while protecting user privacy.

WHEN TO USE:
- General web searches for information
- When you need results from multiple search engines
- When you want fast results without scraping content

USE FIRECRAWL_SEARCH INSTEAD WHEN:
- You need the actual page content, not just URLs/snippets
- You want search + content extraction in one step

=============================================================================
"""

import os
from typing import Any, Dict, List
from datetime import datetime
from langchain_core.tools import tool

from tools.langchain.base import LangChainTool
from . import SEARX_HOST, SEARX_DEFAULT_NUM_RESULTS


class SearxSearchTool(LangChainTool):
    """
    Tool for searching the web using SearxNG metasearch engine.
    
    This tool uses the langchain-community SearxSearchWrapper to query
    a SearxNG instance. Results include titles, URLs, snippets, and
    the source engines that provided each result.
    
    Features:
        - Aggregates results from 70+ search engines
        - Privacy-respecting (no tracking)
        - Returns structured results with source attribution
        - Category filtering (general, images, news, etc.)
    
    Requirements:
        - langchain-community package
        - Running SearxNG instance
    
    Example Usage:
        ```python
        tool = SearxSearchTool()
        result = await tool.execute(
            query="python asyncio tutorial",
            num_results=5,
            categories="general"
        )
        ```
    
    Result Format:
        Formatted markdown with:
        - Search query
        - Result count
        - For each result: title, URL, source engines, category, snippet
    """
    
    # -------------------------------------------------------------------------
    # Tool Configuration
    # -------------------------------------------------------------------------
    
    name = "searx_search"
    """Tool name - must match the function name in get_langchain_tool()."""
    
    description = "Search the web using SearxNG metasearch engine. Returns structured results with titles, snippets, links, and source engines from multiple search engines."
    """Description shown to the LLM when selecting tools."""
    
    # -------------------------------------------------------------------------
    # Schema Definition
    # -------------------------------------------------------------------------
    
    def get_schema(self) -> Dict[str, Dict[str, Any]]:
        """Define the parameters for the search tool."""
        return {
            "query": {
                "type": "string",
                "required": True,
                "description": "The search query string."
            },
            "num_results": {
                "type": "integer",
                "required": False,
                "default": SEARX_DEFAULT_NUM_RESULTS,
                "description": f"Number of results to return. Default: {SEARX_DEFAULT_NUM_RESULTS}"
            },
            "categories": {
                "type": "string",
                "required": False,
                "default": "general",
                "description": "Search category. Options: 'general', 'images', 'news', 'videos', 'music', 'files', 'it', 'science', 'social_media'. Default: 'general'"
            }
        }
    
    # -------------------------------------------------------------------------
    # LangChain Tool Definition
    # -------------------------------------------------------------------------
    
    def get_langchain_tool(self):
        """Return the LangChain @tool decorated function."""
        @tool
        def searx_search(
            query: str,
            num_results: int = SEARX_DEFAULT_NUM_RESULTS,
            categories: str = "general"
        ) -> str:
            """
            Search the web using SearxNG metasearch engine.
            
            Use this tool for general web searches. It returns results from
            multiple search engines with titles, URLs, and snippets.
            
            This is a privacy-respecting search - no tracking or user profiling.
            
            Args:
                query: The search query string
                num_results: Number of results to return (default: 5)
                categories: Search category (default: 'general')
            
            Returns:
                Formatted search results with titles, URLs, snippets, and sources
            """
            return "LANGCHAIN_TOOL_PLACEHOLDER"
        
        return searx_search
    
    # -------------------------------------------------------------------------
    # Execution
    # -------------------------------------------------------------------------
    
    async def execute(
        self, 
        query: str, 
        num_results: int = SEARX_DEFAULT_NUM_RESULTS, 
        categories: str = "general"
    ) -> str:
        """
        Execute the SearxNG search and return formatted results.
        
        Uses langchain-community's SearxSearchWrapper to perform the search.
        Results are formatted as markdown for easy LLM consumption.
        
        Args:
            query: Search query string
            num_results: Number of results to return
            categories: Search category (general, news, images, etc.)
        
        Returns:
            Formatted markdown string with search results
        """
        print(f"\n{'#'*80}")
        print(f"# SEARX SEARCH EXECUTE")
        print(f"# Query: {query}")
        print(f"# Num Results: {num_results}")
        print(f"# Categories: {categories}")
        print(f"# Host: {SEARX_HOST}")
        print(f"{'#'*80}")
        
        try:
            from langchain_community.utilities import SearxSearchWrapper
            
            # Initialize the SearxNG wrapper
            search = SearxSearchWrapper(
                searx_host=SEARX_HOST,
                k=num_results,
                categories=[categories] if categories else ["general"]
            )
            
            # Use .results() for structured data
            results = search.results(query, num_results=num_results)
            
            print(f"\n✅ SearxNG returned {len(results)} results")
            
            if not results:
                return "No search results found for the query."
            
            # Format results for LLM consumption
            formatted_output = f"## Search Results for: \"{query}\"\n\n"
            formatted_output += f"*Found {len(results)} results from SearxNG metasearch*\n\n"
            
            for idx, result in enumerate(results, 1):
                title = result.get('title', 'No Title')
                link = result.get('link', '')
                snippet = result.get('snippet', 'No description available')
                engines = result.get('engines', [])
                category = result.get('category', 'general')
                
                # Format each result as a structured block
                formatted_output += f"### Result {idx}: {title}\n"
                formatted_output += f"**URL:** {link}\n"
                formatted_output += f"**Source Engines:** {', '.join(engines) if engines else 'Unknown'}\n"
                formatted_output += f"**Category:** {category}\n"
                formatted_output += f"**Snippet:** {snippet}\n\n"
                formatted_output += "---\n\n"
            
            print(f"\n📄 Formatted output preview (first 500 chars):\n{formatted_output[:500]}")
            
            return formatted_output
            
        except ImportError as e:
            error_msg = "SearxNG Search Error: langchain_community not installed. Install with: pip install langchain-community"
            print(f"\n❌ {error_msg}")
            return error_msg
        except Exception as e:
            error_msg = f"SearxNG Search Error: {type(e).__name__}: {str(e)}"
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
        Extract citation metadata from SearxNG search results.
        
        Returns metadata about the search including query, result count,
        and source engines.
        """
        return {
            "tool": self.name,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "source_type": "web_search",
            "search_engine": "searxng_metasearch",
            "host": SEARX_HOST,
            "query": tool_args.get("query", ""),
            "num_results_requested": tool_args.get("num_results", SEARX_DEFAULT_NUM_RESULTS),
            "category": tool_args.get("categories", "general"),
        }
