# agents/planner.py
from utils.loggers import logger
def planner_agent(state):

    request = state["request"]

    plan = f"""
    Step 1: Dependency Check
    Step 2: Risk Analysis
    Step 3: Governance Validation
    Step 4: Deployment
    """

    state["plan"] = plan

    logger.info(f"Plan generated for request: {request}")

    return state