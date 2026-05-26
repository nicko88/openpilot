#!/usr/bin/env bash
# Fail if sunnypilot/viz/web/dist is stale relative to its src tree.
# spviz daemon serves dist/ at /, so a stale build means the phone HUD
# is out of sync with committed source.

set -u

WEB_DIR="sunnypilot/viz/web"
DIST_INDEX="$WEB_DIR/dist/index.html"
SRC_DIR="$WEB_DIR/src"
ENTRY_HTML="$WEB_DIR/index.html"

# Skip when scaffold absent (allows partial checkouts / non-spviz branches).
[ -d "$SRC_DIR" ] || exit 0
[ -f "$ENTRY_HTML" ] || exit 0

if [ ! -f "$DIST_INDEX" ]; then
  echo "spviz: $DIST_INDEX missing. Run: (cd $WEB_DIR && npm install && npm run build) and commit dist/."
  exit 1
fi

NEWER=$(find "$SRC_DIR" "$ENTRY_HTML" -newer "$DIST_INDEX" -type f 2>/dev/null)
if [ -n "$NEWER" ]; then
  echo "spviz: dist/ is stale. The following sources are newer than $DIST_INDEX:"
  echo "$NEWER" | sed 's/^/  /'
  echo "Run: (cd $WEB_DIR && npm run build) and commit dist/."
  exit 1
fi

exit 0
