#!/usr/bin/env python3
"""
Test script to verify MCP server connection and tool execution.
Run this to debug MCP connectivity issues before testing the full agent.

Usage:
    python src/test_mcp_connection.py
"""
import asyncio
import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from utils.tools import MCPClient, MCP_SERVER_URL, execute_mcp_tool


async def test_mcp_connection():
    """Test basic MCP server connectivity."""
    print("=" * 80)
    print("MCP CONNECTION TEST")
    print("=" * 80)
    print(f"\nTarget MCP Server: {MCP_SERVER_URL}")
    print("-" * 80)
    
    # Create client
    client = MCPClient(MCP_SERVER_URL)
    
    # Test 1: Initialize
    print("\n[TEST 1] Initialize MCP Session")
    print("-" * 40)
    init_result = await client.initialize()
    
    if "error" in init_result:
        print(f"❌ INITIALIZATION FAILED: {init_result['error']}")
        return False
    else:
        print(f"✅ Initialization successful!")
    
    # Test 2: List tools
    print("\n[TEST 2] List Available Tools")
    print("-" * 40)
    tools_result = await client.list_tools()
    
    if "error" in tools_result:
        print(f"❌ LIST TOOLS FAILED: {tools_result['error']}")
    else:
        print(f"✅ Tools listed successfully!")
        if "result" in tools_result and "tools" in tools_result.get("result", {}):
            tools = tools_result["result"]["tools"]
            print(f"\nAvailable tools ({len(tools)}):")
            for tool in tools:
                print(f"  - {tool.get('name', 'unknown')}: {tool.get('description', 'No description')[:60]}...")
    
    # Test 3: Execute a simple scrape
    print("\n[TEST 3] Execute firecrawl_scrape on example.com")
    print("-" * 40)
    
    scrape_result = await execute_mcp_tool(
        "firecrawl_scrape",
        {"url": "https://example.com"}
    )
    
    if scrape_result.startswith("MCP Error"):
        print(f"❌ SCRAPE FAILED: {scrape_result}")
        return False
    else:
        print(f"✅ Scrape successful!")
        print(f"\nScraped content length: {len(scrape_result)} characters")
        print(f"\nContent preview (first 500 chars):")
        print("-" * 40)
        print(scrape_result[:500])
        print("-" * 40)
        if len(scrape_result) > 500:
            print(f"... ({len(scrape_result) - 500} more characters)")
    
    print("\n" + "=" * 80)
    print("ALL TESTS PASSED ✅")
    print("=" * 80)
    return True


async def test_specific_url(url: str):
    """Test scraping a specific URL."""
    print("=" * 80)
    print(f"SCRAPE TEST: {url}")
    print("=" * 80)
    
    result = await execute_mcp_tool(
        "firecrawl_scrape",
        {"url": url, "formats": ["markdown"], "onlyMainContent": True}
    )
    
    print(f"\nResult length: {len(result)} characters")
    print(f"\nFull content:")
    print("-" * 80)
    print(result)
    print("-" * 80)
    
    return result


if __name__ == "__main__":
    if len(sys.argv) > 1:
        # Test specific URL
        url = sys.argv[1]
        asyncio.run(test_specific_url(url))
    else:
        # Run connection tests
        success = asyncio.run(test_mcp_connection())
        sys.exit(0 if success else 1)
