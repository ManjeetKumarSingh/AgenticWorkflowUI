# agents/governance.py

from utils.llm_studio import ask_lm_studio


def _fallback_governance(state: dict) -> dict:
    risk_present = bool(state.get("risk_present", False))
    request = state.get("request", "").lower()
    approval_required = risk_present or "deploy" in request or "production" in request or "prod" in request
    return {
        "human_approval_required": approval_required,
        "governance_output": (
            "Human approval required before execution."
            if approval_required
            else "No human approval required based on current request and risk."
        ),
        "policy_checks": [
            "Risk threshold evaluated",
            "Environment sensitivity evaluated",
            "Rollback readiness recommended",
        ],
    }


def governance_agent(state):
    """
    Governance check agent.
    Preserves approval status if already set (e.g., after user approval).
    """
    analysis = state.get("_llm_analysis")
    if analysis:
        response = analysis
    else:
        response = ask_lm_studio(
            state,
            system_prompt=(
                "You are a governance validation agent. Return only compact JSON with keys: "
                "human_approval_required boolean, governance_output string, policy_checks array."
            ),
            user_prompt=(
                f"Request: {state.get('request', '')}\n"
                f"Plan: {state.get('plan', '')}\n"
                f"Risk present: {state.get('risk_present', False)}\n"
                "Decide whether human approval is required. Keep it brief."
            ),
            fallback=_fallback_governance(state),
        )

    state["human_approval_required"] = bool(response.get("human_approval_required", False))
    state["governance_output"] = response.get("governance_output", "")
    state["policy_checks"] = response.get("policy_checks", [])
    state["governance_llm_used"] = response.get("_llm_used", False)
    if response.get("_llm_error"):
        state["governance_llm_error"] = response["_llm_error"]

    # Only set approval status if not already set
    if "approval_status" not in state or state.get("approval_status") == "pending":
        # Default to pending for fresh execution
        if "approval_status" not in state:
            state["approval_status"] = "pending"
    
    return state
