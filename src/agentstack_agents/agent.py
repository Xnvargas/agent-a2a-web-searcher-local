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
from utils.citations import (
    format_citations_for_beeai,
    format_tool_data_for_logging,
    # A2A Protocol citation support
    Citation,
    create_citation_metadata,
    calculate_citation_positions,
)
from utils.content_parts import (
    ContentType,
    format_thinking_trajectory,
    format_tool_call_trajectory,
    format_tool_result_trajectory,
    create_thinking_metadata,
    create_response_metadata,
    create_tool_call_metadata,
    create_tool_result_metadata,
    # URI-keyed trajectory metadata (A2A Protocol)
    create_trajectory_metadata,
    create_tool_call_trajectory_metadata,
    create_tool_result_trajectory_metadata,
)
# A2A Parts - Dual-emit helpers for Carbon AI Chat compatibility
from utils.a2a_parts import (
    create_thinking_text_part,
    create_response_text_part,
    emit_thinking_part,           # Wrapped version for yielding (initial phase)
    emit_response_part,           # Wrapped version for yielding
    emit_reasoning_step,          # Batched reasoning steps (post-tool phase)
    emit_tool_call_with_trajectory,
    emit_tool_result_with_trajectory,
)
from utils.error_extension import (
    create_error_metadata,
    create_error_metadata_from_exception,
    create_tool_error_metadata,
)
from utils.extension_uris import ExtensionURIs
from utils.swot_context import SWOTContext, extract_swot_context
from utils.swot_prompt_builder import build_swot_system_prompt
from tools import get_all_tools, get_tool_by_name, ToolRegistry
from langchain_core.messages import HumanMessage, AIMessage, AIMessageChunk
import traceback

