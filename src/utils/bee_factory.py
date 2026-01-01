"""
=============================================================================
BEEAI AGENT FACTORY - Creates BeeAI Framework Agents with Modular Tools
=============================================================================

This module provides the factory function for creating BeeAI Framework agents
that can use the same tools as the LangGraph agent.

FACTORY DESIGN:
---------------

The create_beeai_agent() function is the main entry point. It:
1. Accepts a list of BaseTool instances (or uses all registered tools)
2. Creates executable StructuredTools that call BaseTool.execute() directly
3. Wraps with BeeAI's LangChainTool adapter
4. Creates a RequirementAgent with proper configuration
5. Returns the configured agent ready for execution

KEY FIX (2024):
---------------

The original implementation wrapped placeholder functions from get_langchain_tool()
which just returned "TOOL_PLACEHOLDER". This fix creates actual executable 
StructuredTools that call BaseTool.execute() directly, so BeeAI can actually
run the tools.

USAGE:
------

Basic usage with all registered tools:
```python
from utils.bee_factory import create_beeai_agent
from tools import get_all_tools

agent = create_beeai_agent(
    api_model="gpt-4o",
    api_key="your-key",
    api_base="http://localhost:11434/v1",
    tools=get_all_tools()
)
```

With custom configuration:
```python
agent = create_beeai_agent(
    api_model="granite-4:micro-h",
    api_key="...",
    api_base="...",
    tools=get_all_tools(),
    role="Research Assistant",
    instructions="You help users find information.",
)
```

=============================================================================
"""

from typing import List, Optional, Any, Dict, TYPE_CHECKING
import json
import asyncio

# LangChain imports for creating executable tools
from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field, create_model

# BeeAI Framework imports
from beeai_framework.agents.requirement import RequirementAgent
from beeai_framework.adapters.openai.backend.chat import OpenAIChatModel
from beeai_framework.memory import UnconstrainedMemory, TokenMemory
from beeai_framework.adapters.langchain import LangChainTool as BeeAILangChainToolAdapter
from beeai_framework.tools.think import ThinkTool

if TYPE_CHECKING:
    from tools.base import BaseTool


# =============================================================================
# DEFAULT SYSTEM INSTRUCTIONS
# =============================================================================

DEFAULT_ROLE = "Research Assistant"

