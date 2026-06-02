# graph/dynamic_workflow.py

import uuid
from datetime import datetime
from langgraph.graph import StateGraph, END
from memory.checkpoint_manager import CheckpointManager
from state.workflow_state import WorkflowState, ApprovalStatus, CheckpointStatus
from graph.workflow_config import WorkflowConfig, RouterType

class DynamicWorkflow:
    """Dynamic workflow builder with human-in-the-loop and checkpoints"""
    
    def __init__(self, config: WorkflowConfig):
        self.config = config
        self.checkpoint_manager = CheckpointManager()
        self.graph = self._build_graph()
    
    def _build_graph(self):
        """Build graph from configuration"""
        builder = StateGraph(WorkflowState)
        
        # Add nodes
        for node_id, node in self.config.nodes.items():
            if node.human_approval_required:
                # Wrap agent with checkpoint and approval logic
                builder.add_node(node_id, self._create_approval_node(node))
            else:
                builder.add_node(node_id, self._create_checkpoint_node(node))
        
        # Track conditional edges
        conditional_edges_map = {}
        
        # Add edges
        for edge in self.config.edges:
            if edge.router_type == RouterType.CONDITIONAL and edge.condition:
                # Store conditional edge - will process separately
                if edge.source not in conditional_edges_map:
                    conditional_edges_map[edge.source] = []
                conditional_edges_map[edge.source].append(edge)
            else:
                builder.add_edge(edge.source, edge.target)
        
        # Add conditional edges
        for source, edges in conditional_edges_map.items():
            if edges and edges[0].condition:
                # Build path map for all possible routes this source can take
                paths = {}
                for edge in edges:
                    # The router function returns the target node name
                    paths[edge.target] = edge.target
                
                # Use the first condition function (should be same for all edges from same source)
                builder.add_conditional_edges(
                    source,
                    edges[0].condition,
                    paths
                )
        
        # Set entry point and end
        builder.set_entry_point(self.config.entry_point)
        
        # Connect last nodes to END  
        for node_id in self.config.nodes.keys():
            outgoing_edges = [e for e in self.config.edges if e.source == node_id]
            if not outgoing_edges:
                builder.add_edge(node_id, END)
        
        return builder.compile()
    
    def _create_checkpoint_node(self, node):
        """Create a node with checkpoint capability"""
        def checkpoint_node(state: dict):
            # Create checkpoint
            checkpoint_id = self.checkpoint_manager.create_checkpoint(
                workflow_id=state.get("workflow_id", str(uuid.uuid4())),
                node_name=node.id,
                state=state,
                human_approval_required=False
            )
            
            # Execute agent
            try:
                result = node.agent_func(state)
                
                if result is None:
                    result = state.copy()
                
                # Update checkpoint
                self.checkpoint_manager.update_checkpoint(
                    checkpoint_id,
                    status="completed",
                    data=result
                )
                
                # Track in history
                result["current_step"] = node.id
                if "execution_history" not in result:
                    result["execution_history"] = []
                result["execution_history"].append({
                    "step": node.id,
                    "timestamp": datetime.now().isoformat(),
                    "status": "completed",
                    "checkpoint_id": checkpoint_id
                })
                
                return result
            except Exception as e:
                self.checkpoint_manager.update_checkpoint(
                    checkpoint_id,
                    status="failed",
                    error=str(e)
                )
                result = state.copy()
                result["error"] = str(e)
                return result
        
        return checkpoint_node
    
    def _create_approval_node(self, node):
        """Create a node that requires human approval"""
        def approval_node(state: dict):
            # Create checkpoint with approval requirement
            checkpoint_id = self.checkpoint_manager.create_checkpoint(
                workflow_id=state.get("workflow_id", str(uuid.uuid4())),
                node_name=node.id,
                state=state,
                human_approval_required=True
            )
            
            try:
                # Execute agent
                result = node.agent_func(state)
                
                # Handle None result
                if result is None:
                    result = state.copy()
                
                # IMPORTANT: Set approval required
                result["human_approval_required"] = True
                
                # Only set approval_status to pending if not already approved or rejected
                current_status = result.get("approval_status", "pending")
                if current_status not in ["approved", "rejected"]:
                    result["approval_status"] = "pending"
                
                result["current_step"] = node.id
                
                # Update checkpoint with approval info
                self.checkpoint_manager.update_checkpoint(
                    checkpoint_id,
                    status="paused",
                    data=result,
                    approval_status=result.get("approval_status", "pending")
                )
                
                approval_status = result.get("approval_status", "pending")
                history_status = {
                    "pending": "awaiting_approval",
                    "approved": "approved",
                    "rejected": "rejected",
                }.get(approval_status, approval_status)

                if "execution_history" not in result:
                    result["execution_history"] = []
                result["execution_history"].append({
                    "step": node.id,
                    "timestamp": datetime.now().isoformat(),
                    "status": history_status,
                    "checkpoint_id": checkpoint_id
                })
                
                return result
            except Exception as e:
                result = state.copy()
                result["error"] = str(e)
                result["current_step"] = node.id
                return result
        
        return approval_node
    
    def get_compiled_graph(self):
        """Get the compiled graph for execution"""
        return self.graph
    
    def invoke(self, initial_state: dict, config=None):
        """Execute workflow with optional config"""
        # Ensure workflow has an ID
        if "workflow_id" not in initial_state:
            initial_state["workflow_id"] = str(uuid.uuid4())
        if "created_at" not in initial_state:
            initial_state["created_at"] = datetime.now().isoformat()
        if "execution_history" not in initial_state:
            initial_state["execution_history"] = []
        if "checkpoints" not in initial_state:
            initial_state["checkpoints"] = []
        
        return self.graph.invoke(initial_state, config)
    
    def stream(self, initial_state: dict, config=None):
        """Stream workflow execution"""
        if "workflow_id" not in initial_state:
            initial_state["workflow_id"] = str(uuid.uuid4())
        if "created_at" not in initial_state:
            initial_state["created_at"] = datetime.now().isoformat()
        
        for output in self.graph.stream(initial_state, config):
            yield output
