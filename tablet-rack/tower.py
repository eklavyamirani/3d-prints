#!/usr/bin/env python3
"""
Stacked tablet rack: tablets lie flat, one above another.

Two identical side frames ("combs": a spine, a foot and cantilevered arms) are
joined by two flat cross rails that push through windows in the feet. Each comb
is one 2D profile printed lying flat, so the arms carry their load along the
layers and nothing overhangs.

    python3 tower.py           # writes stl/ (printable) and previews/ (mock-up)

Profile coordinates: x runs from the back of the spine to the open front, y is up.
"""
import math
import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "../skill/bambu-a1mini-print/scripts"))
sys.path.insert(0, os.path.expanduser("~/.claude/skills/bambu-a1mini-print/scripts"))
import manifold3d
from cad_helpers import SEGMENTS, box, export, prism_xy, profile

# ---- dimensions (mm) --------------------------------------------------------
LEVELS = 4          # tablets: one on the foot, the rest on arms (top one is open above)
SLOT_H = 13.0       # clear height above a tablet's shelf, at the spine (tightest point)
REACH = 138.0       # arm length in front of the spine
SPINE = 12.0        # spine thickness
BASE = 11.0         # foot thickness
ARM_ROOT, ARM_TIP = 16.0, 6.0     # arm thickness at the spine / at its tip (deep root = stiff arm)
TILT = 1.5          # degrees the arms rise toward the front (hides sag, keeps tablets back)
BACKSTOP = 9.0      # spine height above the top arm
COMB_T = 20.0       # comb thickness (its print height)
GAP = 110.0         # clear distance between the two combs
R_OUT, R_IN = 2.0, 3.0            # outer corner rounding / fillets at the arm roots

RAIL_W, RAIL_T = 14.0, 4.8        # rail tenon section (4.8 = 24 layers of 0.2)
RAIL_BODY_W = 18.0                # rail width between the combs (makes the shoulders)
FIT = 0.15                        # clearance per side between tenon and window
RAIL_X = [32.0, 118.0]            # window centres along the foot

# Devices for the mock-up, bottom to top: name, thickness, width across the rack, depth.
DEVICES = [("ipad-pro-12.9-m1", 6.4, 280.6, 214.9), ("ipad-pro-13-m4", 5.1, 281.6, 215.5),
           ("kindle-scribe", 5.8, 229.0, 196.0), ("ipad-mini-6", 6.3, 195.4, 134.8)]

J = manifold3d.JoinType.Round
TH = math.radians(TILT)
SIN, COS = math.sin(TH), math.cos(TH)
PITCH = SLOT_H + ARM_ROOT
LEVEL_Y = [BASE + i * PITCH for i in range(LEVELS)]      # shelf height at the spine face
WIN_W, WIN_H = RAIL_W + 2 * FIT, RAIL_T + 2 * 0.2


def opening(cs, r):   # round convex corners
    return cs.offset(-r, J, 2.0, SEGMENTS).offset(r, J, 2.0, SEGMENTS)


def closing(cs, r):   # fillet concave corners
    return cs.offset(r, J, 2.0, SEGMENTS).offset(-r, J, 2.0, SEGMENTS)


def rect(x0, x1, y0, y1):
    return profile([(x0, y0), (x1, y0), (x1, y1), (x0, y1)])


def window(xc):
    return rect(xc - WIN_W / 2, xc + WIN_W / 2, BASE / 2 - WIN_H / 2, BASE / 2 + WIN_H / 2)


def comb_profile():
    length = SPINE + REACH
    top = LEVEL_Y[-1] + BACKSTOP
    cs = rect(0, SPINE, 0, top) + rect(0, length, 0, BASE)
    for y in LEVEL_Y[1:]:
        tip = (SPINE + REACH * COS, y + REACH * SIN)
        cs = cs + profile([(SPINE - 2, y - ARM_ROOT), (SPINE, y - ARM_ROOT),
                           (tip[0] + ARM_TIP * SIN, tip[1] - ARM_TIP * COS), tip, (SPINE - 2, y)])
    cs = closing(opening(cs, R_OUT), R_IN)
    for xc in RAIL_X:
        cs = cs - window(xc)
    return cs.simplify(0.005)


