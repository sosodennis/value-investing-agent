"""
Node: Data Conflict Resolver (The Judge)

This node handles human-in-the-loop adjudication of data conflicts.
It resumes AFTER human interaction has resolved the conflict.
"""

from src.state import AgentState


def data_conflict_resolver_node(state: AgentState) -> dict:
    """
    Data Conflict Resolver node function.
    
    This function:
    1. Resumes after human interaction
    2. Assumes human has updated merged_financials via UI/API
    3. Clears conflict flags to allow workflow to proceed
    
    Returns:
        dict: Updated state with cleared conflict flags
    """
    print("--- DATA CONFLICT RESOLVER (HIL) ---")
    # This node resumes AFTER human interaction.
    # The human has likely updated 'merged_financials' directly via the UI/API before this runs.
    
    print(f"User resolved conflict. Final Revenue: {state.get('merged_financials', {}).get('revenue')}")
    
    return {
        "has_data_conflict": False,  # Clear the flag to proceed
        "conflict_details": None
    }

