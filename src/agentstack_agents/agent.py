"""
=============================================================================
BEEAI AGENT - LangGraph Agent with Modular Tool Architecture
=============================================================================

This is the main agent handler that processes user messages using LangGraph
with modular, extensible tools.

ARCHITECTURE:
-------------

The agent uses a modular tool architecture where tools are:
1. Registered in the tools/ package
2. Automatically discovered by the factory
3. Executed via the appropriate handler (MCP or LangChain)

ADDING NEW TOOLS:
-----------------

1. For MCP tools: See tools/mcp/README.md or existing tools in tools/mcp/firecrawl/
2. For LangChain tools: See tools/langchain/README.md or tools/langchain/searx/

After adding tools, they are automatically available to the agent.

CUSTOMIZING THE AGENT:
----------------------

1. To change available tools: Modify the tools list passed to create_langgraph_agent()
2. To change the system prompt: Modify the system_prompt parameter
3. To change the LLM: Modify the api_model, api_key, api_base parameters

AGENT DETAIL TOOLS:
-------------------

The AgentDetailTool list in the @server.agent decorator should be manually
maintained to match the tools you want to advertise in the BeeAI UI.
Add entries for new tools you want users to see.

=============================================================================
"""

import os
import json
from collections.abc import AsyncGenerator
from typing import Annotated
from a2a.types import Message
from a2a.utils.message import get_message_text
from agentstack_sdk.server import Server
from agentstack_sdk.server.context import RunContext
from agentstack_sdk.a2a.types import AgentMessage, RunYield
from agentstack_sdk.a2a.extensions import (
    AgentDetail,
    AgentDetailContributor,
    AgentDetailTool,
    CitationExtensionServer,
    CitationExtensionSpec,
    TrajectoryExtensionServer,
    TrajectoryExtensionSpec,
    LLMServiceExtensionServer,
    LLMServiceExtensionSpec
)
from agentstack_sdk.a2a.extensions.ui.settings import (
    CheckboxField,
    CheckboxGroupField,
    SettingsExtensionServer,
    SettingsExtensionSpec,
    SettingsRender,
)

# -----------------------------------------------------------------------------
# Import from new modular architecture
# -----------------------------------------------------------------------------
from utils import create_langgraph_agent
from utils.citations import format_citations_for_beeai, format_tool_data_for_logging
from tools import get_all_tools, get_tool_by_name, ToolRegistry
from langchain_core.messages import HumanMessage, AIMessage


# =============================================================================
# SERVER DEFINITION
# =============================================================================

server = Server()


# =============================================================================
# AGENT DEFINITION
#
# EXTENSION POINT: AgentDetailTool List
# -------------------------------------
# Add new tools to this list to advertise them in the BeeAI UI.
# The list should match the tools registered in tools/ package.
# =============================================================================