# -----------------------------------------------------------------------------
# Standalone Mode LLM Configuration (fallback when BeeAI extension unavailable)
# -----------------------------------------------------------------------------
STANDALONE_LLM_API_BASE = os.getenv("LLM_API_BASE", "http://192.168.0.58:11434/v1")
STANDALONE_LLM_API_KEY = os.getenv("LLM_API_KEY", "dummy")
STANDALONE_LLM_MODEL = os.getenv("LLM_MODEL", "glm-4.7-flash:q4_K_M")
# qwen3-next:80b-a3b-thinking-q4_K_M
# nemotron-3-nano:latest
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
            # Tavily Search Tool (AI-optimized web search)
            AgentDetailTool(
                name="tavily_search",
                description="Search the web using Tavily AI-optimized search engine. Returns comprehensive, accurate results with snippets optimized for AI agents.",
            ),
            # Firecrawl Tools
            AgentDetailTool(
                name="firecrawl_scrape",
                description="Scrape content from a single URL with advanced options. Returns markdown or HTML content.",
            ),
            # -----------------------------------------------------------------
            # SWOT Tools - Solution Workshop & Opportunity Tracker
            # -----------------------------------------------------------------
            AgentDetailTool(
                name="search_documents",
                description="Search documents semantically. Automatically filters to current context unless override_scope=True.",
            ),
            AgentDetailTool(
                name="find_similar_solutions",
                description="Find past solutions similar to a use case description. Uses current opportunity's use case if not provided.",
            ),
            AgentDetailTool(
                name="get_current_context",
                description="Get details about the current context (opportunity, account, or global view).",
            ),
            AgentDetailTool(
                name="get_technology_footprint",
                description="Get IBM technology products deployed at an account.",
            ),
            AgentDetailTool(
                name="query_coverage",
                description="Find team members who cover a specific product for an account.",
            ),
            AgentDetailTool(
                name="create_solution_draft",
                description="Create a new solution architecture draft linked to an opportunity.",
            ),
            AgentDetailTool(
                name="create_document_artifact",
                description="Create a document artifact and optionally link to the current entity.",
            ),
        ],
        author=AgentDetailContributor(
            name="Xavier Vargas",
            email="Xavier.Vargas@ibm.com",
            url="http://www.Vargas.Technology",
        ),
        contributors=[
            AgentDetailContributor(
                name="Victoriya Kelyman",
                email="another@beeai.dev",
                url="https://beeai.dev",
            ),
        ]
    )
)
async def Web_Agent(
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
    # Extract SWOT Context from A2A Extensions
    # -------------------------------------------------------------------------
    extensions = context.request.params.get('extensions', {}) if hasattr(context, 'request') and context.request and hasattr(context.request, 'params') else {}
    swot_ctx = extract_swot_context(extensions)

    # Set context for tools (async-safe via ContextVar)
    SWOTContext.set_current(swot_ctx)

    if swot_ctx:
        yield trajectory.trajectory_metadata(
            title="SWOT Context Loaded",
            content=(
                f"Scope: {swot_ctx.scope.type}\n"
                f"Entity: {swot_ctx.summary.entity_name or 'None'}\n"
                f"Account: {swot_ctx.summary.account_name or 'None'}\n"
                f"Opportunity ID: {swot_ctx.scope.opportunity_id or 'None'}"
            )
        )
    else:
        yield trajectory.trajectory_metadata(
            title="SWOT Context",
            content="No context provided - operating in global mode"
        )

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
            print(f"Could not parse settings: {e}")
    else:
        print("Settings extension not activated - using defaults (standalone mode)")

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
        # yield AgentMessage(text=f"LLM configured via BeeAI platform: {api_model}\n")
    else:
        # Standalone mode - use environment variables
        api_model = STANDALONE_LLM_MODEL
        api_key = STANDALONE_LLM_API_KEY
        api_base = STANDALONE_LLM_API_BASE
        print(f"LLM extension not available - using standalone config: {api_model} @ {api_base}")
        # yield AgentMessage(text=f"LLM configured for standalone mode: {api_model}\n")

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
    # - system_prompt: Custom system prompt (now built dynamically from SWOT context)
    # - temperature: LLM temperature
    # -------------------------------------------------------------------------

    # Build dynamic system prompt based on SWOT context
    system_prompt = build_swot_system_prompt(swot_ctx)

    yield trajectory.trajectory_metadata(
        title="System Prompt Built",
        content=f"Mode: {swot_ctx.scope.type if swot_ctx else 'global'}"
    )

    # Create LangGraph Agent with context-aware prompt
    # SWOT tools are auto-registered via ToolRegistry
    agent = create_langgraph_agent(
        api_model=api_model,
        api_key=api_key,
        api_base=api_base,
        tools=tools,  # Includes SWOT tools automatically
        system_prompt=system_prompt,  # Dynamic prompt based on context
        # temperature=0.1,
    )

    # -------------------------------------------------------------------------
    # Thinking Mode (using value set in Settings Validation above)
    # -------------------------------------------------------------------------
    # if is_thinking_enabled:
    #     yield "Thinking mode is enabled - I'll show my reasoning process.\n"
    # else:
    #     yield "Thinking mode is disabled - I'll provide direct responses.\n"

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
    tools_completed = False  # Track when tool execution has finished

    # =========================================================================
    # REASONING VISUALIZATION STATE MACHINE
    # =========================================================================
    # Phases:
    #   "initial"   - Pre-tool: Stream tokens to reasoning.content
    #   "post_tool" - Between tools: Accumulate reasoning into buffer
    #   "final"     - Response: Flush buffer as step, stream response text
    # =========================================================================
    thinking_phase = "initial"  # Current phase: "initial" | "post_tool" | "final"
    post_tool_buffer = ""       # Accumulates reasoning between tool calls
    last_tool_name = None       # For titling the reasoning step
    reasoning_step_counter = 0  # Counter for batched reasoning steps

    config = {"recursion_limit": 100}

    # -------------------------------------------------------------------------
    # TOKEN-LEVEL STREAMING WITH CONTENT CATEGORIZATION & ERROR HANDLING
    #
    # With ChatOllama + reasoning=True, thinking tokens are captured in:
    #   chunk.additional_kwargs['reasoning_content']
    # while response tokens remain in chunk.content
    #
    # IMPORTANT: Some models (Qwen, DeepSeek) put ALL content in reasoning_content,
    # including the final response. We detect this by tracking tool completion
    # state and reclassifying post-tool reasoning_content as response content.
    #
    # CRITICAL: All parts must be wrapped in AgentMessage for proper A2A
    # serialization. Use emit_thinking_part() and emit_response_part() instead
    # of the raw create_*_part() functions.
    #
    # This enables Carbon frontend to render:
    # - thinking -> reasoning.steps / reasoning.content (accordion)
    # - tool_call -> chain_of_thought invocation card (spinner)
    # - tool_result -> chain_of_thought result expansion (checkmark)
    # - response -> main response text
    #
    # Error handling emits structured error metadata via A2A error extension
    # -------------------------------------------------------------------------

    # Console logging for debugging
    print(f"\n{'='*60}")
    print(f"[AGENT] Starting stream for message: {current_message[:100]}...")
    print(f"[AGENT] Thinking mode enabled: {is_thinking_enabled}")
    print(f"{'='*60}\n")

    try:
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
                # ---------------------------------------------------------------
                # REASONING CONTENT (ChatOllama with reasoning=True)
                # Check for reasoning_content in additional_kwargs FIRST
                # This is where thinking tokens appear when using reasoning=True
                #
                # CRITICAL FIX: Some models put ALL output in reasoning_content,
                # including the final response after tool execution. We detect
                # this by checking if tools have completed execution.
                # ---------------------------------------------------------------
                reasoning_content = chunk.additional_kwargs.get('reasoning_content', '')

                if reasoning_content:
                    # Determine if this is true thinking or post-tool response
                    # After tools complete, reasoning_content is actually the response
                    is_final_response_phase = tools_completed and thinking_phase == "final"

                    # Also check for tool_call XML tags - those are still "thinking"
                    # even if we're in the middle of tool execution
                    contains_tool_call_xml = '<tool_call' in reasoning_content or '<function=' in reasoning_content

                    if is_final_response_phase and not contains_tool_call_xml:
                        # -----------------------------------------------------
                        # PHASE 3 - FINAL RESPONSE: Model is generating final answer
                        # but putting it in reasoning_content instead of content
                        # -----------------------------------------------------

                        # Flush any remaining post-tool buffer first
                        if thinking_phase != "final":
                            if post_tool_buffer.strip():
                                step_title = f"Analyzing {last_tool_name} results" if last_tool_name else "Preparing response"
                                print(f"[PHASE->FINAL*] Flushing buffer as step: {step_title}")

                                if is_thinking_enabled:
                                    yield emit_reasoning_step(
                                        title=step_title,
                                        content=post_tool_buffer.strip(),
                                        step_number=reasoning_step_counter
                                    )
                                    reasoning_step_counter += 1

                                post_tool_buffer = ""

                            thinking_phase = "final"
                            print(f"[PHASE] Transitioning to 'final' (from reasoning_content)")

                        print(f"[RESPONSE*] Streaming (from reasoning): {reasoning_content[:80]}..." if len(reasoning_content) > 80 else f"[RESPONSE*] Streaming (from reasoning): {reasoning_content}")

                        # CRITICAL: Use emit_response_part() to wrap in AgentMessage
                        yield emit_response_part(reasoning_content)
                        accumulated_response += reasoning_content

                    elif thinking_phase == "initial":
                        # -----------------------------------------------------
                        # PHASE 1 - INITIAL THINKING: Pre-tool reasoning
                        # Stream tokens directly to reasoning.content (NO titles)
                        # Titles create discrete steps; we want continuous streaming
                        # -----------------------------------------------------
                        accumulated_thinking += reasoning_content
                        print(f"[THINKING] Phase 1 Streaming: {reasoning_content[:80]}..." if len(reasoning_content) > 80 else f"[THINKING] Phase 1 Streaming: {reasoning_content}")

                        if is_thinking_enabled:
                            # Stream WITHOUT title - this goes to reasoning.content
                            yield emit_thinking_part(
                                content=reasoning_content,
                                step_number=None,  # No step number for streaming
                                title=None  # No title - enables content streaming mode
                            )

                    else:
                        # -----------------------------------------------------
                        # PHASE 2 - POST-TOOL: Stream AND accumulate reasoning
                        # Stream tokens for live UI feedback while also
                        # accumulating for batched reasoning steps
                        # The batched emit_reasoning_step() calls (with titles) happen
                        # at phase transitions, not on every token
                        # -----------------------------------------------------
                        post_tool_buffer += reasoning_content
                        accumulated_thinking += reasoning_content
                        print(f"[POST-TOOL BUFFER] Phase 2 Accumulating: {reasoning_content[:80]}..." if len(reasoning_content) > 80 else f"[POST-TOOL BUFFER] Phase 2 Accumulating: {reasoning_content}")

                        # Stream WITHOUT title for live UI feedback
                        # The batched step with title will be emitted at phase transition
                        if is_thinking_enabled:
                            yield emit_thinking_part(
                                content=reasoning_content,
                                step_number=None,  # No step number for streaming
                                title=None  # No title - enables content streaming mode
                            )

                # ---------------------------------------------------------------
                # RESPONSE CONTENT (main text content)
                # This is the standard path for models that properly separate
                # thinking from response content.
                # ---------------------------------------------------------------
                if chunk.content:
                    # Debug: Print to console
                    print(f"[RESPONSE] Streaming: {chunk.content[:80]}..." if len(chunk.content) > 80 else f"[RESPONSE] Streaming: {chunk.content}")

                    # Categorize content based on position relative to tool calls
                    if tool_calls_count == 0 and not tools_completed and not reasoning_content and thinking_phase == "initial":
                        # THINKING: Before any tool calls = reasoning content
                        # (fallback for models that don't use reasoning_content)
                        accumulated_thinking += chunk.content

                        # Emit thinking WITHOUT title for streaming mode
                        if is_thinking_enabled:
                            yield emit_thinking_part(
                                content=chunk.content,
                                step_number=None,  # No step number for streaming
                                title=None  # No title - enables content streaming mode
                            )
                    else:
                        # ---------------------------------------------------------
                        # PHASE TRANSITION: Flush buffer when entering final phase
                        # ---------------------------------------------------------
                        if thinking_phase != "final":
                            # Flush any remaining post-tool reasoning
                            if post_tool_buffer.strip():
                                step_title = f"Analyzing {last_tool_name} results" if last_tool_name else "Preparing response"
                                print(f"[PHASE->FINAL] Flushing buffer as step: {step_title}")

                                if is_thinking_enabled:
                                    yield emit_reasoning_step(
                                        title=step_title,
                                        content=post_tool_buffer.strip(),
                                        step_number=reasoning_step_counter
                                    )
                                    reasoning_step_counter += 1

                                post_tool_buffer = ""

                            thinking_phase = "final"
                            print(f"[PHASE] Transitioning to 'final'")

                        # RESPONSE: After tool calls = final response content
                        # CRITICAL: Use emit_response_part() to wrap in AgentMessage
                        yield emit_response_part(chunk.content)
                        accumulated_response += chunk.content

                # ---------------------------------------------------------------
                # TOOL CALLS (come as chunks during streaming)
                # ---------------------------------------------------------------
                if chunk.tool_calls:
                    tool_calls_count += len(chunk.tool_calls)
                    # Reset tools_completed when new tool calls come in
                    # (handles multi-round tool usage)
                    tools_completed = False

                    for tc in chunk.tool_calls:
                        tool_name_tc = tc.get('name', 'unknown')
                        tool_args_tc = tc.get('args', {})
                        tool_call_id = tc.get('id')

                        # ---------------------------------------------------------
                        # PHASE TRANSITION: Flush post-tool buffer before new tool
                        # ---------------------------------------------------------
                        if thinking_phase == "post_tool" and post_tool_buffer.strip():
                            # Flush accumulated post-tool reasoning as a discrete step
                            step_title = f"Analyzing {last_tool_name} results" if last_tool_name else "Processing"
                            print(f"[PHASE 2->TOOL] Flushing buffer as step: {step_title}")

                            if is_thinking_enabled:
                                yield emit_reasoning_step(
                                    title=step_title,
                                    content=post_tool_buffer.strip(),
                                    step_number=reasoning_step_counter
                                )
                                reasoning_step_counter += 1

                            post_tool_buffer = ""

                        # Transition to post_tool phase after first tool call
                        if thinking_phase == "initial":
                            thinking_phase = "post_tool"
                            print(f"[PHASE] Transitioning from 'initial' to 'post_tool'")

                        # Track last tool name for step titling
                        last_tool_name = tool_name_tc

                        # FIXED: Emit BOTH trajectory metadata AND DataPart
                        # This ensures compatibility with:
                        # 1. AgentStack trajectory UI
                        # 2. Standard A2A clients expecting DataPart
                        # 3. Carbon AI Chat chain_of_thought rendering
                        #
                        # Reference: https://raw.githubusercontent.com/i-am-bee/agentstack/main/docs/stable/agent-integration/messages.mdx
                        for item in emit_tool_call_with_trajectory(
                            trajectory_server=trajectory,
                            tool_name=tool_name_tc,
                            args=tool_args_tc,
                            tool_call_id=tool_call_id
                        ):
                            yield item

                        tool_instance = get_tool_by_name(tool_name_tc)
                        if tool_instance:
                            tool_executions.append({
                                "tool_name": tool_name_tc,
                                "tool_args": tool_args_tc,
                                "tool_call_id": tool_call_id,
                                "tool_instance": tool_instance
                            })

            # -------------------------------------------------------------------
            # TOOL EXECUTION RESULTS (ToolMessage)
            # -------------------------------------------------------------------
            elif hasattr(chunk, 'tool_call_id') and hasattr(chunk, 'content'):
                tool_name = getattr(chunk, 'name', 'unknown')
                tool_call_id = getattr(chunk, 'tool_call_id', None)

                # CRITICAL: Mark that tool execution has completed
                # This triggers the phase change for reasoning_content handling
                tools_completed = True
                print(f"[TOOL COMPLETE] {tool_name} finished - switching to response phase")

                # Emit BOTH trajectory metadata AND DataPart
                # Reference: Carbon chain_of_thought expects status field
                # https://github.com/carbon-design-system/carbon-ai-chat/blob/main/examples/react/reasoning-and-chain-of-thought/src/scenarios.ts
                for item in emit_tool_result_with_trajectory(
                    trajectory_server=trajectory,
                    tool_name=tool_name,
                    result=chunk.content,
                    tool_call_id=tool_call_id,
                    status="success"
                ):
                    yield item

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

        # Stream completion logging
        print(f"\n{'='*60}")
        print(f"[AGENT] Stream complete. Stats:")
        print(f"  - Thinking tokens: {len(accumulated_thinking)} chars")
        print(f"  - Response tokens: {len(accumulated_response)} chars")
        print(f"  - Tool calls: {tool_calls_count}")
        print(f"  - Tools completed: {tools_completed}")
        print(f"  - Final phase: {thinking_phase}")
        print(f"  - Reasoning steps emitted: {reasoning_step_counter}")
        print(f"  - Post-tool buffer remaining: {len(post_tool_buffer)} chars")
        print(f"{'='*60}\n")

        # ---------------------------------------------------------------------
        # Post-Streaming: Handle Citations and Storage
        # Response already streamed token-by-token, just handle storage and citations
        # ---------------------------------------------------------------------

        if tool_citations and final_response:
            yield trajectory.trajectory_metadata(
                title="Citations Summary",
                content=f"Generated {len(tool_citations)} citations from tool executions"
            )

            # Calculate citation positions for A2A protocol compliance
            formatted_citations = calculate_citation_positions(tool_citations, final_response)

            # Emit URI-keyed citation metadata for client parsing
            citation_metadata = create_citation_metadata(formatted_citations)
            yield trajectory.trajectory_metadata(
                title="Citations Data",
                content=json.dumps(citation_metadata)
            )

            # Also emit via citation extension for backward compatibility
            legacy_citations = format_citations_for_beeai(tool_citations, final_response)
            yield citation.message(text="", citations=legacy_citations)

        # Store complete response for conversation history
        if final_response:
            await context.store(AgentMessage(text=final_response))
        else:
            yield "No response generated from agent"

        yield trajectory.trajectory_metadata(
            title="LangGraph Execution Complete",
            content=f"Total tool calls: {tool_calls_count}\nCitations generated: {len(tool_citations)}\nResponse length: {len(final_response)} chars"
        )

        # Clear SWOT context at end of request
        SWOTContext.clear()

    except Exception as e:
        # -------------------------------------------------------------------------
        # Structured Error Handling via A2A Error Extension
        # -------------------------------------------------------------------------
        error_context = {
            "tool_calls_count": tool_calls_count,
            "accumulated_response_length": len(accumulated_response),
            "last_tool": tool_executions[-1]["tool_name"] if tool_executions else None,
        }

        # Create error metadata for A2A protocol
        error_metadata = create_error_metadata_from_exception(
            exception=e,
            context=error_context,
            include_stacktrace=True,
            recoverable=False
        )

        # Log error for debugging
        print(f"Agent execution error: {e}")
        print(f"Error context: {error_context}")
        print(traceback.format_exc())

        # Emit error trajectory for visibility
        yield trajectory.trajectory_metadata(
            title="Execution Error",
            content=f"**Error:** {type(e).__name__}\n\n**Message:** {str(e)}\n\n**Context:**\n```json\n{json.dumps(error_context, indent=2)}\n```"
        )

        # Yield error message with A2A extension metadata
        yield AgentMessage(
            text=f"An error occurred during execution: {str(e)}",
            metadata=error_metadata
        )

        # Store partial response if any
        if accumulated_response:
            await context.store(AgentMessage(text=accumulated_response))

        # Clear SWOT context even on error
        SWOTContext.clear()


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
            host=os.getenv("HOST", "0.0.0.0"),
            port=int(os.getenv("PORT", 8006))
        )
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    run()
