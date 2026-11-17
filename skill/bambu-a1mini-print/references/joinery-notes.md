# Joinery notes: joining printed parts, and going past the 180 mm bed

Desk research from November 2026, done while designing a tablet rack
(`~/repositories/3d-prints/tablet-rack`). Treat the numbers as other people's results;
when a joint from this file gets printed, move what it taught into
`design-notes.md`. Printed so far (2026-11-15): the rack's through tenon, round
splice key and sleeve, for fit only; the fits are in `design-notes.md` under
"Fit and tolerances". None of it has carried a load yet.

## The three findings that changed the design

1. **A joint never makes a member stronger; it lets you change the structure.**
   The rack's problem was long cantilevered arms. No joint fixes an arm, but a
   splice let the rack be wider than the bed, and then every shelf could be
   held at both ends. Ask first whether a joint can remove the weak shape
   (cantilever to supported span, open frame to closed frame).
2. **A printed joint is the weak point, so put it where the load is small.**
   In a PLA tensile study the best interlocking joint kept about 16% of the
   strength of an unjoined bar. A dovetail at the root of a loaded arm is the
   worst place for one. A splice in a rail that only holds two sides apart is
   a good place.
3. **Every simple joint leaves one direction free.** Woodworkers close it with
   a second element: a peg, a wedge, or a second joint at right angles. Decide
   which direction is free and what closes it (the rack uses a sleeve over the
   splice, and the rails' own windows).

## Joints from woodworking, and how they translate

| Joint | What it does in wood | In a print |
|---|---|---|
| Housing (dado) | Shelf end sits in a groove; the standard shelf joint, supported along its whole end | A ledge or groove along the side wall. Simple and strong because the reach is short |
| Sliding dovetail | Like a housing but cannot pull out sideways; fussy to fit | Prints well as a 2D profile. Give it a 1 to 2 degree taper so it tightens as it slides. Leaves the sliding direction free |
| Through mortise and tenon | Strongest frame joint, more so wedged or pegged | A tenon through a window. Friction only unless wedged, pegged or given a snap hook |
| Tusk tenon (hana-sen) | Tenon sticks out and a wedge through it pulls the joint tight; gravity keeps the wedge in | Knock-down and self-tightening, but the tenon and wedge stick out of the side |
| Wedged notch (watari-ago) | Rail notched over the post, wedge driven in beside it | Good against racking; the wedge is held by friction only |
| Drop-down half dovetail (kata-sage-ari) | Clean look, nothing protrudes | Reported as much weaker against racking: little contact area |
| Hooked scarf (okkake daisen tsugi, kanawa tsugi) | Splices two beams end to end, locked by pegs or a wedge | Printed and tested on 4.8 mm square PETG/PLA bars: broke at 160 to 210 N in tension. OpenSCAD files exist (Ueda Lab) |
| Jigsaw or "C" key | Not traditional | The best performer in the printed-joint study; easy as a 2D profile, drops in from above, free in that direction |

## Measured or stated numbers

- **Joint strength (PLA, Prusa MK4, 0.2 mm layers, 100% infill, 135 samples):**
  a round "C" key with a 5 mm neck reached 7 MPa; a solid bar reached 44.4 MPa.
  Dovetail and T shapes were weaker. A 7 mm neck was weaker than the 5 mm one.
  Read from press coverage (All3DP), not the paper (Results in Engineering,
  University of Galway and ATU). A search summary gave 0.05 mm clearance on
  the interlocking features; unconfirmed.
- **Clearance:** Markforged uses 0.08 mm per wall for a sliding fit on its own
  machine, 0.15 mm where a face sat on support. The rack's first print used
  0.15 mm per side in PETG and the user found it a good fit.
- **Across the layers** a print is roughly half as strong as along them
  (figures of 40 to 60% loss are quoted widely, sources weak).
- **Gussets** only help if they run at least half the arm's length; a short one
  moves the stress to its own tip. Sharp inside corners are the usual place a
  bracket cracks, so fillet them.

## Orientation rules that apply to joints

- Print hooks, teeth, snap arms and keys lying on their side, so no layer
  boundary crosses the part that bends or pulls.
- A tongue-and-groove printed so the groove roof overhangs comes out
  inaccurate; a sideways V or a dovetail profile on the bed does not.
- A snap hook that must stand upright is better printed as a separate flat
  piece that slides into a dovetail slot.

## Splitting a part longer than the bed

- Put the cut where bending is lowest, never at the root of an arm or the
  middle of a loaded span.
- Flat cut plus pins or dowels and glue is the usual method. Printed pins let
  both halves lie flat. Superglue holds PLA but is reported not to hold PETG.
- Use an interlocking key where the joint must carry pull without glue, and
  bolts where it must be strong and come apart.
- Fallback if a cantilever cannot be avoided: a steel rod or square bar pressed
  or epoxied into the arm. Square bar also resists twisting. Carbon rod may
  pull loose from PETG.

## Creep

Sources disagree on PLA versus PETG at room temperature and none had a
controlled long-term sag test. Keep sustained stress low (the rack is under
1 MPa) and prefer short reaches over deep sections.

## What the tablet rack does with this

`ladder.py`: two closed side frames with 40 mm ledges (housing-joint idea),
tied by two flat rails that pass through windows in the feet (through tenons,
friction fit). Each rail is two halves joined in the middle by a round key
(takes push and pull), with a sleeve slid over the key (stops the halves
lifting apart). The splice sits on the desk where almost no load passes.

## Sources

- https://all3dp.com/4/ditch-the-glue-researchers-find-c-shaped-joints-outperform-dovetails-in-pla-prints/
- https://markforged.com/resources/blog/joinery-onyx
- https://www.uedalab.jp/3dprint/ (paper: engrXiv 10.31224/2338)
- https://siraya.tech/blogs/news/3d-print-joints
- https://www.digikey.com/en/maker/blogs/2024/how-to-split-and-join-large-3d-prints
- https://www.bigsandwoodworking.com/collapsible-shelving-joinery-considerations/
- https://finewoodworking.com/forum/dado-or-sliding-dovetail
- https://www.woodweb.com/knowledge_base/Sliding_Dovetails_for_Bookshelves.html
- https://www.core77.com/posts/66446/
- https://hackaday.com/2025/01/24/laser-cut-metal-endoskeleton-beefs-up-3d-prints

Some pages fail in a plain fetch (Markforged returns 403, the old Waseda
address is dead, All3DP hides the article body). The connected Edge browser
reads the first two.
