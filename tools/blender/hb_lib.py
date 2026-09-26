"""HariBatti Blender helpers (run inside Blender: bpy + bmesh).

Everything is modelled in code so the asset set can be rebuilt with one command:
  Blender --background --factory-startup --python tools/blender/build_assets.py
Conventions (W7): metres, origin at ground centre, forward = +X, up = +Z (glTF export makes it
+Y up), one "palette" material with a shared 1024 px swatch texture, a "brake" material slot for
tail/brake lamps, separate wheel objects named wheel_*. Original generic designs — no logos.
"""

import math
from pathlib import Path

import bmesh
import bpy
from mathutils import Matrix, Vector

# ---------------------------------------------------------------- palette (8 x 8 swatches)
PALETTE: dict[str, tuple[float, float, float]] = {}
_ORDER = [
    # neutrals
    ("white", (0.93, 0.93, 0.91)), ("pearl", (0.84, 0.84, 0.82)), ("silver", (0.62, 0.64, 0.67)),
    ("grey", (0.38, 0.40, 0.43)), ("charcoal", (0.16, 0.17, 0.19)), ("black", (0.035, 0.037, 0.04)),
    ("tyre", (0.05, 0.05, 0.055)), ("chrome", (0.75, 0.77, 0.80)),
    # glass + lamps
    ("glass", (0.08, 0.12, 0.16)), ("glass_light", (0.22, 0.30, 0.36)), ("headlamp", (0.95, 0.93, 0.82)),
    ("indicator", (0.95, 0.55, 0.10)), ("tail", (0.55, 0.03, 0.03)), ("reflector", (0.85, 0.20, 0.10)),
    ("plate", (0.92, 0.90, 0.80)), ("plate_yellow", (0.93, 0.78, 0.18)),
    # car paints
    ("red", (0.55, 0.05, 0.06)), ("maroon", (0.30, 0.05, 0.07)), ("blue", (0.08, 0.20, 0.45)),
    ("navy", (0.05, 0.08, 0.20)), ("teal", (0.05, 0.32, 0.34)), ("brown", (0.30, 0.18, 0.10)),
    ("beige", (0.70, 0.62, 0.48)), ("gold", (0.62, 0.48, 0.22)),
    # autos / buses / trucks
    ("auto_green", (0.07, 0.36, 0.14)), ("auto_yellow", (0.93, 0.72, 0.08)), ("bus_pink", (0.85, 0.38, 0.47)),
    ("bus_white", (0.90, 0.88, 0.86)), ("truck_orange", (0.85, 0.35, 0.06)), ("truck_yellow", (0.90, 0.66, 0.10)),
    ("tractor_red", (0.62, 0.08, 0.05)), ("canvas", (0.40, 0.33, 0.18)),
    # materials
    ("wood", (0.42, 0.26, 0.13)), ("wood_dark", (0.26, 0.15, 0.07)), ("seat", (0.10, 0.08, 0.07)),
    ("rubber", (0.09, 0.09, 0.10)), ("steel", (0.45, 0.47, 0.50)), ("rust", (0.40, 0.18, 0.08)),
    ("hood_black", (0.06, 0.06, 0.07)), ("e_rick_blue", (0.12, 0.35, 0.65)),
    # people (riders)
    ("skin", (0.55, 0.36, 0.25)), ("shirt_white", (0.85, 0.85, 0.82)), ("shirt_blue", (0.20, 0.35, 0.60)),
    ("shirt_red", (0.60, 0.12, 0.10)), ("trouser", (0.12, 0.13, 0.18)), ("helmet", (0.10, 0.10, 0.12)),
    ("saree", (0.75, 0.15, 0.45)), ("turban", (0.90, 0.45, 0.10)),
    # city
    ("pink_wall", (0.83, 0.50, 0.44)), ("pink_light", (0.90, 0.64, 0.56)), ("terracotta", (0.68, 0.32, 0.28)),
    ("lime_white", (0.93, 0.88, 0.80)), ("sandstone", (0.78, 0.60, 0.42)), ("window_dark", (0.10, 0.07, 0.07)),
    ("shop_glow", (0.95, 0.72, 0.38)), ("awning", (0.20, 0.35, 0.30)),
    ("pole_green", (0.12, 0.25, 0.18)), ("signal_body", (0.08, 0.09, 0.10)), ("lamp_red", (0.90, 0.10, 0.08)),
    ("lamp_amber", (0.95, 0.60, 0.05)), ("lamp_green", (0.10, 0.80, 0.35)), ("led_off", (0.10, 0.10, 0.10)),
    ("concrete", (0.60, 0.58, 0.55)), ("dome_white", (0.95, 0.93, 0.90)),
]
for _i, (_n, _c) in enumerate(_ORDER):
    PALETTE[_n] = _c
