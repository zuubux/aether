#!/bin/bash

# Aether Unified Runner
# Automatically starts aia_weaver if not running, and launches aia_canvas.

# Ensure background processes terminate cleanly on script exit
trap 'kill 0' EXIT

# Resolve repo root and default paths
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Resolve Python virtualenv interpreter reliably (.venv/bin/python vs fallback)
if python3 -c "import PyQt6.QtWidgets" >/dev/null 2>&1; then
    VENV_PYTHON="python3"
elif [ -x "$REPO_ROOT/.venv/bin/python" ]; then
    VENV_PYTHON="$REPO_ROOT/.venv/bin/python"
else
    VENV_PYTHON="python3"
fi

# Ensure PYTHONPATH includes repo root and canvas src so imports resolve cleanly
export PYTHONPATH="$REPO_ROOT:$REPO_ROOT/aia_canvas/src:$REPO_ROOT/aia_weaver/src:${PYTHONPATH:-}"

# Ensure QML_IMPORT_PATH includes aia_canvas/src/qml
QML_SRC_DIR="$REPO_ROOT/aia_canvas/src/qml"
if [ -z "$QML_IMPORT_PATH" ]; then
    export QML_IMPORT_PATH="$QML_SRC_DIR"
elif [[ ":$QML_IMPORT_PATH:" != *":$QML_SRC_DIR:"* ]]; then
    export QML_IMPORT_PATH="$QML_SRC_DIR:$QML_IMPORT_PATH"
fi
export QML2_IMPORT_PATH="$QML_IMPORT_PATH"

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

if [ $DEBUG_MODE -eq 1 ]; then
    echo "Using Python: $VENV_PYTHON"
    echo "QML_IMPORT_PATH: $QML_IMPORT_PATH"
fi

# Check if aia_weaver is running
if ! pgrep -f "aia_weaver/src/main.py" > /dev/null; then
    # Safely remove stale Unix domain sockets before starting Weaver
    SOCKET_CANDIDATES=(
        "${XDG_RUNTIME_DIR:-/tmp}/aia_weaver/aia_weaver.sock"
        "$HOME/.local/share/aether/aia_weaver.sock"
        "/tmp/aia_weaver/aia_weaver.sock"
    )
    for sock in "${SOCKET_CANDIDATES[@]}"; do
        if [ -S "$sock" ] || [ -f "$sock" ]; then
            if [ $DEBUG_MODE -eq 1 ]; then
                echo "Removing stale socket: $sock"
            fi
            rm -f "$sock"
        fi
    done

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

