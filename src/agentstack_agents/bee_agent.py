"""
=============================================================================
BEEAI FRAMEWORK AGENT - RequirementAgent with Modular Tool Architecture
=============================================================================

This is the BeeAI Framework agent handler that processes user messages using
BeeAI's RequirementAgent with the same modular, extensible tools as the
LangGraph agent.

ARCHITECTURE:
-------------

The agent uses BeeAI Framework's RequirementAgent which provides:
1. Declarative tool execution control via requirements
2. Native support for LangChain tools via adapter
3. Built-in memory management
4. Structured agent execution with thinking capabilities

COMPARISON WITH LANGGRAPH AGENT:
--------------------------------

| LangGraph (agent.py)    | BeeAI Framework (bee_agent.py)      |
|-------------------------|-------------------------------------|
| StateGraph orchestration | RequirementAgent orchestration     |
| Explicit graph edges     | Declarative requirements           |
| Manual state management  | Built-in memory classes            |
| llm_call + tool_node     | Single agent.run() execution       |

ADDING NEW TOOLS:
-----------------

Tools are shared with the LangGraph agent:
1. For MCP tools: See tools/mcp/README.md
2. For LangChain tools: See tools/langchain/README.md

Tools are automatically wrapped for BeeAI using the LangChainTool adapter.

RUNNING THIS AGENT:
-------------------

This agent runs on a separate port from the LangGraph agent:
- LangGraph agent: PORT 8005 (default)
- BeeAI agent: PORT 8006 (default)

Set environment variables:
    export BEE_HOST="127.0.0.1"
    export BEE_PORT="8006"

=============================================================================
"""

import os
import json
from collections.abc import AsyncGenerator
from typing import Annotated, Any
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
# Import BeeAI Framework components
# -----------------------------------------------------------------------------
from beeai_framework.agents.requirement import RequirementAgent
from beeai_framework.backend import ChatModel
from beeai_framework.memory import UnconstrainedMemory
from beeai_framework.backend import UserMessage, AssistantMessage, SystemMessage

# -----------------------------------------------------------------------------
# Import from modular architecture
# -----------------------------------------------------------------------------
from utils.bee_factory import create_beeai_agent, wrap_tools_for_beeai
from utils.bee_citations import format_bee_citations_for_beeai
from tools import get_all_tools, get_tool_by_name, ToolRegistry


# =============================================================================
# SERVER DEFINITION
# =============================================================================

bee_server = Server()


# =============================================================================
# BEEAI AGENT DEFINITION
#
# This agent uses BeeAI Framework's RequirementAgent instead of LangGraph.
# It provides the same capabilities but with declarative agent control.
# =============================================================================