SWATCH = {name: i for i, (name, _) in enumerate(_ORDER)}
# (roughness, metallic) per swatch for the glTF metallic-roughness texture; default = matte paint
SURFACE = {name: (0.55, 0.0) for name in SWATCH}
for _n in ("red", "maroon", "blue", "navy", "teal", "brown", "beige", "gold", "white", "pearl", "silver", "grey",
           "charcoal", "black", "auto_green", "auto_yellow", "bus_pink", "bus_white", "truck_orange",
           "truck_yellow", "tractor_red", "e_rick_blue"):
    SURFACE[_n] = (0.32, 0.25)  # glossy car paint
for _n in ("glass", "glass_light"):
    SURFACE[_n] = (0.06, 0.1)
for _n in ("chrome", "steel"):
    SURFACE[_n] = (0.18, 1.0)
for _n in ("tyre", "rubber", "seat", "trouser", "canvas", "hood_black", "wood", "wood_dark", "concrete",
           "pink_wall", "pink_light", "terracotta", "lime_white", "sandstone"):
    SURFACE[_n] = (0.88, 0.0)
for _n in ("headlamp", "indicator", "tail", "reflector", "lamp_red", "lamp_amber", "lamp_green"):
    SURFACE[_n] = (0.15, 0.0)
GRID = 8
TEX_PX = 1024


def swatch_uv(name: str) -> tuple[float, float]:
    """UV coordinate at the centre of a colour swatch."""
    i = SWATCH[name]
    col, row = i % GRID, i // GRID
    return ((col + 0.5) / GRID, 1 - (row + 0.5) / GRID)


def _swatch_image(name: str, file: str, colour_of) -> bpy.types.Image:
    """A 1024 px image of flat swatches, saved as PNG next to this script and packed."""
    img = bpy.data.images.get(name) or bpy.data.images.new(name, TEX_PX, TEX_PX, alpha=False)
    px = [0.0] * (TEX_PX * TEX_PX * 4)
    cell = TEX_PX // GRID
    for sw, i in SWATCH.items():
        r, g, b = colour_of(sw)
        col, row = i % GRID, i // GRID
        y0 = TEX_PX - (row + 1) * cell
        for y in range(y0, y0 + cell):
            base = (y * TEX_PX + col * cell) * 4
            for x in range(cell):
                j = base + x * 4
                px[j : j + 4] = [r, g, b, 1.0]
    img.pixels.foreach_set(px)
    img.update()
    path = Path(__file__).resolve().parent / file
    img.filepath_raw = str(path)
    img.file_format = "PNG"
    img.save()
    img.source = "FILE"
    img.reload()
    img.pack()
    return img


def palette_image() -> bpy.types.Image:
    """Base colours (sRGB)."""
    img = _swatch_image("hb_palette", "palette.png", lambda n: PALETTE[n])
    img.colorspace_settings.name = "sRGB"
    return img


GLOW = {"shop_glow": 1.0, "headlamp": 1.0, "lamp_red": 1.0, "lamp_amber": 1.0, "lamp_green": 1.0,
        "indicator": 0.6, "tail": 0.7}


def emission_image() -> bpy.types.Image:
    """Emission mask for the website (dusk theme): lit shops and lamps keep their colour, the rest is black."""
    img = _swatch_image("hb_emission", "palette_em.png",
                        lambda n: tuple(c * GLOW[n] for c in PALETTE[n]) if n in GLOW else (0.0, 0.0, 0.0))
    img.colorspace_settings.name = "sRGB"
    return img


def surface_image() -> bpy.types.Image:
    """glTF metallic-roughness texture: G = roughness, B = metalness (linear)."""
    img = _swatch_image("hb_surface", "palette_mr.png", lambda n: (0.0, SURFACE[n][0], SURFACE[n][1]))
    img.colorspace_settings.name = "Non-Color"
    return img


_MATS: dict[str, bpy.types.Material] = {}


def palette_material() -> bpy.types.Material:
    if "palette" in _MATS:
        return _MATS["palette"]
    m = bpy.data.materials.new("palette")
    m.use_nodes = True
    nt = m.node_tree
    bsdf = nt.nodes.get("Principled BSDF")
    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.image = palette_image()
    tex.interpolation = "Closest"
    nt.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
    mr = nt.nodes.new("ShaderNodeTexImage")
    mr.image = surface_image()
    mr.interpolation = "Closest"
    sep = nt.nodes.new("ShaderNodeSeparateColor")
    nt.links.new(mr.outputs["Color"], sep.inputs["Color"])
    nt.links.new(sep.outputs["Green"], bsdf.inputs["Roughness"])  # glTF exporter packs these into one
    nt.links.new(sep.outputs["Blue"], bsdf.inputs["Metallic"])  # metallicRoughnessTexture
    _MATS["palette"] = m
    return m


