#!/usr/bin/env python3
"""
Flair 58 splash guard for a half sheet pan, printable on a Bambu Lab A1 mini.

Modular wall panels stand INSIDE the pan on a foot flange and straddle the
pan rim with a "saddle" (arch + outer leg) so they cannot tip in or out.
Each panel has a plain edge (A) and an integrated sliding channel (B); the next
panel's A edge slides down into the B channel, so every seam is overlapped by
a 8 mm deep channel and nothing can splash through. Corner panels carry the
channel turned 90 degrees. No separate connectors are needed.

The inside (machine-facing) surface is one flat, uninterrupted plane from the
top edge to the pan floor: nothing overhangs the espresso, so anything that
hits the plastic runs straight down into the sheet pan.

Chain, viewed from above, walking clockwise with the interior on your right:
    S1 (straight) -> S2 (corner) -> B1 (straight) -> B2 (straight, cable notch)
    -> B3 (corner) -> S3 (straight) -> S4 (straight)

Run:  python3 splash_guard.py           (writes STLs into ./stl and ./assembly.stl)
Deps: pip install manifold3d trimesh numpy
"""
from __future__ import annotations

import math
import os
import sys

import numpy as np
import trimesh
from manifold3d import CrossSection, FillRule, Manifold

# ----------------------------------------------------------------- parameters
# All dimensions in millimetres.

W = 125.0          # wall run of one panel (channel adds 10 mm; print footprint 135 x ~75)
H = 170.0          # wall height (A1 mini max Z = 180)
T = 3.2            # wall thickness; sliced with 4 wall loops so it is solid (v2: was 2.4, bowed)

FLANGE_IN = 22.0   # foot flange reaching inward over the pan floor
FLANGE_T = 3.0     # foot flange thickness
GUSSET = 4.0       # 45 deg fillet between flange and wall
EDGE_CLEAR = 8.5   # flange/bead stop this far from the plain (A) edge so the
                   # neighbour's channel legs can slide past

SLOT = 3.0         # channel slot width (T + 0.6 clearance)
LEG = 2.0          # channel leg thickness
CH_DEPTH = 8.0     # how deep the neighbour edge sits in the channel
CROSS = 2.0        # channel cross-bar thickness (straight joint only)

SADDLE_W = 50.0    # width of the rim saddle (centred on the panel)
SADDLE_IN = 44.0   # clear width inside the saddle, from the wall's outer face
SADDLE_H = 32.0    # clear height inside the saddle (pan rim is ~26-28 mm)
SADDLE_LEG = 3.0   # outer leg thickness (stands on the counter outside the pan)
SADDLE_TOP = 2.8   # roof thickness, measured normal to the slope (thin: a thick
                   # roof shrinks and pulls the wall over)
SADDLE_ANGLE = 60.0  # roof slope from horizontal. v3 used 45 and the PETG slabs
                     # curled, caught the nozzle and knocked the thin leg over;
                     # at 60 each layer is 96 % supported by the one below
SADDLE_FOOT = 12.0 # outward foot on the outer leg: anchors the leg on the plate
                   # while the roof is printed, and on the counter in use
# History: v2 had a flat 32 mm bridge (sagged), v3 a 45 degree gable (failed).

BEAD_OUT = 2.0     # stiffening bead along the top edge, on the OUTSIDE face only
BEAD_H = 6.0

RIB_T = 3.2        # vertical stiffening ribs on the OUTSIDE face (never inside: drips)
RIB_D = 8.0        # how far the ribs stand off the wall
RIB_AT = (0.25, 0.5, 0.75)   # rib positions as a fraction of W

NOTCH_W = 14.0     # power-cord notch in the top edge of the cable panel
NOTCH_D = 22.0

# ------------------------------------------------------------------ helpers

def box(x0, x1, y0, y1, z0, z1) -> Manifold:
    return Manifold.cube([x1 - x0, y1 - y0, z1 - z0]).translate([x0, y0, z0])


def prism_yz(pts_yz, x0, x1) -> Manifold:
    """Prism with a polygon cross-section in the YZ plane, extruded along X."""
    cs = CrossSection([[(float(y), float(z)) for (y, z) in pts_yz]], FillRule.EvenOdd)
    m = Manifold.extrude(cs, x1 - x0)           # (u,v,w) = (y,z,x-extent)
    m = m.rotate([0.0, 90.0, 0.0]).rotate([90.0, 0.0, 0.0])  # -> (w,u,v) = (x,y,z)
    return m.translate([x0, 0.0, 0.0])


