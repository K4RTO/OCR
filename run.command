#!/bin/bash
echo "Starting the Shipping Invoice Extractor..."

# Get the directory of the script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
SENTINEL="$SCRIPT_DIR/.mineru_shutdown"
PORTABLE_SITE="$SCRIPT_DIR/portable_site"
VENV_ACTIVATE="$SCRIPT_DIR/src/.venv/bin/activate"

# Remove stale sentinel if exists
if [ -f "$SENTINEL" ]; then
  rm "$SENTINEL"
fi

PY_CMD=""
if [ -f "$VENV_ACTIVATE" ]; then
  # Activate virtual environment located inside src
  source "$VENV_ACTIVATE"
  PY_CMD="python"
else
  # Fallback to system Python with portable_site packages
  if [ -d "$PORTABLE_SITE" ]; then
    export PYTHONPATH="$PORTABLE_SITE:${PYTHONPATH:-}"
  fi
  if command -v python3 >/dev/null 2>&1; then
    PY_CMD="python3"
  elif command -v python >/dev/null 2>&1; then
    PY_CMD="python"
  else
    echo "ERROR: 未找到可用的 Python 解释器。请安装 Python 3.10+ 或携带现有 .venv 目录。"
    exit 1
  fi
fi

# Run the Gradio app located in src/app
echo "Launching the application... The user interface should open in your default web browser."
"$PY_CMD" "$SCRIPT_DIR/src/app/app.py"
EXIT_CODE=$?

if [ -f "$SENTINEL" ]; then
  rm "$SENTINEL"
  if command -v osascript >/dev/null 2>&1; then
    osascript -e 'tell application "Terminal" to if (count of windows) > 0 then close front window' >/dev/null 2>&1 &
  fi
else
  echo "Application finished."
fi

exit $EXIT_CODE
