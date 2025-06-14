# ecflow/pipeline.py (FINAL - To be used with ECF_SUBMIT_CMD)
import os
from ecflow import Defs, Suite, Task

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
WRAPPER_SCRIPT_PATH = os.path.join(PROJECT_ROOT, "ecflow", "suite", "job_wrapper.sh")

defs = Defs()
suite = defs.add_suite("c3s_ingestion_pipeline")

# The job command is now what gets written inside the temporary .job file.
# It simply calls our wrapper, which handles the real logic.
suite.add_variable(
    "ECF_JOB_CMD",
    f"{WRAPPER_SCRIPT_PATH} %ECF_SCRIPT%"
)
suite.add_variable("ECF_PORT", os.getenv("ECF_PORT", "31415"))
suite.add_variable("RUN_DATE", '2025-06-01')

# Helper to add tasks
def add_task_with_script(task_name):
    task = suite.add_task(task_name)
    script_path = os.path.join(PROJECT_ROOT, "ecflow", "suite", f"{task_name}.ecf")
    task.add_variable("ECF_SCRIPT", script_path)
    return task

start = suite.add_task("start")
start.add_variable("ECF_STUB_TASK", "")

acquire = add_task_with_script("acquire")
acquire.add_trigger("start==complete")
process = add_task_with_script("process_and_visualize")
process.add_trigger("acquire==complete")

os.makedirs("ecflow/def", exist_ok=True)
defs.save_as_defs("ecflow/def/pipeline.def")
print("Final suite definition for ECF_SUBMIT_CMD created.")