def rail_profile():
    """Plan view of a rail: a tenon at each end (tips tapered to start easily),
    a slightly wider body between the combs so each comb seats on a shoulder."""
    total, hw, hb, lead = GAP + 2 * COMB_T, RAIL_W / 2, RAIL_BODY_W / 2, 2.0
    half = [(0, hw - 0.6), (lead, hw), (COMB_T, hw), (COMB_T, hb),
            (total - COMB_T, hb), (total - COMB_T, hw), (total - lead, hw), (total, hw - 0.6)]
    return profile(half + [(x, -y) for x, y in reversed(half)])


def coupon_profile():
    """A short piece of the foot with one window, to test the rail fit cheaply."""
    return rect(0, WIN_W + 12, 0, BASE) - window((WIN_W + 12) / 2)


def as_used(m, x_off=0.0):
    """Printed comb coordinates (x depth, y up, z thickness) -> mock-up
    coordinates (X across, Y depth, Z up)."""
    return m.transform(np.array([[0, 0, 1, x_off], [1, 0, 0, 0], [0, 1, 0, 0]], dtype=float))


if __name__ == "__main__":
    here = os.path.dirname(os.path.abspath(__file__))
    out = lambda *p: os.path.join(here, *p)
    comb = comb_profile()
    width = GAP + 2 * COMB_T
    print(f"rack: {width:.0f} wide x {SPINE + REACH:.0f} deep x {LEVEL_Y[-1] + BACKSTOP:.1f} tall; "
          f"shelves at {[round(y, 1) for y in LEVEL_Y]}, pitch {PITCH}, "
          f"window {WIN_W:.2f} x {WIN_H:.2f} for a {RAIL_W} x {RAIL_T} tenon")
    # Centred on the 180 mm bed and sliced with --no-arrange: the auto-arranger turns
    # this long part and parks it against the bed edge.
    export(prism_xy(comb, 0, COMB_T).translate([90 - (SPINE + REACH) / 2, 90 - (LEVEL_Y[-1] + BACKSTOP) / 2, 0]),
           out("stl/comb.stl"))
    export(prism_xy(rail_profile(), 0, RAIL_T), out("stl/rail.stl"))
    export(prism_xy(coupon_profile(), 0, COMB_T), out("stl/fit_coupon.stl"))
    rail, coupon = prism_xy(rail_profile(), 0, RAIL_T), prism_xy(coupon_profile(), 0, COMB_T)
    export(rail.translate([0, 9, 0]) + rail.translate([0, 33, 0])       # one hand-laid plate:
           + coupon.translate([width / 2 - 13, 48, 0]),                 # the auto-arranger hugs the edge
           out("stl/plate_rails_coupon.stl"))

    # Mock-up: both combs, both rails, and the devices lying on their shelves.
    solid = prism_xy(comb, 0, COMB_T)
    frame = as_used(solid) + as_used(solid, GAP + COMB_T)
    for xc in RAIL_X:
        z0 = BASE / 2 - RAIL_T / 2
        frame = frame + box(0, width, xc - RAIL_W / 2, xc + RAIL_W / 2, z0, z0 + RAIL_T) \
                      + box(COMB_T, width - COMB_T, xc - RAIL_BODY_W / 2, xc + RAIL_BODY_W / 2, z0, z0 + RAIL_T)
    export(frame, out("previews/mock_rack.stl"))
    for i, ((name, t, across, depth), y) in enumerate(zip(DEVICES, LEVEL_Y)):
        c, s = (1.0, 0.0) if i == 0 else (COS, SIN)        # the foot is level, the arms tilt
        x0 = SPINE + R_IN
        slab = profile([(x0, y + 0.01), (x0 + depth * c, y + 0.01 + depth * s),
                        (x0 + depth * c - t * s, y + 0.01 + depth * s + t * c), (x0 - t * s, y + 0.01 + t * c)])
        export(as_used(prism_xy(slab, 0, across), width / 2 - across / 2), out(f"previews/mock_{name}.stl"))
