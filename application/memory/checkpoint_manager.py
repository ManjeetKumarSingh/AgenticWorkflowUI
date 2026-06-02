# memory/checkpoint_manager.py

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any

class CheckpointManager:
    """Manages workflow checkpoints and state persistence"""
    
    def __init__(self, checkpoint_dir: str = "checkpoints"):
        self.checkpoint_dir = Path(checkpoint_dir)
        self.checkpoint_dir.mkdir(exist_ok=True)
    
    def create_checkpoint(self, workflow_id: str, node_name: str, state: dict, 
                         human_approval_required: bool = False) -> str:
        """Create a checkpoint for a workflow step"""
        checkpoint_id = str(uuid.uuid4())
        checkpoint = {
            "id": checkpoint_id,
            "workflow_id": workflow_id,
            "node_name": node_name,
            "status": "created",
            "timestamp": datetime.now().isoformat(),
            "data": state,
            "human_approval_required": human_approval_required,
            "approval_status": "pending",
            "feedback": None
        }
        
        self._save_checkpoint(checkpoint)
        return checkpoint_id
    
    def get_checkpoint(self, checkpoint_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a checkpoint"""
        checkpoint_file = self.checkpoint_dir / f"{checkpoint_id}.json"
        if checkpoint_file.exists():
            with open(checkpoint_file, 'r') as f:
                return json.load(f)
        return None
    
    def update_checkpoint(self, checkpoint_id: str, **updates) -> bool:
        """Update a checkpoint"""
        checkpoint = self.get_checkpoint(checkpoint_id)
        if checkpoint:
            checkpoint.update(updates)
            checkpoint["updated_at"] = datetime.now().isoformat()
            self._save_checkpoint(checkpoint)
            return True
        return False

    def update_workflow_approval_status(
        self,
        workflow_id: str,
        approval_status: str,
        feedback: Optional[str] = None,
        latest_state: Optional[dict] = None,
    ) -> int:
        """Persist a human approval decision across approval-related checkpoints."""
        updated_count = 0
        decision_state = latest_state.copy() if latest_state else None

        if decision_state is not None:
            decision_state["approval_status"] = approval_status
            if feedback is not None:
                decision_state["human_feedback"] = feedback
            decision_state["_pause_for_approval"] = False
            decision_state["_workflow_paused"] = False

        for checkpoint in self.list_workflow_checkpoints(workflow_id):
            checkpoint_data = checkpoint.get("data") or {}
            is_approval_checkpoint = (
                checkpoint.get("human_approval_required")
                or checkpoint_data.get("human_approval_required")
                or checkpoint_data.get("_pause_for_approval")
                or checkpoint.get("node_name") in {"governance", "approval_gate", "awaiting_approval"}
            )

            if not is_approval_checkpoint:
                continue

            checkpoint["status"] = approval_status
            checkpoint["approval_status"] = approval_status
            checkpoint["feedback"] = feedback
            checkpoint["updated_at"] = datetime.now().isoformat()
            if decision_state is not None:
                checkpoint["data"] = decision_state
            else:
                checkpoint_data["approval_status"] = approval_status
                if feedback is not None:
                    checkpoint_data["human_feedback"] = feedback
                checkpoint_data["_pause_for_approval"] = False
                checkpoint_data["_workflow_paused"] = False
                checkpoint["data"] = checkpoint_data

            self._save_checkpoint(checkpoint)
            updated_count += 1

        return updated_count
    
    def list_workflow_checkpoints(self, workflow_id: str) -> List[Dict[str, Any]]:
        """List all checkpoints for a workflow"""
        checkpoints = []
        for checkpoint_file in self.checkpoint_dir.glob("*.json"):
            with open(checkpoint_file, 'r') as f:
                checkpoint = json.load(f)
                if checkpoint.get("workflow_id") == workflow_id:
                    checkpoints.append(checkpoint)
        return sorted(checkpoints, key=lambda x: x["timestamp"])
    
    def _save_checkpoint(self, checkpoint: Dict[str, Any]):
        """Save checkpoint to disk"""
        checkpoint_file = self.checkpoint_dir / f"{checkpoint['id']}.json"
        with open(checkpoint_file, 'w') as f:
            json.dump(checkpoint, f, indent=2)
    
    def get_workflow_state_from_checkpoint(self, workflow_id: str) -> Optional[dict]:
        """Restore workflow state from latest checkpoint"""
        checkpoints = self.list_workflow_checkpoints(workflow_id)
        if checkpoints:
            return checkpoints[-1]["data"]
        return None
