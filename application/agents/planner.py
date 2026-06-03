# agents/planner.py
from utils.loggers import logger
from utils.llm_studio import ask_lm_studio


def _fallback_plan(request: str) -> dict:
    request_lower = request.lower()
    action = "Deployment" if "deploy" in request_lower else "Execution"
    environment = "production" if "production" in request_lower else "dev" if "dev" in request_lower else "target"
    return {
        "plan": (
            f"Step 1: Understand requested {action.lower()} scope\n"
            f"Step 2: Inspect dependencies and target {environment} environment\n"
            "Step 3: Analyze operational, security, and rollback risks\n"
            "Step 4: Validate governance controls and approval requirements\n"
            f"Step 5: Perform {action.lower()} with monitoring and rollback readiness"
        ),
        "summary": f"Prepared a workflow plan for {request}",
        "workflow_type": action.lower(),
    }


def _fallback_analysis(request: str) -> dict:
    plan = _fallback_plan(request)
    return {
        **plan,
        "dependencies": [],
        "assumptions": [],
        "risks": [],
        "risk_score": 20,
        "risk_level": "low",
        "mitigations": [],
        "human_approval_required": "deploy" in request.lower() or "production" in request.lower(),
        "governance_output": "Governance evaluated with fallback rules.",
        "policy_checks": ["Fallback policy check"],
        "action_result": "Execution pending approval and action step.",
        "execution_steps": [],
        "evaluation_result": "Evaluation pending workflow completion.",
        "success_criteria": [],
        "next_actions": [],
    }


def planner_agent(state):

    request = state["request"]
    response = state.get("_llm_analysis")

    if not response:
        response = ask_lm_studio(
            state,
            system_prompt=(
                "You are a fast workflow analysis agent. Return only compact JSON. "
                "Use short strings and max 3 items per list. No markdown."
            ),
            user_prompt=(
                "Analyze this workflow request once for all downstream agents.\n"
                f"Request: {request}\n"
                "Return JSON keys exactly: plan, summary, workflow_type, dependencies, assumptions, "
                "risks, risk_score, risk_level, mitigations, human_approval_required, governance_output, "
                "policy_checks, action_result, execution_steps, evaluation_result, success_criteria, next_actions."
            ),
            fallback=_fallback_analysis(request),
        )

    if "_llm_analysis" not in state:
        state["_llm_analysis"] = response

    state["plan"] = response.get("plan", _fallback_plan(request)["plan"])
    state["plan_summary"] = response.get("summary", "")
    state["workflow_type"] = response.get("workflow_type", "general")
    state["planner_llm_used"] = response.get("_llm_used", False)
    if response.get("_llm_error"):
        state["planner_llm_error"] = response["_llm_error"]

    logger.info(f"Plan generated for request: {request}")

    return state
