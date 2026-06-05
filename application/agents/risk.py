# agents/risk.py

from utils.llm_studio import ask_lm_studio


def _fallback_risk(state: dict) -> dict:
    request = state.get("request", "").lower()
    dependencies = state.get("dependencies", [])
    risk_present = False

    if "production" in request or "prod" in request:
        risk_present = True
    if "deploy" in request:
        risk_present = True
    if any("database" in dep.lower() or "migration" in dep.lower() for dep in dependencies):
        risk_present = True
    if any("credentials" in dep.lower() or "access" in dep.lower() for dep in dependencies):
        risk_present = True

    return {"risk_present": risk_present}


def risk_agent(state):

    analysis = state.get("_llm_analysis")
    if analysis:
        state["risk_present"] = bool(analysis.get("risk_present", False))
        state["risk_llm_used"] = analysis.get("_llm_used", False)
        return state

    response = ask_lm_studio(
        state,
        system_prompt=(
            "You are a risk analysis agent. Return only a single JSON key: "
            "risk_present as a boolean (true if any operational, security, data, "
            "or approval risk exists, false otherwise). No arrays. No score."
        ),
        user_prompt=(
            f"Request: {state.get('request', '')}\n"
            f"Plan: {state.get('plan', '')}\n"
            f"Dependencies: {state.get('dependencies', [])}\n"
            "Does this workflow have any risks? Return risk_present true or false."
        ),
        fallback=_fallback_risk(state),
    )

    state["risk_present"] = bool(response.get("risk_present", False))
    state["risk_llm_used"] = response.get("_llm_used", False)
    if response.get("_llm_error"):
        state["risk_llm_error"] = response["_llm_error"]

    return state
