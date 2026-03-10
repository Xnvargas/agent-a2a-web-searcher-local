"""
Orchestrator Agent — Single A2A entry point.

Responsibilities:
1. Receive full SWOT context from frontend
2. Classify user intent
3. Route to appropriate specialist via handoff tools
4. Assemble specialist responses into final answer
5. Manage conversation history with sliding window + summarization

Does NOT: Execute domain tools directly. Only routes.
"""

from typing import Optional, Dict, Any, List, Literal
import operator

from typing_extensions import TypedDict, Annotated
from langgraph.graph import StateGraph, START, END
from langchain_core.messages import SystemMessage, ToolMessage

from .base import create_specialist_agent, MODEL_REASONING
from .prompts.orchestrator_prompt import build_orchestrator_prompt
from .history import apply_sliding_window, get_last_user_message


# =================================================================
# STATE SCHEMA
# =================================================================

def _merge_tool_attempts(existing: dict, new: dict) -> dict:
    merged = dict(existing)
    for k, v in new.items():
        merged[k] = max(merged.get(k, 0), v)
    return merged


class MultiAgentState(TypedDict):
    """Top-level state flowing through the orchestrator graph."""
    messages: Annotated[list, operator.add]       # Full conversation history
    swot_context: Dict[str, Any]                  # From frontend metadata

    # Routing
    active_agent: str                              # Currently executing agent
    handoff_chain: Annotated[list, operator.add]   # Track handoff path for tracing

    # History management
    summary_of_older_turns: Optional[str]
    recent_turn_count: int

    # Metrics
    total_llm_calls: int

    # LangGraph sub-graph compat
    llm_calls: int
    tool_instances: Dict[str, Any]
    tool_attempts: Annotated[Dict[str, int], _merge_tool_attempts]


# Maximum characters for tool results in context
MAX_TOOL_RESULT_CHARS = 4000
MAX_TOOL_ATTEMPTS = 3
MAX_ERROR_MSG_CHARS = 300


# =================================================================
# ORCHESTRATOR FACTORY
# =================================================================

