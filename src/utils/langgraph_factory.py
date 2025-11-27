"""
=============================================================================
LANGGRAPH AGENT FACTORY - Creates LangGraph Agents with Modular Tools
=============================================================================

This module provides the factory function for creating LangGraph agents
that can use any registered tools (MCP or LangChain).

FACTORY DESIGN:
---------------

The create_langgraph_agent() function is the main entry point. It:
1. Accepts a list of BaseTool instances (or uses all registered tools)
2. Binds tools to the LLM using LangChain's tool binding
3. Creates a state graph with llm_call and tool_node
4. Routes tool execution to the appropriate handler (MCP or LangChain)

USAGE:
------

Basic usage with all registered tools:
```python
from utils import create_langgraph_agent
from tools import get_all_tools

agent = create_langgraph_agent(
    api_model="granite-4:micro-h",
    api_key="your-key",
    api_base="http://localhost:11434/v1",
    tools=get_all_tools()
)
```

Custom tool selection:
```python
from tools import get_tool_by_name

# Only use specific tools
custom_tools = [
    get_tool_by_name("firecrawl_scrape"),
    get_tool_by_name("searx_search"),
]

agent = create_langgraph_agent(
    api_model="...",
    api_key="...",
    api_base="...",
    tools=custom_tools
)
```

EXTENSION POINTS:
-----------------

1. To add tools: See tools/ package documentation
2. To modify LLM: Change llm initialization in create_langgraph_agent()
3. To modify routing: Edit should_continue() function
4. To add nodes: Add new nodes to agent_builder before compile()

=============================================================================
"""

from typing import List, Literal, Callable, Optional, Dict, Any
import operator
import json

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, ToolMessage
from typing_extensions import TypedDict, Annotated
from langgraph.graph import StateGraph, START, END


# =============================================================================
# STATE SCHEMA
# =============================================================================

class MessagesState(TypedDict):
    """
    State maintained throughout the agent graph execution.
    
    This TypedDict defines the state that flows through the LangGraph nodes.
    Each node can read and update this state.
    
    Attributes:
        messages: Accumulated conversation messages (Human, AI, Tool).
                 Uses operator.add to append new messages to existing list.
        llm_calls: Counter tracking number of LLM invocations.
        tool_instances: Map of tool name -> tool instance for execution.
    
    Extension Point:
        Add new state fields here if you need to track additional data
        across the agent execution. For example:
        ```python
        class MessagesState(TypedDict):
            messages: Annotated[list, operator.add]
            llm_calls: int
            tool_instances: dict
            # Add your custom state:
            custom_context: dict
        ```
    """
    messages: Annotated[list, operator.add]
    llm_calls: int
    tool_instances: Dict[str, Any]  # Using Any to avoid TYPE_CHECKING issues with TypedDict


# =============================================================================
# DEFAULT SYSTEM PROMPT
# =============================================================================

DEFAULT_SYSTEM_PROMPT = """You are a helpful AI assistant with web scraping and research capabilities.

You have access to tools that allow you to:
- Search the web for information
- Scrape content from websites
- Extract structured data from web pages
- Discover URLs on websites

When answering questions:
1. Use the appropriate tool for the task
2. Cite your sources with URLs when providing information
3. Be clear about what information came from which source
4. If a tool fails, explain the error and try an alternative approach

Always be helpful, accurate, and transparent about your information sources."""


# =============================================================================
# FACTORY FUNCTION
# =============================================================================

