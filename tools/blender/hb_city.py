"""HariBatti city modules: original Pink City pieces for the website (no copied buildings).

- bldg_jharokha: 3-storey pink block with projecting jharokha balconies and arched windows
- bldg_chhatri: rooftop chhatri pavilion (4 pillars and a dome)
- bldg_arcade: arcaded shopfront row with lit shops, awnings and a crenellated parapet
- signal_pole: signal pole with cantilever, 3 lamps (lamp_red / lamp_amber / lamp_green) and a
  countdown panel (countdown_panel) the website draws the LED digits on
Metres; origin at ground centre; the street-facing side is -Y.
"""

import math

from hb_lib import Part, new_collection


def _arched_window(p: Part, x: float, z: float, y: float, w: float = 0.9, h: float = 1.5):
    """Dark window niche with a pointed arch top, white lime trim around it."""
    p.box((w + 0.16, 0.06, h + 0.16), (x, y - 0.01, z), "lime_white")
    p.box((w, 0.08, h - w / 2), (x, y - 0.03, z - w / 4), "window_dark")
    arch = [(x - w / 2, z + h / 2 - w / 2), (x + w / 2, z + h / 2 - w / 2), (x + w * 0.3, z + h / 2 - w * 0.15),
            (x, z + h / 2), (x - w * 0.3, z + h / 2 - w * 0.15)]
    p.prism(arch, y - 0.07, y - 0.02, "window_dark")


def jharokha():
    col = new_collection("bldg_jharokha")
    p = Part("bldg_jharokha")
    W, D, H = 7.0, 8.0, 9.6
    p.box((W, D, H), (0, 0, H / 2), "pink_wall")
    y = -D / 2
    for f in range(3):
        z = 0.2 + f * 3.2
        p.box((W + 0.1, 0.12, 0.18), (0, y - 0.04, z + 3.0), "lime_white")  # floor band
        for k in (-2.2, 0.0, 2.2):
            if f == 0 and k == 0.0:
                p.box((1.4, 0.10, 2.4), (0, y - 0.03, 1.25), "wood_dark")  # door
                continue
            _arched_window(p, k, z + 1.7, y)
    for f in (1, 2):  # projecting jharokhas on the upper floors
        z = 0.2 + f * 3.2
        for k in (-2.2, 2.2):
            p.box((1.6, 0.9, 0.18), (k, y - 0.45, z + 0.75), "sandstone")  # corbel base
            p.box((1.4, 0.75, 1.2), (k, y - 0.42, z + 1.45), "pink_light")
            p.box((1.0, 0.05, 0.8), (k, y - 0.80, z + 1.5), "window_dark")
            p.box((1.7, 1.0, 0.12), (k, y - 0.45, z + 2.15), "lime_white")
            p.dome(0.55, (k, y - 0.45, z + 2.2), "pink_light", segments=10, rings=3, squash=0.7)
    for k in range(-3, 4):  # parapet merlons
        p.box((0.55, 0.3, 0.55), (k * 1.0, y + 0.15, H + 0.27), "terracotta")
    p.box((W, D, 0.25), (0, 0, H + 0.12), "terracotta")
    return [p.finish(col)]


def chhatri():
    col = new_collection("bldg_chhatri")
    p = Part("bldg_chhatri")
    p.box((2.6, 2.6, 0.30), (0, 0, 0.15), "sandstone")
    for sx in (1, -1):
        for sy in (1, -1):
            p.box((0.22, 0.22, 1.8), (sx * 1.0, sy * 1.0, 1.2), "lime_white")
    p.box((2.6, 2.6, 0.22), (0, 0, 2.2), "sandstone")
    p.box((2.9, 2.9, 0.08), (0, 0, 2.35), "lime_white")
    p.dome(1.1, (0, 0, 2.4), "dome_white", segments=14, rings=5, squash=1.05)
    p.box((0.10, 0.10, 0.45), (0, 0, 3.75), "gold", taper=0.6)  # finial
    return [p.finish(col)]


