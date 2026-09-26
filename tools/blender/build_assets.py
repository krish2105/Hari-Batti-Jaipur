"""Build the HariBatti 3D asset set in headless Blender (W7).

  /Applications/Blender.app/Contents/MacOS/Blender --background --factory-startup \
      --python tools/blender/build_assets.py -- [--no-render]

Writes:
  apps/web/public/models/vehicles/<name>.glb and <name>_lod1.glb (~40% triangles)
  apps/web/public/models/city/<name>.glb
  apps/web/public/models/manifest.json   (triangles, sizes in metres, budget check)
  docs/img/models/<name>.png + lineup.png (turntable renders for the README)
Draco/texture compression is a separate step (tools/blender/compress.sh).
"""

import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
ROOT = HERE.parents[1]

from hb_city import CITY  # noqa: E402
from hb_lib import emission_image, triangles  # noqa: E402
from hb_vehicles import VEHICLES  # noqa: E402

OUT_V = ROOT / "apps/web/public/models/vehicles"
OUT_C = ROOT / "apps/web/public/models/city"
OUT_IMG = ROOT / "docs/img/models"
BUDGET = {"city_bus": 6000}
DEFAULT_BUDGET = 3000
RENDER = "--no-render" not in sys.argv


def clear_scene():
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    for c in list(bpy.data.collections):
        bpy.data.collections.remove(c)


def select_only(objs):
    bpy.ops.object.select_all(action="DESELECT")
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]


def export_glb(objs, path: Path):
    select_only(objs)
    bpy.ops.export_scene.gltf(filepath=str(path), export_format="GLB", use_selection=True, export_apply=True,
                              export_yup=True, export_materials="EXPORT", export_image_format="AUTO",
                              export_extras=False)


def bbox(objs):
    bpy.context.view_layer.update()  # apply pending object moves before measuring
    lo = Vector((1e9, 1e9, 1e9))
    hi = Vector((-1e9, -1e9, -1e9))
    for o in objs:
        for c in o.bound_box:
            w = o.matrix_world @ Vector(c)
            lo = Vector(map(min, lo, w))
            hi = Vector(map(max, hi, w))
    return lo, hi


def add_decimate(objs, ratio: float):
    for o in objs:
        if o.type == "MESH":
            m = o.modifiers.new("lod", "DECIMATE")
            m.ratio = ratio


def remove_decimate(objs):
    for o in objs:
        for m in list(o.modifiers):
            if m.name == "lod":
                o.modifiers.remove(m)


def lod_triangles(objs) -> int:
    deps = bpy.context.evaluated_depsgraph_get()
    n = 0
    for o in objs:
        if o.type == "MESH":
            me = o.evaluated_get(deps).to_mesh()
            n += sum(len(p.vertices) - 2 for p in me.polygons)
            o.evaluated_get(deps).to_mesh_clear()
    return n


# ---------------------------------------------------------------- studio renders


def studio():
    scene = bpy.context.scene
    try:
        scene.render.engine = "BLENDER_EEVEE"
    except TypeError:
        scene.render.engine = "CYCLES"
    scene.render.resolution_x, scene.render.resolution_y = 900, 560
    scene.eevee.taa_render_samples = 64
    scene.render.film_transparent = False
    world = bpy.data.worlds.new("hb_world")
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.93, 0.80, 0.74, 1)
    world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.9
    scene.world = world
    sun = bpy.data.lights.new("sun", "SUN")
    sun.energy = 3.2
    sun.angle = math.radians(8)
    so = bpy.data.objects.new("sun", sun)
    so.rotation_euler = (math.radians(50), math.radians(10), math.radians(140))
    scene.collection.objects.link(so)
    ground = bpy.data.meshes.new("ground")
    s = 60
    ground.from_pydata([(-s, -s, 0), (s, -s, 0), (s, s, 0), (-s, s, 0)], [], [(0, 1, 2, 3)])
    gm = bpy.data.materials.new("ground")
    gm.use_nodes = True
    gm.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.86, 0.72, 0.66, 1)
    ground.materials.append(gm)
    go = bpy.data.objects.new("ground", ground)
    scene.collection.objects.link(go)
    cam = bpy.data.cameras.new("cam")
    cam.lens = 50
    co = bpy.data.objects.new("cam", cam)
    scene.collection.objects.link(co)
    scene.camera = co
    return co, [so, go, co]


