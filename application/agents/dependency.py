# agents/dependency.py

def dependency_agent(state):

    state["dependencies"] = [

        "Redis",

        "PostgreSQL",

        "Kafka"
    ]

    return state