def cyl_y(radius, y0, y1, cx, cz) -> Manifold:
    """Cylinder along Y."""
    m = Manifold.cylinder(y1 - y0, radius, radius, 64)  # along Z
    return m.rotate([-90.0, 0.0, 0.0]).translate([cx, y0, cz])


# --------------------------------------------------------------- panel parts

def wall(x0, x1) -> Manifold:
    return box(x0, x1, 0, T, 0, H)


def flange(x0, x1) -> Manifold:
    f = box(x0, x1, -FLANGE_IN, 0, 0, FLANGE_T)
    g = prism_yz([(0, FLANGE_T), (-GUSSET, FLANGE_T), (0, FLANGE_T + GUSSET)], x0, x1)
    return f + g


def bead(x0, x1) -> Manifold:
    b = box(x0, x1, T, T + BEAD_OUT, H - BEAD_H, H)
    c = prism_yz([(T, H - BEAD_H), (T + BEAD_OUT, H - BEAD_H), (T, H - BEAD_H - BEAD_OUT)], x0, x1)
    return b + c


def ribs() -> Manifold:
    """Full-height ribs on the outside face; they resist the bow a tall thin wall
    takes as the layers cool, and tie the top bead to the saddle bridge."""
    m = None
    for f in RIB_AT:
        cx = W * f
        r = box(cx - RIB_T / 2, cx + RIB_T / 2, T, T + RIB_D, 0, H)   # from the bed: no cantilever
        m = r if m is None else m + r
    return m


def saddle(cx) -> Manifold:
    """Rim saddle: outer leg (with an outward foot) on the counter plus a steep
    gable roof over the pan rim. Clear opening: SADDLE_IN wide, SADDLE_H high at
    both sides and SADDLE_H + SADDLE_IN/2 * tan(SADDLE_ANGLE) under the peak."""
    x0, x1 = cx - SADDLE_W / 2, cx + SADDLE_W / 2
    y_leg0 = T + SADDLE_IN
    y_leg1 = y_leg0 + SADDLE_LEG
    k = math.tan(math.radians(SADDLE_ANGLE))     # rise per unit of run
    tv = SADDLE_TOP / math.cos(math.radians(SADDLE_ANGLE))   # vertical slab thickness
    rise = SADDLE_IN / 2 * k
    ym = T + SADDLE_IN / 2                        # peak position
    leg = box(x0, x1, y_leg0, y_leg1, 0, SADDLE_H)
    foot = box(x0, x1, y_leg0, y_leg1 + SADDLE_FOOT, 0, FLANGE_T)
    foot += prism_yz([(y_leg1, FLANGE_T), (y_leg1 + GUSSET, FLANGE_T), (y_leg1, FLANGE_T + GUSSET)], x0, x1)
    # Underside: from inside the wall up to the peak and down to the leg's outer
    # face, so the slope continues over the leg without a step.
    roof = prism_yz([(T - 1.0, SADDLE_H - k),
                     (ym, SADDLE_H + rise),
                     (y_leg1, SADDLE_H - SADDLE_LEG * k),
                     (y_leg1, SADDLE_H - SADDLE_LEG * k + tv),
                     (ym, SADDLE_H + rise + tv),
                     (T - 1.0, SADDLE_H - k + tv)], x0, x1)
    return leg + foot + roof


def straight_channel() -> Manifold:
    """B edge of a straight panel: H-shaped channel, slot in the plane of the wall."""
    y_in0, y_in1 = -(LEG + (SLOT - T) / 2), -(SLOT - T) / 2          # inner leg
    y_out0, y_out1 = T + (SLOT - T) / 2, T + (SLOT - T) / 2 + LEG    # outer leg
    cross = box(W, W + CROSS, y_in0, y_out1, 0, H)
    inner = box(W + CROSS, W + CROSS + CH_DEPTH, y_in0, y_in1, 0, H)
    outer = box(W + CROSS, W + CROSS + CH_DEPTH, y_out0, y_out1, 0, H)
    return cross + inner + outer


def corner_channel() -> Manifold:
    """B edge of a corner panel: slot perpendicular to the wall, open toward the interior (-Y).
    The neighbour's A edge slides in and butts against this wall's inner face."""
    inner = box(W, W + LEG, -CH_DEPTH, 0, 0, H)
    outer = box(W + LEG + SLOT, W + 2 * LEG + SLOT, -CH_DEPTH, 0, 0, H)
    return inner + outer