def arcade():
    col = new_collection("bldg_arcade")
    p = Part("bldg_arcade")
    W, D, H = 12.0, 9.0, 7.4
    y = -D / 2
    p.box((W, D - 2.0, H), (0, 1.0, H / 2), "pink_wall")  # building set back behind the arcade
    p.box((W, 2.0, 0.25), (0, y + 1.0, 3.6), "pink_light")  # arcade roof slab
    bays = 6
    for k in range(bays + 1):
        x = -W / 2 + k * W / bays
        p.box((0.45, 0.45, 3.5), (x, y + 0.25, 1.75), "pink_light")  # pillars
    for k in range(bays):
        x = -W / 2 + (k + 0.5) * W / bays
        arch = [(x - 0.8, 2.7), (x + 0.8, 2.7), (x + 0.8, 3.45), (x - 0.8, 3.45)]
        p.prism(arch, y + 0.02, y + 0.35, "pink_light")
        p.box((1.6, 0.05, 0.12), (x, y + 0.01, 2.72), "lime_white")
        p.box((1.55, 0.06, 2.4), (x, y + 2.02, 1.25), "shop_glow" if k % 2 == 0 else "steel")  # shop / shutter
        p.box((1.7, 0.9, 0.06), (x, y + 1.55, 2.55), "awning", rot_x=0.35)
        _arched_window(p, x, 5.4, y + 2.0, w=0.8, h=1.4)
    for k in range(-11, 12):
        p.box((0.45, 0.3, 0.5), (k * 0.52, y + 2.1, H + 0.25), "terracotta")
    p.box((W + 0.1, 0.1, 0.2), (0, y + 1.98, 4.2), "lime_white")
    return [p.finish(col)]


def signal_pole():
    col = new_collection("signal_pole")
    p = Part("signal_pole")
    p.box((0.5, 0.5, 0.25), (0, 0, 0.12), "concrete")
    # pole with black/yellow bands near the base
    p.cylinder(0.09, 5.2, (0, 0, 2.7), "charcoal", axis="Z", segments=12)
    for k in range(4):
        p.cylinder(0.095, 0.18, (0, 0, 0.45 + k * 0.36), "truck_yellow", axis="Z", segments=12)
    p.rod((0, 0, 5.0), (0, -3.2, 5.0), 0.10, "charcoal")  # cantilever over the road (-Y)
    parts = [p.finish(col)]
    # signal head on the cantilever and a second one on the pole, facing traffic (+X)
    for tag, (x, y, z) in (("arm", (0.18, -2.8, 4.6)), ("pole", (0.18, 0, 3.2))):
        h = Part(f"signal_head_{tag}")
        h.box((0.32, 0.42, 1.25), (x, y, z), "signal_body")
        for i, c in enumerate(("lamp_red", "lamp_amber", "lamp_green")):
            h.box((0.28, 0.40, 0.04), (x + 0.06, y, z + 0.52 - i * 0.40), "signal_body", rot_y=0.5)  # visor
        parts.append(h.finish(col))
        for i, c in enumerate(("lamp_red", "lamp_amber", "lamp_green")):
            lamp = Part(f"{c}_{tag}")
            lamp.cylinder(0.14, 0.03, (x + 0.17, y, z + 0.40 - i * 0.40), c, axis="X", segments=14)
            parts.append(lamp.finish(col))
    panel = Part("countdown_panel")
    panel.box((0.10, 0.60, 0.40), (0.18, 0, 2.35), "signal_body")
    panel.box((0.02, 0.52, 0.32), (0.24, 0, 2.35), "led_off")
    parts.append(panel.finish(col))
    return parts


CITY = {"bldg_jharokha": jharokha, "bldg_chhatri": chhatri, "bldg_arcade": arcade, "signal_pole": signal_pole}
_ = math
