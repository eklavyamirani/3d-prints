---
name: bambu-a1mini-print
description: Design, slice and send 3D prints to the user's Bambu Lab A1 mini from this Mac (a macOS VM) through Bambu Studio and the Bambu cloud. Use this whenever the user wants to 3D print something, design or model a printable part, make an STL or 3MF, slice a model, "send it to the printer", print another plate, reprint or tweak a failed part, or mentions Bambu Studio, the A1 mini, the AMS, PETG/PLA or a print that came out wrong. It holds the working toolchain (Python CAD, a CLI slicing script, the exact GUI send procedure) and the failures already paid for in plastic, so load it before writing CAD code, running Bambu Studio or touching the printer rather than rediscovering them.
---

# Printing on the Bambu Lab A1 mini from this Mac

This Mac is an Apple Virtualization VM with software OpenGL. The printer is
reachable only through the Bambu cloud: no LAN mode, no SD card. That shapes
everything below. The path that works is:

1. **Model** the part in Python (manifold3d + trimesh) and export STL.
2. **Show** the user a rendered preview and the key dimensions.
3. **Slice** with `scripts/slice_a1mini.py` (Bambu Studio CLI, no GUI needed).
4. **Send** one plate at a time through the Bambu Studio GUI with computer use.
5. **Wait for the user** to report the result, then iterate or send the next plate.

The printer makes real objects out of the user's filament and hours, so two
habits matter more than speed: print a small or single test piece before a full
run, and never start a print the user has not asked for in this conversation
with the bed confirmed clear.

## The setup

