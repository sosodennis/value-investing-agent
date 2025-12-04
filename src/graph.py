"""
LangGraph Workflow - V3 Table-Aligned & Renamed Edition

Architecture Highlights:

1. Parallel Data Ingestion (Miner + User Injection)

2. Phase 3 Data Conflict Resolution (Human Judge)

3. Phase 5 Refinement Loop (Human Coach)

"""

from typing import List, Union

from langgraph.graph import StateGraph, START, END

from langgraph.checkpoint.memory import MemorySaver

from src.consts import NodeConsts, FeedbackConsts
from src.state import AgentState

# --- Node Imports ---

# Engineers should implement these in src/nodes/<node_name>/node.py

from src.nodes.profiler.node import profiler_node

from src.nodes.clarification.node import clarification_request_node

from src.nodes.data_miner.node import data_miner_node

from src.nodes.user_injection.node import user_injection_node

from src.nodes.human_node.node import request_human_help_node

from src.nodes.merger.node import merger_node

from src.nodes.data_conflict_resolver.node import data_conflict_resolver_node # [NEW NAME]

from src.nodes.calculator.node import calculator_node

from src.nodes.valuation_auditor.node import valuation_auditor_node         # [NEW NAME]

from src.nodes.writer.node import writer_node

from src.nodes.human_feedback_manager.node import human_feedback_manager_node # [NEW NAME]


# --- Routing Logic ---

def route_profiler(state: AgentState) -> Union[str, List[str]]:
    """
    Phase 1 Router: Ambiguity vs. Execution
    """
    if state.get("needs_clarification", False):
        print("❓ [Router] Profiler: Ambiguity detected -> Clarification Request")
        return NodeConsts.CLARIFICATION_REQUEST

    print("🚀 [Router] Profiler: Clear -> Launching Parallel Data Fetch")
    # Parallel execution of public mining and private data injection
    return [NodeConsts.MINER, NodeConsts.USER_INJECTION]


def route_miner(state: AgentState) -> str:
    """
    Phase 2 Router: Mining Success vs. Failure
    """
    if state.get("error"):
        print("⚠️ [Router] Miner: Error -> Human Help")
        return NodeConsts.HUMAN_HELP
    return NodeConsts.MERGER


def route_merger(state: AgentState) -> str:
    """
    Phase 3 Router: Data Conflict Resolution
    Checks if the Merger node flagged any significant variance.
    """
    if state.get("has_data_conflict", False):
        print("⚖️ [Router] Merger: Data Conflict Detected -> User Adjudication Needed")
        return NodeConsts.DATA_CONFLICT_RESOLVER

    print("✅ [Router] Merger: Data Consistent -> Calculator")
    return NodeConsts.CALCULATOR


def route_feedback_manager(state: AgentState) -> str:
    """
    Phase 5 Router: Refinement Loop
    Routes based on the TYPE of feedback provided by the human coach.
    """
    feedback_type = state.get("feedback_type", FeedbackConsts.APPROVE)

    if feedback_type == FeedbackConsts.APPROVE:
        print("🎉 [Router] Feedback: Approved -> Workflow End")
        return END

    elif feedback_type == FeedbackConsts.PARAMETER_UPDATE:
        print("🔢 [Router] Feedback: Parameter Update -> Rollback to Calculator")
        # Example: User changed Growth Rate from 2% to 3%
        return NodeConsts.CALCULATOR

    elif feedback_type == FeedbackConsts.NARRATIVE_TWEAK:
        print("📝 [Router] Feedback: Narrative Tweak -> Rollback to Writer")
        # Example: User requested "More pessimistic tone"
        return NodeConsts.WRITER

    print("🔄 [Router] Feedback: General Revision -> Rollback to Writer")
    return NodeConsts.WRITER


# --- Graph Construction ---

