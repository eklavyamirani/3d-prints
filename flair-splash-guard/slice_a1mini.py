#!/usr/bin/env python3
"""
Slice the splash-guard panels for the Bambu Lab A1 mini with Bambu Studio's
command line. Bambu's bundled profiles use "inherits" chains that the CLI does
not resolve on its own, so this script flattens them first.

Usage: python3 slice_a1mini.py [out_dir] [--filament "Bambu PETG Basic @BBL A1M"] [--test]
       --test slices a single straight panel (test_panel_straight.gcode.3mf) for a fit check.
       --per-plate writes one single-plate file per plate (plate_1..N.gcode.3mf), one
       panel per plate, centred. (Two 170 mm panels per plate put them against the
       bed edges with the brim clipped off, and the whole plate came loose mid-print.)
       --panels-per-plate N packs N panels per plate instead (2 fits, but see above).
       --have-straight N leaves out N straight panels you already printed (e.g. the
       test panel), so fewer plates are needed.
Produces <out_dir>/splash_guard_A1mini.gcode.3mf (all plates sliced) plus
per-plate .gcode files and result.json with time/weight estimates.
"""
import json
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
APP = os.path.expanduser("~/Applications/BambuStudio.app")
if not os.path.exists(APP):
    APP = "/Applications/BambuStudio.app"
BIN = os.path.join(APP, "Contents/MacOS/BambuStudio")
PROFILES = os.path.join(APP, "Contents/Resources/profiles/BBL")

MACHINE = "Bambu Lab A1 mini 0.4 nozzle"
PROCESS = "0.20mm Standard @BBL A1M"
# The user's PETG preset, synced from the Bambu cloud (it lives in the user
# preset folder, not the system one). The sliced project carries this single
# filament; when sending the print, map it to the AMS slot that holds PETG.
# (The CLI cannot slice a two-filament project: it fails with
# "could not found group_nozzle_info", so slot numbering is done at print time.)
FILAMENTS = ["COMGROW PETG Basic @Bambu Lab A1 mini 0.4 nozzle"]
PRINT_WITH = 1                     # 1-based index into FILAMENTS
BED_TYPE = "Textured PEI Plate"
USER_PRESETS = os.path.expanduser("~/Library/Application Support/BambuStudio/user")

# straight x4, straight-with-cable-notch x1, corner x2
PARTS = [("panel_straight.stl", 4), ("panel_straight_cable.stl", 1), ("panel_corner.stl", 2)]


def find_profile(kind, name):
    p = os.path.join(PROFILES, kind, name + ".json")
    if os.path.exists(p):
        return p
    for root, _dirs, files in os.walk(USER_PRESETS):
        if name + ".json" in files:
            return os.path.join(root, name + ".json")
    raise FileNotFoundError(name)


def flatten(kind, name, seen=None):
    """Resolve 'inherits' (parent first, child overrides) and 'include' files."""
    seen = seen or set()
    if name in seen:
        raise RuntimeError("cycle at " + name)
    seen.add(name)
    with open(find_profile(kind, name)) as f:
        data = json.load(f)
    merged = {}
    parent = data.pop("inherits", None)
    if parent:
        merged.update(flatten(kind, parent, seen))
    for inc in data.pop("include", []) or []:
        with open(find_profile(kind, inc)) as f:
            merged.update({k: v for k, v in json.load(f).items() if k not in ("type", "name", "from")})
    merged.update(data)
    merged["name"] = name
    merged["inherits"] = ""
    merged.setdefault("type", kind)       # user presets synced from the cloud lack it
    merged.setdefault("instantiation", "true")
    return merged


