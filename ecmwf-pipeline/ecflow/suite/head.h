set -e -u -o pipefail
# Use the ECF_PORT variable passed from the suite
trap 'ecflow_client --port=%ECF_PORT% --abort="[Task] Trapped error"' ERR
ecflow_client --port=%ECF_PORT% --init=$$