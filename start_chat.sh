#!/bin/bash
# MLX Studio Launch Script
set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Activate virtual environment if found
if [ -f "$DIR/.venv/bin/activate" ]; then
    source "$DIR/.venv/bin/activate"
elif [ -f "$HOME/.mlx-env/bin/activate" ]; then
    source "$HOME/.mlx-env/bin/activate"
elif [ -f "$HOME/mlx-env/bin/activate" ]; then
    source "$HOME/mlx-env/bin/activate"
fi

exec python3 "$DIR/gui_chat.py" "$@"
