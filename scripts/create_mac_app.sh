#!/bin/bash

echo "Creating Mac Application Bundle..."

# Project root
PROJECT_ROOT="$( cd "$( dirname "${BASH_SOURCE[0]}" )/.." &> /dev/null && pwd )"
cd "$PROJECT_ROOT"

# App name
APP_NAME="AE Automation"
APP_DIR="$PROJECT_ROOT/$APP_NAME.app"

# Create app bundle structure
mkdir -p "$APP_DIR/Contents/MacOS"
mkdir -p "$APP_DIR/Contents/Resources"

# Create Info.plist
cat > "$APP_DIR/Contents/Info.plist" << 'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleName</key>
    <string>AE Automation</string>
    <key>CFBundleDisplayName</key>
    <string>After Effects Automation</string>
    <key>CFBundleIdentifier</key>
    <string>com.aeautomation.app</string>
    <key>CFBundleVersion</key>
    <string>1.0</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>CFBundleSignature</key>
    <string>????</string>
    <key>CFBundleExecutable</key>
    <string>launcher</string>
    <key>CFBundleIconFile</key>
    <string>AppIcon</string>
    <key>LSMinimumSystemVersion</key>
    <string>10.15</string>
    <key>LSUIElement</key>
    <false/>
    <key>NSHighResolutionCapable</key>
    <true/>
</dict>
</plist>
EOF

# Create launcher script
cat > "$APP_DIR/Contents/MacOS/launcher" << 'EOF'
#!/bin/bash

# Get the app bundle path
APP_BUNDLE="$(dirname "$(dirname "$0")")"
PROJECT_ROOT="$(dirname "$(dirname "$APP_BUNDLE")")"

# Change to project root
cd "$PROJECT_ROOT"

# Run the Python menu bar app
python3 scripts/mac_app/app_launcher.py
EOF

# Make launcher executable
chmod +x "$APP_DIR/Contents/MacOS/launcher"

# Copy icon if exists (create simple one if not)
if [ ! -f "scripts/mac_app/AppIcon.icns" ]; then
    echo "Creating simple app icon..."

    # Create a simple icon using sips (built-in Mac tool)
    # This creates a placeholder - you can replace with a real icon later
    mkdir -p /tmp/icon.iconset

    # Create 1024x1024 base image with text
    cat > /tmp/icon.svg << 'SVGEOF'
<?xml version="1.0" encoding="UTF-8"?>
<svg width="1024" height="1024" xmlns="http://www.w3.org/2000/svg">
  <rect width="1024" height="1024" rx="180" fill="#4A90E2"/>
  <text x="512" y="650" font-family="Arial" font-size="400" font-weight="bold" fill="white" text-anchor="middle">AE</text>
</svg>
SVGEOF

    # Convert to PNG (requires ImageMagick or just use the SVG)
    # For now, we'll create a simple colored rectangle
    # User can replace this with a real icon later

    # Create simple icon file
    cp /tmp/icon.svg "$APP_DIR/Contents/Resources/AppIcon.icns" 2>/dev/null || true
fi

echo "✅ Mac app created: $APP_DIR"
echo ""
echo "To use:"
echo "1. Double-click 'AE Automation.app' to start"
echo "2. Click the 🎬 icon in menu bar"
echo "3. Select 'Start Server'"
echo "4. Your browser will open automatically!"
echo ""
echo "To install (optional):"
echo "  Drag 'AE Automation.app' to your Applications folder"
