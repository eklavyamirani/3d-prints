#!/usr/bin/env python3
"""
Add plate thumbnails to a .gcode.3mf produced by the Bambu Studio CLI.

Headless CLI runs cannot open an OpenGL window, so they write a 3MF whose
_rels/.rels points at Metadata/plate_1.png etc. without the files existing, and
Bambu Studio's GUI chokes on that. This renders each plate from the object
bounding boxes in Metadata/plate_N.json plus the source STLs and inserts
plate_N.png, plate_N_small.png, plate_no_light_N.png, top_N.png and pick_N.png,
then registers them in model_settings.config.

Usage: fix_3mf_thumbnails.py FILE.gcode.3mf PART.stl [PART.stl ...]
(slice_a1mini.py calls this for you. STLs are matched to objects by file name.)
"""
import io
import json
import os
import re
import shutil
import sys
import tempfile
import zipfile

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import trimesh
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

BED = 180.0
_meshes = {}


def mesh_for(name, stls):
    base = re.sub(r"(\.stl)(_\d+)?$", r"\1", name, flags=re.I)
    if base not in _meshes:
        _meshes[base] = trimesh.load(stls[base], force="mesh") if base in stls else None
    return _meshes[base]


def render_plate(plate, stls, elev, azim, size_px, light=True):
    fig = plt.figure(figsize=(size_px / 100, size_px / 100), dpi=100)
    ax = fig.add_subplot(111, projection="3d")
    # Draw in the order added (bed first). With matplotlib's automatic depth sort
    # the bed quad is painted over any part much smaller than the bed.
    ax.computed_zorder = False
    ax.set_facecolor("#1e2124")
    bed = np.array([[[0, 0, 0], [BED, 0, 0], [BED, BED, 0], [0, BED, 0]]], float)
    ax.add_collection3d(Poly3DCollection(bed, facecolors="#2b2f33", edgecolors="#55595e", alpha=1.0))
    lightdir = np.array([0.3, -0.5, 0.8])
    lightdir /= np.linalg.norm(lightdir)
    for obj in plate["bbox_objects"]:
        src = mesh_for(obj["name"], stls)
        if src is None:          # no STL given for this object: leave it out of the picture
            continue
        m = src.copy()
        bb = obj["bbox"]
        lo = m.bounds[0]
        m.apply_translation([bb[0] - lo[0], bb[1] - lo[1], -lo[2]])
        tri = m.vertices[m.faces]
        shade = 0.55 + 0.45 * np.clip(m.face_normals @ lightdir, 0, 1) if light else np.full(len(tri), 0.8)
        cols = np.clip(np.array([0.0, 0.68, 0.26])[None, :] * shade[:, None], 0, 1)
        ax.add_collection3d(Poly3DCollection(tri, facecolors=cols, edgecolors="none"))
    ax.set_xlim(0, BED)
    ax.set_ylim(0, BED)
    ax.set_zlim(0, BED)
    ax.set_box_aspect((1, 1, 1))
    ax.view_init(elev=elev, azim=azim)
    ax.set_axis_off()
    fig.subplots_adjust(0, 0, 1, 1)
    buf = io.BytesIO()
    fig.savefig(buf, format="png", facecolor="#1e2124")
    plt.close(fig)
    return buf.getvalue()


def blank_png(size_px):
    fig = plt.figure(figsize=(size_px / 100, size_px / 100), dpi=100)
    fig.patch.set_facecolor((0, 0, 0, 1))
    buf = io.BytesIO()
    fig.savefig(buf, format="png", facecolor=fig.get_facecolor())
    plt.close(fig)
    return buf.getvalue()


def main(path, stl_paths):
    stls = {os.path.basename(p): p for p in stl_paths}
    with zipfile.ZipFile(path) as z:
        names = z.namelist()
        plates = sorted(n for n in names if re.fullmatch(r"Metadata/plate_\d+\.json", n))
        settings = z.read("Metadata/model_settings.config").decode()
        images = {}
        for pj in plates:
            idx = int(re.search(r"plate_(\d+)\.json", pj).group(1))
            plate = json.loads(z.read(pj))
            print(f"plate {idx}: " + ", ".join(o["name"] for o in plate["bbox_objects"]))
            images[f"Metadata/plate_{idx}.png"] = render_plate(plate, stls, 32, -60, 512)
            images[f"Metadata/plate_{idx}_small.png"] = render_plate(plate, stls, 32, -60, 128)
            images[f"Metadata/plate_no_light_{idx}.png"] = render_plate(plate, stls, 32, -60, 512, light=False)
            images[f"Metadata/top_{idx}.png"] = render_plate(plate, stls, 90, -90, 512)
            images[f"Metadata/pick_{idx}.png"] = blank_png(512)
            block_re = re.compile(rf'(<metadata key="plater_id" value="{idx}"/>\n)')
            extra = (f'    <metadata key="thumbnail_file" value="Metadata/plate_{idx}.png"/>\n'
                     f'    <metadata key="thumbnail_no_light_file" value="Metadata/plate_no_light_{idx}.png"/>\n'
                     f'    <metadata key="top_file" value="Metadata/top_{idx}.png"/>\n'
                     f'    <metadata key="pick_file" value="Metadata/pick_{idx}.png"/>\n')
            if f'value="Metadata/plate_{idx}.png"' not in settings:
                settings = block_re.sub(lambda m: m.group(1) + extra, settings, count=1)
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".3mf", dir=os.path.dirname(os.path.abspath(path)))
        tmp.close()
        with zipfile.ZipFile(tmp.name, "w", zipfile.ZIP_DEFLATED) as out:
            for n in names:
                if n in images or n == "Metadata/model_settings.config":
                    continue
                out.writestr(z.getinfo(n), z.read(n))
            out.writestr("Metadata/model_settings.config", settings)
            for n, data in images.items():
                out.writestr(n, data, compress_type=zipfile.ZIP_STORED)
    shutil.move(tmp.name, path)
    print("updated", path)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2:])
