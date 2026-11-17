#!/bin/zsh
# Open one .3mf in a fresh Bambu Studio GUI instance, ready to be driven by
# computer use. Usage: open_in_bambu.sh /abs/path/file.gcode.3mf
#
# Each step exists because of a failure seen on this Mac (an Apple
# Virtualization VM with software OpenGL):
#  - no display attached  -> the app aborts at launch, so refuse to start
#  - a running instance   -> `open` does not load the new file into it; quit it
#  - leftover restore dir -> the app shows a "restore project" panel that computer
#                            use cannot click
#  - first launch after a quit often crashes -> retry once
# Run outside the command sandbox.
set -u
FILE="${1:?usage: open_in_bambu.sh FILE.3mf}"
[[ -f "$FILE" ]] || { echo "no such file: $FILE"; exit 2; }
HERE="${0:A:h}"

"$HERE/check_display.sh" || exit 3

pkill -x BambuStudio 2>/dev/null
sleep 3
rm -rf "$(getconf DARWIN_USER_TEMP_DIR)bamboo_model"/*(N)

for attempt in 1 2; do
  open -a BambuStudio "$FILE"
  sleep 20
  if pgrep -x BambuStudio >/dev/null; then
    echo "Bambu Studio is running (pid $(pgrep -x BambuStudio)) with ${FILE:t}"
    echo "Next: take a screenshot; expect the 'Customized Preset' dialog."
    exit 0
  fi
  echo "launch attempt $attempt died; retrying"
done
echo "Bambu Studio would not stay up. Check the display and ~/Library/Logs/DiagnosticReports."
exit 1
