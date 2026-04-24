def run_plan(user_input):
    """
    command 层：只负责调用 agent
    """
    from mini_ecc.agents.planner import run_planner

    return run_planner(user_input)