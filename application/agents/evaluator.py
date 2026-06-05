# agents/evaluator.py

from utils.llm_studio import ask_lm_studio


def _fallback_evaluation(state: dict) -> dict:
    risk_present = bool(state.get("risk_present", False))
    return {
        "evaluation_result": (
            "Workflow completed with risks present."
            if risk_present
            else "Workflow completed with no risks."
        ),
        "success_criteria": [
            "Workflow reached final evaluation step",
            "Approval rules were applied",
            "Execution result was captured",
        ],
        "next_actions": [
            "Review execution history",
            "Validate monitoring signals",
            "Document final outcome",
        ],
    }


def evaluator_agent(state):

    analysis = state.get("_llm_analysis")
    if analysis:
        state["evaluation_result"] = analysis.get("evaluation_result", "")
        state["success_criteria"] = analysis.get("success_criteria", [])
        state["next_actions"] = analysis.get("next_actions", [])
        state["evaluator_llm_used"] = True
        return state

    response = ask_lm_studio(
        state,
        system_prompt=(
            "You are a workflow evaluator. Return only JSON with keys: "
            "evaluation_result string, success_criteria array, next_actions array."
        ),
            user_prompt=(
                f"Request: {state.get('request', '')}\n"
                f"Risk present: {state.get('risk_present', False)}\n"
                f"Action result: {state.get('action_result', '')}\n"
                "Evaluate the workflow outcome and recommend next actions."
            ),
        fallback=_fallback_evaluation(state),
    )

    state["evaluation_result"] = response.get("evaluation_result", "")
    state["success_criteria"] = response.get("success_criteria", [])
    state["next_actions"] = response.get("next_actions", [])
    state["evaluator_llm_used"] = response.get("_llm_used", False)
    if response.get("_llm_error"):
        state["evaluator_llm_error"] = response["_llm_error"]

    return state