def main():
    args = sys.argv[1:]
    filaments = list(FILAMENTS)
    print_with = PRINT_WITH
    if "--filament" in args:          # single filament override
        i = args.index("--filament")
        filaments, print_with = [args[i + 1]], 1
        del args[i:i + 2]
    parts, out_name = list(PARTS), "splash_guard_A1mini.gcode.3mf"
    if "--have-straight" in args:
        i = args.index("--have-straight")
        have = int(args[i + 1])
        del args[i:i + 2]
        parts[0] = (parts[0][0], parts[0][1] - have)
    if "--test" in args:
        args.remove("--test")
        parts, out_name = [("panel_straight.stl", 1)], "test_panel_straight.gcode.3mf"
    per_plate = 1
    if "--panels-per-plate" in args:
        i = args.index("--panels-per-plate")
        per_plate = int(args[i + 1])
        del args[i:i + 2]
    if "--per-plate" in args:
        args.remove("--per-plate")
        # in the order straight, cable, corner
        items = [n for n, c in parts for _ in range(c)]
        plates = []
        for pair in (items[i:i + per_plate] for i in range(0, len(items), per_plate)):
            plate_parts = []
            for n in pair:
                if plate_parts and plate_parts[-1][0] == n:
                    plate_parts[-1] = (n, plate_parts[-1][1] + 1)
                else:
                    plate_parts.append((n, 1))
            plates.append(plate_parts)
        for i, plate_parts in enumerate(plates, 1):
            run(args, filaments, print_with, plate_parts, f"plate_{i}.gcode.3mf")
        return
    run(args, filaments, print_with, parts, out_name)


def run(args, filaments, print_with, parts, out_name):
    out_dir = os.path.abspath(args[0]) if args else os.path.join(HERE, "sliced")
    os.makedirs(out_dir, exist_ok=True)
    cfg_dir = os.path.join(out_dir, "profiles")
    os.makedirs(cfg_dir, exist_ok=True)

    paths = {}
    for kind, name in (("machine", MACHINE), ("process", PROCESS)):
        flat = flatten(kind, name)
        if kind == "process":
            # Give the tweaked process its own name and mark it as a user preset:
            # otherwise Bambu Studio swaps in the stock system preset when the 3mf
            # is opened and re-sliced in the GUI, dropping the overrides below.
            flat["name"] = PROCESS + " - splash guard"
            flat["from"] = "User"
            flat.pop("setting_id", None)
            flat["curr_bed_type"] = BED_TYPE
            flat["wall_loops"] = "4"          # 4 x 0.42 mm per side: the 3.2 mm wall prints solid
            flat["brim_type"] = "outer_only"  # keep flange and saddle leg flat on the plate
            flat["brim_width"] = "5"
        p = os.path.join(cfg_dir, kind + ".json")
        with open(p, "w") as f:
            json.dump(flat, f, indent=1)
        paths[kind] = p
        print(f"{kind:9s} {name}: {len(flat)} keys")
    fil_paths = []
    for i, name in enumerate(filaments, 1):
        flat = flatten("filament", name)
        p = os.path.join(cfg_dir, f"filament_{i}.json")
        with open(p, "w") as f:
            json.dump(flat, f, indent=1)
        fil_paths.append(p)
        print(f"filament{i} {name}: {len(flat)} keys" + ("  <- used for all objects" if i == print_with else ""))

    for f in os.listdir(out_dir):
        if f.endswith((".gcode", ".json")) or f == out_name:
            os.remove(os.path.join(out_dir, f))

    stls = [os.path.join(HERE, "stl", n) for n, _ in parts]
    clones = ",".join(str(c) for _, c in parts)
    cmd = [BIN, "--debug", "1",
           "--load-settings", f"{paths['machine']};{paths['process']}",
           "--load-filaments", ";".join(fil_paths),
           "--load-filament-ids", ",".join(str(print_with) for _ in parts),
           "--clone-objects", clones,
           "--arrange", "1", "--orient", "0",
           "--slice", "0",
           "--export-3mf", out_name,
           "--outputdir", out_dir] + stls
    print("running Bambu Studio CLI ...")
    r = subprocess.run(cmd, cwd=out_dir, capture_output=True, text=True)
    for line in (r.stdout + r.stderr).splitlines():
        if "error" in line.lower() and "can not find key" not in line:
            print(line)
    res = os.path.join(out_dir, "result.json")
    with open(res) as f:
        result = json.load(f)
    print("return:", result.get("return_code"), result.get("error_string"))
    total_s = 0
    for p in result.get("sliced_plates", []):
        s = p.get("total_predication", 0)
        total_s += s
        g = sum(fl.get("total_used_g", 0) for fl in p.get("filaments", []))
        print(f"  plate {p['id']}: {s/3600:.1f} h, {g:.0f} g, objects: "
              + ", ".join(o.get('name', '?') for o in p.get("objects", [])))
    print(f"total: {total_s/3600:.1f} h")
    out_3mf = os.path.join(out_dir, out_name)
    subprocess.run([sys.executable, os.path.join(HERE, "fix_3mf_thumbnails.py"), out_3mf], check=True)
    print("sliced project:", out_3mf)


if __name__ == "__main__":
    main()
