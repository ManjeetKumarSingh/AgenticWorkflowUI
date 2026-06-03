# agents/risk.py

from utils.llm_studio import ask_lm_studio


def _fallback_risk(state: dict) -> dict:
    request = state.get("request", "").lower()
    dependencies = state.get("dependencies", [])
    risks = []
    risk_score = 20

    if "production" in request or "prod" in request:
        risks.extend(["Customer impact during production change", "Rollback complexity"])
        risk_score += 45
    if "deploy" in request:
        risks.append("Deployment failure or partial rollout")
        risk_score += 15
    if any("database" in dep.lower() or "migration" in dep.lower() for dep in dependencies):
        risks.append("Data migration or schema compatibility issue")
        risk_score += 20
    if any("credentials" in dep.lower() or "access" in dep.lower() for dep in dependencies):
        risks.append("Access or credential readiness issue")
        risk_score += 10
    if "dev" in request and not risks:
        risks.append("Low environment risk, verify configuration drift")

    risk_score = min(risk_score, 100)
    return {
        "risks": list(dict.fromkeys(risks)),
        "risk_score": risk_score,
        "risk_level": "high" if risk_score >= 70 else "medium" if risk_score >= 40 else "low",
        "mitigations": [
            "Validate dependencies before execution",
            "Prepare rollback steps",
            "Monitor key signals after execution",
        ],
    }


def risk_agent(state):

    analysis = state.get("_llm_analysis")
    if analysis:
        state["risks"] = analysis.get("risks", [])
        state["risk_score"] = analysis.get("risk_score", 0)
        state["risk_level"] = analysis.get("risk_level", "low")
        state["mitigations"] = analysis.get("mitigations", [])
        state["risk_llm_used"] = analysis.get("_llm_used", False)
        return state

    response = ask_lm_studio(
        state,
        system_prompt=(
            "You are a workflow risk analysis agent. Return only JSON with keys: "
            "risks as an array, risk_score as 0-100 integer, risk_level as low/medium/high, "
            "mitigations as an array."
        ),
        user_prompt=(
            f"Request: {state.get('request', '')}\n"
            f"Plan: {state.get('plan', '')}\n"
            f"Dependencies: {state.get('dependencies', [])}\n"
            "Analyze operational, security, data, and approval risks."
        ),
        fallback=_fallback_risk(state),
    )

    state["risks"] = response.get("risks", [])
    state["risk_score"] = response.get("risk_score", 0)
    state["risk_level"] = response.get("risk_level", "low")
    state["mitigations"] = response.get("mitigations", [])
    state["risk_llm_used"] = response.get("_llm_used", False)
    if response.get("_llm_error"):
        state["risk_llm_error"] = response["_llm_error"]

    return state
