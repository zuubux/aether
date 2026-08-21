#!/bin/bash

# Aether Unified Runner
# Automatically starts aia_weaver if not running, and launches aia_canvas.

# Ensure background processes terminate cleanly on script exit
trap 'kill 0' EXIT

# Resolve python interpreter
VENV_PYTHON=".venv/bin/python"
if [ ! -x "$VENV_PYTHON" ]; then
    VENV_PYTHON="python3"
fi

# Resolve repo root and default paths
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Check for --help intercept
for arg in "$@"; do
    if [ "$arg" == "-h" ] || [ "$arg" == "--help" ]; then
        $VENV_PYTHON "$REPO_ROOT/aia_canvas/src/main.py" --help
        exit 0
    fi
done

# Forward --debug if set in arguments
WEAVER_ARGS="--watch-dir $REPO_ROOT/aia_weaver/sandbox"
DEBUG_MODE=0
for arg in "$@"; do
    if [ "$arg" == "--debug" ] || [ "$arg" == "-v" ]; then
        WEAVER_ARGS="$WEAVER_ARGS --debug"
        DEBUG_MODE=1
    fi
done

# Check if aia_weaver is running
if ! pgrep -f "aia_weaver/src/main.py" > /dev/null; then
    if [ $DEBUG_MODE -eq 1 ]; then
        echo "Starting aia_weaver daemon in background..."
        $VENV_PYTHON "$REPO_ROOT/aia_weaver/src/main.py" $WEAVER_ARGS &
    else
        mkdir -p ~/.local/share/aether
        $VENV_PYTHON "$REPO_ROOT/aia_weaver/src/main.py" $WEAVER_ARGS > ~/.local/share/aether/weaver.log 2>&1 &
    fi
    sleep 1
else
    if [ $DEBUG_MODE -eq 1 ]; then
        echo "aia_weaver is already running."
    fi
fi

if [ $DEBUG_MODE -eq 1 ]; then
    echo "Starting aia_canvas..."
fi
$VENV_PYTHON "$REPO_ROOT/aia_canvas/src/main.py" "$@"
