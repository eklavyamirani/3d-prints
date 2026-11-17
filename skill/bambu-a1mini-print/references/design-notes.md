# Design notes: what this printer and filament actually did

Everything here was learned from real prints: mostly a seven-panel PETG splash
guard with 170 mm tall panels (`~/repositories/3d-prints/flair-splash-guard`), plus the
joints of a tablet rack (`~/repositories/3d-prints/tablet-rack`). Treat the numbers as
known-good starting points, not limits. It says nothing yet about snap fits,
round holes or threads; use general FDM practice there, tell the user it is
untested on this printer, and add what the print teaches to this file.

## Overhangs and bridges in PETG

- **Flat bridges sag.** A 44 mm flat bridge, 2.8 mm thick, printed but drooped
  on its underside. Fine where nobody looks, not for a mating surface.
- **45 degree slopes failed.** A 45 degree gable (two slabs meeting at a peak)
  curled upward as it printed, the nozzle caught the curl, and it knocked over
  the thin wall holding it. The slicer raised no warning.
- **60 degrees from horizontal printed clean with no support.** At 0.2 mm
  layers each layer rests about 96 percent on the one below. Use 60 degrees or
  steeper for unsupported roofs, arches and chamfers in PETG.
- **The slicer's overhang warning will not save you.** Bambu Studio's support
  threshold is an angle from horizontal, default 30 degrees, so 45 and 60
  degree slopes both pass silently. Judge overhangs yourself.
- **Supports are the fallback, not the plan.** PETG supports weld to PETG, tall
  thin support towers are their own failure risk, and they add time and
  material. Reshape the part first (gable, chamfer, teardrop hole, split and
  rotate). If supports are unavoidable: tree, build plate only.

## Tall, thin features

- A 3 mm thick, 32 mm tall, 50 mm wide free-standing leg got knocked over
  mid-print. Give any thin upright a foot: a 12 mm outward flange with a 4 mm
  gusset (an L section) held, both on the plate and in use.
- A 170 mm tall flat wall, 2.4 mm thick, bowed on the first test print. Made
  3.2 mm thick and printed solid (`wall_loops=4`, so no infill gap inside) with three 8 mm deep
  ribs on the back, it stood straight.
- Start ribs and stiffeners at z = 0. A rib that started 3 mm above the bed was
  flagged as a "floating cantilever" and needed a bridge for no reason.

## Bed layout and adhesion

- The bed is 180 mm but the usable, brim-friendly area is smaller. Two parts
  placed to "just fit" ended with first layers from y = 0.2 to y = 177 and the
  brim clipped off; the whole plate detached mid-print and became spaghetti.
  Keep every part at least 10 mm from the edge. One centred part per plate has
  been fully reliable, and for tall parts it also limits the loss if one fails.
- A 5 mm outer brim (`brim_type=outer_only`, `brim_width=5`) kept flanges and
  feet flat on textured PEI. "Outer" still means every outside contour, so the
  brim also grows inside open slots and jaws and must be trimmed there.
- Low parts went without a brim (`brim_type=no_brim`) on one plate: four flat
  rail halves 124 to 134 mm long x 18 x 4.8 mm, two 20 mm tall sleeves and a 12 mm
  coupon, PETG, 4 wall loops. All came off usable and the joints fitted; the
  user reported no lifting. One plate only, so not yet a rule.
- Tall parts (170 mm of a 180 mm Z) print fine; nothing special was needed.
- A 150 x 93 mm footprint, 48 mm tall (the tablet rack's side: an 8 mm frame
  lying flat with 40 mm ledges standing up from it), centred with
  `--no-arrange`, 3 wall loops and the 5 mm outer brim, in PETG: the user
  reported it "came out good" (2026-11-16). 3 h 10 min, 129 g.

## Fit and tolerances

- Dimensions taken from spec sheets are a guess until a part touches the real
  object. Print one piece and have the user test the fit before the full run;
  the first splash-guard test panel is what exposed the bowing and the sag.
- Tell the user which dimensions the fit depends on and ask them to measure
  those if they have not. Leave generous clearance where a part straddles or
  slides over something (the guard's saddle leaves about 5 mm over the pan rim).
- **0.15 mm per side is a good hand-push fit in this PETG** (tablet rack,
  `~/repositories/3d-prints/tablet-rack/ladder.py`, printed 2026-11-15, 0.2 mm layers,
  4 wall loops, no brim). The user called all of these "fits well":
  - a 14.0 x 4.8 mm tenon, printed flat, through a window 14.3 wide x 5.2
    tall (0.15 per side in the bed plane, 0.2 per side across the layers);
  - a round splice key (6 mm neck, 5 mm radius bulb) dropped into a socket
    offset 0.15 mm all round, both halves printed flat.
- A sleeve printed standing on its end (20 mm long, 4 mm walls, hole 18.3 x 5.2
  for an 18.0 x 4.8 rail) fitted too, but one of the two came out "a bit too
  snug, but manageable". Same model, same plate, so the difference is print
  variation, not the dimension. My guess, not checked: the first layers flare
  into the hole (elephant's foot). For a sleeve that must slide easily, go to
  0.2 mm per side or chamfer the hole's bottom edge.

## Known-good PETG settings

The user's COMGROW PETG Basic preset (240 C nozzle, 230 C first layer, 70 C
textured PEI) with the stock `0.20mm Standard @BBL A1M` process plus:
`wall_loops=4`, `brim_type=outer_only`, `brim_width=5`. A 135 x 84 x 170 mm
panel of about 118 cm3 takes 3.4 hours and 137 g with these.

## Symptom to fix

| What the photo shows | Likely cause | Fix that worked |
|---|---|---|
| Part or whole plate came off the bed | Parts at the bed edge, brim clipped | One centred part per plate, 5 mm brim |
| Underside of a bridge droops | Flat bridge too long for PETG | Replace with a 60 degree gable or arch |
| Spaghetti where a sloped roof should be, thin wall lying down | 45 degree slope curled and the nozzle hit it | 60 degree slope, foot on the thin wall |
| Tall wall bows | Wall too thin or hollow | 3.2 mm solid wall (4 loops) plus ribs |
| Slicer "floating cantilever" warning | Feature starts above the bed with nothing under it | Run it down to z = 0 |