def create_langgraph_agent(
    api_model: str,
    api_key: str,
    api_base: str,
    tools: List["BaseTool"] = None,
    system_prompt: str = None,
    temperature: float = 0,
    recursion_limit: int = 100
) -> StateGraph:
    """
    Create a LangGraph agent configured with the provided tools.
    
    This is the main factory function for creating agents. It sets up:
    - LLM with tool binding
    - State graph with llm_call and tool_node
    - Routing logic for tool execution
    
    Args:
        api_model: Model name for the LLM (e.g., "granite-4:micro-h")
        api_key: API key for the LLM service
        api_base: Base URL for the LLM API (e.g., "http://localhost:11434/v1")
        tools: List of BaseTool instances to make available. If None, uses
               all registered tools from ToolRegistry.
        system_prompt: Custom system prompt. If None, uses DEFAULT_SYSTEM_PROMPT.
        temperature: LLM temperature (0 = deterministic). Default: 0
        recursion_limit: Max recursion for tool loops. Default: 100
    
    Returns:
        Compiled StateGraph ready for streaming execution
    
    Example:
        ```python
        from tools import get_all_tools
        
        agent = create_langgraph_agent(
            api_model="granite-4:micro-h",
            api_key="your-key",
            api_base="http://localhost:11434/v1",
            tools=get_all_tools(),
            system_prompt="You are a research assistant."
        )
        
        # Execute the agent
        async for chunk in agent.astream({"messages": [HumanMessage("Hello")]}):
            print(chunk)
        ```
    
    Extension Points:
        1. Modify system_prompt to change agent behavior
        2. Pass custom tools list to limit available tools
        3. Adjust temperature for more/less creative responses
        4. Increase recursion_limit for complex multi-step tasks
    """
    # Import here to avoid circular imports
    from tools import get_all_tools
    
    # Use all registered tools if none provided
    if tools is None:
        tools = get_all_tools()
    
    # Use default system prompt if none provided
    if system_prompt is None:
        system_prompt = DEFAULT_SYSTEM_PROMPT
    
    print(f"\n{'='*80}")
    print(f"🏭 LANGGRAPH FACTORY: Creating agent")
    print(f"   Model: {api_model}")
    print(f"   Tools: {len(tools)}")
    for tool in tools:
        print(f"      - {tool.name} ({tool.tool_type})")
    print(f"{'='*80}")
    
    # -------------------------------------------------------------------------
    # Initialize LLM
    # -------------------------------------------------------------------------
    
    llm = ChatOpenAI(
        model=api_model,
        api_key=api_key,
        base_url=api_base,
        temperature=temperature
    )
    
    # -------------------------------------------------------------------------
    # Build tool mapping and bind to LLM
    # -------------------------------------------------------------------------
    
    # Create mapping of tool name -> BaseTool instance for execution
    tool_instances: Dict[str, "BaseTool"] = {tool.name: tool for tool in tools}
    
    # Get LangChain tool functions for binding to LLM
    langchain_tools = [tool.get_langchain_tool() for tool in tools]
    tools_by_name = {t.name: t for t in langchain_tools}
    
    # Bind tools to LLM (enables function calling)
    llm_with_tools = llm.bind_tools(langchain_tools)
    
    # -------------------------------------------------------------------------
    # Define Graph Nodes
    # -------------------------------------------------------------------------
    
    def llm_call(state: dict) -> dict:
        """
        LLM node: Processes messages and decides on next action.
        
        This node:
        1. Prepends the system prompt to the conversation
        2. Invokes the LLM with all messages
        3. Returns either a tool call request or final response
        
        Extension Point:
            Modify this function to change how the LLM is invoked,
            add pre/post processing, or inject additional context.
        """
        system_message = SystemMessage(content=system_prompt)
        
        return {
            "messages": [
                llm_with_tools.invoke(
                    [system_message] + state["messages"]
                )
            ],
            "llm_calls": state.get('llm_calls', 0) + 1,
            "tool_instances": state.get("tool_instances", tool_instances)
        }
    
    async def tool_node(state: dict) -> dict:
        """
        Tool execution node: Executes tools and returns results.
        
        This node handles both MCP and LangChain tools by:
        1. Looking up the tool instance by name
        2. Calling the tool's execute() method
        3. Returning a ToolMessage with the result
        
        The tool routing is handled automatically by BaseTool.execute()
        - MCPTool: Calls MCP server via JSON-RPC
        - LangChainTool: Executes Python implementation directly
        
        Extension Point:
            To add custom tool execution logic, override execute() in
            your BaseTool subclass rather than modifying this node.
        """
        result = []
        instances = state.get("tool_instances", tool_instances)
        
        # Get tool calls from last message
        last_message = state['messages'][-1]
        num_tool_calls = len(last_message.tool_calls) if hasattr(last_message, 'tool_calls') else 0
        
        print(f"\n{'='*80}")
        print(f"🔄 TOOL NODE: Processing {num_tool_calls} tool call(s)")
        print(f"{'='*80}")
        
        if num_tool_calls == 0:
            print("⚠️  No tool calls found in last message")
            return {"messages": result}
        
        for idx, tool_call in enumerate(last_message.tool_calls, 1):
            tool_name = tool_call["name"]
            tool_args = tool_call["args"]
            tool_call_id = tool_call["id"]
            
            print(f"\n{'─'*60}")
            print(f"📤 [{idx}/{num_tool_calls}] Executing tool: {tool_name}")
            print(f"📤 Tool call ID: {tool_call_id}")
            print(f"📤 Arguments: {json.dumps(tool_args, indent=2)}")
            print(f"{'─'*60}")
            
            # Look up the tool instance
            tool_instance = instances.get(tool_name)
            
            if tool_instance is None:
                error_msg = f"Unknown tool: {tool_name}. Available tools: {list(instances.keys())}"
                print(f"\n❌ {error_msg}")
                result.append(ToolMessage(
                    content=error_msg,
                    tool_call_id=tool_call_id,
                    name=tool_name
                ))
                continue
            
            try:
                # Execute the tool using its execute() method
                # This handles MCP vs LangChain routing automatically
                print(f"\n⏳ Awaiting {tool_name}.execute()...")
                observation = await tool_instance.execute(**tool_args)
                
                # Log the result
                print(f"\n📥 TOOL NODE received result:")
                print(f"📥 Result type: {type(observation).__name__}")
                print(f"📥 Result length: {len(str(observation))} chars")
                
                # Show content preview
                result_preview = str(observation)[:1000]
                print(f"📥 Result preview:\n{'-'*40}\n{result_preview}")
                if len(str(observation)) > 1000:
                    print(f"... (truncated, total: {len(str(observation))} chars)")
                print(f"{'-'*40}")
                
                result.append(ToolMessage(
                    content=str(observation),
                    tool_call_id=tool_call_id,
                    name=tool_name
                ))
                print(f"\n✅ Tool {tool_name} completed successfully")
                
            except Exception as e:
                import traceback
                error_msg = f"Error executing {tool_name}: {str(e)}"
                print(f"\n❌ TOOL NODE EXCEPTION:")
                print(f"❌ Error: {error_msg}")
                print(f"❌ Traceback:\n{traceback.format_exc()}")
                
                result.append(ToolMessage(
                    content=error_msg,
                    tool_call_id=tool_call_id,
                    name=tool_name
                ))
        
        print(f"\n{'='*80}")
        print(f"🔄 TOOL NODE SUMMARY:")
        print(f"   - Processed: {len(result)} tool call(s)")
        for r in result:
            content_preview = str(r.content)[:100]
            print(f"   - {r.name}: {len(str(r.content))} chars - '{content_preview}...'")
        print(f"{'='*80}\n")
        
        return {"messages": result}
    
    def should_continue(state: MessagesState) -> Literal["tool_node", END]:
        """
        Routing logic: Determines next step after LLM response.
        
        Checks if the last message contains tool_calls:
        - If yes: Route to tool_node to execute tools, then back to llm_call
        - If no: Route to END (return response to user)
        
        Extension Point:
            Add additional routing logic here, such as:
            - Max tool calls check
            - Specific tool result handling
            - Error recovery routing
        """
        messages = state["messages"]
        last_message = messages[-1]
        
        if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
            return "tool_node"  # Execute tools and loop back to LLM
        
        return END  # No tools needed, return response to user
    
    # -------------------------------------------------------------------------
    # Build the Agent Graph
    # -------------------------------------------------------------------------
    
    # Create the state graph with our schema
    agent_builder = StateGraph(MessagesState)
    
    # Register nodes
    # Extension Point: Add custom nodes here
    # agent_builder.add_node("custom_node", custom_function)
    agent_builder.add_node("llm_call", llm_call)
    agent_builder.add_node("tool_node", tool_node)
    
    # Define edges
    # START -> llm_call (entry point)
    agent_builder.add_edge(START, "llm_call")
    
    # llm_call -> tool_node OR END (conditional routing)
    agent_builder.add_conditional_edges(
        "llm_call",
        should_continue,
        ["tool_node", END]
    )
    
    # tool_node -> llm_call (loop back after tool execution)
    agent_builder.add_edge("tool_node", "llm_call")
    
    # Extension Point: Add custom edges here
    # agent_builder.add_edge("custom_node", "llm_call")
    
    # -------------------------------------------------------------------------
    # Compile and Return
    # -------------------------------------------------------------------------
    
    print(f"\n✅ Agent compiled successfully with {len(tools)} tools")
    
    return agent_builder.compile()
