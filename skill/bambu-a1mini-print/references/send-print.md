# Sending a sliced plate through the Bambu Studio GUI

Verified on Bambu Studio 2.09.01.70, five sends in a row. The whole thing takes
about two minutes when the display is attached.

## Before you start

- The user asked for this plate, and the bed is clear.
- The file is a single-plate `.gcode.3mf` from `slice_a1mini.py`.
- Computer use: request access to BambuStudio, then full-screen control. The
  background `app_*` tools can screenshot Bambu windows (useful to peek at the
  Device tab) but their clicks and keys are refused on Bambu's dialogs ("belongs
  to a different process"), so the send needs full-screen control.

## Launch

```bash
~/.claude/skills/bambu-a1mini-print/scripts/open_in_bambu.sh /abs/path/NAME_plate_1.gcode.3mf
```

Run it outside the sandbox. It checks the display, quits any running instance
(a running instance does not load a new file from `open`), clears the restore
folder (otherwise a "restore project" panel appears that cannot be clicked),
opens the file and retries once, because the first launch after a quit often
crashes.

## Clicking in this app

- Take a fresh full-screen screenshot, in its own batch, right before every
  batch that clicks. Otherwise the click fails with "Could not verify which
  document this window is editing". If it still fails, wait 3 seconds, take
  another screenshot and retry; it goes through on the second try.
- Use clicks only. Keyboard input to the main window is refused.
- Find buttons in the screenshot each time. The window is not always the same
  size: both a 1389x868 and a 1456x819 coordinate frame have been seen.
- Do not touch macOS system alerts or Bambu's Open/Save/Restore panels; they
  belong to other processes and the user has declined access to them.

## The dialogs, in order

1. **"Customized Preset"** appears over the main window ("The 3mf has following
   customized filament or printer presets..."). It is expected: the project
   carries the user's own filament preset. Click **OK**. The plate then loads
   and the title bar shows the file name.

2. **"Configuration update"** may appear a few seconds later or right after the
   first click ("A new configuration package available, Do you want to install
   it?"). Click **Cancel**: installing changes system presets mid-project, and
   that is the user's call. Mention it in the report so they can accept it
   themselves.

3. **Slice plate** (green button, top right). Even though the file is already
   sliced, the GUI needs its own slice before Print is enabled. Wait about 50
   seconds. Success looks like the Preview tab with a "Slicing Result" panel
   showing filament grams and total time. Check they match the CLI estimate and
   that the process preset on the left ends with your `--name`. A slicer warning
   banner here (for example "floating cantilever") is worth reading and
   reporting before sending.

4. **Print plate** (top right, next to Slice). The "Send print job" dialog
   opens after a few seconds. Verify before sending:
   - the file name is the plate you mean
   - Printer: A1 mini, plate type Textured PEI
   - Filament: the chip shows the right material mapped to an AMS slot (for
     example PETG -> A3). If it maps to the wrong spool or shows a warning,
     stop and ask the user.
   - Auto Bed Leveling: On. Flow Dynamics Calibration: On. Timelapse: Off.

5. **Send**. Wait about 40 seconds. The app switches to the **Device** tab and
   shows the job under Printing Progress: file name, 0%, "Heatbed preheating",
   total time and "Estimated finish time". That screen is the proof the job
   reached the printer; report the finish time from it.

6. Release full-screen control.

## When it goes wrong

- **Screenshot says "CU display unavailable" / capture returned nil**: the VM
  display detached. Stop, tell the user the plate is loaded but not sent, and
  ask them to bring the display back. An instance that was already running
  survives and can continue once the display returns; an instance launched
  without a display has no window and must be relaunched.
- **App vanished after launch**: run the launch script again. If it keeps
  dying, check the display first, then `references/troubleshooting.md`.
- **Print plate stays grey**: the slice did not finish or failed; look at the
  bottom-left notification area in a screenshot.
- **Send dialog shows the printer busy or offline**: do not retry blindly. The
  previous job may still be running, or the printer is off. Tell the user.
