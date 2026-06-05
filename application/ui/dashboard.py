# ui/dashboard.py

import time

import streamlit as st
import streamlit.components.v1 as components
from datetime import datetime
from graph.workflow import graph, dynamic_workflow, WorkflowState
from memory.checkpoint_manager import CheckpointManager
from utils.llm_studio import LmStudioError, list_lm_studio_models, chat_lm_studio_stream

checkpoint_manager = CheckpointManager()


def _copy_meta_html(content: str, model: str, time_str: str, token_str: str) -> str:
    js_safe = content.replace("\\", "\\\\").replace("'", "\\'").replace("\n", "\\n").replace("\r", "\\r")
    display_model = model.split("/")[-1][:20] if model else ""
    return f"""<div style="display:flex;align-items:center;gap:0.5rem;font-family:'Inter',-apple-system,BlinkMacSystemFont,sans-serif;padding:0.125rem 0 0.25rem;">
<button id="cpy" onclick="copyMsg()" style="display:inline-flex;align-items:center;gap:0.2rem;cursor:pointer;font-size:0.65rem;color:#b0b0b0;border:none;border-radius:4px;padding:0.15rem 0.4rem;background:transparent;user-select:none;transition:all 0.2s ease;line-height:1;"
onmouseover="this.style.color='#666';this.style.background='#f0f0f0'"
onmouseout="this.style.color='#b0b0b0';this.style.background='transparent'">📋</button>
<span style="font-size:0.65rem;color:#bbb;display:flex;align-items:center;gap:0.35rem;flex-wrap:wrap;">
<span style="color:#60a5fa;">{display_model}</span>
<span style="color:#d0d0d0;">·</span>
<span style="color:#fbbf24;">{time_str}</span>
<span style="color:#d0d0d0;">·</span>
<span style="color:#94a3b8;">{token_str}</span>
</span>
</div>
<script>
function copyMsg(){{
var t='{js_safe}';
var b=document.getElementById('cpy');
if(navigator.clipboard){{
navigator.clipboard.writeText(t).then(function(){{
b.innerHTML='✓';b.style.color='#22c55e';
setTimeout(function(){{b.innerHTML='📋';b.style.color='#b0b0b0';}},1800);
}}).catch(function(){{b.style.color='#ef4444';}});
}}else{{b.style.color='#ef4444';}}
}}
</script>"""


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

from utils.loggers import logger

def _persist_chat(redis_client, username):
    if not redis_client or not username:
        logger.warning("dashboard | ❌ Chat NOT persisted — redis_client=%s, user='%s'", bool(redis_client), username)
        return
    if not redis_client.enabled:
        logger.warning("dashboard | ❌ Chat NOT persisted — Redis not connected. Start Redis with: redis-server")
        return
    logger.info("dashboard | ✅ Persisting %d messages for '%s' to Redis", len(st.session_state.chat_history), username)
    redis_client.save_chat_history(username, st.session_state.chat_history)

