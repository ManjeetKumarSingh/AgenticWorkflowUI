# state/workflow_state.py

from typing import TypedDict

class WorkflowState(TypedDict):

    request: str

    plan: str

    dependencies: list

    risks: list

    approved: bool

    action_result: str

    evaluation_result: str