| Thing | Value |
|---|---|
| Printer | Bambu Lab A1 mini, 0.4 mm nozzle, 180 x 180 x 180 mm, AMS lite |
| Plate | Textured PEI |
| App | Bambu Studio 2.09 at `~/Applications/BambuStudio.app` (signed in to the user's account) |
| Default filament | `COMGROW PETG Basic @Bambu Lab A1 mini 0.4 nozzle`, a preset synced from the user's account |
| Other filament | `Bambu PLA Matte @BBL A1M` is also loaded in the AMS |
| Python | `python3` (mise) with manifold3d, trimesh, numpy, matplotlib |

AMS slots change when the user swaps spools. Do not assume a slot number: the
Send dialog shows the mapping (last seen: PETG in A3, PLA in A1). Ask which
filament to use if the user has not said; PETG has been the choice for anything
near heat or water.

## 1. Model

OpenSCAD is not installable here (its Homebrew cask is disabled). Write a small
parametric Python script instead: named dimensions at the top, `manifold3d` for
solids, `trimesh` to export STL. `scripts/cad_helpers.py` has the building
blocks (boxes, cylinders, extruded and rounded 2D profiles) and an `export()`
that writes the STL and checks it; its docstring is a working example, so read
that instead of exploring the manifold3d API. Keep the model script and its
STLs in the project folder so a reprint is one edit away.

Prints live in `~/repositories/3d-prints` (public on GitHub), one directory per
print: the model script, `stl/`, `sliced/` (only the `.gcode.3mf` files), a
README, and `final.png`, a render of the finished product. Add a new print as a
new directory there and list it in the root README. `skill/` in that repository
is a copy of this skill: after editing the skill, copy it over and commit. The
repository is public, so keep account details, serial numbers, screenshots of
the desktop and local paths out of it.

Model each part in the orientation it will print, sitting on z = 0. `export()`
reports size, volume, whether the mesh is watertight and how many separate
bodies it has; a printable part is watertight and one body.

Orientation decides most outcomes. Prefer the one with no overhangs (a part
that is a single 2D profile can simply lie on that profile), and put layers
along, not across, anything that has to flex or carry a bending load, because
layer lines are where prints split.

Read `references/design-notes.md` before settling a design. It records what
this printer and this PETG did with overhangs, bridges, thin tall features and
bed layout, including two designs that failed.

When a part must join to another, come apart, or be longer than the 180 mm bed,
read `references/joinery-notes.md` first. It is desk research, not print
results: which joints carry what, where to put a splice, clearances and
strengths other people measured.

Then show the user what they are about to print:

```bash
python3 ~/.claude/skills/bambu-a1mini-print/scripts/render_stl.py previews/part.png stl/part.stl
```

Add a second view when one angle hides something (`--elev 90 --azim -90` is a
true top view). Put the PNG in front of the user with the session's file-sending
tool if it has one (`SendUserFile`), since they often follow from another
device; otherwise save it in the project and link it. Include the bounding box,
any dimension they should check against the real object, and any choice you
made where the request was ambiguous.

## 2. Slice

```bash
python3 ~/.claude/skills/bambu-a1mini-print/scripts/slice_a1mini.py \
  --out sliced --name bracket --per-plate 1 \
  --set wall_loops=4 --set brim_type=outer_only --set brim_width=5 \
  stl/bracket.stl:2 stl/clip.stl
```

Run it with the command sandbox disabled; the CLI will not start inside it.
`--help` lists every option. What to know:

- `PART.stl:COUNT` repeats a part. A job that fits one plate needs nothing more
  and comes out as `NAME.gcode.3mf`. For anything bigger add `--per-plate N`,
  which writes one single-plate file per N parts (`NAME_plate_1.gcode.3mf`,
  ...): the send flow below handles one plate per file, and a multi-plate
  project cannot be sent plate by plate reliably here.
- The script prints time and grams per plate. Relay those to the user before
  sending; they decide whether a 7 hour plate is worth it.
- It warns when a part lands within 10 mm of the bed edge. Take that seriously:
  the slicer accepts such a layout silently, and it has cost a whole plate.
  Put fewer parts on the plate.
- Process overrides go in `--set key=value` using Bambu's preset key names. A
  misspelt key is ignored without an error, so confirm it in the footer of the
  raw gcode written beside the 3MF:
  `grep -hE "^; (wall_loops|brim_type) =" sliced/*.gcode`.
- The brim is a choice, not a default. Large flat-footed or tall parts want the
  5 mm outer brim; a small squat part may not need one, and an "outer" brim
  also fills open concavities such as a clip's jaw or a slotted hole, where it
  has to be picked out afterwards.
- The auto-arranger may turn a long part 90 degrees and park it off-centre: a
  150 x 107 mm part with a 5 mm brim landed 2.3 mm from the bed edge. When the
  edge warning fires for a single part that should fit, centre it on (90, 90)
  in the model and slice with `--no-arrange`, which keeps the STL's own XY.
- One filament per project. The CLI cannot slice a two-filament project. For a
  different material pass `--filament "<preset name>"`.
- Supports are off unless you turn them on
  (`--set enable_support=1 --set "support_type=tree(auto)" --set support_on_build_plate_only=1`).
  Prefer designing the overhang away; see the design notes for why.

If slicing misbehaves, `references/troubleshooting.md` has the known causes.

## 3. Send

Sending is a physical, hard-to-undo action. Do it only when the user has asked
for this plate in this conversation. "Send plate 2" covers plate 2, not plate 3.
Before each send, confirm the previous job is finished and the bed is clear:
the user saying so is enough, and the Device tab of a running Bambu Studio shows
"Finished" at 100% if you want to check.

The send goes through the GUI with full-screen computer use, because the cloud
upload has no CLI and the app's dialogs cannot be driven in the background.
Follow `references/send-print.md` step by step: it has the launch script, the
dialogs in the order they appear, what each should show, and the quirks of
clicking in this app. The short version:

```bash
~/.claude/skills/bambu-a1mini-print/scripts/open_in_bambu.sh "$PWD/sliced/bracket_plate_1.gcode.3mf"
```

then OK on "Customized Preset", Cancel on "Configuration update" if it appears,
Slice plate, Print plate, check the Send dialog, Send, and confirm the job on
the Device tab.

If the display is detached (the launch script says so), stop and ask the user to
bring the VM display back. Nothing else gets around it.

## 4. After the print

Ask for a photo when the user reports a problem, and look at where it failed
before changing anything: a part that came off the bed, a sagging bridge and a
knocked-over thin wall need different fixes, and `references/design-notes.md`
maps symptoms to the fixes that worked. Change one thing, reprint the smallest
piece that proves it, then commit to the full run. Keep already-printed good
parts in the count so the user does not reprint them.

Close each send with: what was sent, print time, grams, estimated finish time,
and which plates remain.

## Keeping this skill current

When a session learns something new about this printer, this Mac or a filament
(a new failure, a fix, a setting that mattered, a changed AMS layout), add it to
the matching reference file here so the next session starts from it.
