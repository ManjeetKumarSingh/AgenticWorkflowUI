# Architecture Overview - Dynamic Agentic Workflow

## 🏗️ Before vs After

### BEFORE (Hardcoded)
```
❌ Workflow edges hardcoded in graph
❌ No human-in-the-loop capability  
❌ No state persistence
❌ Adding steps requires code changes
❌ No approval mechanism
❌ No execution history
```

### AFTER (Dynamic + Human-in-the-Loop)
```
✅ Configuration-driven workflow
✅ Human approval gates on any step
✅ Automatic checkpoint persistence
✅ Add steps via configuration only
✅ Approval queue in dashboard
✅ Full execution history tracking
✅ Resume from any checkpoint
```

---

## 🔀 System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Streamlit Dashboard                       │
├─────────────────────────────────────────────────────────────┤
│  Tab 1: Execute  │  Tab 2: Checkpoints  │  Tab 3: Approvals │
└─────────────────────────────────────────────────────────────┘
                            ↓
        ┌──────────────────────────────────┐
        │    DynamicWorkflow Engine        │
        │  (graph/dynamic_workflow.py)     │
        └──────────────────────────────────┘
              ↓                        ↓
    ┌──────────────────┐    ┌─────────────────────┐
    │ WorkflowConfig   │    │ CheckpointManager   │
    │ (defines steps   │    │ (persists state)    │
    │  & routing)      │    │                     │
    └──────────────────┘    └─────────────────────┘
              ↓                        ↓
    ┌──────────────────┐    ┌─────────────────────┐
    │ Agent Functions  │    │ Checkpoint Files    │
    │ (process state)  │    │ (JSON on disk)      │
    └──────────────────┘    └─────────────────────┘
```

---

## 🔄 Workflow Execution Flow with Human Loop

```
User Input
    ↓
Workflow Starts (Step 1: Planner)
    ↓
Step 1: Planner executes → creates checkpoint
    ↓
Step 2: Dependency → creates checkpoint
    ↓
Step 3: Risk Assessment → creates checkpoint
    ↓
Step 4: Governance (requires_approval: TRUE) → creates checkpoint + PAUSES
    ↓
⏸️ WAITING FOR HUMAN APPROVAL
    │
    ├─→ [Show in Dashboard Approval Tab]
    ├─→ [User clicks Approve/Reject]
    │
    ↓ (if Approved)
    ↓
Step 5: Action → creates checkpoint
    ↓
Step 6: Evaluation → creates checkpoint
    ↓
Workflow Complete ✅
```

---

## 📝 Configuration-Driven Example

### Define Workflow in Code (once):
```python
WORKFLOW_NODES = {
    "planner": {"name": "Planner", "agent": planner_agent, "requires_approval": False},
    "risk": {"name": "Risk Analysis", "agent": risk_agent, "requires_approval": False},
    "governance": {"name": "Governance", "agent": governance_agent, "requires_approval": True},
    "action": {"name": "Execute", "agent": action_agent, "requires_approval": False},
}

WORKFLOW_EDGES = [
    {"source": "planner", "target": "risk"},
    {"source": "risk", "target": "governance"},
    {"source": "governance", "target": "action"},
]
```

### Change Workflow (no code changes!):
```python
# Change 1: Add new step
WORKFLOW_NODES["quality_check"] = {"name": "QA", "agent": qa_agent, "requires_approval": True}

# Change 2: Add routing
WORKFLOW_EDGES.append({"source": "action", "target": "quality_check"})

# Change 3: Require approval elsewhere
WORKFLOW_NODES["planner"]["requires_approval"] = True

# ✅ Dashboard automatically updates!
```

---

## 💾 Checkpoint Persistence

```
When Step Executes:
    ↓
Checkpoint Created:
    {
        "id": "uuid-123",
        "node_name": "governance",
        "status": "paused",
        "timestamp": "2024-06-03T10:30:00",
        "data": { entire state },
        "human_approval_required": true,
        "approval_status": "pending"
    }
    ↓
Saved to Disk:
    checkpoints/uuid-123.json
    ↓
Later: Resume from checkpoint:
    state = CheckpointManager.get_checkpoint("uuid-123")
    result = dynamic_workflow.invoke(state)