def brake_material() -> bpy.types.Material:
    """Tail/brake lamps: the website drives this slot's emission per vehicle."""
    if "brake" in _MATS:
        return _MATS["brake"]
    m = bpy.data.materials.new("brake")
    m.use_nodes = True
    bsdf = m.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (0.6, 0.02, 0.02, 1)
    bsdf.inputs["Emission Color"].default_value = (1.0, 0.05, 0.03, 1)
    bsdf.inputs["Emission Strength"].default_value = 0.6
    bsdf.inputs["Roughness"].default_value = 0.3
    _MATS["brake"] = m
    return m


# ---------------------------------------------------------------- mesh building


class Part:
    """Accumulates faces for one object, each face tagged with a palette colour."""

    def __init__(self, name: str):
        self.name = name
        self.bm = bmesh.new()
        self.uv = self.bm.loops.layers.uv.new("UVMap")
        self.brake_faces: list[bmesh.types.BMFace] = []

    def _colour(self, faces, colour: str, brake: bool = False):
        u, v = swatch_uv(colour)
        for f in faces:
            for loop in f.loops:
                loop[self.uv].uv = (u, v)
            if brake:
                self.brake_faces.append(f)

    def add_verts_faces(self, verts: list[tuple], faces: list[tuple], colour: str, brake: bool = False):
        vs = [self.bm.verts.new(v) for v in verts]
        new = []
        for f in faces:
            try:
                new.append(self.bm.faces.new([vs[i] for i in f]))
            except ValueError:
                pass
        self._colour(new, colour, brake)
        return new

    def box(self, size, loc, colour: str, brake: bool = False, taper: float = 0.0, rot_z: float = 0.0,
            rot_y: float = 0.0, rot_x: float = 0.0):
        """Box (sx, sy, sz) centred at loc; taper shrinks the top face (0..1); optional rotations."""
        sx, sy, sz = (s / 2 for s in size)
        tx, ty = sx * (1 - taper), sy * (1 - taper)
        v = [(-sx, -sy, -sz), (sx, -sy, -sz), (sx, sy, -sz), (-sx, sy, -sz),
             (-tx, -ty, sz), (tx, -ty, sz), (tx, ty, sz), (-tx, ty, sz)]
        rot = Matrix.Rotation(rot_z, 3, "Z") @ Matrix.Rotation(rot_y, 3, "Y") @ Matrix.Rotation(rot_x, 3, "X")
        v = [tuple(rot @ Vector(p) + Vector(loc)) for p in v]
        f = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
        return self.add_verts_faces(v, f, colour, brake)

    def rod(self, a, b, thickness: float, colour: str):
        """Thin square bar from point a to point b (frames, handles, pillars)."""
        va, vb = Vector(a), Vector(b)
        d = vb - va
        length = d.length
        q = Vector((1, 0, 0)).rotation_difference(d.normalized())
        t = thickness / 2
        base = [(0, -t, -t), (length, -t, -t), (length, t, -t), (0, t, -t),
                (0, -t, t), (length, -t, t), (length, t, t), (0, t, t)]
        v = [tuple(q @ Vector(p) + va) for p in base]
        f = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
        return self.add_verts_faces(v, f, colour)

    def prism(self, profile: list[tuple[float, float]], a0: float, a1: float, colour: str,
              side_colour: str | None = None, cap_colours: list[str] | None = None, axis: str = "Y",
              tuck: float = 0.0):
        """Extrude a 2D silhouette across a0..a1.

        axis="Y": profile is (x, z), a side view, extruded across the width.
        axis="X": profile is (y, z), a front view, extruded along the length.
        Profiles are counter-clockwise. cap_colours gives one colour per profile edge
        (e.g. windscreen glass, roof paint, rear glass)."""
        n = len(profile)
        if axis == "Y":
            zs = [z for _, z in profile]
            z_lo, z_hi = min(zs), max(zs)

            def inset(z):  # tumblehome: the sides lean in by `tuck` metres at the top
                return tuck * (z - z_lo) / max(1e-6, z_hi - z_lo)

            verts = [(u, a0 + inset(z), z) for u, z in profile] + [(u, a1 - inset(z), z) for u, z in profile]
        else:
            verts = [(a0, u, z) for u, z in profile] + [(a1, u, z) for u, z in profile]
        side = [tuple(range(n))[::-1], tuple(range(n, 2 * n))]
        if axis == "X":
            side = [s[::-1] for s in side]
        self.add_verts_faces(verts, side, side_colour or colour)
        out = []
        for i in range(n):
            f = (i, (i + 1) % n, n + (i + 1) % n, n + i)
            if axis == "X":
                f = f[::-1]
            out += self.add_verts_faces(verts, [f], (cap_colours[i] if cap_colours else colour))
        return out

    def cylinder(self, radius: float, width: float, loc, colour: str, axis: str = "Y", segments: int = 16,
                 cap_colour: str | None = None, hub: float = 0.0, hub_colour: str = "chrome"):
        """Cylinder along an axis (wheels: axis Y). Optional hub ring on both caps."""
        cx, cy, cz = loc
        ring0, ring1 = [], []
        for k in range(segments):
            a = 2 * math.pi * k / segments
            c, s = math.cos(a) * radius, math.sin(a) * radius
            if axis == "Y":
                ring0.append((cx + c, cy - width / 2, cz + s)); ring1.append((cx + c, cy + width / 2, cz + s))
            elif axis == "X":
                ring0.append((cx - width / 2, cy + c, cz + s)); ring1.append((cx + width / 2, cy + c, cz + s))
            else:
                ring0.append((cx + c, cy + s, cz - width / 2)); ring1.append((cx + c, cy + s, cz + width / 2))
        verts = ring0 + ring1
        n = segments
        sides = [(i, (i + 1) % n, n + (i + 1) % n, n + i) for i in range(n)]
        self.add_verts_faces(verts, sides, colour)
        if hub > 0:
            # caps as an outer tyre ring + inner hub disc
            for ring, sign in ((ring0, -1), (ring1, 1)):
                inner = []
                for x, y, z in ring:
                    if axis == "Y":
                        inner.append((cx + (x - cx) * hub, y + sign * 0.004, cz + (z - cz) * hub))
                    else:
                        inner.append((x, y, z))
                vs = ring + inner
                faces = [(i, (i + 1) % n, n + (i + 1) % n, n + i) for i in range(n)]
                self.add_verts_faces(vs, faces if sign > 0 else [f[::-1] for f in faces], cap_colour or colour)
                self.add_verts_faces(inner, [tuple(range(n)) if sign > 0 else tuple(range(n))[::-1]], hub_colour)
        else:
            self.add_verts_faces(verts, [tuple(range(n))[::-1], tuple(range(n, 2 * n))], cap_colour or colour)

    def dome(self, radius: float, loc, colour: str, segments: int = 12, rings: int = 4, squash: float = 1.0):
        cx, cy, cz = loc
        verts, faces = [], []
        for r in range(rings + 1):
            phi = (math.pi / 2) * r / rings
            for k in range(segments):
                a = 2 * math.pi * k / segments
                verts.append((cx + radius * math.cos(phi) * math.cos(a), cy + radius * math.cos(phi) * math.sin(a),
                              cz + radius * squash * math.sin(phi)))
        for r in range(rings):
            for k in range(segments):
                a, b = r * segments + k, r * segments + (k + 1) % segments
                faces.append((a, b, b + segments, a + segments))
        self.add_verts_faces(verts, faces, colour)

    def finish(self, collection=None, smooth_angle: float = 0.0) -> bpy.types.Object:
        """Create the Blender object with palette + brake materials."""
        mesh = bpy.data.meshes.new(self.name)
        for f in self.brake_faces:
            f.material_index = 1
        bmesh.ops.recalc_face_normals(self.bm, faces=list(self.bm.faces))
        self.bm.to_mesh(mesh)
        self.bm.free()
        mesh.materials.append(palette_material())
        mesh.materials.append(brake_material())
        obj = bpy.data.objects.new(self.name, mesh)
        (collection or bpy.context.scene.collection).objects.link(obj)
        # smooth by angle: round parts (wheels, domes, helmets) shade smoothly, hard edges stay crisp
        mesh.shade_smooth()
        mesh.set_sharp_from_angle(angle=math.radians(35))
        return obj


def wheel(name: str, radius: float, width: float, loc, collection, segments: int = 16, rim: str = "silver"):
    """A separate wheel object named wheel_* with its origin at the axle (for rotation)."""
    p = Part(name)
    p.cylinder(radius, width, (0, 0, 0), "tyre", axis="Y", segments=segments, cap_colour="tyre", hub=0.6,
               hub_colour=rim)
    obj = p.finish(collection)
    obj.location = loc
    return obj


def new_collection(name: str) -> bpy.types.Collection:
    col = bpy.data.collections.new(name)
    bpy.context.scene.collection.children.link(col)
    return col


def triangles(objs) -> int:
    n = 0
    for o in objs:
        if o.type == "MESH":
            n += sum(len(p.vertices) - 2 for p in o.data.polygons)
    return n
