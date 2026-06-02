# DYNAMIC WORKFLOW SYSTEM - Architecture Guide

## Overview
Your workflow is now **fully dynamic** with human-in-the-loop and checkpoint capabilities.

## Key Components

### 1. **Enhanced State Management** (`state/workflow_state.py`)
- **WorkflowState**: Extended with human approval, checkpoints, and history tracking
- **ApprovalStatus**: Tracks approval state (pending, approved, rejected, needs_revision)
- **CheckpointStatus**: Tracks checkpoint state (created, in_progress, completed, failed, paused)
- **Checkpoint**: Data structure for saving workflow state at each step

### 2. **Checkpoint Manager** (`memory/checkpoint_manager.py`)
Persists workflow state at each step:
```python
- create_checkpoint(): Save state at each node
- get_checkpoint(): Retrieve checkpoint data
- update_checkpoint(): Update approval status
- list_workflow_checkpoints(): History of all steps
- get_workflow_state_from_checkpoint(): Resume from checkpoint
```

### 3. **Configuration-Driven Workflow** (`graph/workflow_config.py`)
Replace hardcoding with configuration:
```python
WORKFLOW_NODES = {
    "node_id": {
        "name": "Display Name",
        "agent": agent_function,
        "requires_approval": True/False  # Human approval needed
    }
}

WORKFLOW_EDGES = [
    {"source": "a", "target": "b", "condition": router_func}
]
```

### 4. **Dynamic Workflow Engine** (`graph/dynamic_workflow.py`)
- Builds graph from configuration
- Wraps nodes with checkpoint logic
- Implements human-in-the-loop for approval nodes
- Tracks execution history
- Handles errors gracefully

### 5. **Updated Main Workflow** (`graph/workflow.py`)
Now uses dynamic configuration instead of hardcoded edges.

### 6. **Enhanced Dashboard** (`ui/dashboard.py`)
Three tabs:
- **Execute Workflow**: Run with real-time progress
- **Checkpoints**: View all saved states
- **Approval Queue**: Approve/reject with human feedback

---

## How to Add a New Workflow Step

### Add to `WORKFLOW_NODES`:
```python
"new_step": {
    "name": "New Step Display Name",
    "agent": new_agent_function,
    "requires_approval": False,  # Set True if needs human approval
}
```

### Add to `WORKFLOW_EDGES`:
```python
{"source": "previous_step", "target": "new_step"}
```

---

## Human-in-the-Loop Usage

When a node has `requires_approval: True`:

1. **Execution pauses** at that step
2. **Checkpoint is created** with the output
3. **Dashboard shows approval queue** with data
4. **User clicks Approve/Reject**
5. **Workflow resumes** or terminates

---

## Resume from Checkpoint

```python
from memory.checkpoint_manager import CheckpointManager

manager = CheckpointManager()
previous_state = manager.get_workflow_state_from_checkpoint("workflow_id")
result = dynamic_workflow.invoke(previous_state)
```

---

## Key Features

✅ **Dynamic Configuration**: No code changes needed to modify workflow
✅ **Checkpoints**: Every step is saved, can resume anytime
✅ **Human Approval**: Mark steps that need human decision
✅ **Execution History**: Full audit trail of all steps
✅ **Error Handling**: Graceful failure and retry
✅ **Extensible**: Easy to add new nodes and edges

---

## Running the App

```bash
cd /Users/manjeetkumar/Devlopment/AI-ML/AgenticWorkflowUI/application
streamlit run app.py
```

Visit http://localhost:8501 to see the dashboard with:
- Execute Workflow tab
- Checkpoints viewer
- Approval queue
- Dynamic workflow diagram
