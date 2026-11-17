#!/usr/bin/env python3
"""
Stackable tablet rack: the side frames of tower.py cut into one unit per level.

Each side of the rack is a column of units. A unit is a block with one arm; a
dovetail tongue under the block slides sideways into the socket on top of the
unit below, so the joint can take the pull that the loaded arm puts on the back
of the block. The column starts on a base (the foot, which holds the lowest
tablet and takes the cross rails) and ends in a cap (back stop for the top
tablet). Add or remove units to change the number of levels.

    python3 stack.py           # writes stl/ (parts and print plates) and previews/

Profile coordinates: x runs from the back of the block to the open front, y is up.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "../skill/bambu-a1mini-print/scripts"))
sys.path.insert(0, os.path.expanduser("~/.claude/skills/bambu-a1mini-print/scripts"))
import math

from cad_helpers import box, export, prism_xy, profile
from tower import (BASE, COMB_T, GAP, RAIL_BODY_W, RAIL_T, RAIL_W, R_IN, as_used, closing,
                   opening, rail_profile, rect, window, WIN_W)

# ---- dimensions (mm) --------------------------------------------------------
UNITS = 3           # arm units per side; levels = UNITS + 1 (the base holds one tablet)
BLOCK = 26.0        # block depth, front to back
REACH = 133.0       # arm length in front of the block (block + reach stays under 160, the bed limit)
SLOT_H = 13.0       # clear height over the tablet below, at the block (tightest point)
ARM_ROOT, ARM_TIP = 16.0, 6.0
TILT = 2.0          # degrees the arms rise toward the front; joint play settles some of it
CAP_H = 9.0
R_OUT = 1.5
# Dovetail: tongue under each block, near the back where the joint is pulled apart.
DT_X = 8.5          # tongue centre, from the back of the block
DT_NECK, DT_HEAD, DT_H = 6.0, 10.0, 4.5
DT_FIT = 0.15       # clearance per side in the socket; tune with the fit coupon
RAIL_X = [40.0, 125.0]

DEVICES = [("ipad-pro-12.9-m1", 6.4, 280.6, 214.9), ("ipad-pro-13-m4", 5.1, 281.6, 215.5),
           ("kindle-scribe", 5.8, 229.0, 196.0), ("ipad-mini-6", 6.3, 195.4, 134.8)]

PITCH = SLOT_H + ARM_ROOT
TH = math.radians(TILT)
SIN, COS = math.sin(TH), math.cos(TH)
LENGTH = BLOCK + REACH


def tongue(y):
    """Dovetail hanging below the line y, wider at its far end."""
    n, h = DT_NECK / 2, DT_HEAD / 2
    cs = profile([(DT_X - n, y + 1), (DT_X - n, y), (DT_X - h, y - DT_H), (DT_X + h, y - DT_H),
                  (DT_X + n, y), (DT_X + n, y + 1)])
    return opening(cs, 0.4)


def socket(y):
    """Matching pocket cut down from the surface y, DT_FIT bigger all round."""
    n, h, c = DT_NECK / 2 + DT_FIT, DT_HEAD / 2 + DT_FIT, DT_FIT
    return profile([(DT_X - n, y + 1), (DT_X - n, y), (DT_X - h, y - DT_H - c),
                    (DT_X + h, y - DT_H - c), (DT_X + n, y), (DT_X + n, y + 1)])


def unit_profile():
    tip = (BLOCK + REACH * COS, PITCH + REACH * SIN)
    cs = rect(0, BLOCK, 0, PITCH) + profile([
        (BLOCK - 2, PITCH - ARM_ROOT), (BLOCK, PITCH - ARM_ROOT),
        (tip[0] + ARM_TIP * SIN, tip[1] - ARM_TIP * COS), tip, (BLOCK - 2, PITCH)])
    cs = closing(opening(cs, R_OUT), R_IN + 1)
    return (cs + tongue(0) - socket(PITCH)).simplify(0.005)


def base_profile():
    cs = opening(rect(0, LENGTH, 0, BASE), R_OUT) - socket(BASE)
    for xc in RAIL_X:
        cs = cs - window(xc)
    return cs.simplify(0.005)


def cap_profile():
    return (opening(rect(0, BLOCK, 0, CAP_H), 2.0) + tongue(0)).simplify(0.005)


def socket_coupon_profile():
    """A slice of block top with one socket: slide a cap into it to test the fit."""
    return rect(0, DT_X * 2 + 3, 0, 10) - socket(10)


def window_coupon_profile():
    return rect(0, WIN_W + 12, 0, BASE) - window((WIN_W + 12) / 2)


def plate(rows, gap=4.0):
    """Lay parts out for one print plate: `rows` is a list of rows, each a list
    of solids placed left to right; rows stack toward +Y. The result is centred
    on the 180 mm bed, to be sliced with --no-arrange."""
    out, y = None, 0.0
    for row in rows:
        x, top = 0.0, 0.0
        for m in row:
            x0, y0, _, x1, y1, _ = m.bounding_box()
            placed = m.translate([x - x0, y - y0, 0])
            out = placed if out is None else out + placed
            x += (x1 - x0) + gap
            top = max(top, y1 - y0)
        y += top + gap
    x0, y0, _, x1, y1, _ = out.bounding_box()
    return out.translate([90 - (x0 + x1) / 2, 90 - (y0 + y1) / 2, 0])


def nested_units(n):
    """n arm units stacked toward +Y, each block tucked just above the block below."""
    u = prism_xy(unit_profile(), 0, COMB_T)
    out = u
    for i in range(1, n):
        out = out + u.translate([0, i * (PITCH + DT_H + 3.0), 0])
    return out


if __name__ == "__main__":
    here = os.path.dirname(os.path.abspath(__file__))
    out = lambda *p: os.path.join(here, *p)
    solid = lambda cs, h=COMB_T: prism_xy(cs, 0, h)
    unit, base, cap = solid(unit_profile()), solid(base_profile()), solid(cap_profile())
    rail = solid(rail_profile(), RAIL_T)
    width, height = GAP + 2 * COMB_T, BASE + UNITS * PITCH + CAP_H
    print(f"rack: {width:.0f} wide x {LENGTH:.0f} deep x {height:.0f} tall, {UNITS + 1} levels, "
          f"pitch {PITCH}; per side: 1 base + {UNITS} units + 1 cap")
    export(unit, out("stl/unit.stl"))
    export(base, out("stl/base.stl"))
    export(cap, out("stl/cap.stl"))
    export(rail, out("stl/rail.stl"))

    # Print plates (laid out by hand, centred on the bed, no brim).
    small = [cap, cap, solid(socket_coupon_profile()), solid(window_coupon_profile())]
    export(plate([[rail], [rail], small]), out("stl/plate1_rails_caps_coupons.stl"))
    export(plate([[base], [base], [nested_units(3)]]), out("stl/plate2_bases_3units.stl"))
    export(plate([[nested_units(3)]]), out("stl/plate3_3units.stl"))

    # Mock-up: two assembled columns, the rails, and the devices.
    column = base
    for k in range(UNITS):
        column = column + unit.translate([0, BASE + k * PITCH, 0])
    column = column + cap.translate([0, BASE + UNITS * PITCH, 0])
    frame = as_used(column) + as_used(column, GAP + COMB_T)
    for xc in RAIL_X:
        z0 = BASE / 2 - RAIL_T / 2
        frame = frame + box(0, width, xc - RAIL_W / 2, xc + RAIL_W / 2, z0, z0 + RAIL_T) \
                      + box(COMB_T, width - COMB_T, xc - RAIL_BODY_W / 2, xc + RAIL_BODY_W / 2, z0, z0 + RAIL_T)
    export(frame, out("previews/mock_rack.stl"))
    export(as_used(column), out("previews/column.stl"))
    for i, (name, t, across, depth) in enumerate(DEVICES[:UNITS + 1]):
        y = BASE + i * PITCH
        c, s = (1.0, 0.0) if i == 0 else (COS, SIN)
        x0 = BLOCK + 1.0
        slab = profile([(x0, y + 0.01), (x0 + depth * c, y + 0.01 + depth * s),
                        (x0 + depth * c - t * s, y + 0.01 + depth * s + t * c), (x0 - t * s, y + 0.01 + t * c)])
        export(as_used(prism_xy(slab, 0, across), width / 2 - across / 2), out(f"previews/mock_{name}.stl"))
