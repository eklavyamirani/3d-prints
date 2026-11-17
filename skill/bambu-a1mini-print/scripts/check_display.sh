#!/bin/zsh
# Exit 0 when a display is attached to this Mac, 1 when it is not.
# This Mac is a VM whose display detaches when the viewer window closes or
# sleeps. Without a display, Bambu Studio aborts at launch and full-screen
# computer use reports "CU display unavailable".
out=$(swift -e 'import CoreGraphics; let d = CGMainDisplayID(); let b = CGDisplayBounds(d); print(d, Int(b.width), Int(b.height))' 2>/dev/null)
read -r id w h <<< "$out"
if [[ -n "${w:-}" && "$w" -gt 0 ]]; then
  echo "display attached: ${w}x${h}"
  exit 0
fi
echo "NO DISPLAY attached (CGMainDisplayID=${id:-?}). Ask the user to bring the VM display back; the GUI cannot be driven until then."
exit 1
