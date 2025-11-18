#!/bin/bash
# Run classify_programs.py with virtual display (invisible)

# Start virtual display
export DISPLAY=:99
Xvfb :99 -screen 0 1920x1080x24 > /dev/null 2>&1 &
XVFB_PID=$!

# Wait for Xvfb to start
sleep 2

# Run the classification script with all arguments passed through
uv run python classify_programs.py "$@"

# Clean up
kill $XVFB_PID 2>/dev/null

