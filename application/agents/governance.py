# agents/governance.py

def governance_agent(state):
    """
    Governance check agent.
    Preserves approval status if already set (e.g., after user approval).
    """
    # Only set approval status if not already set
    if "approval_status" not in state or state.get("approval_status") == "pending":
        # Default to pending for fresh execution
        if "approval_status" not in state:
            state["approval_status"] = "pending"
    
    return state