DEFAULT_INSTRUCTIONS = """You are a helpful AI assistant with web scraping and research capabilities.

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
# LLM INITIALIZATION HELPER
# =============================================================================

def create_beeai_llm(api_model: str, api_key: str, api_base: str) -> OpenAIChatModel:
    """
    Create a BeeAI ChatModel configured for LiteLLM/OpenAI-compatible endpoint.
    
    Mirrors the LangGraph ChatOpenAI configuration:
        llm = ChatOpenAI(model=api_model, api_key=api_key, base_url=api_base)
    
    The model name is passed EXACTLY as-is, without any prefix stripping,
    because LiteLLM needs the exact registered model name.
    
    Args:
        api_model: Model name exactly as configured (e.g., "other:granite-4.0-h-small")
                  Passed directly without modification.
        api_key: API key for the LLM service
        api_base: Base URL for the LLM API (e.g., "http://localhost:11434/v1")
    
    Returns:
        OpenAIChatModel configured for the endpoint
    
    Example:
        ```python
        llm = create_beeai_llm(
            api_model="other:granite-4.0-h-small",  # Passed exactly as-is
            api_key="my-api-key",
            api_base="http://localhost:4000/v1"
        )
        ```
    """
    # Pass the model name EXACTLY as-is, just like ChatOpenAI does
    # Don't strip any prefixes - LiteLLM needs the exact registered model name
    
    settings = {
        "api_key": api_key,
        "base_url": api_base,
    }
    
    print(f"   🔧 Creating OpenAIChatModel (mirroring ChatOpenAI):")
    print(f"      model: {api_model}")
    print(f"      base_url: {api_base}")
    print(f"      api_key: {'***' + api_key[-4:] if api_key and len(api_key) > 4 else '(provided)'}")
    
    return OpenAIChatModel(api_model, settings=settings)


# =============================================================================
# SCHEMA TO PYDANTIC CONVERSION
# =============================================================================

def _schema_type_to_python(type_str: str) -> type:
    """
    Convert schema type string to Python type.
    
    Args:
        type_str: Schema type string ("string", "integer", "boolean", etc.)
    
    Returns:
        Python type
    """
    type_map = {
        "string": str,
        "integer": int,
        "number": float,
        "boolean": bool,
        "array": list,
        "object": dict,
    }
    return type_map.get(type_str, str)


def _create_args_schema(tool_name: str, schema: Dict[str, Dict[str, Any]]) -> type:
    """
    Create a Pydantic model from a tool's schema for StructuredTool.
    
    Args:
        tool_name: Name of the tool (used in model name)
        schema: Schema dict from BaseTool.get_schema()
    
    Returns:
        Pydantic model class for the tool's arguments
    
    Example:
        Schema: {"url": {"type": "string", "required": True, "description": "URL to scrape"}}
        Returns: A Pydantic model with url: str field
    """
    fields = {}
    
    for param_name, param_config in schema.items():
        python_type = _schema_type_to_python(param_config.get("type", "string"))
        description = param_config.get("description", "")
        required = param_config.get("required", False)
        default = param_config.get("default", None)
        
        if required:
            # Required field with description
            fields[param_name] = (python_type, Field(description=description))
        else:
            # Optional field with default
            fields[param_name] = (Optional[python_type], Field(default=default, description=description))
    
    # Create a unique model name
    model_name = f"{tool_name.replace('_', ' ').title().replace(' ', '')}Args"
    
    # Create the Pydantic model dynamically
    return create_model(model_name, **fields)


# =============================================================================
# TOOL WRAPPER FUNCTION
# =============================================================================

def wrap_tools_for_beeai(tools: List["BaseTool"]) -> List[Any]:
    """
    Create executable StructuredTools for use with BeeAI Framework.
    
    This function takes BaseTool instances and creates actual executable
    StructuredTools that call BaseTool.execute() directly. This fixes the
    issue where the original implementation wrapped placeholder functions
    that just returned "TOOL_PLACEHOLDER".
    
    The key difference from the original:
    - BEFORE: Wrapped get_langchain_tool() which returns placeholders
    - AFTER: Creates StructuredTool with async executor calling execute()
    
    Args:
        tools: List of BaseTool instances from the tools registry
    
    Returns:
        List of BeeAI-compatible tool instances (wrapped StructuredTools)
    
    Example:
        ```python
        from tools import get_all_tools
        
        registry_tools = get_all_tools()
        beeai_tools = wrap_tools_for_beeai(registry_tools)
        # These tools will actually execute when called by BeeAI
        ```
    """
    wrapped_tools = []
    
    print(f"\n{'='*80}")
    print(f"🐝 BEEAI TOOL WRAPPER: Creating executable tools for {len(tools)} tools")
    print(f"{'='*80}")
    
    for tool in tools:
        try:
            # ---------------------------------------------------------------------
            # Create async executor that calls the REAL execute() method
            # ---------------------------------------------------------------------
            # We use a factory function to properly capture the tool in a closure
            def make_async_executor(t):
                async def async_execute(**kwargs) -> str:
                    """Async executor that calls BaseTool.execute() directly."""
                    print(f"\n🐝 BEEAI TOOL EXECUTING: {t.name}")
                    print(f"   Args: {json.dumps(kwargs, default=str)[:200]}...")
                    
                    try:
                        result = await t.execute(**kwargs)
                        result_preview = str(result)[:200] if result else "(empty)"
                        print(f"   ✅ Result preview: {result_preview}...")
                        return result
                    except Exception as e:
                        error_msg = f"Tool {t.name} execution error: {type(e).__name__}: {str(e)}"
                        print(f"   ❌ {error_msg}")
                        return error_msg
                
                return async_execute
            
            # ---------------------------------------------------------------------
            # Create sync executor as fallback (uses asyncio.run)
            # ---------------------------------------------------------------------
            def make_sync_executor(t):
                def sync_execute(**kwargs) -> str:
                    """Sync executor fallback that wraps async execute()."""
                    print(f"\n🐝 BEEAI TOOL (SYNC) EXECUTING: {t.name}")
                    
                    try:
                        # Try to get the current event loop
                        try:
                            loop = asyncio.get_running_loop()
                            # If we're in an async context, we can't use asyncio.run
                            # Create a new task instead
                            import concurrent.futures
                            with concurrent.futures.ThreadPoolExecutor() as executor:
                                future = executor.submit(
                                    asyncio.run, 
                                    t.execute(**kwargs)
                                )
                                return future.result(timeout=60)
                        except RuntimeError:
                            # No running loop, safe to use asyncio.run
                            return asyncio.run(t.execute(**kwargs))
                    except Exception as e:
                        error_msg = f"Tool {t.name} sync execution error: {type(e).__name__}: {str(e)}"
                        print(f"   ❌ {error_msg}")
                        return error_msg
                
                return sync_execute
            
            # ---------------------------------------------------------------------
            # Build args_schema from tool's schema
            # ---------------------------------------------------------------------
            tool_schema = tool.get_schema()
            args_schema = _create_args_schema(tool.name, tool_schema) if tool_schema else None
            
            # ---------------------------------------------------------------------
            # Create StructuredTool with both sync and async executors
            # ---------------------------------------------------------------------
            # BeeAI primarily uses async, so the coroutine is important
            executable_tool = StructuredTool.from_function(
                func=make_sync_executor(tool),
                coroutine=make_async_executor(tool),
                name=tool.name,
                description=tool.description,
                args_schema=args_schema,
                return_direct=False,
            )
            
            # ---------------------------------------------------------------------
            # Wrap with BeeAI's LangChainTool adapter
            # ---------------------------------------------------------------------
            beeai_tool = BeeAILangChainToolAdapter[Any](executable_tool)
            
            wrapped_tools.append(beeai_tool)
            print(f"   ✓ Created executable tool: {tool.name} ({tool.tool_type})")
            if args_schema:
                print(f"      Schema fields: {list(tool_schema.keys())}")
            
        except Exception as e:
            import traceback
            print(f"   ✗ Failed to wrap {tool.name}: {type(e).__name__}: {str(e)}")
            print(f"      Traceback: {traceback.format_exc()}")
    
    print(f"\n{'='*80}")
    print(f"🐝 Successfully created {len(wrapped_tools)}/{len(tools)} executable tools")
    print(f"{'='*80}\n")
    
    return wrapped_tools


# =============================================================================
# FACTORY FUNCTION
# =============================================================================

def create_beeai_agent(
    api_model: str,
    api_key: str,
    api_base: str,
    tools: List["BaseTool"] = None,
    role: str = None,
    instructions: str = None,
    include_think_tool: bool = True,
    max_iterations: int = 15,
    max_retries_per_step: int = 3,
) -> RequirementAgent:
    """
    Create a BeeAI Framework RequirementAgent configured with the provided tools.
    
    This is the main factory function for creating BeeAI agents. It sets up:
    - LLM via ChatModel
    - Tool wrapping via LangChainTool adapter
    - Memory configuration
    - Agent role and instructions
    
    Args:
        api_model: Model name for the LLM (e.g., "gpt-4o", "granite-4:micro-h")
        api_key: API key for the LLM service
        api_base: Base URL for the LLM API (e.g., "http://localhost:11434/v1")
        tools: List of BaseTool instances to make available. If None, uses
               all registered tools from ToolRegistry.
        role: Agent role description. Default: "Research Assistant"
        instructions: Custom instructions. If None, uses DEFAULT_INSTRUCTIONS.
        include_think_tool: Whether to include ThinkTool for reasoning. Default: True
        max_iterations: Maximum execution iterations. Default: 15
        max_retries_per_step: Retries per step on failure. Default: 3
    
    Returns:
        Configured RequirementAgent ready for execution
    
    Example:
        ```python
        from tools import get_all_tools
        
        agent = create_beeai_agent(
            api_model="gpt-4o",
            api_key="your-key",
            api_base="https://api.openai.com/v1",
            tools=get_all_tools(),
        )
        
        # Execute the agent
        response = await agent.run(
            prompt="Search for Python tutorials",
            max_iterations=15,
        )
        print(response.answer.text)
        ```
    """
    # Import here to avoid circular imports
    from tools import get_all_tools
    
    # Use all registered tools if none provided
    if tools is None:
        tools = get_all_tools()
    
    # Use defaults if not provided
    if role is None:
        role = DEFAULT_ROLE
    
    if instructions is None:
        instructions = DEFAULT_INSTRUCTIONS
    
    print(f"\n{'='*80}")
    print(f"🐝 BEEAI FACTORY: Creating BeeAI RequirementAgent")
    print(f"   Model: {api_model}")
    print(f"   Base URL: {api_base}")
    print(f"   Role: {role}")
    print(f"   Tools: {len(tools)}")
    print(f"   Include ThinkTool: {include_think_tool}")
    print(f"{'='*80}")
    
    # -------------------------------------------------------------------------
    # Initialize LLM using OpenAIChatModel directly
    # -------------------------------------------------------------------------
    # This approach works with any OpenAI-compatible API including LiteLLM,
    # Ollama, and other inference servers provided by the agentstack platform.
    
    llm = create_beeai_llm(
        api_model=api_model,
        api_key=api_key,
        api_base=api_base,
    )
    
    # -------------------------------------------------------------------------
    # Wrap tools for BeeAI
    # -------------------------------------------------------------------------
    
    beeai_tools = wrap_tools_for_beeai(tools)
    
    # Optionally add ThinkTool for reasoning
    if include_think_tool:
        beeai_tools.insert(0, ThinkTool())
        print(f"   Added ThinkTool for reasoning")
    
    # -------------------------------------------------------------------------
    # Configure Memory
    # -------------------------------------------------------------------------
    
    # Using UnconstrainedMemory for simplicity
    # For production, consider TokenMemory with capacity management
    memory = UnconstrainedMemory()
    
    # -------------------------------------------------------------------------
    # Create RequirementAgent
    # -------------------------------------------------------------------------
    
    agent = RequirementAgent(
        llm=llm,
        tools=beeai_tools,
        memory=memory,
        role=role,
        instructions=instructions,
    )
    
    print(f"\n✅ BeeAI RequirementAgent created successfully")
    print(f"   Total tools: {len(beeai_tools)}")
    print(f"   Memory type: {type(memory).__name__}")
    print(f"{'='*80}\n")
    
    return agent


# =============================================================================
# ASYNC RUN HELPER
# =============================================================================

async def run_beeai_agent(
    agent: RequirementAgent,
    user_input: str,
) -> str:
    """
    Execute a BeeAI agent with the given input.
    
    This is a convenience function that handles the async execution
    and returns just the answer text.
    
    Args:
        agent: Configured RequirementAgent instance
        user_input: User's input message/question
    
    Returns:
        str: Agent's response text
    
    Example:
        ```python
        agent = create_beeai_agent(...)
        response = await run_beeai_agent(agent, "What is Python?")
        print(response)
        ```
    """
    print(f"\n{'='*80}")
    print(f"🐝 BEEAI RUN: Executing agent")
    print(f"   Input: {user_input[:100]}...")
    print(f"{'='*80}\n")
    
    try:
        # RequirementAgent.run() takes positional argument, not keyword
        response = await agent.run(user_input)
        
        # Handle different response structures
        if hasattr(response, 'answer') and response.answer:
            answer_text = response.answer.text
        elif hasattr(response, 'output') and response.output:
            if isinstance(response.output, list) and len(response.output) > 0:
                last_msg = response.output[-1]
                answer_text = last_msg.text if hasattr(last_msg, 'text') else str(last_msg)
            else:
                answer_text = str(response.output)
        elif hasattr(response, 'result'):
            answer_text = response.result.text if hasattr(response.result, 'text') else str(response.result)
        else:
            answer_text = str(response) if response else "No response generated"
        
        print(f"\n{'='*80}")
        print(f"🐝 BEEAI RUN COMPLETE")
        print(f"   Answer length: {len(answer_text)} chars")
        print(f"{'='*80}\n")
        
        return answer_text
        
    except Exception as e:
        error_msg = f"BeeAI Agent Error: {type(e).__name__}: {str(e)}"
        print(f"\n❌ {error_msg}")
        return error_msg
