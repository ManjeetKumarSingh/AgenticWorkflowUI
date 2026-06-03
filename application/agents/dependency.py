# agents/dependency.py

from utils.llm_studio import ask_lm_studio


def _fallback_dependencies(state: dict) -> dict:
    request = state.get("request", "").lower()
    dependencies = []

    keyword_map = {
        "deploy": ["CI/CD pipeline", "Container registry", "Target environment access"],
        "dev": ["Development environment", "Feature branch", "Developer credentials"],
        "production": ["Production cluster", "Monitoring stack", "Rollback artifact"],
        "database": ["Database connection", "Migration scripts", "Backup snapshot"],
        "api": ["API gateway", "Service credentials", "Contract tests"],
        "kafka": ["Kafka broker", "Consumer lag dashboard"],
        "redis": ["Redis cache", "Cache invalidation plan"],
        "postgres": ["PostgreSQL database", "Schema migration plan"],
    }

    for keyword, items in keyword_map.items():
        if keyword in request:
            dependencies.extend(items)

    if not dependencies:
        dependencies = ["Source repository", "Runtime environment", "Monitoring access"]

    return {
        "dependencies": list(dict.fromkeys(dependencies)),
        "assumptions": ["Dependencies inferred from the request text"],
    }


def dependency_agent(state):

    analysis = state.get("_llm_analysis")
    if analysis:
        state["dependencies"] = analysis.get("dependencies", [])
        state["dependency_assumptions"] = analysis.get("assumptions", [])
        state["dependency_llm_used"] = analysis.get("_llm_used", False)
        return state

    request = state.get("request", "")
    response = ask_lm_studio(
        state,
        system_prompt=(
            "You are a dependency analysis agent. Return only JSON with keys: "
            "dependencies as an array of concrete systems/tools/data needed, assumptions as an array."
        ),
        user_prompt=(
            f"Workflow request: {request}\n"
            f"Current plan: {state.get('plan', '')}\n"
            "Identify realistic dependencies for this workflow."
        ),
        fallback=_fallback_dependencies(state),
    )

    state["dependencies"] = response.get("dependencies", [])
    state["dependency_assumptions"] = response.get("assumptions", [])
    state["dependency_llm_used"] = response.get("_llm_used", False)
    if response.get("_llm_error"):
        state["dependency_llm_error"] = response["_llm_error"]

    return state
