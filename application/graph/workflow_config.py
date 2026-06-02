# graph/workflow_config.py

from typing import Dict, List, Callable, Any
from dataclasses import dataclass
from enum import Enum

class RouterType(str, Enum):
    CONDITIONAL = "conditional"
    HUMAN_APPROVAL = "human_approval"
    SIMPLE = "simple"

@dataclass
class WorkflowNode:
    """Represents a node in the workflow"""
    id: str
    name: str
    agent_func: Callable
    human_approval_required: bool = False
    retry_on_failure: bool = True
    timeout_seconds: int = 300

@dataclass
class WorkflowEdge:
    """Represents an edge between nodes"""
    source: str
    target: str
    condition: Callable = None  # Optional conditional function
    router_type: RouterType = RouterType.SIMPLE

@dataclass
class WorkflowConfig:
    """Configuration for the workflow"""
    name: str
    entry_point: str
    nodes: Dict[str, WorkflowNode]
    edges: List[WorkflowEdge]
    version: str = "1.0"
    enable_checkpoints: bool = True
    enable_human_loop: bool = True

def create_workflow_config(nodes_dict: Dict[str, Callable], 
                          edges_config: List[Dict[str, Any]],
                          entry_point: str = "planner") -> WorkflowConfig:
    """
    Factory function to create workflow config dynamically
    
    Args:
        nodes_dict: {"node_id": {"agent": func, "requires_approval": bool}}
        edges_config: [{"source": "a", "target": "b", "condition": func}]
        entry_point: Starting node
    """
    
    nodes = {}
    for node_id, config in nodes_dict.items():
        nodes[node_id] = WorkflowNode(
            id=node_id,
            name=config.get("name", node_id),
            agent_func=config.get("agent"),
            human_approval_required=config.get("requires_approval", False),
            retry_on_failure=config.get("retry_on_failure", True),
            timeout_seconds=config.get("timeout", 300)
        )
    
    edges = []
    for edge_config in edges_config:
        edges.append(WorkflowEdge(
            source=edge_config["source"],
            target=edge_config["target"],
            condition=edge_config.get("condition"),
            router_type=RouterType(edge_config.get("router_type", "simple"))
        ))
    
    return WorkflowConfig(
        name="DynamicWorkflow",
        entry_point=entry_point,
        nodes=nodes,
        edges=edges,
        enable_checkpoints=True,
        enable_human_loop=True
    )
