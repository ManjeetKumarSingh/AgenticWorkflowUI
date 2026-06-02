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
    dependencies: List[str]
    risks: List[str]
    governance_output: str
    action_result: str
    evaluation_result: str
    
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
