#!/bin/zsh
# Build "News Mood.app" in ~/Applications and put a shortcut on the Desktop.
# The app runs the code in this folder, so rerun this only if you move the folder.
set -euo pipefail

PROJECT="$(cd "$(dirname "$0")/.." && pwd)"
APP="$HOME/Applications/News Mood.app"

if [[ ! -x "$PROJECT/venv/bin/python" ]]; then
  echo "Setting up the Python environment..."
  python3 -m venv "$PROJECT/venv"
  "$PROJECT/venv/bin/pip" install -q -r "$PROJECT/requirements.txt"
fi

"$PROJECT/venv/bin/python" "$PROJECT/scripts/make_icon.py" > /dev/null

rm -rf "$APP"
mkdir -p "$APP/Contents/MacOS" "$APP/Contents/Resources"

# App icon (.icns) from the PNG.
ICONSET="$(mktemp -d)/AppIcon.iconset"
mkdir -p "$ICONSET"
for size in 16 32 128 256 512; do
  sips -z $size $size "$PROJECT/assets/icon.png" --out "$ICONSET/icon_${size}x${size}.png" > /dev/null
  sips -z $((size * 2)) $((size * 2)) "$PROJECT/assets/icon.png" --out "$ICONSET/icon_${size}x${size}@2x.png" > /dev/null
done
iconutil -c icns "$ICONSET" -o "$APP/Contents/Resources/AppIcon.icns"

cat > "$APP/Contents/Info.plist" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>CFBundleName</key><string>News Mood</string>
  <key>CFBundleDisplayName</key><string>News Mood</string>
  <key>CFBundleIdentifier</key><string>com.rithviksanum.newsmood</string>
  <key>CFBundleExecutable</key><string>NewsMood</string>
  <key>CFBundleIconFile</key><string>AppIcon</string>
  <key>CFBundlePackageType</key><string>APPL</string>
  <key>CFBundleShortVersionString</key><string>1.0</string>
  <key>LSMinimumSystemVersion</key><string>12.0</string>
  <key>NSHighResolutionCapable</key><true/>
</dict>
</plist>
PLIST

cat > "$APP/Contents/MacOS/NewsMood" <<LAUNCHER
#!/bin/zsh
mkdir -p "\$HOME/Library/Logs"
# Script-based apps can get launched under Rosetta (Intel emulation), which breaks
# the native packages in the venv, so force Apple Silicon mode when available.
if [[ "\$(sysctl -n hw.optional.arm64 2>/dev/null)" == "1" ]]; then
  exec arch -arm64 "$PROJECT/venv/bin/python" "$PROJECT/desktop.py" >> "\$HOME/Library/Logs/NewsMood.log" 2>&1
fi
exec "$PROJECT/venv/bin/python" "$PROJECT/desktop.py" >> "\$HOME/Library/Logs/NewsMood.log" 2>&1
LAUNCHER
chmod +x "$APP/Contents/MacOS/NewsMood"

ln -sfn "$APP" "$HOME/Desktop/News Mood.app"
touch "$APP"  # make Finder pick up the icon

echo "Built: $APP"
echo "Shortcut: ~/Desktop/News Mood.app"