def frame(cam_obj, objs, yaw_deg: float = 35, pitch_deg: float = 18, pad: float = 1.25):
    lo, hi = bbox(objs)
    centre = (lo + hi) / 2
    size = max((hi - lo).length, 1.0)
    dist = size * pad * 1.2
    yaw, pitch = math.radians(yaw_deg), math.radians(pitch_deg)
    cam_obj.location = centre + Vector((math.cos(yaw) * math.cos(pitch), -math.sin(yaw) * math.cos(pitch),
                                        math.sin(pitch))) * dist
    direction = centre - cam_obj.location
    cam_obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()


def render(path: Path):
    bpy.context.scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)


# ---------------------------------------------------------------- main


def main():
    for d in (OUT_V, OUT_C, OUT_IMG):
        d.mkdir(parents=True, exist_ok=True)
    clear_scene()
    emission_image()  # tools/blender/palette_em.png (the website's night glow mask)
    manifest = {"units": "metres", "forward": "+X (glTF)", "up": "+Y (glTF)", "vehicles": {}, "city": {}}
    built: dict[str, list] = {}
    for name, fn in VEHICLES.items():
        objs = fn()
        tris = triangles(objs)
        lo, hi = bbox(objs)
        export_glb(objs, OUT_V / f"{name}.glb")
        add_decimate(objs, 0.4)
        tris_lod1 = lod_triangles(objs)
        export_glb(objs, OUT_V / f"{name}_lod1.glb")
        remove_decimate(objs)
        budget = BUDGET.get(name, DEFAULT_BUDGET)
        manifest["vehicles"][name] = {
            "triangles": tris, "triangles_lod1": tris_lod1, "budget": budget, "within_budget": tris <= budget,
            "length_m": round(hi.x - lo.x, 2), "width_m": round(hi.y - lo.y, 2), "height_m": round(hi.z - lo.z, 2),
            "wheels": sorted(o.name for o in objs if o.name.startswith("wheel_")),
        }
        built[name] = objs
        print(f"[hb] {name:15s} {tris:5d} tris (LOD1 {tris_lod1:5d}) budget {budget} "
              f"{hi.x - lo.x:.2f} x {hi.y - lo.y:.2f} x {hi.z - lo.z:.2f} m", flush=True)
    for name, fn in CITY.items():
        objs = fn()
        lo, hi = bbox(objs)
        # city pieces sit apart from the vehicles in the scene
        for o in objs:
            o.location.x += 60
        export_glb(objs, OUT_C / f"{name}.glb")
        manifest["city"][name] = {"triangles": triangles(objs), "size_m": [round(v, 2) for v in (hi - lo)],
                                  "objects": sorted(o.name for o in objs)}
        for o in objs:
            o.location.x -= 60
        built[name] = objs
        print(f"[hb] {name:15s} {triangles(objs):5d} tris", flush=True)

    if RENDER:
        cam, _ = studio()
        everything = [o for objs in built.values() for o in objs]
        for o in everything:
            o.hide_render = True
        for name, objs in built.items():
            for o in objs:
                o.hide_render = False
            frame(cam, objs)
            render(OUT_IMG / f"{name}.png")
            for o in objs:
                o.hide_render = True
        # lineup of all vehicles side by side (all facing forward), smallest to largest
        order = sorted(VEHICLES, key=lambda n: manifest["vehicles"][n]["length_m"])
        y = 0.0
        line = []
        for name in order:
            objs = built[name]
            wd = manifest["vehicles"][name]["width_m"]
            for o in objs:
                o.location.y += y + wd / 2
                o.hide_render = False
            y += wd + 0.9
            line += objs
        frame(cam, line, yaw_deg=62, pitch_deg=16, pad=0.78)
        bpy.context.scene.render.resolution_x, bpy.context.scene.render.resolution_y = 1800, 700
        render(OUT_IMG / "lineup.png")

    (ROOT / "apps/web/public/models/manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print("[hb] done", flush=True)


main()
