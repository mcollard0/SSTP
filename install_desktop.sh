#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_DIR="${HOME}/.local/share/applications"
ICON_DIR="${HOME}/.local/share/icons/hicolor/128x128/apps"

mkdir -p "$APP_DIR" "$ICON_DIR"
cp "$SCRIPT_DIR/assets/icon.png" "$ICON_DIR/sstp.png"

# Generate desktop file with absolute path
cat << EOF > "$APP_DIR/sstp.desktop"
[Desktop Entry]
Name=Stuart Saves the Pomodoro
GenericName=Pomodoro Timer
Comment=Retro-futuristic laboratory Pomodoro desktop timer
Exec=${SCRIPT_DIR}/run.sh
Icon=sstp
Terminal=false
Type=Application
Categories=Utility;Clock;
StartupNotify=true
EOF

chmod +x "$APP_DIR/sstp.desktop"
update-desktop-database "$APP_DIR" 2>/dev/null || true

echo "Installed Stuart Saves the Pomodoro to application launcher!"
