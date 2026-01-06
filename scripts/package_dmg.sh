#!/bin/bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
BUILD_DIR="$ROOT_DIR/build"
APP_NAME="Payroll Timesheet Validator"
APP_BUNDLE="$BUILD_DIR/$APP_NAME.app"
APP_CONTENTS="$APP_BUNDLE/Contents"
APP_RESOURCES="$APP_CONTENTS/Resources/app"
ICONSET_DIR="$BUILD_DIR/AppIcon.iconset"
ICON_ICNS="$APP_CONTENTS/Resources/AppIcon.icns"
DMG_STAGE="$BUILD_DIR/dmg"
DIST_DIR="$ROOT_DIR/dist"

rm -rf "$BUILD_DIR"
mkdir -p "$APP_CONTENTS/MacOS" "$APP_RESOURCES" "$DIST_DIR"

cat > "$APP_CONTENTS/Info.plist" <<'PLIST'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
  <dict>
    <key>CFBundleName</key>
    <string>Payroll Timesheet Validator</string>
    <key>CFBundleDisplayName</key>
    <string>Payroll Timesheet Validator</string>
    <key>CFBundleIdentifier</key>
    <string>com.payroll.validator</string>
    <key>CFBundleVersion</key>
    <string>1.0</string>
    <key>CFBundleShortVersionString</key>
    <string>1.0</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>CFBundleExecutable</key>
    <string>PayrollTimesheetValidator</string>
    <key>CFBundleIconFile</key>
    <string>AppIcon</string>
    <key>LSMinimumSystemVersion</key>
    <string>10.15</string>
    <key>NSHighResolutionCapable</key>
    <true/>
    <key>LSApplicationCategoryType</key>
    <string>public.app-category.business</string>
    <key>NSSupportsAutomaticGraphicsSwitching</key>
    <true/>
  </dict>
</plist>
PLIST

LAUNCHER_SRC="$BUILD_DIR/launcher.c"
cat > "$LAUNCHER_SRC" <<'CFILE'
#include <limits.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

static void show_dialog(const char *message) {
  char command[1024];
  snprintf(command, sizeof(command),
           "/usr/bin/osascript -e 'display dialog \"%s\" buttons {\"OK\"} "
           "default button \"OK\" with icon caution'",
           message);
  system(command);
}

int main(int argc, char *argv[]) {
  char exe_path[PATH_MAX];
  if (realpath(argv[0], exe_path) == NULL) {
    show_dialog("Unable to locate app resources.");
    return 1;
  }

  char *last = strrchr(exe_path, '/');
  if (!last) {
    show_dialog("Unable to locate app resources.");
    return 1;
  }
  *last = '\0';

  char app_dir[PATH_MAX];
  snprintf(app_dir, sizeof(app_dir), "%s/../Resources/app", exe_path);
  if (chdir(app_dir) != 0) {
    show_dialog("Unable to locate app resources.");
    return 1;
  }

  const char *candidates[] = {"/opt/homebrew/bin/python3",
                              "/usr/local/bin/python3", "/usr/bin/python3",
                              NULL};
  const char *python = NULL;
  for (int i = 0; candidates[i]; i++) {
    if (access(candidates[i], X_OK) == 0) {
      python = candidates[i];
      break;
    }
  }

  if (!python) {
    show_dialog("Python 3 was not found. Please install Python 3 from "
                "python.org and reopen the app.");
    return 1;
  }

  char *const args[] = {(char *)python, "app.py", NULL};
  execv(python, args);
  show_dialog("Failed to start the validator.");
  return 1;
}
CFILE

# Build Universal Binary for both Intel and Apple Silicon
clang -O2 -arch x86_64 -arch arm64 -mmacosx-version-min=10.15 \
  -o "$APP_CONTENTS/MacOS/PayrollTimesheetValidator" "$LAUNCHER_SRC"

python3 "$ROOT_DIR/scripts/make_icon.py"
BASE_ICON="$ROOT_DIR/assets/icon.png"
rm -rf "$ICONSET_DIR"
mkdir -p "$ICONSET_DIR"
sips -z 16 16 "$BASE_ICON" --out "$ICONSET_DIR/icon_16x16.png" >/dev/null
sips -z 32 32 "$BASE_ICON" --out "$ICONSET_DIR/icon_16x16@2x.png" >/dev/null
sips -z 32 32 "$BASE_ICON" --out "$ICONSET_DIR/icon_32x32.png" >/dev/null
sips -z 64 64 "$BASE_ICON" --out "$ICONSET_DIR/icon_32x32@2x.png" >/dev/null
sips -z 128 128 "$BASE_ICON" --out "$ICONSET_DIR/icon_128x128.png" >/dev/null
sips -z 256 256 "$BASE_ICON" --out "$ICONSET_DIR/icon_128x128@2x.png" >/dev/null
sips -z 256 256 "$BASE_ICON" --out "$ICONSET_DIR/icon_256x256.png" >/dev/null
sips -z 512 512 "$BASE_ICON" --out "$ICONSET_DIR/icon_256x256@2x.png" >/dev/null
sips -z 512 512 "$BASE_ICON" --out "$ICONSET_DIR/icon_512x512.png" >/dev/null
sips -z 1024 1024 "$BASE_ICON" --out "$ICONSET_DIR/icon_512x512@2x.png" >/dev/null
iconutil -c icns "$ICONSET_DIR" -o "$ICON_ICNS"

rsync -a --delete "$ROOT_DIR/app.py" "$APP_RESOURCES/"
rsync -a --delete "$ROOT_DIR/src" "$APP_RESOURCES/"

# Ad-hoc code sign the app bundle for macOS Sequoia compatibility
# This allows the app to run without being blocked by Gatekeeper
codesign --force --deep --sign - "$APP_BUNDLE"
echo "App bundle signed with ad-hoc signature"

rm -rf "$DMG_STAGE"
mkdir -p "$DMG_STAGE"
cp -R "$APP_BUNDLE" "$DMG_STAGE/"
ln -s /Applications "$DMG_STAGE/Applications"

DMG_PATH="$DIST_DIR/PayrollTimesheetValidator.dmg"
if [ -f "$DMG_PATH" ]; then
  rm "$DMG_PATH"
fi

# Remove quarantine attributes from the staged app
xattr -cr "$DMG_STAGE/$APP_NAME.app" 2>/dev/null || true

hdiutil create -volname "$APP_NAME" -srcfolder "$DMG_STAGE" -ov -format UDZO "$DMG_PATH"

# Sign the DMG itself for added compatibility
codesign --force --sign - "$DMG_PATH" 2>/dev/null || true

echo "DMG created at: $DMG_PATH"
echo ""
echo "Note for macOS Sequoia users:"
echo "  If the app is blocked, right-click and select 'Open' the first time,"
echo "  or run: xattr -cr '/Applications/$APP_NAME.app'"
