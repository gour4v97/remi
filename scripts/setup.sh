#!/usr/bin/env bash
set -e

# =====================================================================
#  Remi Suite - Linux / macOS Setup Script
# =====================================================================

echo "=========================================================="
echo "          Remi Voice AI Suite - Unix Setup                "
echo "          Publisher: GAURAV                               "
echo "=========================================================="

# 1. Detect Python
PYTHON_BIN=""
for cmd in python3.12 python3.11 python3 python; do
    if command -v "$cmd" >/dev/null 2>&1; then
        PYTHON_BIN=$(command -v "$cmd")
        break
    fi
done

if [ -z "$PYTHON_BIN" ]; then
    echo "Error: Python 3.11+ is required but was not found."
    exit 1
fi

echo "[1/3] Using Python: $($PYTHON_BIN --version) ($PYTHON_BIN)"

# 2. Install dependencies
echo "[2/3] Installing dependencies..."
$PYTHON_BIN -m pip install --upgrade pip
$PYTHON_BIN -m pip install -e ".[dev]"

# 3. Run non-interactive setup
echo "[3/3] Running Remi setup..."
$PYTHON_BIN -m remi setup --non-interactive

echo ""
echo "=========================================================="
echo "  Setup Complete! Launch via:"
echo "    remi start      # Browser Voice Assistant"
echo "    remi dictation  # Voice Trans Dictation"
echo "    remi serve      # REST API Server"
echo "=========================================================="
