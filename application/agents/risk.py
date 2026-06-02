# agents/risk.py

def risk_agent(state):

    request = state["request"]

    if "production" in request.lower():

        state["risks"] = [
            "High Traffic",
            "Deployment Risk"
        ]

    else:

        state["risks"] = []

    return state