```

---

## 🎛️ Configuration vs Code

| Feature | Before | After |
|---------|--------|-------|
| Add workflow step | Edit code + recompile | Add dict entry |
| Change routing | Edit graph logic | Change condition |
| Add human approval | Redesign workflow | Set `requires_approval: True` |
| View history | None | Checkpoints tab |
| Resume workflow | Start from beginning | Resume from checkpoint |
| Production changes | Need deployment | Live config change |

---

## 🚀 3-Tab Dashboard Interface

```
┌────────────────────────────────────────────────────────┐
│  Execute Workflow │ Checkpoints │ Approval Queue        │
├────────────────────────────────────────────────────────┤
│                                                         │
│ Tab 1: Execute Workflow                               │
│ ├─ Input Request                                      │
│ ├─ Execute Button                                     │
│ └─ Results (Plan, Risks, Actions, Evaluation)         │
│    └─ Workflow Architecture Diagram                   │
│                                                         │
├────────────────────────────────────────────────────────┤
│                                                         │
│ Tab 2: Checkpoints                                    │
│ ├─ Checkpoint 1: planner (2024-06-03 10:15)           │
│ ├─ Checkpoint 2: dependency (2024-06-03 10:16)        │
│ ├─ Checkpoint 3: governance [PAUSED] (2024-06-03 10:17) │
│ └─ [View all checkpoint data]                         │
│                                                         │
├────────────────────────────────────────────────────────┤
│                                                         │
│ Tab 3: Approval Queue                                 │
│ ├─ ⏳ Awaiting approval for: governance               │
│ ├─ [View pending decision data]                       │
│ ├─ [✅ Approve Button]  [❌ Reject Button]            │
│ └─ [Feedback text field]                              │
│                                                         │
└────────────────────────────────────────────────────────┘
```

---

## 📊 Execution History Tracking

```
Each workflow stores:
├─ execution_history: []
│  ├─ {step: "planner", timestamp: "...", status: "completed"}
│  ├─ {step: "dependency", timestamp: "...", status: "completed"}
│  ├─ {step: "governance", timestamp: "...", status: "awaiting_approval"}
│  ├─ {step: "governance", timestamp: "...", status: "approved"}
│  ├─ {step: "action", timestamp: "...", status: "completed"}
│  └─ {step: "evaluator", timestamp: "...", status: "completed"}
│
├─ checkpoints: []
│  ├─ checkpoint_1.json (planner state)
│  ├─ checkpoint_2.json (dependency state)
│  ├─ checkpoint_3.json (governance state - AWAITING APPROVAL)
│  ├─ checkpoint_4.json (action state)
│  └─ checkpoint_5.json (evaluator state)
│
└─ metadata:
   ├─ workflow_id: "wf_1717398600"
   ├─ created_at: "2024-06-03T10:30:00"
   ├─ updated_at: "2024-06-03T10:35:45"
   └─ error: null (or error message if failed)
```

---

## 🎯 Key Files Updated

```
📁 application/
├─ state/
│  └─ workflow_state.py (UPDATED - enhanced state)
├─ memory/
│  └─ checkpoint_manager.py (NEW - persistence)
├─ graph/
│  ├─ workflow_config.py (NEW - configuration)
│  ├─ dynamic_workflow.py (NEW - engine)
│  └─ workflow.py (UPDATED - config-driven)
├─ ui/
│  └─ dashboard.py (UPDATED - 3-tab interface)
├─ examples/
│  └─ usage_example.py (NEW - examples)
├─ DYNAMIC_WORKFLOW_GUIDE.md (NEW)
└─ IMPLEMENTATION_SUMMARY.md (NEW)
```

---

## ✅ Features Summary

### ✨ Dynamic Configuration
- No code changes to add/remove steps
- YAML-like configuration dict
- Easy to read and modify

### 🔐 Human-in-the-Loop
- Mark any step for approval
- Dashboard shows queue
- Capture feedback/rejection reason

### 💾 Checkpoint System  
- Auto-save at each step
- Resume from any point
- Full state recovery

### 📊 Rich Dashboard
- Execute workflows visually
- Browse checkpoint history
- Manage approvals
- View workflow diagram

### 🔄 Flexible Routing
- Conditional edges
- Human approval gates
- Custom router functions

---

## 🚀 Getting Started (5 minutes)

1. **Start Dashboard:**
   ```bash
   cd application
   streamlit run app.py
   ```

2. **Execute Workflow:**
   - Go to "Execute Workflow" tab
   - Enter a request
   - Click Execute

3. **Review Checkpoints:**
   - Go to "Checkpoints" tab
   - See all saved states

4. **Try Approval:**
   - Execute workflow
   - Go to "Approval Queue" tab
   - Click Approve/Reject

5. **Add New Step:**
   - Edit `graph/workflow.py`
   - Add to WORKFLOW_NODES
   - Add to WORKFLOW_EDGES
   - ✅ Done! Dashboard updates automatically

---

**Your workflow system is now enterprise-ready with human oversight and full auditability! 🎉**
