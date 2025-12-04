"""
Node: User Injection - Private Data Loading

This node loads and processes user-provided private data sources
such as internal Excel files, PDFs, or other proprietary data.
"""

from src.state import AgentState


def user_injection_node(state: AgentState) -> dict:
    """
    User Injection node function.
    
    This function:
    1. Loads user-provided private data (PDFs, Excel, etc.)
    2. Extracts financial data using LlamaParse or similar tools
    3. Returns structured user_data for merger reconciliation
    
    Note: This is a mock implementation. In production, use LlamaParse
    to read uploaded PDF/Excel paths from state.
    
    Returns:
        dict: Updated state with user_data
    """
    print("--- USER INJECTION: Loading Private Data ---")
    # Mock implementation
    # In production: Use LlamaParse to read uploaded PDF/Excel paths from state
    
    # Returning mock data for demonstration
    return {
        "user_data": {
            "revenue": 105000000,  # Simulated private data
            "source": "Internal Excel"
        }
    }

