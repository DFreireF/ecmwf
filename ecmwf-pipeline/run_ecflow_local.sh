# run_ecflow.sh (SIMPLIFIED AND CORRECTED)

#!/bin/bash
set -e
if [ -z "$CONDA_DEFAULT_ENV" ]; then
    echo "FATAL: Conda env not active."; exit 1;
fi

PROJECT_ROOT=$(pwd)
export ECF_PORT=31415
export ECF_HOST=localhost
SUITE_NAME="c3s_ingestion_pipeline"
SERVER_LOG="${PROJECT_ROOT}/ecflow.log"

# --- Cleanup function adapted for default directories ---
cleanup() {
    echo; echo "Shutting down...";
    pkill -9 -f "ecflow_server --port=${ECF_PORT}" || true
    ecflow_client --kill="/${SUITE_NAME}" >/dev/null 2>&1 || true
    ecflow_client --delete="/${SUITE_NAME}" >/dev/null 2>&1 || true

    # Clean up artifacts, including the default suite runtime directory
    rm -f "${SERVER_LOG}" ecflow_check.log "${PROJECT_ROOT}/ecflow/def/pipeline.def"
    rm -rf "${PROJECT_ROOT}/${SUITE_NAME}" # Clean up default runtime directory
}
trap cleanup EXIT
cleanup

# --- Main ---
echo "Generating suite and making task scripts executable..."
python ecflow/pipeline.py
chmod +x ecflow/suite/*.ecf

# Create the DEFAULT runtime directory that ecFlow will expect for job outputs.
echo "Creating default runtime directory: ./${SUITE_NAME}"
mkdir -p "${PROJECT_ROOT}/${SUITE_NAME}"

echo "Starting ecflow_server..."
ecflow_server --port=${ECF_PORT} > "${SERVER_LOG}" 2>&1 &
sleep 3

echo "Loading suite onto the server..."
ecflow_client --load="ecflow/def/pipeline.def"
ecflow_client --begin=${SUITE_NAME}

echo "=========================================================="
echo "Server is RUNNING. Suite is loaded and queued."
echo
echo "To START the workflow, run this in a NEW terminal:"
echo "  conda activate ecmwf-pipeline"
echo "  export ECF_PORT=31415"
echo "  ecflow_client --force=complete /c3s_ingestion_pipeline/start"
echo
echo "To MONITOR the output, run this in ANOTHER new terminal:"
echo "  tail -f ${PROJECT_ROOT}/${SUITE_NAME}/acquire.1"
echo "=========================================================="
echo "(This script is now waiting. Press Ctrl+C to stop.)"

wait