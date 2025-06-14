#!/bin/bash

# A script to test each component of the data processing pipeline independently.
# This helps ensure the core Python logic is working before running the full
# ecFlow suite.

# Exit immediately if any command fails
set -e

# --- STEP 0: ENVIRONMENT & CONFIGURATION ---
echo "---[TEST 1/5]--- Verifying Environment and Configuration..."

# Check for active Conda environment
if [ -z "$CONDA_DEFAULT_ENV" ]; then
    echo "ERROR: Conda environment not activated. Please run 'conda activate ecmwf-pipeline' first."
    exit 1
fi

# Define paths and variables
PROJECT_ROOT=$(pwd)
CONFIG_FILE="${PROJECT_ROOT}/config.yaml"
# We will use a fixed test date for reproducibility
TEST_DATE="2025-06-01"

if [ ! -f "$CONFIG_FILE" ]; then
    echo "ERROR: Configuration file not found at ${CONFIG_FILE}"
    exit 1
fi
echo "Environment and Config................. PASS"
echo

# --- STEP 2: CLEAN SLATE ---
echo "---[TEST 2/5]--- Cleaning previous test run outputs..."
rm -rf data/raw/* data/bufr/* data/plots/* mlruns/*
# Recreate directories
mkdir -p data/raw data/bufr data/plots
echo "Workspace is clean..................... PASS"
echo

# --- STEP 3: TESTING DATA ACQUISITION (`acquire_data.py`) ---
echo "---[TEST 3/5]--- Testing data acquisition component..."
ACQUIRE_SCRIPT="${PROJECT_ROOT}/bin/acquire_data.py"

# Execute the script, capturing output. If it fails, 'set -e' will stop the script.
echo "Running acquire_data.py for date ${TEST_DATE}..."
python3 "${ACQUIRE_SCRIPT}" --date "${TEST_DATE}" --config "${CONFIG_FILE}"

# Verify that the expected output file was created
EXPECTED_NC_FILE="${PROJECT_ROOT}/data/raw/ecmwf-era5_20250601_surface.nc"
if [ ! -f "$EXPECTED_NC_FILE" ]; then
    echo "ERROR: Expected output file ${EXPECTED_NC_FILE} was not created."
    exit 1
fi
echo "Output NetCDF file created successfully."
echo "Data acquisition component............. PASS"
echo

# --- STEP 4: TESTING PROCESSING & VIZ (`process_and_visualize.py`) ---
echo "---[TEST 4/5]--- Testing processing and visualization component..."
PROCESS_SCRIPT="${PROJECT_ROOT}/bin/process_and_visualize.py"

# Execute the script
echo "Running process_and_visualize.py for date ${TEST_DATE}..."
python3 "${PROCESS_SCRIPT}" --date "${TEST_DATE}" --config "${CONFIG_FILE}"

# Verify its outputs
EXPECTED_BUFR_FILE="${PROJECT_ROOT}/data/bufr/ecmwf-era5_20250601_surface.bufr"
EXPECTED_PLOT_FILE="${PROJECT_ROOT}/data/plots/dashboard_2025-06-01.png"

if [ ! -f "$EXPECTED_BUFR_FILE" ]; then
    echo "ERROR: Expected BUFR file was not created."
    exit 1
fi
echo "Output BUFR file created successfully."

if [ ! -f "$EXPECTED_PLOT_FILE" ]; then
    echo "ERROR: Expected dashboard plot was not created."
    exit 1
fi
echo "Output dashboard plot created successfully."
echo "Processing and viz component........... PASS"
echo

# --- STEP 5: TESTING MLFLOW TRACKING ---
echo "---[TEST 5/5]--- Verifying MLflow run was created..."
# A simple way to check is to see if the mlruns directory was created and is not empty
if [ ! -d "mlruns" ] || [ -z "$(ls -A mlruns)" ]; then
    echo "ERROR: MLflow tracking directory 'mlruns' was not created or is empty."
    exit 1
fi
echo "MLflow run was created."
echo "MLflow tracking........................ PASS"
echo

# --- ALL TESTS PASSED ---
echo "========================================"
echo " ✅  All components passed tests successfully!"
echo "========================================"