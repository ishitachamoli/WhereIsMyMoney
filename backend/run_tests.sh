#!/bin/bash
# Run tests for WhereIsMyMoneyGoing backend
# Uses the available Python 3.11 with necessary library paths

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYLIBS_DIR="$SCRIPT_DIR/.pylibs"
PYTHON="/usr/patching-agent/python3.11/bin/python3.11"
SQLITE_LIB="/local/apollo/package/local_1/AL2_x86_64/SQLite/SQLite-118104.0-0/lib"

export LD_LIBRARY_PATH="$SQLITE_LIB:$LD_LIBRARY_PATH"
export PYTHONPATH="$PYLIBS_DIR:$PYTHONPATH"
export DATABASE_URL="sqlite:///./test_wimm.db"
export ENVIRONMENT="test"

cd "$SCRIPT_DIR"

echo "Running WhereIsMyMoneyGoing backend tests..."
echo "Python: $PYTHON"
echo ""

$PYTHON -m pytest tests/test_upload.py tests/test_transactions.py tests/test_analytics.py -v "$@"

# Cleanup test DB
rm -f test_wimm.db
