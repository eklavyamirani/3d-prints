#!/usr/bin/env python3
"""
Ladder tablet rack: tablets lie flat on ledges at both sides, nothing hangs.

Each side is a closed ladder frame (a post at the front, a post at the back,
one rung per level) with a ledge standing along every rung. The posts sit
outside the tablets' width, so a tablet slides in from the front between them
and rests on a ledge at each edge. That needs a rack wider than the print bed,
so each cross rail is two halves spliced in the middle: a round key takes the
push and pull, and a sleeve slid over the key stops the halves lifting apart.

    python3 ladder.py          # writes stl/ (parts and print plates) and previews/

Side profile coordinates: x runs from the back to the front, y is up. The side
prints lying on its outer face: the ladder is the first 8 mm, the ledges rise
from it. One part serves both sides (it is the same front to back).
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "../skill/bambu-a1mini-print/scripts"))
sys.path.insert(0, os.path.expanduser("~/.claude/skills/bambu-a1mini-print/scripts"))
import manifold3d
from manifold3d import CrossSection

from cad_helpers import SEGMENTS, box, export, prism_xy, profile
from stack import plate
from tower import (BASE, FIT, RAIL_BODY_W, RAIL_T, RAIL_W, WIN_H, WIN_W, as_used, closing, opening,
                   rect, window)

# ---- dimensions (mm) --------------------------------------------------------
LEVELS = 4
DEPTH = 150.0       # front to back (150 + a 5 mm brim each end = the 160 mm safe bed area)
POST = 12.0         # post width, front to back
PANEL_T = 8.0       # ladder thickness (posts and rungs)
LEDGE = 40.0        # how far the ledges reach in: the mini in its case (198 across) pushed against
                    # one post still has 7 mm on the far ledge
LEDGE_T = 6.0       # ledge thickness (the bottom one is BASE thick, it houses the rails)
SLOT_H = 18.0       # clear height between a ledge and the one above (thickest cased device measured: 14.5)
TOP = 10.0          # post height above the top ledge
CLEAR_W = 231.0     # clear width between the posts (12.9 Pro in its folio with the pencil: 225.3 measured)
RAIL_X = [30.0, 120.0]
KEY_NECK, KEY_R = 6.0, 5.0        # splice key: neck width, bulb radius
KEY_FIT = 0.15
SLEEVE_L, SLEEVE_WALL = 20.0, 4.0

# Devices for the mock-up, bottom to top: name, thickness, width across the rack, depth.
# Sizes are in their folio cases, from retailer listings (which disagree by a few mm): estimates.
DEVICES = [("ipad-pro-12.9-m1", 14.5, 225.3, 285.0), ("ipad-pro-13-m4", 12.0, 220.0, 285.0),
           ("kindle-scribe", 12.0, 205.0, 234.0), ("ipad-mini-6", 12.0, 198.0, 140.0)]

PITCH = SLOT_H + LEDGE_T
LEVEL_Y = [BASE + i * PITCH for i in range(LEVELS)]
HEIGHT = LEVEL_Y[-1] + TOP
WIDTH = CLEAR_W + 2 * PANEL_T
TENON = PANEL_T + LEDGE             # a rail end goes right through ladder and ledge
MID = WIDTH / 2
J = manifold3d.JoinType.Round


def rungs(inset=0.0):
    cs = rect(inset, DEPTH - inset, 0, BASE)
    for y in LEVEL_Y[1:]:
        cs = cs + rect(inset, DEPTH - inset, y - LEDGE_T, y)
    return cs


def windows():
    cs = window(RAIL_X[0])
    for xc in RAIL_X[1:]:
        cs = cs + window(xc)
    return cs


def panel_profile():
    cs = rungs() + rect(0, POST, 0, HEIGHT) + rect(DEPTH - POST, DEPTH, 0, HEIGHT)
    return (closing(opening(cs, 2.0), 3.0) - windows()).simplify(0.005)


def ledge_profile():
    """The ledges stop 1 mm short of the ladder's ends, so their rounded corners
    never share an arc with the ladder's (that left slivers in the mesh)."""
    return opening(rungs(1.0), 2.0).simplify(0.005)


