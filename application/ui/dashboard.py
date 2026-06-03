# ui/dashboard.py

import time

import streamlit as st
from datetime import datetime
from graph.workflow import graph, dynamic_workflow, WorkflowState
from memory.checkpoint_manager import CheckpointManager
from utils.llm_studio import LmStudioError, list_lm_studio_models, chat_lm_studio_stream

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

    st.title("⚡ Agentic Workflow Studio")
    
    # Create tabs
    tab1, tab2, tab3, tab4 = st.tabs(["Execute Workflow", "Checkpoints", "Approval Queue", "LLM Chat"])
    
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
                    max_value=120,
                    value=15,
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
                        "llm_config": {
                            "enabled": llm_enabled,
                            "base_url": llm_url,
                            "model": llm_model,
                            "timeout": llm_timeout,
                            "max_tokens": llm_max_tokens,
                            "require_llm": llm_enabled,
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
                        st.caption(
                            f"Risk level: {result.get('risk_level', 'N/A')} | "
                            f"Score: {result.get('risk_score', 'N/A')}"
                        )
                        risks = result.get("risks", [])
                        if risks:
                            for risk in risks:
                                st.warning(f"🔴 {risk}")
                        else:
                            st.info("✅ No risks identified")

                        mitigations = result.get("mitigations", [])
                        if mitigations:
                            st.write("**Mitigations:**")
                            for mitigation in mitigations:
                                st.write(f"• {mitigation}")
                    
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

    # ============ TAB 4: LLM Chat ============
    with tab4:
        st.subheader("💬 Chat with Local LLM")

        st.markdown(
            """
        <style>
        div[data-testid="stChatInput"] {
            position: fixed !important;
            bottom: 0 !important;
            left: 50% !important;
            transform: translateX(-50%) !important;
            width: calc(100% - 3rem) !important;
            max-width: 736px !important;
            background-color: #ffffff !important;
            z-index: 1000 !important;
            padding: 0.75rem 1rem !important;
            padding-bottom: calc(0.75rem + env(safe-area-inset-bottom, 0px)) !important;
            border-top: 1px solid #e5e7eb !important;
            box-shadow: 0 -2px 12px rgba(0,0,0,0.08) !important;
        }
        .main > .block-container {
            padding-bottom: 6rem !important;
        }
        .chat-marker + .element-container > div[data-testid="stVerticalBlock"] {
            height: calc(100vh - 280px) !important;
            min-height: 200px !important;
        }
        </style>
        """,
            unsafe_allow_html=True,
        )

        if "chat_history" not in st.session_state:
            st.session_state.chat_history = []
        if "chat_lm_connected" not in st.session_state:
            st.session_state.chat_lm_connected = False
            st.session_state.chat_lm_models = []
            st.session_state.chat_lm_model = "local-model"

        with st.expander("⚙️ Chat Settings", expanded=False):
            chat_url = st.text_input(
                "LM Studio Chat URL",
                value="http://localhost:1234/v1/chat/completions",
                key="chat_llm_url",
            )
            chat_timeout = st.number_input(
                "Timeout (s)", min_value=5, max_value=120, value=60, key="chat_timeout"
            )
            chat_system = st.text_area(
                "System Prompt",
                value="You are a helpful AI assistant. Keep responses concise and clear.",
                key="chat_system_prompt",
                height=100,
            )

            if st.button("🔌 Connect / Reconnect", use_container_width=True, key="chat_connect_btn"):
                with st.spinner("Connecting to LM Studio..."):
                    try:
                        models = list_lm_studio_models(chat_url, timeout=5)
                        st.session_state.chat_lm_models = models
                        st.session_state.chat_lm_model = models[0] if models else "local-model"
                        st.session_state.chat_lm_connected = True
                        st.rerun()
                    except LmStudioError as exc:
                        st.session_state.chat_lm_connected = False
                        st.error(str(exc))

            if st.session_state.chat_lm_connected:
                current_idx = 0
                if st.session_state.chat_lm_model in st.session_state.chat_lm_models:
                    current_idx = st.session_state.chat_lm_models.index(st.session_state.chat_lm_model)
                st.selectbox("Model", st.session_state.chat_lm_models, index=current_idx, key="chat_model_select")
                st.session_state.chat_lm_model = st.session_state.chat_model_select
                st.success(f"✅ Connected – {st.session_state.chat_lm_model}")

            if st.button("🗑️ Clear Conversation", use_container_width=True, key="clear_chat_btn"):
                st.session_state.chat_history = []
                st.rerun()

        chat_connected = st.session_state.chat_lm_connected
        if not chat_connected:
            st.info("💡 Open **Chat Settings** above and connect to LM Studio to start chatting.")

        # Marker to identify the messages container for CSS targeting
        st.markdown(
            '<div class="chat-marker" style="display:none"></div>',
            unsafe_allow_html=True,
        )

        # Messages window: independently scrollable container
        msg_window = st.container(height=400)

        with msg_window:
            for message in st.session_state.chat_history:
                with st.chat_message(message["role"]):
                    st.markdown(message["content"])

                    safe = message["content"]
                    safe = safe.replace("\\", "\\\\")
                    safe = safe.replace("'", "\\'")
                    safe = safe.replace("\n", "\\n")
                    safe = safe.replace("\r", "\\r")
                    safe = safe.replace("&", "&amp;")
                    safe = safe.replace('"', "&quot;")
                    safe = safe.replace("<", "&lt;")
                    safe = safe.replace(">", "&gt;")

                    meta_parts = [
                        f'<span style="cursor:pointer;font-size:0.8rem;color:#999;user-select:none;" '
                        f'onclick="navigator.clipboard.writeText(\'{safe}\')'
                        f'.then(()=>{{this.style.color=\'#22c55e\';'
                        f'setTimeout(()=>{{this.style.color=\'#999\'}},2000)}})'
                        f'.catch(()=>{{this.style.color=\'#ef4444\'}})" '
                        f'title="Copy message">📋</span>'
                    ]

                    if message.get("role") == "assistant":
                        model = message.get("model", "")
                        resp_time = message.get("response_time", "")
                        if model or resp_time:
                            meta_parts.append(
                                f'<span style="font-size:0.75rem;color:#bbb;">'
                                f'{model} · {resp_time}</span>'
                            )

                    st.markdown(
                        f'<div style="display:flex;align-items:center;gap:0.5rem;margin-top:0.25rem;">'
                        + " ".join(meta_parts)
                        + '</div>',
                        unsafe_allow_html=True,
                    )

        if prompt := st.chat_input("Ask the local LLM...", disabled=not chat_connected):
            st.session_state.chat_history.append({
                "role": "user",
                "content": prompt,
                "timestamp": datetime.now().isoformat(),
            })

            with msg_window:
                with st.chat_message("user"):
                    st.markdown(prompt)

                with st.chat_message("assistant"):
                    status = st.status("⏳ Connecting to LLM...")
                    stream_placeholder = st.empty()
                    full_response = ""

                    messages = [
                        {"role": "system", "content": chat_system},
                        *[{"role": m["role"], "content": m["content"]} for m in st.session_state.chat_history],
                    ]

                    try:
                        start_time = time.time()
                        status.update(label="🤔 Thinking...")
                        stream = chat_lm_studio_stream(
                            base_url=chat_url,
                            model=st.session_state.chat_lm_model,
                            messages=messages,
                            timeout=chat_timeout,
                        )

                        for chunk in stream:
                            if not full_response:
                                status.update(label="✍️ Generating...")
                            full_response += chunk
                            stream_placeholder.markdown(full_response + "▌")

                        elapsed = time.time() - start_time
                        time_str = f"{elapsed:.1f}s" if elapsed < 60 else f"{elapsed//60:.0f}m {elapsed%60:.0f}s"

                        stream_placeholder.markdown(full_response)
                        status.update(label="✅ Done", state="complete")
                        st.session_state.chat_history.append({
                            "role": "assistant",
                            "content": full_response,
                            "model": st.session_state.chat_lm_model,
                            "response_time": time_str,
                            "timestamp": datetime.now().isoformat(),
                        })

                    except LmStudioError as exc:
                        status.update(label=f"❌ {exc}", state="error")
                        if full_response:
                            stream_placeholder.markdown(full_response)
                            st.session_state.chat_history.append({
                                "role": "assistant",
                                "content": full_response,
                                "model": st.session_state.chat_lm_model,
                                "response_time": "interrupted",
                                "timestamp": datetime.now().isoformat(),
                            })

        # Dynamic auto-scroll for chat messages window
        st.components.v1.html(
            """
        <script>
        (function() {
            try {
                var w = window.parent.document;
                var containers = w.querySelectorAll('[data-testid="stVerticalBlock"]');
                var target = null;
                for (var i = 0; i < containers.length; i++) {
                    if (containers[i].scrollHeight > containers[i].clientHeight + 50) {
                        target = containers[i];
                        break;
                    }
                }
                if (!target) return;
                target.scrollTop = target.scrollHeight;
                var interval = setInterval(function() {
                    var dist = target.scrollHeight - target.scrollTop - target.clientHeight;
                    if (dist < 200) {
                        target.scrollTop = target.scrollHeight;
                    }
                }, 300);
                setTimeout(function() { clearInterval(interval); }, 120000);
            } catch(e) {}
        })();
        </script>
        """,
            height=0,
        )
