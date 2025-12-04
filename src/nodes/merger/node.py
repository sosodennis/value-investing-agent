"""
Node: Merger - Data Reconciliation

This node reconciles data from multiple sources (SEC filings and user-provided data)
and detects conflicts that require human adjudication.
"""

from src.state import AgentState


def merger_node(state: AgentState) -> dict:
    """
    Merger node function.
    
    This function:
    1. Compares SEC data with user-provided data
    2. Detects significant variances (conflicts)
    3. Returns conflict flag or merged financials
    
    Returns:
        dict: Updated state with has_data_conflict flag and merged_financials
    """
    print("--- MERGER NODE: Reconciling Data Sources ---")
    
    sec_rev = state.get('sec_data', {}).get('revenue', 0)
    user_rev = state.get('user_data', {}).get('revenue', 0)
    
    # Simple Variance Analysis Logic
    variance = abs(sec_rev - user_rev) / (sec_rev + 1e-9)
    threshold = 0.05  # 5% tolerance
    
    if variance > threshold:
        conflict_msg = f"Revenue mismatch: SEC says {sec_rev}, User says {user_rev} (Diff: {variance:.1%})"
        return {
            "has_data_conflict": True,
            "conflict_details": conflict_msg,
            # Do NOT update merged_financials yet; wait for judge
        }
    
    # No conflict? Default to User data (Expert Override), or average
    return {
        "has_data_conflict": False,
        "merged_financials": state.get('user_data') if user_rev else state.get('sec_data')
    }

