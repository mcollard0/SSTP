#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_DIR="${HOME}/.local/share/applications"
ICON_DIR_128="${HOME}/.local/share/icons/hicolor/128x128/apps"
ICON_DIR_SCALABLE="${HOME}/.local/share/icons/hicolor/scalable/apps"
PIXMAPS_DIR="${HOME}/.local/share/pixmaps"

mkdir -p "$APP_DIR" "$ICON_DIR_128" "$ICON_DIR_SCALABLE" "$PIXMAPS_DIR"
cp "$SCRIPT_DIR/assets/icon.png" "$ICON_DIR_128/sstp.png"
cp "$SCRIPT_DIR/assets/icon.png" "$ICON_DIR_SCALABLE/sstp.png"
cp "$SCRIPT_DIR/assets/icon.png" "$PIXMAPS_DIR/sstp.png"

# Generate desktop file with absolute path and StartupWMClass
cat << EOF > "$APP_DIR/sstp.desktop"
[Desktop Entry]
Name=Stuart Saves the Pomodoro
GenericName=Pomodoro Timer
Comment=Retro-futuristic laboratory Pomodoro desktop timer
Exec=${SCRIPT_DIR}/run.sh
Icon=${SCRIPT_DIR}/assets/icon.png
Terminal=false
Type=Application
Categories=Utility;Clock;AudioVideo;
StartupNotify=true
StartupWMClass=sstp
EOF

chmod +x "$APP_DIR/sstp.desktop"
update-desktop-database "$APP_DIR" 2>/dev/null || true
gtk-update-icon-cache -f -t "${HOME}/.local/share/icons/hicolor" 2>/dev/null || true
kbuildsycoca6 2>/dev/null || true

echo "Installed Stuart Saves the Pomodoro to application launcher!"
