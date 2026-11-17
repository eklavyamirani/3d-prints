#!/usr/bin/env python3
"""Render PNG previews of the panels and the assembled guard with matplotlib."""
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import trimesh
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "previews")


def draw(ax, mesh, color, alpha=1.0):
    tri = mesh.vertices[mesh.faces]
    n = mesh.face_normals
    light = np.array([0.3, -0.6, 0.75])
    shade = 0.55 + 0.45 * np.clip(tri_shade(n, light), 0, 1)
    base = np.array(matplotlib.colors.to_rgb(color))
    cols = np.clip(base[None, :] * shade[:, None], 0, 1)
    pc = Poly3DCollection(tri, facecolors=cols, edgecolors="none", alpha=alpha)
    ax.add_collection3d(pc)


def tri_shade(normals, light):
    light = light / np.linalg.norm(light)
    return normals @ light


def setup(ax, bounds, elev, azim):
    lo, hi = bounds
    c = (lo + hi) / 2
    r = (hi - lo).max() / 2
    ax.set_xlim(c[0] - r, c[0] + r)
    ax.set_ylim(c[1] - r, c[1] + r)
    ax.set_zlim(c[2] - r, c[2] + r)
    ax.set_box_aspect((1, 1, 1))
    ax.view_init(elev=elev, azim=azim)
    ax.set_axis_off()


def render_part(path, name, views):
    m = trimesh.load(path, force="mesh")
    fig = plt.figure(figsize=(5 * len(views), 5), dpi=110)
    for i, (title, elev, azim) in enumerate(views):
        ax = fig.add_subplot(1, len(views), i + 1, projection="3d")
        draw(ax, m, "#d9a441")
        setup(ax, m.bounds, elev, azim)
        ax.set_title(title, fontsize=10)
    fig.suptitle(name, fontsize=12)
    fig.tight_layout()
    out = os.path.join(OUT, name + ".png")
    fig.savefig(out, facecolor="white")
    plt.close(fig)
    print("wrote", out)


def pan_mesh(L, Wd, h, origin):
    """Rough half-sheet-pan shell for context: sloped sides, open top."""
    # inner floor L x Wd at z=0, rim at z=h flares out by 12 mm
    f = 12.0
    x0, y0 = origin
    verts = []
    faces = []
    bot = [(x0, y0), (x0 + L, y0), (x0 + L, y0 + Wd), (x0, y0 + Wd)]
    top = [(x0 - f, y0 - f), (x0 + L + f, y0 - f), (x0 + L + f, y0 + Wd + f), (x0 - f, y0 + Wd + f)]
    for (x, y) in bot:
        verts.append((x, y, 0))
    for (x, y) in top:
        verts.append((x, y, h))
    faces += [(0, 1, 2), (0, 2, 3)]
    for i in range(4):
        j = (i + 1) % 4
        faces += [(i, j, 4 + j), (i, 4 + j, 4 + i)]
    return trimesh.Trimesh(vertices=np.array(verts, float), faces=np.array(faces))


def render_assembly(path):
    m = trimesh.load(path, force="mesh")
    lo, hi = m.bounds
    # the guard interior: inner faces at x=0 and x=interior_x, y=interior_y
    pan = pan_mesh(413, 286, 26, (lo[0] + 32, lo[1] + 36))
    pan.apply_translation([0, 0, -0.01])
    views = [("front, slightly above", 22, -60), ("top", 90, -90), ("from the kitchen wall side", 18, 120)]
    fig = plt.figure(figsize=(16, 6), dpi=110)
    bounds = np.array([np.minimum(lo, pan.bounds[0]), np.maximum(hi, pan.bounds[1])])
    for i, (title, elev, azim) in enumerate(views):
        ax = fig.add_subplot(1, 3, i + 1, projection="3d")
        draw(ax, pan, "#9aa3ad", alpha=0.35)
        draw(ax, m, "#d9a441")
        setup(ax, bounds, elev, azim)
        ax.set_title(title, fontsize=10)
    fig.suptitle("Assembled guard standing in a 413 x 286 mm (interior) half sheet pan", fontsize=12)
    fig.tight_layout()
    out = os.path.join(OUT, "assembly.png")
    fig.savefig(out, facecolor="white")
    plt.close(fig)
    print("wrote", out)


def main():
    os.makedirs(OUT, exist_ok=True)
    views = [("inside face", 20, -110), ("outside face / rim saddle", 20, 60), ("end view (print profile)", 8, 0)]
    render_part(os.path.join(HERE, "stl", "panel_straight.stl"), "panel_straight", views)
    render_part(os.path.join(HERE, "stl", "panel_straight_cable.stl"), "panel_straight_cable", views)
    render_part(os.path.join(HERE, "stl", "panel_corner.stl"), "panel_corner", views)
    render_assembly(os.path.join(HERE, "assembly.stl"))


if __name__ == "__main__":
    main()
