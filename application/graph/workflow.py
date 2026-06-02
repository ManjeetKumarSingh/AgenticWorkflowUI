from langgraph.graph import StateGraph
from langgraph.graph import END
from graph.workflow_config import create_workflow_config
from graph.dynamic_workflow import DynamicWorkflow

from agents.action import action_agent
from agents.dependency import dependency_agent
from agents.evaluator import evaluator_agent
from agents.governance import governance_agent
from agents.planner import planner_agent
from agents.risk import risk_agent
from agents.approval_gate import approval_gate
from state.workflow_state import WorkflowState, ApprovalStatus

__all__ = ["graph", "WorkflowState", "dynamic_workflow"]

def approval_router(state):
    """Route based on approval status"""
    if state.get("approval_status") == "rejected" or state.get("_workflow_rejected"):
        return "rejected"

    # If approval was already approved, continue to action
    if state.get("approval_status") == "approved":
        return "action"
    
    # If waiting for approval, go to awaiting_approval node
    if state.get("_pause_for_approval"):
        return "awaiting_approval"
    
    # Default to action
    return "action"

def awaiting_approval_node(state):
    """Node that pauses workflow for human approval"""
    state["_workflow_paused"] = True
    return state

def rejected_node(state):
    """Terminal node for workflows rejected by human review."""
    state["_pause_for_approval"] = False
    state["_workflow_paused"] = False
    state["_workflow_rejected"] = True
    state["current_step"] = "rejected"
    return state

# Configuration-driven workflow definition
WORKFLOW_NODES = {
    "planner": {
        "name": "Planner",
        "agent": planner_agent,
        "requires_approval": False,
    },
    "dependency": {
        "name": "Dependency Analysis",
        "agent": dependency_agent,
        "requires_approval": False,
    },
    "risk": {
        "name": "Risk Assessment",
        "agent": risk_agent,
        "requires_approval": False,
    },
    "governance": {
        "name": "Governance Check",
        "agent": governance_agent,
        "requires_approval": True,  # Human approval needed
    },
    "approval_gate": {
        "name": "Approval Gate",
        "agent": approval_gate,
        "requires_approval": False,
    },
    "awaiting_approval": {
        "name": "Awaiting Human Approval",
        "agent": awaiting_approval_node,
        "requires_approval": False,
    },
    "rejected": {
        "name": "Rejected",
        "agent": rejected_node,
        "requires_approval": False,
    },
    "action": {
        "name": "Action Execution",
        "agent": action_agent,
        "requires_approval": False,
    },
    "evaluator": {
        "name": "Evaluation",
        "agent": evaluator_agent,
        "requires_approval": False,
    },
}

# Edges with conditional routing from approval_gate
WORKFLOW_EDGES = [
    {"source": "planner", "target": "dependency"},
    {"source": "dependency", "target": "risk"},
    {"source": "risk", "target": "governance"},
    {"source": "governance", "target": "approval_gate"},
    # Conditional edges from approval_gate
    {"source": "approval_gate", "target": "awaiting_approval", "condition": approval_router, "router_type": "conditional"},
    {"source": "approval_gate", "target": "action", "condition": approval_router, "router_type": "conditional"},
    {"source": "approval_gate", "target": "rejected", "condition": approval_router, "router_type": "conditional"},
    {"source": "action", "target": "evaluator"},
]

# Create dynamic workflow from configuration
workflow_config = create_workflow_config(
    nodes_dict=WORKFLOW_NODES,
    edges_config=WORKFLOW_EDGES,
    entry_point="planner"
)

# Build dynamic workflow with checkpoints and human-in-the-loop
dynamic_workflow = DynamicWorkflow(workflow_config)
graph = dynamic_workflow.get_compiled_graph()
