"""
Node: Human Feedback Manager (The Coach)

This node manages human feedback and classifies it for routing decisions.
It resumes AFTER human provides feedback via UI/API.
"""

from src.state import AgentState


def human_feedback_manager_node(state: AgentState) -> dict:
    """
    Human Feedback Manager node function.
    
    This function:
    1. Resumes after human provides feedback
    2. Processes feedback type (approve, parameter_update, narrative_tweak)
    3. Updates state for routing logic in graph.py
    
    Note: In a real app, you might use an LLM here to classify free-text feedback
    into "parameter_update" vs "narrative_tweak". For now, we assume the frontend/API
    sets the 'feedback_type' directly.
    
    Returns:
        dict: Updated state (routing happens in conditional edge in graph.py)
    """
    print("--- HUMAN FEEDBACK MANAGER (HIL) ---")
    # This node resumes AFTER human provides feedback.
    
    # In a real app, you might use an LLM here to classify the free-text feedback
    # into "parameter_update" vs "narrative_tweak".
    # For now, we assume the frontend/API sets the 'feedback_type'.
    
    feedback_type = state.get("feedback_type", "approve")
    comments = state.get("human_feedback", [])
    
    print(f"Received Feedback Type: {feedback_type}")
    print(f"Comments: {comments}")
    
    # The return value here just updates state/logs, 
    # the actual routing happens in the Conditional Edge in graph.py
    return {}