@bee_server.agent(
    detail=AgentDetail(
        ui_type="chat",
        user_greeting="Welcome! I'm a BeeAI Framework agent with web scraping and research capabilities powered by modular tools and RequirementAgent.",
        license="Apache 2.0",
        programming_language="Python",
        framework="BeeAI Framework + RequirementAgent + Modular Tools",
        
        # ---------------------------------------------------------------------
        # TOOL LIST - Same tools as LangGraph agent
        # These are wrapped using BeeAI's LangChainTool adapter
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
            # BeeAI Native Tools
            AgentDetailTool(
                name="think",
                description="BeeAI ThinkTool for structured reasoning. Allows the agent to think through complex problems step by step.",
            ),
        ],
        author=AgentDetailContributor(
            name="Xavier Vargas",
            email="Xavier.Vargas@ibm.com",
            url="http://www.Vargas.Technology",
        ),
        contributors=[
            AgentDetailContributor(
                name="BeeAI Framework",
                email="beeai@ibm.com",
                url="https://beeai.dev",
            ),
        ]
    )
)
async def bee_granite_4_starter(
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
                        id="bee_thinking_group",
                        fields=[
                            CheckboxField(
                                id="bee_thinking",
                                label="Enable BeeAI ThinkTool",
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
    BeeAI Framework agent handler that processes user messages using RequirementAgent.
    
    This agent uses BeeAI Framework instead of LangGraph for orchestration.
    It provides the same tool capabilities but with:
    - Declarative requirements-based execution control
    - Built-in memory management
    - Native ThinkTool for reasoning
    - Simplified async execution
    
    The same tools from tools/ package are automatically wrapped for BeeAI.
    """
    print("🐝 BEEAI AGENT STARTING!")
    
    # -------------------------------------------------------------------------
    # Settings Validation
    # -------------------------------------------------------------------------
    if not settings:
        yield "Settings extension hasn't been activated, no settings are available"
        return
    
    # Store current user message in BeeAI context for history tracking
    await context.store(input)
    
    # Parse user settings
    parsed_settings = settings.parse_settings_response()
    bee_thinking_group = parsed_settings.values["bee_thinking_group"]
    
    # -------------------------------------------------------------------------
    # Extract User Message
    # -------------------------------------------------------------------------
    current_message = get_message_text(input)
    yield trajectory.trajectory_metadata(
        title="🐝 BeeAI: Capture User Input", 
        content=f"{current_message}"
    )
    
    # -------------------------------------------------------------------------
    # Load Conversation History
    # -------------------------------------------------------------------------
    history = [
        message async for message in context.load_history() 
        if isinstance(message, Message) and message.parts
    ]
    
    yield trajectory.trajectory_metadata(
        title="🐝 BeeAI: Loaded Conversation History", 
        content=f"Total messages in history: {len(history)}"
    )
    
    # -------------------------------------------------------------------------
    # LLM Configuration
    # -------------------------------------------------------------------------
    if llm:
        llm_config = llm.data.llm_fulfillments.get("default")
        api_model = llm_config.api_model
        api_key = llm_config.api_key
        api_base = llm_config.api_base
        yield AgentMessage(text=f"🐝 BeeAI LLM configured for model: {api_model}\n")
        
        # ---------------------------------------------------------------------
        # Get Tools from Registry
        # Same tools as LangGraph agent, automatically wrapped for BeeAI
        # ---------------------------------------------------------------------
        tools = get_all_tools()
        
        yield trajectory.trajectory_metadata(
            title="🐝 BeeAI: Tools Loaded from Registry",
            content=f"Available tools ({len(tools)}):\n" + "\n".join([f"- {t.name} ({t.tool_type})" for t in tools])
        )
        
        # ---------------------------------------------------------------------
        # ThinkTool Setting
        # ---------------------------------------------------------------------
        is_thinking_enabled = (
            bee_thinking_group.type == "checkbox_group" 
            and bee_thinking_group.values["bee_thinking"].value
        )
        
        if is_thinking_enabled:
            yield "🐝 BeeAI ThinkTool is enabled - I'll use structured reasoning.\n"
        else:
            yield "🐝 BeeAI ThinkTool is disabled - I'll provide direct responses.\n"
        
        # ---------------------------------------------------------------------
        # Create BeeAI Agent
        # ---------------------------------------------------------------------
        try:
            agent = create_beeai_agent(
                api_model=api_model,
                api_key=api_key,
                api_base=api_base,
                tools=tools,
                include_think_tool=is_thinking_enabled,
            )
            
            yield trajectory.trajectory_metadata(
                title="🐝 BeeAI: Agent Created",
                content=f"RequirementAgent initialized with {len(tools)} tools (ThinkTool: {is_thinking_enabled})"
            )
            
        except Exception as e:
            error_msg = f"🐝 BeeAI Agent creation failed: {type(e).__name__}: {str(e)}"
            yield AgentMessage(text=error_msg)
            return
        
        # ---------------------------------------------------------------------
        # Prepare Memory with History
        # ---------------------------------------------------------------------
        # Convert history to BeeAI memory format
        for msg in history:
            msg_text = get_message_text(msg)
            if msg.role == "user":
                await agent.memory.add(UserMessage(msg_text))
            else:
                await agent.memory.add(AssistantMessage(msg_text))
        
        yield trajectory.trajectory_metadata(
            title="🐝 BeeAI: Memory Prepared",
            content=f"Added {len(history)} messages to agent memory"
        )
        
        # ---------------------------------------------------------------------
        # Execute BeeAI Agent
        # ---------------------------------------------------------------------
        yield trajectory.trajectory_metadata(
            title="🐝 BeeAI: Starting Agent Execution",
            content=f"Prompt: {current_message[:200]}..."
        )
        
        tool_citations = []
        final_response = ""
        
        try:
            # Execute the agent - pass message as positional argument
            # RequirementAgent.run() accepts: str or List[UserMessage]
            response = await agent.run(current_message)
            
            # Extract the answer - check different possible response structures
            if hasattr(response, 'answer') and response.answer:
                final_response = response.answer.text
            elif hasattr(response, 'output') and response.output:
                # Some versions may use 'output' instead of 'answer'
                if isinstance(response.output, list) and len(response.output) > 0:
                    last_msg = response.output[-1]
                    final_response = last_msg.text if hasattr(last_msg, 'text') else str(last_msg)
                else:
                    final_response = str(response.output)
            elif hasattr(response, 'result'):
                final_response = response.result.text if hasattr(response.result, 'text') else str(response.result)
            else:
                final_response = str(response) if response else "No response generated from BeeAI agent"
            
            yield trajectory.trajectory_metadata(
                title="🐝 BeeAI: Agent Execution Complete",
                content=f"Response length: {len(final_response)} chars\nPreview: {final_response[:300]}..."
            )
            
            # Extract tool execution information if available
            # BeeAI agents track tool usage in their execution trace
            if hasattr(response, 'iterations') and response.iterations:
                tool_call_count = 0
                for iteration in response.iterations:
                    if hasattr(iteration, 'tool_calls'):
                        tool_call_count += len(iteration.tool_calls)
                        # Collect citation info from tool calls
                        for tc in iteration.tool_calls:
                            tool_instance = get_tool_by_name(tc.tool_name) if hasattr(tc, 'tool_name') else None
                            if tool_instance:
                                cite_metadata = tool_instance.get_citation_metadata(
                                    getattr(tc, 'args', {}),
                                    getattr(tc, 'result', '')
                                )
                                tool_citations.append(cite_metadata)
                
                yield trajectory.trajectory_metadata(
                    title="🐝 BeeAI: Tool Execution Summary",
                    content=f"Total tool calls: {tool_call_count}\nCitations collected: {len(tool_citations)}"
                )
            
        except Exception as e:
            import traceback
            error_msg = f"🐝 BeeAI execution error: {type(e).__name__}: {str(e)}"
            yield trajectory.trajectory_metadata(
                title="🐝 BeeAI: Execution Error",
                content=f"{error_msg}\n\nTraceback:\n{traceback.format_exc()}"
            )
            final_response = error_msg
        
        # ---------------------------------------------------------------------
        # Format and Return Response
        # ---------------------------------------------------------------------
        formatted_citations = []
        
        if tool_citations and final_response:
            yield trajectory.trajectory_metadata(
                title="🐝 BeeAI: Citations Summary",
                content=f"Generated {len(tool_citations)} citations from tool executions"
            )
            formatted_citations = format_bee_citations_for_beeai(tool_citations, final_response)
        
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
            error_msg = "🐝 No response generated from BeeAI agent"
            yield AgentMessage(text=error_msg)
        
        yield trajectory.trajectory_metadata(
            title="🐝 BeeAI: Execution Complete",
            content=f"Response delivered\nCitations: {len(tool_citations)}\nResponse length: {len(final_response)}"
        )
    else:
        yield AgentMessage(text="🐝 There is no LLM provided, BeeAI agent requires an LLM configuration")


# =============================================================================
# SERVER RUN
# =============================================================================

def run():
    """
    Start the BeeAI agent server.
    
    Configuration via environment variables:
    - BEE_HOST: Server host (default: 127.0.0.1)
    - BEE_PORT: Server port (default: 8006)
    
    Note: This runs on a different port than the LangGraph agent (8005)
    to allow both agents to run simultaneously.
    """
    try:
        bee_server.run(
            host=os.getenv("BEE_HOST", "127.0.0.1"), 
            port=int(os.getenv("BEE_PORT", 8006))
        )
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    run()