@server.agent(
    detail=AgentDetail(
        ui_type="chat",
        user_greeting="Welcome! I'm a Granite 4 agent with web scraping and research capabilities powered by modular tools and LangGraph.",
        license="Apache 2.0",
        programming_language="Python",
        framework="BeeAI + LangGraph + Modular Tools",
        
        # ---------------------------------------------------------------------
        # TOOL LIST - Add entries here for new tools you want to advertise
        # These should match tools registered in the tools/ package
        # ---------------------------------------------------------------------
        tools=[
            # SearxNG Search Tool
            AgentDetailTool(
                name="searx_search",
                description="Search the web using SearxNG metasearch engine. Returns structured results with titles, snippets, links, and source engines from multiple search engines.",
            ),
            # Firecrawl Tools
            AgentDetailTool(
                name="firecrawl_scrape",
                description="Scrape content from a single URL with advanced options. Returns markdown or HTML content.",
            ),
            AgentDetailTool(
                name="firecrawl_map",
                description="Map a website to discover all indexed URLs. Best for finding specific sections of a website.",
            ),
            AgentDetailTool(
                name="firecrawl_search",
                description="Search the web and optionally extract content from search results.",
            ),
            AgentDetailTool(
                name="firecrawl_extract",
                description="Extract structured information from web pages using LLM capabilities.",
            ),
            AgentDetailTool(
                name="firecrawl_crawl",
                description="Start an asynchronous crawl job with advanced options.",
            ),
            AgentDetailTool(
                name="firecrawl_check_crawl_status",
                description="Check the status of a crawl job.",
            ),
            AgentDetailTool(
                name="firecrawl_batch_scrape",
                description="Scrape multiple URLs efficiently with built-in rate limiting.",
            ),
            AgentDetailTool(
                name="firecrawl_check_batch_status",
                description="Check the status of a batch scraping operation.",
            ),
            # -----------------------------------------------------------------
            # ADD NEW TOOLS HERE
            # Example:
            # AgentDetailTool(
            #     name="my_new_tool",
            #     description="Description of what the tool does.",
            # ),
            # -----------------------------------------------------------------
        ],
        author=AgentDetailContributor(
            name="Xavier Vargas",
            email="Xavier.Vargas@ibm.com",
            url="http://www.Vargas.Technology",
        ),
        contributors=[
            AgentDetailContributor(
                name="Another Person",
                email="another@beeai.dev",
                url="https://beeai.dev",
            ),
        ]
    )
)
async def granite_4_starter(
    input: Message,
    context: RunContext,
    llm: Annotated[
        LLMServiceExtensionServer,
        LLMServiceExtensionSpec.single_demand(suggested=("ollama:granite-4:micro-h",))
    ],
    citation: Annotated[
        CitationExtensionServer,
        CitationExtensionSpec()
    ],
    trajectory: Annotated[
        TrajectoryExtensionServer,
        TrajectoryExtensionSpec()
    ],
    settings: Annotated[
        SettingsExtensionServer,
        SettingsExtensionSpec(
            params=SettingsRender(
                fields=[
                    CheckboxGroupField(
                        id="thinking_group",
                        fields=[
                            CheckboxField(
                                id="thinking",
                                label="Enable Thinking Mode",
                                default_value=True,
                            )
                        ],
                    )
                ],
            ),
        ),
    ],
) -> AsyncGenerator[RunYield, Message]:
    """
    Main agent handler that processes user messages using LangGraph with modular tools.
    
    This agent uses the new modular tool architecture where tools are:
    - Registered in the tools/ package (MCP or LangChain)
    - Automatically discovered and loaded
    - Executed via the appropriate handler based on tool type
    
    Extension Points:
        1. Add tools: Create new tool files in tools/mcp/ or tools/langchain/
        2. Customize prompt: Modify the system_prompt in create_langgraph_agent()
        3. Filter tools: Pass specific tools list instead of get_all_tools()
    """
    print("AGENT STARTING!")
    
    # -------------------------------------------------------------------------
    # Settings Validation
    # -------------------------------------------------------------------------
    if not settings:
        yield "Settings extension hasn't been activated, no settings are available"
        return
    
    # Store current user message in BeeAI context for history tracking
    await context.store(input)
    
    # Parse user settings (e.g., thinking mode toggle)
    parsed_settings = settings.parse_settings_response()
    thinking_group = parsed_settings.values["thinking_group"]
    
    # -------------------------------------------------------------------------
    # Extract User Message
    # -------------------------------------------------------------------------
    current_message = get_message_text(input)
    yield trajectory.trajectory_metadata(
        title="Capture & Store User Input", 
        content=f"{current_message}"
    )
    
    # -------------------------------------------------------------------------
    # Load Conversation History
    # -------------------------------------------------------------------------
    history = [
        message async for message in context.load_history() 
        if isinstance(message, Message) and message.parts
    ]
    
    # Convert BeeAI message history to LangChain message objects
    langchain_messages = []
    for message in history:
        msg_text = get_message_text(message)
        if message.role == "user":
            langchain_messages.append(HumanMessage(content=msg_text))
        else:
            langchain_messages.append(AIMessage(content=msg_text))
    
    yield trajectory.trajectory_metadata(
        title="Loaded Conversation History", 
        content=f"Total messages in history: {len(langchain_messages)}"
    )
    
    # -------------------------------------------------------------------------
    # LLM Configuration
    # -------------------------------------------------------------------------
    if llm:
        llm_config = llm.data.llm_fulfillments.get("default")
        api_model = llm_config.api_model
        api_key = llm_config.api_key
        api_base = llm_config.api_base
        yield AgentMessage(text=f"LLM access configured for model: {api_model}\n")
        
        # ---------------------------------------------------------------------
        # Get Tools from Registry
        # 
        # EXTENSION POINT: Tool Selection
        # You can customize which tools the agent has access to:
        #
        # Option 1: All registered tools (default)
        #   tools = get_all_tools()
        #
        # Option 2: Specific tools by name
        #   tools = [
        #       get_tool_by_name("firecrawl_scrape"),
        #       get_tool_by_name("searx_search"),
        #   ]
        #
        # Option 3: Filter by type
        #   from tools import ToolRegistry
        #   tools = ToolRegistry.get_tools_by_type("mcp")  # Only MCP tools
        # ---------------------------------------------------------------------
        tools = get_all_tools()
        
        yield trajectory.trajectory_metadata(
            title="Tools Loaded from Registry",
            content=f"Available tools ({len(tools)}):\n" + "\n".join([f"- {t.name} ({t.tool_type})" for t in tools])
        )
        
        # ---------------------------------------------------------------------
        # Create LangGraph Agent
        # 
        # EXTENSION POINT: Agent Configuration
        # You can customize the agent by passing additional parameters:
        # - system_prompt: Custom system prompt
        # - temperature: LLM temperature
        # ---------------------------------------------------------------------
        agent = create_langgraph_agent(
            api_model=api_model,
            api_key=api_key,
            api_base=api_base,
            tools=tools,
            # Uncomment to customize:
            # system_prompt="You are a specialized research assistant.",
            # temperature=0.1,
        )
        
        # ---------------------------------------------------------------------
        # Thinking Mode
        # ---------------------------------------------------------------------
        is_thinking_enabled = (
            thinking_group.type == "checkbox_group" 
            and thinking_group.values["thinking"].value
        )
        
        if is_thinking_enabled:
            yield "Thinking mode is enabled - I'll show my reasoning process.\n"
        else:
            yield "Thinking mode is disabled - I'll provide direct responses.\n"
        
        # ---------------------------------------------------------------------
        # Execute Agent
        # ---------------------------------------------------------------------
        messages = langchain_messages + [HumanMessage(content=current_message)]
        
        yield trajectory.trajectory_metadata(
            title="Starting LangGraph Agent with Modular Tools",
            content=f"Passing {len(messages)} messages to agent (including {len(langchain_messages)} history messages)\nTools: {len(tools)}"
        )
        
        # Track tool executions and citations
        tool_citations = []
        tool_executions = []
        final_response = ""
        node_count = 0
        tool_calls_count = 0
        
        config = {"recursion_limit": 100}

        async for chunk in agent.astream({
            "messages": messages, 
            "llm_calls": 0,
            "tool_instances": {t.name: t for t in tools}
        }, config=config):
            node_count += 1
            
            # Process each node's output
            for node_name, node_output in chunk.items():
                yield trajectory.trajectory_metadata(
                    title=f"Node {node_count}: {node_name}",
                    content=f"State: {str(node_output)[:500]}..."
                )
                
                # Parse message types from state
                if isinstance(node_output, dict) and "messages" in node_output:
                    messages_list = node_output["messages"]
                    
                    for msg in messages_list:
                        # Track tool calls from LLM
                        if hasattr(msg, "tool_calls") and msg.tool_calls:
                            tool_calls_count += len(msg.tool_calls)
                            tool_calls_info = [
                                f"- {tc['name']}({json.dumps(tc['args'], indent=2)})"
                                for tc in msg.tool_calls
                            ]
                            
                            yield trajectory.trajectory_metadata(
                                title=f"Tool Calls from {node_name}",
                                content="\n".join(tool_calls_info)
                            )
                            
                            # Collect citation metadata for each tool call
                            for tc in msg.tool_calls:
                                tool_instance = get_tool_by_name(tc['name'])
                                if tool_instance:
                                    # We'll get actual result later, for now store args
                                    tool_executions.append({
                                        "tool_name": tc['name'],
                                        "tool_args": tc['args'],
                                        "tool_instance": tool_instance
                                    })
                        
                        # Track tool results
                        elif hasattr(msg, "content") and hasattr(msg, "tool_call_id"):
                            tool_name = getattr(msg, 'name', 'unknown')
                            
                            yield trajectory.trajectory_metadata(
                                title=f"Tool Result: {tool_name}",
                                content=f"Result: {msg.content[:500]}..."
                            )
                            
                            # Generate citation for this tool result
                            for exec_info in tool_executions:
                                if exec_info.get("tool_name") == tool_name and "result" not in exec_info:
                                    exec_info["result"] = msg.content
                                    # Note: use different var name to avoid shadowing 'citation' parameter
                                    cite_metadata = exec_info["tool_instance"].get_citation_metadata(
                                        exec_info["tool_args"],
                                        msg.content
                                    )
                                    tool_citations.append(cite_metadata)
                                    break
                        
                        # Capture final AI response
                        elif hasattr(msg, "content") and msg.content:
                            content = msg.content
                            if content and not hasattr(msg, "tool_call_id"):
                                final_response = content
        
        # ---------------------------------------------------------------------
        # Format and Return Response
        # ---------------------------------------------------------------------
        formatted_citations = []
        
        if tool_citations and final_response:
            yield trajectory.trajectory_metadata(
                title="Citations Summary",
                content=f"Generated {len(tool_citations)} citations from tool executions"
            )
            formatted_citations = format_citations_for_beeai(tool_citations, final_response)
        
        # Return final response with citations
        if final_response:
            if formatted_citations:
                yield citation.message(text=final_response, citations=formatted_citations)
            else:
                yield AgentMessage(text=final_response)
            
            # Store in context for future history
            agent_message = AgentMessage(text=final_response)
            await context.store(agent_message)
        else:
            error_msg = "No response generated from agent"
            yield AgentMessage(text=error_msg)
        
        yield trajectory.trajectory_metadata(
            title="LangGraph Execution Complete",
            content=f"Total nodes executed: {node_count}\nTotal tool calls: {tool_calls_count}\nCitations generated: {len(tool_citations)}\nFinal response: {final_response[:200]}..."
        )
    else:
        yield AgentMessage(text="There is no llm provided, this would be a hard-coded agent return")


# =============================================================================
# SERVER RUN
# =============================================================================

def run():
    """
    Start the BeeAI agent server.
    
    Configuration via environment variables:
    - HOST: Server host (default: 127.0.0.1)
    - PORT: Server port (default: 8005)
    """
    try:
        server.run(
            host=os.getenv("HOST", "127.0.0.1"), 
            port=int(os.getenv("PORT", 8005))
        )
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    run()
