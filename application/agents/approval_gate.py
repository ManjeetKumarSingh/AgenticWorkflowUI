# agents/approval_gate.py

def approval_gate(state):
    """
    Gate that checks if approval is needed and pauses workflow if required.
    Returns updated state marking whether to continue or await approval.
    """
    approval_status = state.get("approval_status", "pending")
    is_approval_required = state.get("human_approval_required", False)
    
    if is_approval_required and approval_status == "rejected":
        state["_pause_for_approval"] = False
        state["_workflow_paused"] = False
        state["_workflow_rejected"] = True
        return state

    # Mark the next action based on approval status
    if is_approval_required and approval_status == "pending":
        # Halt here - don't continue
        state["_pause_for_approval"] = True
        state["_workflow_paused"] = True
        state["_workflow_rejected"] = False
    else:
        # Approved or not required - continue
        state["_pause_for_approval"] = False
        state["_workflow_paused"] = False
        state["_workflow_rejected"] = False
    
    return state
