#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:$PATH"

PYTHON=""
for candidate in /opt/homebrew/bin/python3 /usr/local/bin/python3 /usr/bin/python3; do
  if [ -x "$candidate" ]; then
    PYTHON="$candidate"
    break
  fi
done

if [ -z "$PYTHON" ]; then
  /usr/bin/osascript -e 'display dialog "Python 3 was not found. Please install Python 3 from python.org and reopen the app." buttons {"OK"} default button "OK" with icon caution' || true
  exit 1
fi

exec "$PYTHON" app.py
