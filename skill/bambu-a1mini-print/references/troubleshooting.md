# Troubleshooting Bambu Studio on this Mac

This Mac is an Apple Virtualization VM (VirtualMac2,1, paravirtual GPU,
software OpenGL only). Most oddities trace back to that.

## The display detaches

The VM's display goes away when the viewer window is closed or sleeps.

- Check: `scripts/check_display.sh` (exit 1 when detached). Underneath,
  `CGMainDisplayID()` returns 0 with zero bounds, and
  `system_profiler SPDisplaysDataType -json` returns an empty list.
- Effects: full-screen computer use reports "CU display unavailable" or
  "Screenshot capture returned nil"; Bambu Studio launched meanwhile aborts
  (SIGABRT in GLRendererFloat `glsAssignDrawable`) or never gets a window.
- An instance that was already running keeps running, and its windows can still
  be captured with the background `app_screenshot`, but it cannot be clicked.
- Only the user can bring the display back. Ask, then continue. Do not read a
  launch crash as an app problem until the display check passes.
- Seen 2026-11-15: the same `glsAssignDrawable` abort four launches in a row
  while the display check passed (1920x1080) and the two graphics keys below
  were intact. The VM screen was locked: once the user unlocked it the app
  launched (on the script's second attempt) and the send went through. So a
  locked screen passes the display check but still kills the launch. After one
  failed run of the script, ask the user to unlock the VM screen.

## Bambu Studio crashes drawing the sliced preview

Fixed on 2026-11-07 in `~/Library/Application Support/BambuStudio/BambuStudio.conf`:
`"msaa_type": "Disabled"` and `"use_retina_opengl": false` (in the `app`
section). With those, slicing, Preview and the cloud Print dialog all work. The
stock file is kept beside it as `BambuStudio.conf.bak-before-msaa-change`.

If the crash returns after an app update, check those two keys first: an update
may have reset them. Edit the file only while the app is closed, since the app
rewrites it on quit.

Do not set `use_legacy_opengl`: the app then aborts at startup.

## CLI slicing

- **No `result.json`, or the CLI exits at once**: it ran inside the command
  sandbox. Rerun with the sandbox disabled.
- **"Failed to create GLFW window" in the log**: expected in a CLI run and
  harmless; the script hides it.
- **Speeds or temperatures look wrong**: a profile was passed unflattened. The
  CLI does not resolve `inherits`; always go through `slice_a1mini.py`.
- **"could not found group_nozzle_info"**: the project had two filaments. Slice
  with one.
- **Preset not found**: system presets are in
  `~/Applications/BambuStudio.app/Contents/Resources/profiles/BBL/{machine,process,filament}`;
  presets synced from the user's account are under
  `~/Library/Application Support/BambuStudio/user/<id>/`. Account presets lack a
  `type` key, which the script fills in. If the user made a new filament preset,
  the app has to have been opened once since, so it syncs to disk.
- **GUI drops the overrides on re-slice**: the process preset was not renamed.
  The script names it `<process> - <name>` and marks it `from: User`; the left
  panel in the GUI should show that name.
- **3MF opens with broken or missing thumbnails**: `fix_3mf_thumbnails.py` did
  not run (the script runs it automatically). To look at what it drew:
  `unzip -p FILE.gcode.3mf Metadata/plate_1.png > /tmp/p.png`. A thumbnail
  showing only the empty bed was a draw-order bug, fixed 2026-11-10.

## GUI behaviour to plan around

- `open -a BambuStudio file` with an instance already running does not load the
  file, and in some cases spawns a second instance. Always quit first; the
  launch script does.
- The first launch after a quit often dies within seconds. Launch again.
- A leftover folder in `$(getconf DARWIN_USER_TEMP_DIR)bamboo_model` makes the
  app offer to restore a project in a panel computer use cannot reach. The
  launch script empties it.
- Exporting or saving from the GUI is not possible through computer use (the
  Save panel is another process). Produce every file with the CLI script.
- There is no way to cancel or pause a running print from here except the
  Device tab's stop button, and stopping is the user's decision.
