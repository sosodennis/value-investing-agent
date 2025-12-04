"""
Global State Definition for AI Equity Analyst Agent

This module defines the TypedDict structure that represents the shared state
across all nodes in the LangGraph workflow.

Supports V3 Architecture: Cyclic, Adaptive, and Human-in-the-Loop.
"""

from typing import TypedDict, Annotated, List, Dict, Optional, Any
import operator


class AgentState(TypedDict):
    """
    Global State object for the Financial Analyst Agent.

    Supports V3 Architecture: Cyclic, Adaptive, and Human-in-the-Loop.
    """
    # --- 1. Identity & Config ---
    ticker: str
    user_preferences: Dict[str, Any]  # e.g., {"risk_tolerance": "low", "valuation_method": "DCF"}
    
    # --- 2. Phase 1: Clarification Flags ---
    needs_clarification: bool     # Set by Profiler if intent is ambiguous
    clarification_history: Annotated[List[str], operator.add]  # History of user/agent clarification chat
    
    # --- 3. Phase 2: Data Layers ---
    sec_data: Dict[str, Any]      # Data from public Miner
    user_data: Dict[str, Any]     # Data from User Injection (PDF/Excel)
    error: Optional[str]          # For error handling in Miner
    
    # --- 4. Phase 3: Reconciliation ---
    merged_financials: Dict[str, Any]  # The "Single Source of Truth" after merging
    has_data_conflict: bool       # Set by Merger if variance > threshold
    conflict_details: Optional[str]  # Description of the conflict for the user
    
    # --- 5. Phase 4: Analysis & Audit ---
    valuation_metrics: Dict[str, Any]  # Outputs from Calculator
    audit_trail: List[str]        # Step-by-step calculation log for transparency
    
    # --- 6. Phase 5: Report & Refinement ---
    report_content: str           # Final Markdown draft
    feedback_type: str            # "approve", "parameter_update", "narrative_tweak"
    human_feedback: List[str]     # Specific instructions from the user
