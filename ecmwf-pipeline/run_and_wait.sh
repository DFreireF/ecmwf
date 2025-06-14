#!/bin/bash
# run_and_wait.sh (FINAL, USING ECF_SUBMIT_CMD)
# A self-contained script to run the entire ecFlow pipeline from start to finish.

set -e

# --- 1. Environment and Configuration ---
if [ -z "$CONDA_DEFAULT_ENV" ]; then
    echo "FATAL: Conda environment not active. Please run 'conda activate ecmwf-pipeline' first."
    exit 1
fi

PROJECT_ROOT=$(pwd)
export ECF_PORT=31415
export ECF_HOST=localhost
SUITE_NAME="c3s_ingestion_pipeline"
SUITE_RUN_DIR="${PROJECT_ROOT}/${SUITE_NAME}"

# --- 2. Cleanup Function ---
cleanup() {
    echo; echo "--- [CLEANUP] Shutting down... ---"
    pkill -9 -f "ecflow_server --port=${ECF_PORT}" || true
    rm -f "${HOSTNAME}.${ECF_PORT}.ecf.log"
    rm -rf "${SUITE_RUN_DIR}" "${PROJECT_ROOT}/ecflow/def"
}
trap cleanup EXIT
echo "--- [SETUP] Performing initial cleanup... ---"
cleanup

# --- 3. Suite Generation (Using a simplified definition now) ---
echo "--- [SETUP] Generating simplified suite definition... ---"
python ecflow/pipeline.py # We'll provide a new, clean pipeline.py below
chmod +x ecflow/suite/*.ecf
mkdir -p "${SUITE_RUN_DIR}"

# --- 4. THE DEFINITIVE FIX: Use ECF_SUBMIT_CMD ---
# This environment variable forces the server to use our command for job submission.
# It overrides the compiled-in default.
# %ECF_RID% is the Process ID for the job.
# %ECF_JOB% is the path to the temporary .job file ecFlow creates.
# %ECF_JOBOUT% is the path for the log file.
export ECF_SUBMIT_CMD="bash %ECF_JOB% > %ECF_JOBOUT% 2>&1 & echo %ECF_RID% > %ECF_JOB%.rid"

echo "--- [SETUP] Starting ecflow_server with ECF_SUBMIT_CMD override... ---"
ecflow_server --port=${ECF_PORT} &
sleep 2
SERVER_LOG_FILE="${HOSTNAME}.${ECF_PORT}.ecf.log"
echo "--- [SETUP] Server is running. Log file is: ${SERVER_LOG_FILE}"

# --- 5. Load and Run Suite ---
echo "--- [SETUP] Loading and beginning the suite... ---"
ecflow_client --port=${ECF_PORT} --load="ecflow/def/pipeline.def"
ecflow_client --port=${ECF_PORT} --begin=${SUITE_NAME}

echo "--- [RUN] Forcing 'start' task to begin the pipeline... ---"
ecflow_client --port=${ECF_PORT} --force=complete /${SUITE_NAME}/start

# --- 6. Wait for Completion ---
echo "--- [MONITOR] Waiting for the suite to complete... ---"
# The waiting logic here is fine and doesn't need to change.
while true; do
    status=$(ecflow_client --port=${ECF_PORT} --get_state "/${SUITE_NAME}" | grep "state:" | awk '{print $2}')
    if [[ "$status" == "complete" ]]; then
        echo; echo "--- [SUCCESS] Suite completed successfully! ---"
        break
    fi
    if [[ "$status" == "aborted" ]]; then
        echo; echo "--- [FAILURE] Suite aborted! ---"
        # Find and print the log of the failed task
        aborted_task_log=$(find "${SUITE_RUN_DIR}" -type f -name "*.1" | head -n 1)
        if [ -f "$aborted_task_log" ]; then
            echo "--- Aborted Task Log: ${aborted_task_log} ---"
            cat "$aborted_task_log"
        fi
        exit 1
    fi
    printf "."
    sleep 5
done

echo "--- [REPORT] All tasks completed. Check the 'data/' directory. ---"
exit 0