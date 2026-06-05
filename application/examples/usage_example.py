# examples/usage_example.py
"""
Example showing how to use the new Dynamic Workflow system
"""

from graph.workflow import dynamic_workflow
from state.workflow_state import ApprovalStatus
from datetime import datetime

# Example 1: Simple execution
def example_basic_execution():
    """Basic workflow execution"""
    initial_state = {
        "request": "Deploy new feature to production",
        "workflow_id": f"wf_{datetime.now().timestamp()}",
        "current_step": "planner",
        "plan": "",
        "dependencies": [],
        "risk_present": False,
        "approved": False,
        "action_result": "",
        "evaluation_result": "",
        "human_approval_required": False,
        "human_feedback": None,
        "approval_status": ApprovalStatus.PENDING,
        "checkpoints": [],
        "execution_history": [],
        "workflow_config": None,
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
        "error": None,
    }
    
    # Execute workflow
    result = dynamic_workflow.invoke(initial_state)
    print("Execution Result:")
    print(f"- Plan: {result.get('plan')}")
    print(f"- Risk present: {result.get('risk_present')}")
    print(f"- Action Result: {result.get('action_result')}")
    print(f"- Evaluation: {result.get('evaluation_result')}")


# Example 2: Stream execution (step-by-step)
def example_stream_execution():
    """Stream workflow execution to see each step"""
    initial_state = {
        "request": "Analyze system performance",
        "workflow_id": f"wf_{datetime.now().timestamp()}",
        # ... other fields ...
    }
    
    print("Streaming workflow execution:")
    for step in dynamic_workflow.stream(initial_state):
        print(f"Step: {step}")


# Example 3: Resume from checkpoint
def example_resume_from_checkpoint():
    """Resume workflow from a saved checkpoint"""
    from memory.checkpoint_manager import CheckpointManager
    
    manager = CheckpointManager()
    
    # Get saved state from last checkpoint
    saved_state = manager.get_workflow_state_from_checkpoint("your_workflow_id")
    
    if saved_state:
        # Resume execution
        result = dynamic_workflow.invoke(saved_state)
        print("Resumed workflow completed:", result)


# Example 4: Modify workflow configuration
def example_custom_workflow():
    """Create a custom workflow configuration"""
    from graph.workflow_config import create_workflow_config
    from graph.dynamic_workflow import DynamicWorkflow
    from agents.planner import planner_agent
    from agents.action import action_agent
    
    # Define custom workflow
    custom_nodes = {
        "start": {
            "name": "Start",
            "agent": planner_agent,
            "requires_approval": False,
        },
        "execute": {
            "name": "Execute",
            "agent": action_agent,
            "requires_approval": True,  # Needs human approval
        },
    }
    
    custom_edges = [
        {"source": "start", "target": "execute"}
    ]
    
    # Create and use custom workflow
    config = create_workflow_config(custom_nodes, custom_edges, "start")
    custom_workflow = DynamicWorkflow(config)
    
    initial_state = {
        "request": "Custom workflow test",
        # ... other fields ...
    }
    
    result = custom_workflow.invoke(initial_state)
    print("Custom workflow result:", result)


if __name__ == "__main__":
    print("=== Dynamic Workflow Examples ===\n")
    
    print("1. Basic Execution:")
    example_basic_execution()
    
    print("\n2. Stream Execution (see each step):")
    # example_stream_execution()  # Uncomment to use
    
    print("\n3. Resume from Checkpoint:")
    # example_resume_from_checkpoint()  # Uncomment to use
    
    print("\n4. Custom Workflow:")
    # example_custom_workflow()  # Uncomment to use
