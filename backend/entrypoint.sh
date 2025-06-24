#!/usr/bin/env bash
set -euo pipefail

# Generate nginx config
echo "[$(date +'%Y-%m-%dT%H:%M:%S%z')] Generating nginx.conf..."
envsubst '${PORT}' < /etc/nginx/nginx.conf.template > /etc/nginx/nginx.conf

# X11 Configuration
export DISPLAY=:99
export XAUTHORITY=/tmp/.Xauth
rm -f /tmp/.X11-unix/X99 2>/dev/null || true

# Start Xvfb
echo "Starting Xvfb..."
Xvfb $DISPLAY -screen 0 1920x1080x24 -ac +extension GLX +render -noreset -auth $XAUTHORITY &

# Wait for X to be ready
echo "Waiting for X server..."
while [ ! -e /tmp/.X11-unix/X99 ]; do sleep 0.1; done
until xdpyinfo -display $DISPLAY >/dev/null 2>&1; do
    echo "X server not ready yet..."
    sleep 0.5
done

# Configure X authority
echo "Configuring X auth..."
touch $XAUTHORITY
xauth add $DISPLAY . "$(mcookie)"
xauth generate $DISPLAY . trusted

# Start window manager
echo "Starting fluxbox..."
fluxbox &

# Start VNC server
echo "Starting x11vnc..."
x11vnc -forever -shared -nopw -display $DISPLAY -rfbport 5900 -auth $XAUTHORITY &

# Optional: Start noVNC (only if installed)
# echo "Starting noVNC..."
# /opt/novnc/utils/novnc_proxy --vnc localhost:5900 --listen 10000 --heartbeat 10 &

# Start Nginx
echo "Starting Nginx..."
nginx

# Start Flask app via Gunicorn (must point to correct module)
echo "Starting Gunicorn..."
exec gunicorn -w 4 -b 0.0.0.0:5000 linkedin_bot:app
