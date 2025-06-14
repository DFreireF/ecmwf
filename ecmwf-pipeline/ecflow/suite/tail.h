%include "head.h"
trap 0
# Use the ECF_PORT variable passed from the suite
ecflow_client --port=%ECF_PORT% --complete
%include "tail.h"