def render_dashboard(auth=None, redis_client=None):

    user = st.session_state.get("user", {})
    username = user.get("username", "")
    role = user.get("role", "")
    can_run = auth.has_permission(user, "run_workflow") if auth else True
    can_create = auth.has_permission(user, "create_workflow") if auth else True
    can_approve = auth.has_permission(user, "approve_workflow") if auth else True
    can_chat = auth.has_permission(user, "chat") if auth else True
    can_manage = auth.has_permission(user, "manage_users") if auth else True

    st.title("⚡ Agentic Workflow Studio")
    
    tab_labels = []
    tab_labels.append("▶️ Execute Workflow" if can_run else "▶️ Execute Workflow (🔒)")
    tab_labels.append("📦 Checkpoints" if can_create else "📦 Checkpoints (🔒)")
    tab_labels.append("✅ Approval Queue" if can_approve else "✅ Approval Queue (🔒)")
    tab_labels.append("💬 LLM Chat" if can_chat else "💬 LLM Chat (🔒)")

    if can_manage:
        tab_labels.append("👥 User Management")
        tab1, tab2, tab3, tab4, tab5 = st.tabs(tab_labels)
    else:
        tab1, tab2, tab3, tab4 = st.tabs(tab_labels)
        tab5 = None

    # ============ TAB 1: Execute Workflow ============
    with tab1:
        if not can_run:
            st.warning("🔒 You do not have permission to execute workflows. Contact an admin.")
            st.stop()
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

        with st.expander("LLM Studio Settings", expanded=False):
            llm_enabled = st.checkbox("Use LM Studio for agent reasoning", value=False)
            llm_col1, llm_col2, llm_col3 = st.columns([2, 1, 1])
            with llm_col1:
                llm_url = st.text_input(
                    "LM Studio Chat Completions URL",
                    value="http://localhost:1234/v1/chat/completions",
                    disabled=not llm_enabled,
                )
            with llm_col2:
                llm_timeout = st.number_input(
                    "Timeout seconds",
                    min_value=5,
                    max_value=300,
                    value=60,
                    disabled=not llm_enabled,
                )
            with llm_col3:
                llm_max_tokens = st.number_input(
                    "Max tokens",
                    min_value=120,
                    max_value=1200,
                    value=450,
                    disabled=not llm_enabled,
                )

            llm_model = "local-model"
            lm_studio_ready = not llm_enabled
            if llm_enabled:
                try:
                    available_models = list_lm_studio_models(llm_url, timeout=5)
                    llm_model = st.selectbox("Loaded local model", available_models)
                    st.success(f"LM Studio connected. {len(available_models)} model(s) available.")
                    lm_studio_ready = True
                except LmStudioError as exc:
                    st.error(str(exc))
                    st.info("Start LM Studio, load a model, and enable the OpenAI-compatible local server.")
                    lm_studio_ready = False
        
        if execute_btn and request:
            if llm_enabled and not lm_studio_ready:
                st.error("LM Studio mode is enabled, but no live local model is available.")
                return

            with st.spinner("⏳ Executing workflow..."):
                try:
                    # Initialize state
                    initial_state = {
                        "request": request,
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
                        "approval_status": "pending",
                        "checkpoints": [],
                        "execution_history": [],
                        "workflow_config": None,
                        "llm_config": {
                            "enabled": llm_enabled,
                            "base_url": llm_url,
                            "model": llm_model,
                            "timeout": llm_timeout,
                            "max_tokens": llm_max_tokens,
                            "require_llm": False,
                        },
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
                    if redis_client and username:
                        redis_client.save_last_workflow(username, result)
                        if result.get("workflow_id"):
                            redis_client.save_last_workflow_id(username, result["workflow_id"])
                    
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
                        st.subheader("⚠️ Risk Check")
                        if result.get("risk_present"):
                            st.warning("🔴 Risks identified — approval may be required")
                        else:
                            st.info("✅ No risks detected")
                    
                    st.divider()
                    act_col1, act_col2 = st.columns(2)
                    
                    with act_col1:
                        st.subheader("⚡ Action Result")
                        st.write(result.get("action_result", "No action executed"))
                    
                    with act_col2:
                        st.subheader("📊 Evaluation")
                        st.write(result.get("evaluation_result", "No evaluation available"))

                    st.divider()
                    st.subheader("🧠 Agent Reasoning Source")
                    llm_cols = st.columns(6)
                    agent_flags = [
                        ("Plan", "planner_llm_used"),
                        ("Deps", "dependency_llm_used"),
                        ("Risk", "risk_llm_used"),
                        ("Gov", "governance_llm_used"),
                        ("Action", "action_llm_used"),
                        ("Eval", "evaluator_llm_used"),
                    ]
                    for col, (label, key) in zip(llm_cols, agent_flags):
                        col.metric(label, "LLM" if result.get(key) else "Fallback")
                    
                    # Store in session for checkpoint view
                    st.session_state.last_workflow = result
                    st.session_state.last_workflow_id = result.get("workflow_id")
                    if redis_client and username:
                        redis_client.save_last_workflow(username, result)
                        if result.get("workflow_id"):
                            redis_client.save_last_workflow_id(username, result["workflow_id"])
                    
                except Exception as e:
                    import traceback
                    st.error(f"❌ Error during execution: {str(e)}")
                    st.error(f"Details: {traceback.format_exc()}")
    
    # ============ TAB 2: Checkpoints ============
    with tab2:
        if not can_create:
            st.warning("🔒 You do not have permission to view checkpoints. Contact an admin.")
            st.stop()
        st.subheader("🔖 Execution Checkpoints")
        
        if st.session_state.get("last_workflow_id"):
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
        if not can_approve:
            st.warning("🔒 You do not have permission to approve workflows. Contact an admin.")
            st.stop()
        st.subheader("✅ Human Approval Queue")
        
        if st.session_state.get("last_workflow"):
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
                    st.write("**Risk Check:**")
                    if workflow.get("risk_present"):
                        st.warning("🔴 Risks identified")
                    else:
                        st.info("✅ No risks detected")
                
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
                                        if redis_client and username:
                                            redis_client.save_last_workflow(username, resumed_result)
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
                                            st.write("**Risk Check:**")
                                            if resumed_result.get("risk_present"):
                                                st.warning("🔴 Risks identified")
                                            else:
                                                st.info("✅ No risks detected")
                                        
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
                            if redis_client and username:
                                redis_client.save_last_workflow(username, workflow)
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
                        st.write("**Risk Check:**")
                        if workflow.get("risk_present"):
                            st.warning("🔴 Risks identified")
                        else:
                            st.write("None detected")
                
            else:
                st.success("✅ No pending approvals")

    # ============ TAB 4: LLM Chat ============
    with tab4:
        if not can_chat:
            st.warning("🔒 You do not have permission to use the chat. Contact an admin.")
            st.stop()
        st.markdown(
            """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&display=swap');
        .chat-container {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
        }

        /* ===== Unified Chat Card (messages + input = seamless) ===== */
        .chat-card-wrap {
            max-width: 720px;
            margin-left: auto;
            margin-right: auto;
            width: calc(100% - 2rem);
        }

        /* Messages container — top of the card */
        .chat-marker + .element-container > div[data-testid="stVerticalBlock"] {
            min-height: 180px !important;
            padding-top: 0.5rem !important;
            width: calc(100% - 2rem) !important;
            max-width: 720px !important;
            margin-left: auto !important;
            margin-right: auto !important;
            background: #ffffff !important;
            scroll-behavior: smooth !important;
            overflow-y: auto !important;
            overflow-x: hidden !important;
            border: 1px solid rgba(229,231,235,0.5) !important;
            border-bottom: none !important;
            border-radius: 1rem 1rem 0 0 !important;
        }
        .chat-marker + .element-container > div[data-testid="stVerticalBlock"] > div:first-child > div {
            padding: 0.25rem 0.5rem !important;
        }
        /* Custom thin scrollbar */
        .chat-marker + .element-container > div[data-testid="stVerticalBlock"]::-webkit-scrollbar {
            width: 4px;
        }
        .chat-marker + .element-container > div[data-testid="stVerticalBlock"]::-webkit-scrollbar-track {
            background: transparent;
        }
        .chat-marker + .element-container > div[data-testid="stVerticalBlock"]::-webkit-scrollbar-thumb {
            background: rgba(0,0,0,0.08);
            border-radius: 2px;
        }
        .chat-marker + .element-container > div[data-testid="stVerticalBlock"]::-webkit-scrollbar-thumb:hover {
            background: rgba(0,0,0,0.12);
        }

        /* Input — bottom of the card (same width, attaches seamlessly) */
        div[data-testid="stChatInput"] {
            position: fixed !important;
            bottom: 0 !important;
            left: 50% !important;
            transform: translateX(-50%) !important;
            width: calc(100% - 2rem) !important;
            max-width: 720px !important;
            background: #ffffff !important;
            backdrop-filter: none !important;
            z-index: 1000 !important;
            padding: 0.75rem 1rem !important;
            padding-bottom: calc(0.75rem + env(safe-area-inset-bottom, 20px)) !important;
            border: 1px solid rgba(229,231,235,0.5) !important;
            border-top: none !important;
            border-radius: 0 0 1rem 1rem !important;
            box-shadow: 0 4px 24px rgba(0,0,0,0.05), 0 1px 4px rgba(0,0,0,0.03) !important;
            transition: box-shadow 0.2s ease !important;
        }
        div[data-testid="stChatInput"]:focus-within {
            box-shadow: 0 4px 32px rgba(0,0,0,0.08), 0 1px 4px rgba(0,0,0,0.05) !important;
        }
        div[data-testid="stChatInput"] textarea {
            font-size: 0.9375rem !important;
            line-height: 1.5 !important;
            border-radius: 0.75rem !important;
            background: #f5f6f7 !important;
            border: 1px solid rgba(0,0,0,0.04) !important;
            transition: background 0.2s ease, border-color 0.2s ease !important;
        }
        div[data-testid="stChatInput"] textarea:focus {
            background: #ffffff !important;
            border-color: #667eea !important;
        }
        div[data-testid="stChatInput"] textarea::placeholder {
            color: #b0b0b0 !important;
            font-weight: 400 !important;
        }
        .main > .block-container {
            padding-bottom: 6.5rem !important;
        }

        /* ===== Chat Header (floating label above card) ===== */
        .chat-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            max-width: 720px;
            margin: 0 auto 0.25rem;
            padding: 0 0.5rem;
            width: calc(100% - 2rem);
        }

        /* ===== Chat Message Bubbles ===== */
        div[data-testid="stChatMessage"] {
            display: flex !important;
            align-items: flex-end !important;
            gap: 8px !important;
            padding: 0 !important;
            margin-bottom: 6px !important;
            animation: fadeSlideUp 0.25s ease-out;
        }

        /* Avatars */
        div[data-testid^="chatAvatarIcon"] {
            flex-shrink: 0 !important;
            width: 30px !important;
            height: 30px !important;
            font-size: 15px !important;
            display: flex !important;
            align-items: center !important;
            justify-content: center !important;
        }
        div[data-testid^="chatAvatarIcon"] img {
            width: 30px !important;
            height: 30px !important;
            border-radius: 50% !important;
            object-fit: cover !important;
        }

        /* User bubble (indigo gradient, right) */
        div[data-testid="chatAvatarIcon-user"] + div[data-testid="stChatMessageContent"] {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
            color: #fff !important;
            border-radius: 18px 18px 4px 18px !important;
            padding: 10px 16px !important;
            max-width: 75% !important;
            box-shadow: 0 2px 8px rgba(102,126,234,0.2) !important;
        }
        div[data-testid="chatAvatarIcon-user"] + div[data-testid="stChatMessageContent"] * {
            color: #fff !important;
        }

        /* Assistant bubble (light gray, left) */
        div[data-testid="chatAvatarIcon-assistant"] + div[data-testid="stChatMessageContent"] {
            background: #f0f0f0 !important;
            color: #1a1a2e !important;
            border-radius: 18px 18px 18px 4px !important;
            padding: 10px 16px !important;
            max-width: 75% !important;
            box-shadow: 0 1px 3px rgba(0,0,0,0.04) !important;
        }
        div[data-testid="chatAvatarIcon-assistant"] + div[data-testid="stChatMessageContent"] * {
            color: #1a1a2e !important;
        }

        /* Content text */
        div[data-testid="stChatMessageContent"] p {
            font-size: 0.9375rem !important;
            line-height: 1.6 !important;
            margin: 0 !important;
        }
        div[data-testid="stChatMessageContent"] p + p {
            margin-top: 0.5rem !important;
        }

        /* ===== Timestamp below bubbles ===== */
        .msg-ts {
            font-size: 0.6rem;
            color: #bbb;
            padding: 0 4px;
            user-select: none;
            letter-spacing: 0.01em;
        }
        .msg-ts-row {
            display: flex;
            align-items: center;
            justify-content: flex-end;
            gap: 0.5rem;
            margin-top: 2px;
        }
        .msg-ts-row.assistant {
            justify-content: flex-start;
        }

        /* ===== LLM Status Widget (Thinking / Generating / Done) ===== */
        div[data-testid="stStatusWidget"] {
            border: none !important;
            background: transparent !important;
            padding: 0 !important;
            margin: 0 !important;
            border-radius: 0 !important;
            box-shadow: none !important;
        }
        div[data-testid="stStatusWidget"] div[data-testid="stMarkdownContainer"] p {
            font-size: 0.82rem !important;
            font-weight: 500 !important;
            margin: 0 !important;
            color: #999 !important;
        }
        div[data-testid="stStatusWidget"] svg {
            width: 16px !important;
            height: 16px !important;
            color: #999 !important;
        }
        div[data-testid="stStatusWidget"][state="complete"] div[data-testid="stMarkdownContainer"] p {
            color: #22c55e !important;
        }
        div[data-testid="stStatusWidget"][state="complete"] svg {
            color: #22c55e !important;
        }
        div[data-testid="stStatusWidget"][state="error"] div[data-testid="stMarkdownContainer"] p {
            color: #ef4444 !important;
        }
        div[data-testid="stStatusWidget"][state="error"] svg {
            color: #ef4444 !important;
        }

        /* ===== Stream Cursor ===== */
        .stream-cursor {
            display: inline-block;
            width: 2px;
            height: 1em;
            background: #3b82f6;
            margin-left: 1px;
            animation: blink 0.8s step-end infinite;
            vertical-align: text-bottom;
        }
        @keyframes blink {
            50% { opacity: 0; }
        }

        /* ===== Animations ===== */
        @keyframes fadeSlideUp {
            from { opacity: 0; transform: translateY(8px); }
            to { opacity: 1; transform: translateY(0); }
        }

        /* ===== Responsive ===== */
        @media (max-width: 768px) {
            .chat-header {
                width: calc(100% - 0.5rem);
                padding: 0.5rem 0.75rem;
            }
            div[data-testid="stChatInput"] {
                width: calc(100% - 0.5rem) !important;
                padding: 0.5rem 0.75rem !important;
                padding-bottom: calc(0.5rem + env(safe-area-inset-bottom, 16px)) !important;
                border-radius: 0 0 0.75rem 0.75rem !important;
            }
            .chat-marker + .element-container > div[data-testid="stVerticalBlock"] {
                min-height: 150px !important;
                width: calc(100% - 0.5rem) !important;
                border-radius: 0.75rem 0.75rem 0 0 !important;
            }
            .main > .block-container {
                padding-bottom: 5rem !important;
            }
            div[data-testid="chatAvatarIcon-user"] + div[data-testid="stChatMessageContent"],
            div[data-testid="chatAvatarIcon-assistant"] + div[data-testid="stChatMessageContent"] {
                max-width: 88% !important;
            }
            div[data-testid="stChatMessage"] {
                margin-bottom: 4px !important;
            }
        }

        /* ===== Dark Mode ===== */
        @media (prefers-color-scheme: dark) {
            .chat-header .chat-title {
                color: #e4e4e7 !important;
            }
            div[data-testid="stChatInput"] {
                background: #1e1e20 !important;
                border-color: rgba(60,60,65,0.5) !important;
            }
            div[data-testid="stChatInput"] textarea {
                background: #2a2a2d !important;
                color: #e4e4e7 !important;
                border-color: rgba(60,60,65,0.3) !important;
            }
            div[data-testid="stChatInput"] textarea:focus {
                background: #333336 !important;
                border-color: #5b6abf !important;
            }
            div[data-testid="stChatInput"] textarea::placeholder {
                color: #666 !important;
            }
            .chat-marker + .element-container > div[data-testid="stVerticalBlock"] {
                background: #1a1a1c !important;
                border-color: rgba(60,60,65,0.5) !important;
            }
            div[data-testid="chatAvatarIcon-assistant"] + div[data-testid="stChatMessageContent"] {
                background: #2a2a2d !important;
                color: #e4e4e7 !important;
            }
            div[data-testid="chatAvatarIcon-assistant"] + div[data-testid="stChatMessageContent"] * {
                color: #e4e4e7 !important;
            }
            div[data-testid="chatAvatarIcon-user"] + div[data-testid="stChatMessageContent"] {
                background: linear-gradient(135deg, #5b6abf 0%, #6a3f91 100%) !important;
            }
            .msg-ts { color: #555 !important; }
        }
        </style>
        """,
            unsafe_allow_html=True,
        )

        # If user changed since last load, discard stale session data and reload from Redis
        loaded_for = st.session_state.get("_loaded_for_user")
        if loaded_for != username:
            for key in ["chat_history", "last_workflow", "last_workflow_id"]:
                st.session_state.pop(key, None)
            logger.info("dashboard | User switched (%s -> %s), reloading from Redis", loaded_for, username)
            st.session_state._loaded_for_user = username

        if "chat_history" not in st.session_state:
            loaded = redis_client.load_chat_history(username) if redis_client else []
            st.session_state.chat_history = loaded
            user_msg_count = sum(1 for m in loaded if m.get("role") == "user")
            asst_msg_count = sum(1 for m in loaded if m.get("role") == "assistant")
            logger.info("dashboard | 📥 Loaded chat_history for user='%s': %d messages (%d user, %d assistant) from Redis key 'user:%s:chat_history'",
                        username, len(loaded), user_msg_count, asst_msg_count, username)

        if "last_workflow" not in st.session_state:
            loaded = redis_client.load_last_workflow(username) if redis_client else None
            st.session_state.last_workflow = loaded if loaded is not None else {}
            logger.info("dashboard | 📥 Loaded last_workflow for user='%s': %s", username, "found" if loaded else "none")

        if "last_workflow_id" not in st.session_state:
            loaded = redis_client.load_last_workflow_id(username) if redis_client else None
            st.session_state.last_workflow_id = loaded or ""
            logger.info("dashboard | 📥 Loaded last_workflow_id for user='%s': %s", username, loaded or "none")

        st.markdown('<div class="chat-container">', unsafe_allow_html=True)

        if "chat_lm_connected" not in st.session_state:
            st.session_state.chat_lm_connected = False
            st.session_state.chat_lm_models = []
            st.session_state.chat_lm_model = "local-model"
        if "chat_settings_open" not in st.session_state:
            st.session_state.chat_settings_open = not st.session_state.chat_lm_connected

        with st.expander("⚙️ Settings", expanded=st.session_state.chat_settings_open):
            st.caption("Configure your local LLM connection")
            chat_url = st.text_input(
                "API URL",
                value="http://localhost:1234/v1/chat/completions",
                key="chat_llm_url",
                help="LM Studio OpenAI-compatible chat completions endpoint",
            )
            chat_col1, chat_col2 = st.columns(2)
            with chat_col1:
                chat_timeout = st.number_input(
                    "Timeout (s)", min_value=5, max_value=120, value=60, key="chat_timeout"
                )
            with chat_col2:
                chat_sys_height = st.number_input(
                    "System prompt height (px)", min_value=60, max_value=300, value=80, key="chat_sys_height"
                )
            chat_system = st.text_area(
                "System Prompt",
                value="You are a helpful AI assistant. Keep responses concise and clear.",
                key="chat_system_prompt",
                height=chat_sys_height,
            )

            st.divider()
            ccol1, ccol2 = st.columns(2)
            with ccol1:
                if st.button("🔌 Connect", use_container_width=True, key="chat_connect_btn"):
                    with st.spinner("Connecting..."):
                        try:
                            models = list_lm_studio_models(chat_url, timeout=5)
                            st.session_state.chat_lm_models = models
                            st.session_state.chat_lm_model = models[0] if models else "local-model"
                            st.session_state.chat_lm_connected = True
                            st.session_state.chat_settings_open = False
                            st.rerun()
                        except LmStudioError as exc:
                            st.session_state.chat_lm_connected = False
                            st.error(str(exc))

            with ccol2:
                if st.button("🗑️ Clear", use_container_width=True, key="clear_chat_btn"):
                    st.session_state.chat_history = []
                    if redis_client and username:
                        redis_client.save_chat_history(username, [])
                    st.rerun()

            if st.session_state.chat_lm_connected:
                current_idx = 0
                if st.session_state.chat_lm_model in st.session_state.chat_lm_models:
                    current_idx = st.session_state.chat_lm_models.index(st.session_state.chat_lm_model)
                st.selectbox("Model", st.session_state.chat_lm_models, index=current_idx, key="chat_model_select", label_visibility="collapsed")
                st.session_state.chat_lm_model = st.session_state.chat_model_select

        chat_connected = st.session_state.chat_lm_connected

        chat_model_display = st.session_state.chat_lm_model.split("/")[-1][:24] if chat_connected else "offline"
        chat_status_color = "#22c55e" if chat_connected else "#ef4444"
        redis_ok = redis_client.enabled if redis_client else False
        redis_color = "#22c55e" if redis_ok else "#ef4444"
        redis_label = "Redis" if redis_ok else "No Redis"
        st.markdown(
            f"""<div class="chat-header">
<div style="display:flex;align-items:center;gap:0.5rem;">
<span class="chat-title" style="font-size:1rem;font-weight:600;color:#1a1a2e;">💬 Chat</span>
<span style="font-size:0.6rem;color:#999;background:#f5f5f5;padding:0.1rem 0.45rem;border-radius:8px;">local</span>
<span style="font-size:0.55rem;color:{redis_color};background:{redis_color}18;padding:0.1rem 0.4rem;border-radius:6px;">{redis_label}</span>
</div>
<div style="display:flex;align-items:center;gap:0.35rem;">
<span style="width:6px;height:6px;border-radius:50%;background:{chat_status_color};display:inline-block;"></span>
<span style="font-size:0.65rem;color:#999;">{chat_model_display}</span>
</div>
</div>""",
            unsafe_allow_html=True,
        )

        if not chat_connected:
            st.info("💡 Open **Settings** above and connect to LM Studio to start chatting.")

        # Marker to identify the messages container for CSS targeting
        st.markdown(
            '<div class="chat-marker" style="display:none"></div>',
            unsafe_allow_html=True,
        )

        # Messages window: independently scrollable container
        msg_window = st.container(height=400)

        with msg_window:
            if not st.session_state.chat_history:
                st.markdown(
                    '<div style="text-align:center;padding:2.5rem 1rem;border-radius:0.75rem;">'
                    '<div style="font-size:2.2rem;margin-bottom:0.6rem;">💬</div>'
                    '<div style="font-size:0.9rem;color:#bbb;font-weight:500;">Start a conversation</div>'
                    '<div style="font-size:0.75rem;color:#ccc;margin-top:0.25rem;">Type a message below to begin</div>'
                    '</div>',
                    unsafe_allow_html=True,
                )

            for i, message in enumerate(st.session_state.chat_history):
                role = message["role"]
                avatar_icon = "👤" if role == "user" else "🤖"
                with st.chat_message(role, avatar=avatar_icon):
                    st.markdown(message["content"])

                    # Format timestamp
                    ts_raw = message.get("timestamp", "")
                    ts_display = ""
                    if ts_raw:
                        try:
                            dt = datetime.fromisoformat(ts_raw)
                            ts_display = dt.strftime("%I:%M %p").lstrip("0")
                            if dt.date() != datetime.now().date():
                                ts_display = dt.strftime("%b %d, ") + ts_display
                        except Exception:
                            pass

                    if role == "assistant":
                        model = message.get("model", "")
                        resp_time = message.get("response_time", "")
                        tokens = message.get("tokens", "")

                        st.markdown(
                            f'<div class="msg-ts-row assistant"><span class="msg-ts">{ts_display}</span></div>',
                            unsafe_allow_html=True,
                        )

                        copy_html = _copy_meta_html(
                            content=message["content"],
                            model=model,
                            time_str=resp_time,
                            token_str=tokens,
                        )
                        components.html(copy_html, height=28)
                    else:
                        st.markdown(
                            f'<div class="msg-ts-row"><span class="msg-ts">{ts_display}</span></div>',
                            unsafe_allow_html=True,
                        )

        chat_placeholder = "Ask the local LLM..." if chat_connected else "Connect to LM Studio to chat"
        if prompt := st.chat_input(chat_placeholder, disabled=not chat_connected):
            st.session_state.chat_history.append({
                "role": "user",
                "content": prompt,
                "timestamp": datetime.now().isoformat(),
            })
            _persist_chat(redis_client, username)

            with msg_window:
                with st.chat_message("user", avatar="👤"):
                    st.markdown(prompt)
                    st.markdown(
                        f'<div class="msg-ts-row"><span class="msg-ts">{datetime.now().strftime("%I:%M %p").lstrip("0")}</span></div>',
                        unsafe_allow_html=True,
                    )

                with st.chat_message("assistant", avatar="🤖"):
                    stream_start = datetime.now()
                    llm_status = st.status("🤔 **Thinking**", state="running")
                    stream_placeholder = st.empty()
                    full_response = ""

                    messages = [
                        {"role": "system", "content": chat_system},
                        *[{"role": m["role"], "content": m["content"]} for m in st.session_state.chat_history],
                    ]

                    total_chars = sum(len(m["content"]) for m in messages)
                    logger.info(
                        "dashboard | 🧠 Sending %d messages (%d system + %d conversation) as LLM context to model='%s' — "
                        "total %d chars, ~%d est. tokens (4:1 ratio, system=%d chars, conversation=%d chars, last_msg_role=%s)",
                        len(messages),
                        1,
                        len(st.session_state.chat_history),
                        st.session_state.chat_lm_model,
                        total_chars,
                        total_chars // 4,
                        len(chat_system),
                        total_chars - len(chat_system),
                        st.session_state.chat_history[-1]["role"] if st.session_state.chat_history else "none",
                    )

                    try:
                        usage_info = {}
                        start_time = time.time()
                        stream = chat_lm_studio_stream(
                            base_url=chat_url,
                            model=st.session_state.chat_lm_model,
                            messages=messages,
                            timeout=chat_timeout,
                            usage_info=usage_info,
                        )

                        llm_status.update(label="✍️ **Generating...**", state="running")

                        for chunk in stream:
                            full_response += chunk
                            stream_placeholder.markdown(full_response + '<span class="stream-cursor"></span>', unsafe_allow_html=True)

                        llm_status.update(label="✅ **Done**", state="complete")

                        elapsed = time.time() - start_time
                        if elapsed < 1:
                            time_str = f"{elapsed*1000:.0f}ms"
                        elif elapsed < 60:
                            time_str = f"{elapsed:.1f}s"
                        else:
                            time_str = f"{elapsed//60:.0f}m {elapsed%60:.0f}s"

                        total_prompt = usage_info.get("prompt_tokens", 0)
                        total_completion = usage_info.get("completion_tokens", 0) or max(0, len(full_response) // 4)
                        total_prompt = total_prompt or max(0, sum(len(m["content"]) for m in messages) // 4)
                        token_str = f"{total_prompt}→{total_completion} tok"

                        ts_display = stream_start.strftime("%I:%M %p").lstrip("0")
                        st.markdown(
                            f'<div class="msg-ts-row assistant"><span class="msg-ts">{ts_display}</span></div>',
                            unsafe_allow_html=True,
                        )

                        copy_html = _copy_meta_html(
                            content=full_response,
                            model=st.session_state.chat_lm_model,
                            time_str=time_str,
                            token_str=token_str,
                        )

                        stream_placeholder.markdown(full_response)
                        components.html(copy_html, height=28)

                        st.session_state.chat_history.append({
                            "role": "assistant",
                            "content": full_response,
                            "model": st.session_state.chat_lm_model,
                            "response_time": time_str,
                            "tokens": token_str,
                            "timestamp": stream_start.isoformat(),
                        })
                        _persist_chat(redis_client, username)

                    except LmStudioError as exc:
                        llm_status.update(label=f"❌ **{exc}**", state="error")
                        if full_response:
                            ts_display = stream_start.strftime("%I:%M %p").lstrip("0")
                            st.markdown(
                                f'<div class="msg-ts-row assistant"><span class="msg-ts">{ts_display}</span></div>',
                                unsafe_allow_html=True,
                            )
                            stream_placeholder.markdown(full_response)
                            st.session_state.chat_history.append({
                                "role": "assistant",
                                "content": full_response,
                                "model": st.session_state.chat_lm_model,
                                "response_time": "interrupted",
                                "tokens": "-",
                                "timestamp": stream_start.isoformat(),
                            })
                            _persist_chat(redis_client, username)

        # Dynamic height + auto-scroll for chat messages window
        st.components.v1.html(
            """
        <script>
        (function() {
            try {
                var w = window.parent.document;

                function findMsgContainer() {
                    var marker = w.querySelector('.chat-marker');
                    if (!marker) return null;
                    var el = marker.nextElementSibling;
                    if (!el) return null;
                    var vb = el.querySelector('[data-testid="stVerticalBlock"]');
                    return vb || el;
                }

                function findChatInput() {
                    return w.querySelector('[data-testid="stChatInput"]');
                }

                function adjustHeight() {
                    var msg = findMsgContainer();
                    var input = findChatInput();
                    if (!msg || !input) return;
                    var rect = msg.getBoundingClientRect();
                    var inputRect = input.getBoundingClientRect();
                    var available = inputRect.top - rect.top - 6;
                    if (available > 100) {
                        msg.style.height = available + 'px';
                    }
                }

                function autoScroll() {
                    var msg = findMsgContainer();
                    if (!msg) return;
                    var dist = msg.scrollHeight - msg.scrollTop - msg.clientHeight;
                    if (dist < 250) {
                        msg.scrollTop = msg.scrollHeight;
                    }
                }

                adjustHeight();
                autoScroll();

                w.addEventListener('resize', adjustHeight);
                var checkInterval = setInterval(function() {
                    adjustHeight();
                    autoScroll();
                }, 400);

                setTimeout(function() { clearInterval(checkInterval); }, 180000);
            } catch(e) {}
        })();
        </script>
        """,
            height=0,
        )

        st.markdown('</div>', unsafe_allow_html=True)

    # ============ TAB 5: User Management (admin only) ============
    if tab5 is not None:
        with tab5:
            st.subheader("👥 User Management")
            st.caption("Manage users and their roles.")

            users = auth.list_users()
            if not users:
                st.info("No users found.")
            else:
                data = []
                for u in users:
                    data.append({
                        "Username": u["username"],
                        "Role": u["role"],
                        "Created": datetime.fromisoformat(u["created_at"]).strftime("%Y-%m-%d"),
                    })

                st.dataframe(data, use_container_width=True, hide_index=True)

                st.divider()
                st.markdown("**Change User Role**")
                with st.form("role_form"):
                    target = st.selectbox("Select User", [u["username"] for u in users if u["username"] != user.get("username", "")])
                    new_role = st.selectbox("New Role", ["admin", "user", "viewer"])
                    if st.form_submit_button("Update Role", use_container_width=True, type="primary"):
                        err = auth.update_role(target, new_role)
                        if err:
                            st.error(err)
                        else:
                            st.success(f"Role updated: {target} → {new_role}")
                            st.rerun()
