#!/bin/bash

# --- Job Wrapper for Conda Environments ---
# This script's purpose is to correctly initialize Conda before running an ecFlow task.

# BE ROBUST: Exit on any error, treat unset variables as errors.
set -e -u -o pipefail

# --- USER CONFIGURATION: Set the path to your Anaconda/Miniconda installation ---
# This is the ONLY line you might need to change.
CONDA_BASE_PATH="/home/duskdawn/anaconda3"
# -----------------------------------------------------------------------------

# Source the main conda script to make the 'conda' command available.
# This is the correct way to initialize conda in a script.
source "${CONDA_BASE_PATH}/etc/profile.d/conda.sh"

# Activate the specific environment for our pipeline.
conda activate ecmwf-pipeline

# --- Sanity Checks (for debugging) ---
echo "--- [WRAPPER] Environment Initialized ---"
echo "--- [WRAPPER] User: $(whoami)"
echo "--- [WRAPPER] Host: $(hostname)"
echo "--- [WRAPPER] CONDA_DEFAULT_ENV: ${CONDA_DEFAULT_ENV}"
echo "--- [WRAPPER] Path to python: $(which python)"
echo "--- [WRAPPER] Path to ecflow_client: $(which ecflow_client)"
echo "---------------------------------------"

# Execute the actual ecFlow task script that was passed as an argument.
# "$@" passes all arguments from the wrapper to the script exactly as they were received.
exec "$@"