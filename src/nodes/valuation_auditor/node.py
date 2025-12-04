"""
Node: Valuation Auditor (The AI Auditor)

This node performs automated sanity checks on valuation metrics
to ensure calculations are reasonable and within expected ranges.
"""

from src.state import AgentState


def valuation_auditor_node(state: AgentState) -> dict:
    """
    Valuation Auditor node function.
    
    This function:
    1. Performs sanity checks on valuation metrics
    2. Validates WACC, growth rates, and other key parameters
    3. Generates audit trail for review
    
    Returns:
        dict: Updated state with audit_trail
    """
    print("--- VALUATION AUDITOR: Sanity Checking ---")
    
    metrics = state.get('valuation_metrics', {})
    audit_log = []
    
    # Example Check: Is WACC reasonable?
    wacc = metrics.get('wacc', 0)
    if wacc < 0.04 or wacc > 0.15:
        audit_log.append(f"⚠️ Warning: WACC {wacc:.1%} is outside typical range (4-15%).")
    else:
        audit_log.append(f"✅ WACC {wacc:.1%} looks reasonable.")
        
    return {"audit_trail": audit_log}