def create_orchestrator(
    swot_context: Optional[Dict[str, Any]],
    api_base: str = "http://192.168.0.58:11434",
) -> "CompiledGraph":
    """
    Create the multi-agent orchestrator graph.

    This replaces the single create_langgraph_agent() call.
    Called once per A2A request in agent.py.
    """
    import json
    from langchain_ollama import ChatOllama
    from .tool_sets import get_orchestrator_tools

    # Build orchestrator prompt
    system_prompt = build_orchestrator_prompt(swot_context)

    # Get handoff tools (the orchestrator's only tools)
    handoff_tools = get_orchestrator_tools()

    # Build tool instances map
    tool_instances = {t.name: t for t in handoff_tools}

    # Get LangChain tool functions for binding
    langchain_tools = [t.get_langchain_tool() for t in handoff_tools]

    # Initialize LLM
    ollama_base_url = api_base.rstrip("/").replace("/v1", "")

    print(f"\n{'='*80}")
    print(f"  ORCHESTRATOR: Creating multi-agent graph")
    print(f"   Model: {MODEL_REASONING}")
    print(f"   Handoff tools: {[t.name for t in handoff_tools]}")
    print(f"   Ollama URL: {ollama_base_url}")
    print(f"{'='*80}")

    llm = ChatOllama(
        base_url=ollama_base_url,
        model=MODEL_REASONING,
        temperature=0,
        reasoning=True,
        streaming=True,
        num_predict=-1,
        num_ctx=50000,
    )

    llm_with_tools = llm.bind_tools(langchain_tools)

    # ── Node: LLM call (routing decision) ──
    def llm_call(state: dict) -> dict:
        """Orchestrator LLM node: classifies intent and routes."""
        sys_msg = SystemMessage(content=system_prompt)

        # Apply sliding window to history
        windowed_msgs, summary, needs_summarization = apply_sliding_window(
            state["messages"],
            state.get("summary_of_older_turns"),
        )

        return {
            "messages": [
                llm_with_tools.invoke([sys_msg] + windowed_msgs)
            ],
            "llm_calls": state.get("llm_calls", 0) + 1,
            "total_llm_calls": state.get("total_llm_calls", 0) + 1,
            "tool_instances": state.get("tool_instances") or tool_instances,
            "tool_attempts": state.get("tool_attempts", {}),
            "summary_of_older_turns": summary if needs_summarization else state.get("summary_of_older_turns"),
        }

    # ── Node: Tool execution (handoff dispatch) ──
    async def tool_node(state: dict) -> dict:
        """Execute handoff tools — each creates a specialist sub-graph."""
        import hashlib

        result = []
        instances = state.get("tool_instances") or tool_instances
        attempts = dict(state.get("tool_attempts", {}))

        last_message = state["messages"][-1]
        if not hasattr(last_message, "tool_calls") or not last_message.tool_calls:
            return {"messages": result, "tool_attempts": attempts}

        # Track duplicate handoff calls
        previous_call_sigs = set()
        for msg in state.get("messages", []):
            if hasattr(msg, "tool_calls") and msg.tool_calls:
                for prev_tc in msg.tool_calls:
                    sig = hashlib.md5(
                        f"{prev_tc['name']}:{json.dumps(prev_tc['args'], sort_keys=True)}".encode()
                    ).hexdigest()
                    previous_call_sigs.add(sig)

        print(f"\n{'='*60}")
        print(f"  ORCHESTRATOR TOOL NODE: {len(last_message.tool_calls)} handoff(s)")
        print(f"{'='*60}")

        for tc in last_message.tool_calls:
            tool_name = tc["name"]
            tool_args = tc["args"]
            tool_call_id = tc["id"]

            print(f"\n  Handoff: {tool_name}")
            print(f"  Args: {json.dumps(tool_args, indent=2)[:500]}")

            # Check for duplicate handoff call
            call_sig = hashlib.md5(
                f"{tool_name}:{json.dumps(tool_args, sort_keys=True)}".encode()
            ).hexdigest()
            if call_sig in previous_call_sigs:
                dup_msg = (
                    f"This exact handoff ({tool_name}) was already executed with "
                    f"identical arguments. Use the previous result to formulate "
                    f"your response — do NOT retry the same handoff."
                )
                print(f"  DUPLICATE HANDOFF DETECTED: {tool_name} — skipping")
                result.append(ToolMessage(content=dup_msg, tool_call_id=tool_call_id, name=tool_name))
                continue
            previous_call_sigs.add(call_sig)

            # Check retry limit
            current_failures = attempts.get(tool_name, 0)
            if current_failures >= MAX_TOOL_ATTEMPTS:
                block_msg = (
                    f"Tool '{tool_name}' has failed {current_failures} "
                    f"consecutive times. Maximum retries ({MAX_TOOL_ATTEMPTS}) reached."
                )
                result.append(ToolMessage(content=block_msg, tool_call_id=tool_call_id, name=tool_name))
                continue

            tool_instance = instances.get(tool_name)
            if tool_instance is None:
                error_msg = f"Unknown tool: {tool_name}. Available: {list(instances.keys())}"
                result.append(ToolMessage(content=error_msg, tool_call_id=tool_call_id, name=tool_name))
                continue

            try:
                print(f"  Executing {tool_name}...")
                observation = await tool_instance.execute(**tool_args)

                raw = str(observation)
                is_error = raw.startswith("Error")
                if is_error:
                    attempts[tool_name] = current_failures + 1
                else:
                    attempts[tool_name] = 0

                # Truncate if needed
                if len(raw) > MAX_TOOL_RESULT_CHARS:
                    content = raw[:MAX_TOOL_RESULT_CHARS] + f"\n\n[...truncated at {MAX_TOOL_RESULT_CHARS} chars]"
                else:
                    content = raw

                result.append(ToolMessage(content=content, tool_call_id=tool_call_id, name=tool_name))
                print(f"  {tool_name} completed ({len(raw)} chars)")

            except Exception as e:
                import traceback
                attempts[tool_name] = current_failures + 1
                error_brief = str(e)[:MAX_ERROR_MSG_CHARS]
                condensed = f"Error executing {tool_name}: {error_brief}"
                print(f"  ERROR in {tool_name}: {e}")
                print(traceback.format_exc())
                result.append(ToolMessage(content=condensed, tool_call_id=tool_call_id, name=tool_name))

        return {"messages": result, "tool_attempts": attempts}

    # ── Routing: should continue? ──
    def should_continue(state: MultiAgentState) -> Literal["tool_node", "__end__"]:
        messages = state["messages"]
        last_message = messages[-1]
        if hasattr(last_message, "tool_calls") and last_message.tool_calls:
            return "tool_node"
        return END

    # ── Build graph ──
    graph = StateGraph(MultiAgentState)

    graph.add_node("llm_call", llm_call)
    graph.add_node("tool_node", tool_node)

    graph.add_edge(START, "llm_call")
    graph.add_conditional_edges("llm_call", should_continue, ["tool_node", END])
    graph.add_edge("tool_node", "llm_call")

    print(f"\n  Orchestrator graph compiled successfully")

    return graph.compile()