def build_graph():
    """
    Constructs the V3 Cyclic Graph.
    """
    workflow = StateGraph(AgentState)

    # 1. Add All Nodes
    # ----------------
    workflow.add_node(NodeConsts.PROFILER, profiler_node)
    workflow.add_node(NodeConsts.CLARIFICATION_REQUEST, clarification_request_node)

    # Data Layer
    workflow.add_node(NodeConsts.MINER, data_miner_node)
    workflow.add_node(NodeConsts.USER_INJECTION, user_injection_node)
    workflow.add_node(NodeConsts.HUMAN_HELP, request_human_help_node)  # For miner errors

    # Consolidation
    workflow.add_node(NodeConsts.MERGER, merger_node)
    workflow.add_node(NodeConsts.DATA_CONFLICT_RESOLVER, data_conflict_resolver_node)  # Human Judge

    # Analysis
    workflow.add_node(NodeConsts.CALCULATOR, calculator_node)
    workflow.add_node(NodeConsts.VALUATION_AUDITOR, valuation_auditor_node)  # AI Auditor

    # Output & Refinement
    workflow.add_node(NodeConsts.WRITER, writer_node)
    workflow.add_node(NodeConsts.HUMAN_FEEDBACK_MANAGER, human_feedback_manager_node)  # Human Coach

    # 2. Define Edges (The Flow)
    # --------------------------
    workflow.add_edge(START, NodeConsts.PROFILER)

    # Phase 1: Clarification Loop
    workflow.add_conditional_edges(
        NodeConsts.PROFILER,
        route_profiler,
        {
            NodeConsts.CLARIFICATION_REQUEST: NodeConsts.CLARIFICATION_REQUEST,
            NodeConsts.MINER: NodeConsts.MINER,
            NodeConsts.USER_INJECTION: NodeConsts.USER_INJECTION,
        },
    )
    workflow.add_edge(NodeConsts.CLARIFICATION_REQUEST, NodeConsts.PROFILER)  # Loop back with new info

    # Phase 2: Data Collection
    workflow.add_edge(NodeConsts.USER_INJECTION, NodeConsts.MERGER)  # Direct path

    workflow.add_conditional_edges(  # Conditional path for miner
        NodeConsts.MINER,
        route_miner,
        {
            NodeConsts.HUMAN_HELP: NodeConsts.HUMAN_HELP,
            NodeConsts.MERGER: NodeConsts.MERGER,
        },
    )
    workflow.add_edge(NodeConsts.HUMAN_HELP, NodeConsts.MINER)  # Retry mining after help

    # Phase 3: Data Reconciliation
    # Merger -> (Conflict Resolver OR Calculator)
    workflow.add_conditional_edges(
        NodeConsts.MERGER,
        route_merger,
        {
            NodeConsts.DATA_CONFLICT_RESOLVER: NodeConsts.DATA_CONFLICT_RESOLVER,
            NodeConsts.CALCULATOR: NodeConsts.CALCULATOR,
        },
    )
    workflow.add_edge(NodeConsts.DATA_CONFLICT_RESOLVER, NodeConsts.CALCULATOR)  # Resolved -> Continue

    # Phase 4: Analysis Pipeline
    workflow.add_edge(NodeConsts.CALCULATOR, NodeConsts.VALUATION_AUDITOR)
    workflow.add_edge(NodeConsts.VALUATION_AUDITOR, NodeConsts.WRITER)

    # Phase 5: Refinement Loop
    workflow.add_edge(NodeConsts.WRITER, NodeConsts.HUMAN_FEEDBACK_MANAGER)

    workflow.add_conditional_edges(
        NodeConsts.HUMAN_FEEDBACK_MANAGER,
        route_feedback_manager,
        {
            END: END,
            NodeConsts.CALCULATOR: NodeConsts.CALCULATOR,
            NodeConsts.WRITER: NodeConsts.WRITER,
        },
    )

    # 3. Compile
    app = workflow.compile(
        checkpointer=MemorySaver(),
        interrupt_before=[
            NodeConsts.CLARIFICATION_REQUEST,  # HIL: Intent Clarification
            NodeConsts.DATA_CONFLICT_RESOLVER,  # HIL: Data Adjudication
            NodeConsts.HUMAN_FEEDBACK_MANAGER,  # HIL: Final Review & Coaching
        ],
    )

    return app