def side():
    panel = panel_profile()          # cut the ledges out of one full-height prism: a clean mesh
    return prism_xy(panel, 0, TENON) - prism_xy(panel.offset(0.5, J, 2.0, SEGMENTS) - ledge_profile(), PANEL_T, TENON + 1)


def rail_outline():
    """Plan view of a whole rail, x along it: a tenon at each end, a wider body
    between the ledges so each side seats on a shoulder."""
    hw, hb, lead = RAIL_W / 2, RAIL_BODY_W / 2, 2.0
    half = [(0, hw - 0.6), (lead, hw), (TENON, hw), (TENON, hb),
            (WIDTH - TENON, hb), (WIDTH - TENON, hw), (WIDTH - lead, hw), (WIDTH, hw - 0.6)]
    return profile(half + [(x, -y) for x, y in reversed(half)])


def key():
    """Round-headed key on the end of one half (round, because sharp dovetail
    corners are where printed joints crack)."""
    return rect(MID - 1, MID + 0.5 + KEY_R, -KEY_NECK / 2, KEY_NECK / 2) \
        + CrossSection.circle(KEY_R, SEGMENTS).translate((MID + 0.5 + KEY_R, 0))


def rail_halves():
    whole = rail_outline()
    a = (whole ^ rect(-1, MID, -20, 20)) + key()
    b = (whole ^ rect(MID, WIDTH + 1, -20, 20)) - key().offset(KEY_FIT, J, 2.0, SEGMENTS)
    return a.simplify(0.005), b.simplify(0.005)


def sleeve_profile():
    w = RAIL_BODY_W + 2 * FIT + 2 * SLEEVE_WALL
    hole = rect(SLEEVE_WALL, w - SLEEVE_WALL, BASE / 2 - WIN_H / 2, BASE / 2 + WIN_H / 2)
    return opening(rect(0, w, 0, BASE), 1.5) - hole


def coupon_profile():
    return rect(0, WIN_W + 12, 0, BASE) - window((WIN_W + 12) / 2)


if __name__ == "__main__":
    here = os.path.dirname(os.path.abspath(__file__))
    out = lambda *p: os.path.join(here, *p)
    part = side()
    a, b = (prism_xy(cs, 0, RAIL_T) for cs in rail_halves())
    sleeve = prism_xy(sleeve_profile(), 0, SLEEVE_L)
    coupon = prism_xy(coupon_profile(), 0, 12.0)
    print(f"rack: {WIDTH:.0f} wide x {DEPTH:.0f} deep x {HEIGHT:.0f} tall; ledges at "
          f"{[round(y, 1) for y in LEVEL_Y]}, {SLOT_H} clear, {CLEAR_W} between posts, "
          f"{CLEAR_W - 2 * LEDGE:.0f} between ledge tips")
    export(part.translate([90 - DEPTH / 2, 90 - HEIGHT / 2, 0]), out("stl/side.stl"))
    export(a, out("stl/rail_half_key.stl"))
    export(b, out("stl/rail_half_socket.stl"))
    export(sleeve, out("stl/sleeve.stl"))
    export(plate([[a], [a], [b], [b], [sleeve, sleeve, coupon]]), out("stl/plate1_rails_sleeves_coupon.stl"))

    # Mock-up: both sides, both rails with their sleeves, and the devices.
    left = as_used(part)
    frame = left + left.mirror([1, 0, 0]).translate([WIDTH, 0, 0])
    z0 = BASE / 2 - RAIL_T / 2
    sw = RAIL_BODY_W + 2 * FIT + 2 * SLEEVE_WALL
    for xc in RAIL_X:
        frame = frame + a.translate([0, xc, z0]) + b.translate([0, xc, z0]) \
              + as_used(sleeve, MID + 5.5 - SLEEVE_L / 2).translate([0, xc - sw / 2, 0])
    export(frame, out("previews/mock_rack.stl"))
    for (name, t, across, depth), y in zip(DEVICES, LEVEL_Y):
        export(box(MID - across / 2, MID + across / 2, DEPTH / 2 - depth / 2, DEPTH / 2 + depth / 2,
                   y + 0.01, y + t), out(f"previews/mock_{name}.stl"))
