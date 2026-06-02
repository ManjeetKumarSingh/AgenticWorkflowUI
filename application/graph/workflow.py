from langgraph.graph import StateGraph
from langgraph.graph import END

from agents.action import action_agent
from agents.dependency import dependency_agent
from agents.evaluator import evaluator_agent
from agents.governance import governance_agent
from agents.planner import planner_agent
from agents.risk import risk_agent
from state.workflow_state import WorkflowState

__all__ = ["graph", "WorkflowState"]

def risk_router(state):

    if len(state["risks"]) > 0:

        return "approval"

    return "action"

builder = StateGraph(
    WorkflowState
)
builder.add_node(
    "planner",
    planner_agent
)

builder.add_node(
    "dependency",
    dependency_agent
)

builder.add_node(
    "risk",
    risk_agent
)

builder.add_node(
    "governance",
    governance_agent
)

builder.add_node(
    "action",
    action_agent
)

builder.add_node(
    "evaluator",
    evaluator_agent
)

builder.set_entry_point(
    "planner"
)

builder.add_edge(
    "planner",
    "dependency"
)

builder.add_edge(
    "dependency",
    "risk"
)

builder.add_conditional_edges(
    "risk",
    risk_router,
    {
        "approval": "governance",
        "action": "action"
    }
)

builder.add_edge(
    "governance",
    "action"
)

builder.add_edge(
    "action",
    "evaluator"
)

builder.add_edge(
    "evaluator",
    END
)

graph = builder.compile()