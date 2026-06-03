# agents/action.py

from utils.llm_studio import ask_lm_studio


def _fallback_action(state: dict) -> dict:
    request = state.get("request", "")
    environment = "production" if "production" in request.lower() else "dev" if "dev" in request.lower() else "target"
    return {
        "action_result": f"Simulated execution completed for {environment} environment.",
        "execution_steps": [
            "Validated approval and dependencies",
            "Prepared execution context",
            "Simulated requested workflow action",
            "Captured post-action status",
        ],
    }


def action_agent(state):

    analysis = state.get("_llm_analysis")
    if analysis:
        state["action_result"] = analysis.get("action_result", "")
        state["execution_steps"] = analysis.get("execution_steps", [])
        state["action_llm_used"] = True
        return state

    response = ask_lm_studio(
        state,
        system_prompt=(
            "You are an execution agent. Do not claim real infrastructure changes. "
            "Return only JSON with keys: action_result string, execution_steps array."
        ),
        user_prompt=(
            f"Request: {state.get('request', '')}\n"
            f"Plan: {state.get('plan', '')}\n"
            f"Dependencies: {state.get('dependencies', [])}\n"
            "Generate a realistic simulated execution result."
        ),
        fallback=_fallback_action(state),
    )

    state["action_result"] = response.get("action_result", "")
    state["execution_steps"] = response.get("execution_steps", [])
    state["action_llm_used"] = response.get("_llm_used", False)
    if response.get("_llm_error"):
        state["action_llm_error"] = response["_llm_error"]

    return state
