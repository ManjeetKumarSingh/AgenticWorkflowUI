# ui/dashboard.py

import streamlit as st
from datetime import datetime
from graph.workflow import graph, dynamic_workflow, WorkflowState
from memory.checkpoint_manager import CheckpointManager

checkpoint_manager = CheckpointManager()

def mark_workflow_rejected(workflow: dict, feedback: str) -> dict:
    """Update in-memory workflow state and related checkpoints after rejection."""
    workflow["approval_status"] = "rejected"
    workflow["_pause_for_approval"] = False
    workflow["_workflow_paused"] = False
    workflow["_workflow_rejected"] = True
    workflow["human_feedback"] = feedback
    workflow["updated_at"] = datetime.now().isoformat()

    for entry in workflow.get("execution_history", []):
        if entry.get("status") == "awaiting_approval" or entry.get("step") in {
            "governance",
            "approval_gate",
            "awaiting_approval",
        }:
            entry["status"] = "rejected"

    checkpoint_manager.update_workflow_approval_status(
        workflow_id=workflow.get("workflow_id"),
        approval_status="rejected",
        feedback=feedback,
        latest_state=workflow,
    )

    return workflow

def render_dashboard():

    st.title("🚀 Agentic AI Platform - Dynamic Workflow")
    
    # Create tabs
    tab1, tab2, tab3 = st.tabs(["Execute Workflow", "Checkpoints", "Approval Queue"])
    
    # ============ TAB 1: Execute Workflow ============
    with tab1:
        col1, col2 = st.columns([3, 1])
        with col1:
            request = st.text_input(
                "Enter Request",
                key="user_request",
                placeholder="Describe your workflow request..."
            )
        with col2:
            st.markdown("<div style='height: 1.75rem'></div>", unsafe_allow_html=True)
            execute_btn = st.button("▶️ Execute", use_container_width=True, key="exec_btn")
        
        if execute_btn and request:
            with st.spinner("⏳ Executing workflow..."):
                try:
                    # Initialize state
                    initial_state = {
                        "request": request,
                        "workflow_id": f"wf_{datetime.now().timestamp()}",
                        "current_step": "planner",
                        "plan": "",
                        "dependencies": [],
                        "risks": [],
                        "approved": False,
                        "action_result": "",
                        "evaluation_result": "",
                        "human_approval_required": False,
                        "human_feedback": None,
                        "approval_status": "pending",
                        "checkpoints": [],
                        "execution_history": [],
                        "workflow_config": None,
                        "created_at": datetime.now().isoformat(),
                        "updated_at": datetime.now().isoformat(),
                        "error": None,
                    }
                    
                    # Execute workflow
                    result = dynamic_workflow.invoke(initial_state)
                    
                    # Handle None result
                    if result is None:
                        st.error("❌ Workflow returned None result")
                        return
                    
                    # Check if paused for approval
                    if result.get("_workflow_paused") and result.get("_pause_for_approval"):
                        st.warning("⏸️ **Workflow paused** - Awaiting human approval")
                        st.info("👉 Please go to the **Approval Queue** tab to review and approve this workflow step.")
                    else:
                        # Display results
                        st.success("✅ Workflow Execution Complete!")
                    
                    # Store result
                    st.session_state.last_workflow = result
                    st.session_state.last_workflow_id = result.get("workflow_id")
                    
                    # Results columns
                    res_col1, res_col2 = st.columns(2)
                    
                    with res_col1:
                        st.subheader("📋 Plan")
                        st.write(result.get("plan", "No plan generated"))
                        
                        st.subheader("📚 Dependencies")
                        deps = result.get("dependencies", [])
                        if deps:
                            for dep in deps:
                                st.write(f"• {dep}")
                        else:
                            st.info("No dependencies found")
                    
                    with res_col2:
                        st.subheader("⚠️ Risks Identified")
                        risks = result.get("risks", [])
                        if risks:
                            for risk in risks:
                                st.warning(f"🔴 {risk}")
                        else:
                            st.info("✅ No risks identified")
                    
                    st.divider()
                    act_col1, act_col2 = st.columns(2)
                    
                    with act_col1:
                        st.subheader("⚡ Action Result")
                        st.write(result.get("action_result", "No action executed"))
                    
                    with act_col2:
                        st.subheader("📊 Evaluation")
                        st.write(result.get("evaluation_result", "No evaluation available"))
                    
                    # Store in session for checkpoint view
                    st.session_state.last_workflow = result
                    st.session_state.last_workflow_id = result.get("workflow_id")
                    
                except Exception as e:
                    import traceback
                    st.error(f"❌ Error during execution: {str(e)}")
                    st.error(f"Details: {traceback.format_exc()}")
    
    # ============ TAB 2: Checkpoints ============
    with tab2:
        st.subheader("🔖 Execution Checkpoints")
        
        if "last_workflow_id" in st.session_state:
            workflow_id = st.session_state.last_workflow_id
            checkpoints = checkpoint_manager.list_workflow_checkpoints(workflow_id)
            
            if checkpoints:
                for i, cp in enumerate(checkpoints, 1):
                    with st.expander(f"Checkpoint {i}: {cp['node_name']} - {cp['timestamp']}", expanded=False):
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric("Status", cp['status'])
                        with col2:
                            st.metric("Node", cp['node_name'])
                        with col3:
                            st.metric("Approval Required", "Yes" if cp['human_approval_required'] else "No")
                        
                        st.write("**Checkpoint Data:**")
                        st.json(cp['data'])
            else:
                st.info("No checkpoints available. Run a workflow first.")
        else:
            st.info("Execute a workflow first to view checkpoints.")
    
    # ============ TAB 3: Approval Queue ============
    with tab3:
        st.subheader("✅ Human Approval Queue")
        
        if "last_workflow" in st.session_state:
            workflow = st.session_state.last_workflow
            
            # Check if workflow is paused for approval
            is_paused = workflow.get("_workflow_paused") or workflow.get("human_approval_required")
            approval_status = workflow.get("approval_status", "pending")
            
            if (is_paused and workflow.get("_pause_for_approval")) or approval_status in {"approved", "rejected"}:
                if approval_status == "pending":
                    st.warning(f"⏳ **Awaiting approval for: {workflow.get('current_step')}**")
                
                # Show what needs approval
                st.divider()
                st.write("### 📋 For Review:")
                rev_col1, rev_col2 = st.columns(2)
                
                with rev_col1:
                    st.write("**Current Step:**", workflow.get("current_step", "N/A"))
                    st.write("**Plan:**")
                    st.write(workflow.get("plan", "N/A"))
                
                with rev_col2:
                    st.write("**Identified Risks:**")
                    risks = workflow.get("risks", [])
                    if risks:
                        for risk in risks:
                            st.warning(f"🔴 {risk}")
                    else:
                        st.info("✅ No risks identified")
                
                st.divider()
                
                # Only show buttons if not already decided
                if approval_status == "pending":
                    feedback_text = st.text_input("Feedback for rejection (optional)")
                    approval_col1, approval_col2 = st.columns(2)
                    
                    with approval_col1:
                        if st.button("✅ Approve", use_container_width=True, key="approve_btn"):
                            # Update workflow state with approval
                            workflow["approval_status"] = "approved"
                            workflow["_pause_for_approval"] = False
                            workflow["_workflow_paused"] = False
                            workflow["human_feedback"] = "Approved by user"
                            
                            # Resume workflow execution from current state
                            with st.spinner("⏳ Resuming workflow..."):
                                try:
                                    # Continue execution from the approval point
                                    resumed_result = dynamic_workflow.invoke(workflow)
                                    
                                    if resumed_result is None:
                                        st.error("❌ Workflow returned None result on resume")
                                    else:
                                        # Update session state with resumed result
                                        st.session_state.last_workflow = resumed_result
                                        st.success("✅ Workflow approved and completed!")
                                        
                                        # Show execution history
                                        st.subheader("📜 Execution History")
                                        history = resumed_result.get("execution_history", [])
                                        if history:
                                            for entry in history:
                                                st.info(f"✓ {entry['step']}: {entry['status']}")
                                        
                                        # Show final results
                                        st.success("✅ Workflow Completed Successfully!")
                                        st.divider()
                                        
                                        st.subheader("📊 Final Results")
                                        res_col1, res_col2 = st.columns(2)
                                        
                                        with res_col1:
                                            st.write("**Plan:**")
                                            st.write(resumed_result.get("plan", "N/A"))
                                            st.write("**Dependencies:**")
                                            deps = resumed_result.get("dependencies", [])
                                            if deps:
                                                for dep in deps:
                                                    st.write(f"• {dep}")
                                            else:
                                                st.write("None")
                                        
                                        with res_col2:
                                            st.write("**Risks:**")
                                            risks = resumed_result.get("risks", [])
                                            if risks:
                                                for risk in risks:
                                                    st.warning(f"🔴 {risk}")
                                            else:
                                                st.info("✅ No risks identified")
                                        
                                        st.divider()
                                        action_col1, action_col2 = st.columns(2)
                                        
                                        with action_col1:
                                            st.write("**Action Result:**")
                                            st.write(resumed_result.get("action_result", "N/A"))
                                        
                                        with action_col2:
                                            st.write("**Evaluation:**")
                                            st.write(resumed_result.get("evaluation_result", "N/A"))
                                        
                                        st.rerun()
                                except Exception as e:
                                    import traceback
                                    st.error(f"❌ Error resuming workflow: {str(e)}")
                                    st.error(f"Details: {traceback.format_exc()}")
                    
                    with approval_col2:
                        if st.button("❌ Reject", use_container_width=True, key="reject_btn"):
                            workflow = mark_workflow_rejected(
                                workflow,
                                feedback_text or "Rejected by user",
                            )
                            st.session_state.last_workflow = workflow
                            st.rerun()
                
                # Show status if already decided
                if approval_status == "approved":
                    st.success("✅ Workflow approved and executed")
                    
                elif approval_status == "rejected":
                    st.error("❌ Workflow rejected")
                    st.write(f"**Feedback:** {workflow.get('human_feedback', 'N/A')}")
                    st.divider()
                    
                    # Show execution history for rejected workflow
                    st.subheader("📜 Execution Steps")
                    history = workflow.get("execution_history", [])
                    if history:
                        for i, entry in enumerate(history, 1):
                            st.info(f"{i}. **{entry['step']}** - {entry['status'].upper()}")
                    else:
                        st.write("No execution history available")
                    
                    st.divider()
                    
                    # Show workflow state at rejection point
                    st.subheader("📊 Workflow State at Rejection")
                    state_col1, state_col2 = st.columns(2)
                    
                    with state_col1:
                        st.write("**Plan:**")
                        st.write(workflow.get("plan", "N/A"))
                        st.write("**Dependencies:**")
                        deps = workflow.get("dependencies", [])
                        if deps:
                            for dep in deps:
                                st.write(f"• {dep}")
                        else:
                            st.write("None")
                    
                    with state_col2:
                        st.write("**Risks:**")
                        risks = workflow.get("risks", [])
                        if risks:
                            for risk in risks:
                                st.warning(f"🔴 {risk}")
                        else:
                            st.write("None identified")
                
            else:
                st.success("✅ No pending approvals")
