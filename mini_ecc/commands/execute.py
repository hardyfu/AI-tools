from mini_ecc.agents.planner import run_planner
from mini_ecc.agents.coder import run_coder_for_task
from mini_ecc.agents.assembler import run_assembler

def run_execute(user_input: str):
    print("=== Planner Output ===")
    plan = run_planner(user_input)
    print(plan)

    goal = plan.get("goal", user_input)
    tasks = plan.get("tasks", [])

    task_outputs = []

    print("\n=== Task-by-Task Execution ===")
    for i, task in enumerate(tasks, start=1):
        print(f"\n--- Task {i}: {task} ---")
        result = run_coder_for_task(user_input, goal, task)
        print(result)

        task_outputs.append({
            "task": task,
            "result": result
        })

    print("\n=== Assembler Output ===")
    final_code = run_assembler(user_input, plan, task_outputs)
    print(final_code)

    output_path = "final_output.html"
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(final_code)

    print(f"\nSaved final output to {output_path}")

    return {
        "plan": plan,
        "task_outputs": task_outputs,
        "final_code": final_code
    }