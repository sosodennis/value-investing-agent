"""
LangGraph Workflow Definition

This module defines the StateGraph structure, node connections, and routing logic
for the AI Equity Analyst Agent workflow.
"""

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

from src.state import AgentState
from src.nodes.profiler.node import profiler_node
from src.nodes.data_miner.node import data_miner_node
from src.nodes.calculator.node import calculator_node
from src.nodes.reviewer.node import reviewer_node
from src.nodes.researcher.node import researcher_node
from src.nodes.writer.node import writer_node
from src.nodes.human_node.node import request_human_help_node


def route_after_miner(state: AgentState) -> str:
    """
    Conditional routing function after Data Miner node.
    
    Routes to human_help if error is detected, otherwise to calculator.
    
    Args:
        state: Current agent state
        
    Returns:
        str: Next node name ("human_help" or "calculator")
    """
    if state.get("error"):
        print("🔀 [Router] Error detected -> Human Help")
        return "human_help"
    print("🔀 [Router] Success -> Calculator")
    return "calculator"


def build_graph():
    """
    Build and compile the LangGraph workflow.
    
    Returns:
        Compiled graph with checkpointer and interrupt support
    """
    workflow = StateGraph(AgentState)
    
    # Add Nodes
    workflow.add_node("profiler", profiler_node)
    workflow.add_node("miner", data_miner_node)
    workflow.add_node("human_help", request_human_help_node)
    workflow.add_node("calculator", calculator_node)
    workflow.add_node("reviewer", reviewer_node)  # [New] Insight Reviewer
    workflow.add_node("researcher", researcher_node)
    workflow.add_node("writer", writer_node)
    
    # Add Edges
    # Start -> Profiler -> Miner -> Calculator -> Reviewer -> Researcher -> Writer -> END
    workflow.add_edge(START, "profiler")
    workflow.add_edge("profiler", "miner")
    
    workflow.add_conditional_edges(
        "miner",
        route_after_miner,
        {"human_help": "human_help", "calculator": "calculator"}
    )
    
    workflow.add_edge("human_help", "miner")  # Loop Back
    
    # Calculator -> Reviewer -> Researcher (新連接)
    workflow.add_edge("calculator", "reviewer")
    workflow.add_edge("reviewer", "researcher")
    
    workflow.add_edge("researcher", "writer")
    workflow.add_edge("writer", END)
    
    return workflow.compile(
        checkpointer=MemorySaver(),
        interrupt_before=["human_help"]
    )
