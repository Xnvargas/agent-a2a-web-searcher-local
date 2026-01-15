"""
=============================================================================
AGENTSTACK AGENT - LangGraph Agent with Modular Tool Architecture
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
from a2a.types import Message, AgentCapabilities
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
from utils.content_parts import (
    ContentType,
    format_thinking_trajectory,
    format_tool_call_trajectory,
    format_tool_result_trajectory,
    create_thinking_metadata,
    create_response_metadata,
    create_tool_call_metadata,
    create_tool_result_metadata,
    # A2A-compliant part creators for structured streaming
    create_thinking_text_part,
    create_response_text_part,
    create_tool_call_data_part,
    create_tool_result_data_part,
    create_status_text_part,
)
from tools import get_all_tools, get_tool_by_name, ToolRegistry
from langchain_core.messages import HumanMessage, AIMessage, AIMessageChunk

# -----------------------------------------------------------------------------
# Standalone Mode LLM Configuration (fallback when BeeAI extension unavailable)
# -----------------------------------------------------------------------------
STANDALONE_LLM_API_BASE = os.getenv("LLM_API_BASE", "http://192.168.0.58:11434/v1")
STANDALONE_LLM_API_KEY = os.getenv("LLM_API_KEY", "dummy")
STANDALONE_LLM_MODEL = os.getenv("LLM_MODEL", "qwen3-next:80b-a3b-thinking-q4_K_M")


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
    capabilities=AgentCapabilities(streaming=True),
    detail=AgentDetail(
        ui_type="chat",
        user_greeting="Welcome! I'm an AI agent with web scraping and research capabilities powered by modular tools and LangGraph.",
        license="Apache 2.0",
        programming_language="Python",
        framework="Langgraph",
        
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
async def a2a_starter(
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
    # Settings Validation (Graceful for standalone mode)
    # -------------------------------------------------------------------------
    is_thinking_enabled = True  # Default when settings unavailable
    
    if settings:
        try:
            parsed_settings = settings.parse_settings_response()
            thinking_group = parsed_settings.values.get("thinking_group")
            if thinking_group and thinking_group.type == "checkbox_group":
                thinking_val = thinking_group.values.get("thinking")
                if thinking_val:
                    is_thinking_enabled = thinking_val.value
        except Exception as e:
            print(f"⚠️  Could not parse settings: {e}")
    else:
        print("⚠️  Settings extension not activated - using defaults (standalone mode)")
    
    # Store current user message in BeeAI context for history tracking
    await context.store(input)
    
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
    # LLM Configuration (with standalone fallback)
    # -------------------------------------------------------------------------
    if llm:
        # Platform mode - use BeeAI LLM extension
        llm_config = llm.data.llm_fulfillments.get("default")
        api_model = llm_config.api_model
        api_key = llm_config.api_key
        api_base = llm_config.api_base
        yield AgentMessage(text=f"LLM configured via BeeAI platform: {api_model}\n")
    else:
        # Standalone mode - use environment variables
        api_model = STANDALONE_LLM_MODEL
        api_key = STANDALONE_LLM_API_KEY
        api_base = STANDALONE_LLM_API_BASE
        print(f"⚠️  LLM extension not available - using standalone config: {api_model} @ {api_base}")
        yield AgentMessage(text=f"LLM configured for standalone mode: {api_model}\n")

    # -------------------------------------------------------------------------
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
    # -------------------------------------------------------------------------
    tools = get_all_tools()
    
    yield trajectory.trajectory_metadata(
        title="Tools Loaded from Registry",
        content=f"Available tools ({len(tools)}):\n" + "\n".join([f"- {t.name} ({t.tool_type})" for t in tools])
    )
    
    # -------------------------------------------------------------------------
    # Create LangGraph Agent
    # 
    # EXTENSION POINT: Agent Configuration
    # You can customize the agent by passing additional parameters:
    # - system_prompt: Custom system prompt
    # - temperature: LLM temperature
    # -------------------------------------------------------------------------
    agent = create_langgraph_agent(
        api_model=api_model,
        api_key=api_key,
        api_base=api_base,
        tools=tools,
        # Uncomment to customize:
        # system_prompt="You are a specialized research assistant.",
        # temperature=0.1,
    )
    
    # -------------------------------------------------------------------------
    # Thinking Mode (using value set in Settings Validation above)
    # -------------------------------------------------------------------------
    if is_thinking_enabled:
        yield "Thinking mode is enabled - I'll show my reasoning process.\n"
    else:
        yield "Thinking mode is disabled - I'll provide direct responses.\n"
    
    # -------------------------------------------------------------------------
    # Execute Agent
    # -------------------------------------------------------------------------
    messages = langchain_messages + [HumanMessage(content=current_message)]
    
    yield trajectory.trajectory_metadata(
        title="Starting LangGraph Agent with Modular Tools",
        content=f"Passing {len(messages)} messages to agent (including {len(langchain_messages)} history messages)\nTools: {len(tools)}"
    )
    
    # Track tool executions and citations
    tool_citations = []
    tool_executions = []
    accumulated_response = ""  # Accumulate streamed tokens
    accumulated_thinking = ""  # Accumulate thinking content (before tool calls)
    tool_calls_count = 0
    thinking_step = 0  # Counter for thinking steps
    
    config = {"recursion_limit": 100}

    # -------------------------------------------------------------------------
    # TOKEN-LEVEL STREAMING WITH A2A-COMPLIANT STRUCTURED PARTS
    # 
    # Content is categorized based on position relative to tool calls:
    # - Before any tool calls = "thinking" content (reasoning)
    # - After tool executions = "response" content (final answer)
    # 
    # A2A Protocol Compliance:
    # - TextPart with metadata.content_type for thinking/response
    # - DataPart with data.type for tool_call/tool_result
    # 
    # This enables Carbon frontend to render:
    # - thinking → reasoning.steps / reasoning.content (accordion)
    # - tool_call → chain_of_thought invocation card (spinner)
    # - tool_result → chain_of_thought result expansion (checkmark)
    # - response → main response text
    # -------------------------------------------------------------------------
    async for chunk, metadata in agent.astream(
        {
            "messages": messages, 
            "llm_calls": 0,
            "tool_instances": {t.name: t for t in tools}
        }, 
        config=config,
        stream_mode="messages",  # KEY: enables token-level streaming
    ):
        node_name = metadata.get("langgraph_node", "unknown")
        
        # Handle streaming LLM tokens (AIMessageChunk)
        if isinstance(chunk, AIMessageChunk):
            # Stream text content token-by-token to frontend
            if chunk.content:
                # Categorize content based on position relative to tool calls
                if tool_calls_count == 0:
                    # THINKING: Before any tool calls = reasoning content
                    accumulated_thinking += chunk.content
                    
                    # Emit thinking as A2A-compliant TextPart with metadata
                    if is_thinking_enabled:
                        # Stream structured AgentMessage with thinking metadata
                        # Frontend parses: parts[0].metadata.content_type == 'thinking'
                        yield AgentMessage(parts=[
                            create_thinking_text_part(
                                text=chunk.content,
                                step_number=None  # Real-time streaming, no step yet
                            )
                        ])
                        
                        # Periodically emit thinking trajectory for sidebar/debug
                        if len(accumulated_thinking) % 100 < 10:
                            thinking_step += 1
                            title, content = format_thinking_trajectory(
                                accumulated_thinking[-200:],  # Last 200 chars
                                step_number=thinking_step
                            )
                            yield trajectory.trajectory_metadata(
                                title=title,
                                content=content
                            )
                else:
                    # RESPONSE: After tool calls = final response content
                    # Stream structured AgentMessage with response metadata  
                    # Frontend parses: parts[0].metadata.content_type == 'response'
                    yield AgentMessage(parts=[
                        create_response_text_part(text=chunk.content)
                    ])
                    accumulated_response += chunk.content
            
            # Track tool calls (come as chunks during streaming)
            if chunk.tool_calls:
                tool_calls_count += len(chunk.tool_calls)
                
                for tc in chunk.tool_calls:
                    tool_name_tc = tc.get('name', 'unknown')
                    tool_args_tc = tc.get('args', {})
                    tool_call_id = tc.get('id')
                    
                    # Emit A2A DataPart for tool call
                    # Frontend parses: parts[0].data.type == 'tool_call' → spinner card
                    yield AgentMessage(parts=[
                        create_tool_call_data_part(
                            tool_name=tool_name_tc,
                            args=tool_args_tc,
                            tool_call_id=tool_call_id,
                            status="in_progress"
                        )
                    ])
                    
                    # Also emit trajectory metadata for sidebar visibility
                    title, content = format_tool_call_trajectory(
                        tool_name=tool_name_tc,
                        args=tool_args_tc,
                        tool_call_id=tool_call_id
                    )
                    yield trajectory.trajectory_metadata(
                        title=title,
                        content=content
                    )
                    
                    tool_instance = get_tool_by_name(tool_name_tc)
                    if tool_instance:
                        tool_executions.append({
                            "tool_name": tool_name_tc,
                            "tool_args": tool_args_tc,
                            "tool_call_id": tool_call_id,
                            "tool_instance": tool_instance
                        })
        
        # Handle tool execution results (ToolMessage)
        elif hasattr(chunk, 'tool_call_id') and hasattr(chunk, 'content'):
            tool_name = getattr(chunk, 'name', 'unknown')
            tool_call_id = getattr(chunk, 'tool_call_id', None)
            
            # Emit A2A DataPart for tool result
            # Frontend parses: parts[0].data.type == 'tool_result' → checkmark card
            yield AgentMessage(parts=[
                create_tool_result_data_part(
                    tool_name=tool_name,
                    result=chunk.content,
                    tool_call_id=tool_call_id,
                    status="success"
                )
            ])
            
            # Also emit trajectory metadata for sidebar visibility
            title, content = format_tool_result_trajectory(
                tool_name=tool_name,
                result=chunk.content,
                tool_call_id=tool_call_id,
                status="success"
            )
            yield trajectory.trajectory_metadata(
                title=title,
                content=content
            )
            
            # Generate citation for this tool result
            for exec_info in tool_executions:
                if exec_info.get("tool_name") == tool_name and "result" not in exec_info:
                    exec_info["result"] = chunk.content
                    cite_metadata = exec_info["tool_instance"].get_citation_metadata(
                        exec_info["tool_args"],
                        chunk.content
                    )
                    tool_citations.append(cite_metadata)
                    break
        
        # Skip user messages in stream
        elif isinstance(chunk, HumanMessage):
            continue
    
    # Use accumulated_response for final processing
    final_response = accumulated_response
    
    # -------------------------------------------------------------------------
    # Post-Streaming: Handle Citations and Storage
    # Response already streamed token-by-token, just handle storage and citations
    # -------------------------------------------------------------------------
    formatted_citations = []
    
    if tool_citations and final_response:
        yield trajectory.trajectory_metadata(
            title="Citations Summary",
            content=f"Generated {len(tool_citations)} citations from tool executions"
        )
        formatted_citations = format_citations_for_beeai(tool_citations, final_response)
        
        # Emit citation metadata (frontend can apply to already-streamed text)
        yield trajectory.trajectory_metadata(
            title="Citations Data",
            content=json.dumps([
                {"url": c["url"], "title": c["title"], "start": c["start_index"], "end": c["end_index"]}
                for c in formatted_citations
            ])
        )
    
    # Store complete response for conversation history
    if final_response:
        await context.store(AgentMessage(text=final_response))
    else:
        yield "No response generated from agent"
    
    yield trajectory.trajectory_metadata(
        title="LangGraph Execution Complete",
        content=f"Total tool calls: {tool_calls_count}\nCitations generated: {len(tool_citations)}\nResponse length: {len(final_response)} chars"
    )


# =============================================================================
# SERVER RUN
# =============================================================================

def run():
    """
    Start the Agentstack A2A agent server.
    
    Configuration via environment variables:
    - HOST: Server host (default: 127.0.0.1)
    - PORT: Server port (default: 8005)
    """
    try:
        server.run(
            host=os.getenv("HOST", "127.0.0.1"), 
            port=int(os.getenv("PORT", 8006))
        )
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    run()
