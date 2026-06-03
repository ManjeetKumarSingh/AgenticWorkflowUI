# state/workflow_state.py

from typing import TypedDict, Any, Optional, List
from enum import Enum

class ApprovalStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    NEEDS_REVISION = "needs_revision"

class CheckpointStatus(str, Enum):
    CREATED = "created"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"

class WorkflowState(TypedDict, total=False):
    """
    Flexible workflow state that can hold any workflow-related data.
    Supports human-in-the-loop, checkpoints, and dynamic execution.
    Uses TypedDict with total=False to allow all fields to be optional.
    """
    # Core workflow fields
    workflow_id: str
    request: str
    created_at: str
    current_step: str
    
    # Output fields
    plan: str
    plan_summary: str
    workflow_type: str
    dependencies: List[str]
    dependency_assumptions: List[str]
    risks: List[str]
    risk_score: int
    risk_level: str
    mitigations: List[str]
    governance_output: str
    policy_checks: List[str]
    action_result: str
    execution_steps: List[str]
    evaluation_result: str
    success_criteria: List[str]
    next_actions: List[str]
    
    # LLM fields
    llm_config: dict
    planner_llm_used: bool
    dependency_llm_used: bool
    risk_llm_used: bool
    governance_llm_used: bool
    action_llm_used: bool
    evaluator_llm_used: bool
    
    # Approval fields
    human_approval_required: bool
    approval_status: str
    approval_comment: str
    
    # Checkpoint fields
    execution_history: List[dict]
    checkpoints: List[dict]
    
    # Internal workflow control fields
    _pause_for_approval: bool
    _workflow_paused: bool
    error: str
    
    # Allow any other fields
    __extra__: Any