def cable_notch(cx) -> Manifold:
    r = NOTCH_W / 2
    zc = H - NOTCH_D + r
    return box(cx - r, cx + r, -10, T + BEAD_OUT + 10, zc, H + 5) + cyl_y(r, -10, T + BEAD_OUT + 10, cx, zc)


# ------------------------------------------------------------------- panels

def straight_panel(cable: bool = False) -> Manifold:
    m = wall(0, W)
    m += straight_channel()
    m += flange(EDGE_CLEAR, W + CROSS)
    m += bead(EDGE_CLEAR, W)
    m += ribs()
    m += saddle(W / 2)
    if cable:
        m -= cable_notch(W / 2)
    return m


def corner_panel() -> Manifold:
    end = W + 2 * LEG + SLOT
    m = wall(0, end)
    m += corner_channel()
    m += flange(EDGE_CLEAR, W - FLANGE_IN)      # leave room for the neighbour's flange
    m += bead(EDGE_CLEAR, end)
    m += ribs()
    m += saddle(W / 2)
    return m


# ----------------------------------------------------------------- assembly

def place(m: Manifold, origin, heading_deg) -> Manifold:
    """Put a panel's A edge at `origin`, running along `heading_deg` (0 = +X).
    Panel local frame: wall along +X, interior at -Y."""
    return m.rotate([0, 0, heading_deg]).translate([origin[0], origin[1], 0])


def assembly() -> tuple[Manifold, dict]:
    """Full U, interior at the centre. Returns the manifold and layout info."""
    pitch = W + CROSS                       # A-edge to next A-edge for straight joints
    corner_adv = W + LEG + (SLOT - T) / 2   # A-edge of corner panel to the neighbour's inner face
    parts = []
    # left side runs +Y (heading 90), interior at +X
    s1 = place(straight_panel(), (0, 0), 90)
    s2 = place(corner_panel(), (0, pitch), 90)
    yb = pitch + corner_adv                 # inner face plane of the back wall
    b1 = place(straight_panel(), (0, yb), 0)
    b2 = place(straight_panel(cable=True), (pitch, yb), 0)
    b3 = place(corner_panel(), (2 * pitch, yb), 0)
    xr = 2 * pitch + corner_adv             # inner face plane of right side wall
    s3 = place(straight_panel(), (xr, yb), -90)
    s4 = place(straight_panel(), (xr, yb - pitch), -90)
    parts = [s1, s2, b1, b2, b3, s3, s4]
    m = parts[0]
    for p in parts[1:]:
        m += p
    info = dict(interior_x=xr, interior_y=yb, side_len=yb + 2 * LEG + SLOT,
                outer_x=xr + T + 2 * LEG + (SLOT - T) / 2 + T * 0)
    return m, info


# ------------------------------------------------------------------- export

def to_trimesh(m: Manifold) -> trimesh.Trimesh:
    mesh = m.to_mesh()
    v = np.asarray(mesh.vert_properties)[:, :3]
    f = np.asarray(mesh.tri_verts)
    tm = trimesh.Trimesh(vertices=v, faces=f, process=True)
    return tm


def export(m: Manifold, path: str) -> trimesh.Trimesh:
    tm = to_trimesh(m)
    tm.export(path)
    b = tm.bounds
    print(f"{os.path.basename(path):28s} size {b[1]-b[0]} mm  volume {tm.volume/1000:.1f} cm3  "
          f"~{tm.volume/1000*1.24:.0f} g PLA  watertight={tm.is_watertight}")
    return tm


def main(out_dir: str) -> None:
    os.makedirs(os.path.join(out_dir, "stl"), exist_ok=True)
    export(straight_panel(), os.path.join(out_dir, "stl", "panel_straight.stl"))
    export(straight_panel(cable=True), os.path.join(out_dir, "stl", "panel_straight_cable.stl"))
    export(corner_panel(), os.path.join(out_dir, "stl", "panel_corner.stl"))
    asm, info = assembly()
    tm = export(asm, os.path.join(out_dir, "assembly.stl"))
    print("assembly: interior span X =", round(info["interior_x"], 1),
          "mm, interior depth Y =", round(info["interior_y"], 1),
          "mm, side wall length =", round(info["side_len"], 1), "mm")
    print("components (separate solids) in assembly:", len(asm.decompose()))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(os.path.abspath(__file__)))
