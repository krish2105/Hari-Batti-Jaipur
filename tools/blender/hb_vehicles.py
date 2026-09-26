"""HariBatti vehicle set: original, generic low-poly models of Jaipur traffic (no brands or logos).

Real-world sizes in metres (typical Indian vehicles), forward = +X, left = +Y (India drives on
the left, so bus doors are on +Y), origin at ground centre. Each builder returns the objects of
one model: a body object plus separate wheel_* objects.
"""

import math

from hb_lib import Part, new_collection, wheel


def _arch(cx: float, r: float, ra: float, sill: float, steps: int = 5) -> list[tuple[float, float]]:
    """Points along a wheel-arch cut-out (left to right) for a side silhouette."""
    pts = [(cx - ra, sill), (cx - ra, r)]
    for k in range(1, steps):
        t = math.pi - math.pi * k / steps
        pts.append((cx + ra * math.cos(t), r + ra * math.sin(t)))
    pts += [(cx + ra, r), (cx + ra, sill)]
    return pts


def rider(p: Part, x: float, seat_z: float, shirt: str = "shirt_blue", helmet: bool = True, lean: float = 0.25,
          hands_x: float | None = None, hands_z: float | None = None, y: float = 0.0):
    """A seated rider with human proportions: seat to head top is about 0.88 m."""
    p.box((0.40, 0.30, 0.13), (x + 0.14, y, seat_z + 0.07), "trouser")  # thighs
    for s in (1, -1):
        p.rod((x + 0.32, y + s * 0.10, seat_z + 0.05), (x + 0.38, y + s * 0.13, seat_z - 0.36), 0.095, "trouser")
        p.box((0.22, 0.09, 0.06), (x + 0.44, y + s * 0.13, seat_z - 0.39), "charcoal")  # shoes
    tilt = -lean * 0.6
    p.box((0.22, 0.36, 0.50), (x + 0.02 + lean * 0.12, y, seat_z + 0.38), shirt, taper=-0.08, rot_y=tilt)  # torso
    sx, sz = x + 0.04 + lean * 0.25, seat_z + 0.58  # shoulders
    hx = hands_x if hands_x is not None else x + 0.55
    hz = hands_z if hands_z is not None else seat_z + 0.40
    for s in (1, -1):
        elbow = ((sx + hx) / 2 + 0.02, y + s * 0.24, (sz + hz) / 2 - 0.06)
        p.rod((sx, y + s * 0.19, sz), elbow, 0.075, shirt)
        p.rod(elbow, (hx, y + s * 0.22, hz), 0.065, "skin")
    p.box((0.10, 0.11, 0.08), (sx, y, sz + 0.07), "skin")  # neck
    if helmet:
        p.dome(0.135, (sx + 0.01, y, sz + 0.13), "helmet", segments=12, rings=4, squash=1.2)
        p.box((0.05, 0.19, 0.06), (sx + 0.13, y, sz + 0.19), "glass")  # visor
    else:
        p.dome(0.11, (sx, y, sz + 0.12), "skin", segments=10, rings=3, squash=1.15)
        p.dome(0.125, (sx, y, sz + 0.21), "turban", segments=10, rings=2, squash=0.7)


def _car(name: str, L: float, W: float, H: float, wb: float, r: float, style: str, paint: str):
    col = new_collection(name)
    p = Part(f"{name}_body")
    x0, x1, wr, wf = -L / 2, L / 2, -wb / 2, wb / 2
    sill, belt = r * 0.72, H * (0.60 if style == "suv" else 0.56)
    ra = r * 1.16
    hood = {"hatch": 0.95, "sedan": 1.15, "suv": 1.05}[style]
    lower = [(x0 + 0.06, sill + 0.10)] + _arch(wr, r, ra, sill) + _arch(wf, r, ra, sill) + [
        (x1 - 0.10, sill + 0.08), (x1, sill + 0.30), (x1 - 0.03, belt - 0.14), (x1 - 0.40, belt - 0.03),
        (x1 - hood, belt), (x0 + (0.30 if style == "sedan" else 0.08), belt + 0.01),
        (x0 + 0.02, belt - 0.16), (x0, sill + 0.30),
    ]
    half = W / 2
    p.prism(lower, -half, half, paint)
    gh = half - 0.10
    ws = x1 - hood
    if style == "hatch":
        green = [(x0 + 0.12, belt), (ws, belt), (ws - 0.80, H), (x0 + 0.36, H - 0.02), (x0 + 0.08, belt + 0.28)]
        caps = [paint, "glass", paint, "glass", paint]
    elif style == "sedan":
        green = [(x0 + 0.78, belt), (ws, belt), (ws - 0.82, H), (x0 + 1.36, H - 0.03), (x0 + 0.72, belt + 0.03)]
        caps = [paint, "glass", paint, "glass", paint]
    else:
        green = [(x0 + 0.12, belt), (ws, belt), (ws - 0.62, H), (x0 + 0.16, H), (x0 + 0.08, belt + 0.12)]
        caps = [paint, "glass", paint, "glass", paint]
    p.prism(green, -gh, gh, paint, side_colour="glass", cap_colours=caps, tuck=0.13)
    # pillars over the side glass (B and C), roof trim
    bx = (ws - 0.6 + x0 + 0.5) / 2
    for s in (1, -1):
        p.box((0.09, 0.02, H - belt - 0.04), (bx, s * (gh - 0.058), (H + belt) / 2), paint, rot_x=s * 0.26)
        p.box((0.10, 0.18, 0.08), (ws - 0.05, s * (half + 0.06), belt + 0.06), paint)  # mirror
        p.box((0.05, 0.14, 0.05), (ws - 0.02, s * (half + 0.10), belt + 0.06), "glass_light")
        p.box((0.02, 0.28, 0.12), (x1 - 0.03, s * (half - 0.26), belt - 0.18), "headlamp")
        p.box((0.03, 0.22, 0.10), (x0 + 0.02, s * (half - 0.22), belt - 0.16), "tail", brake=True)
        p.box((0.03, 0.06, 0.04), (x1 - 0.05, s * (half - 0.08), sill + 0.34), "indicator")
        p.box((0.30, 0.02, 0.03), (bx - 0.35, s * (half + 0.004), belt - 0.12), "chrome")  # door handle line
    p.box((0.10, W * 0.98, 0.20), (x1 - 0.02, 0, sill + 0.18), "charcoal")  # front bumper
    p.box((0.10, W * 0.98, 0.20), (x0 + 0.02, 0, sill + 0.18), "charcoal")  # rear bumper
    p.box((0.03, W * 0.46, 0.13), (x1 - 0.005, 0, belt - 0.24), "black")  # grille
    p.box((0.02, 0.50, 0.11), (x1 + 0.03, 0, sill + 0.20), "plate")
    p.box((0.02, 0.50, 0.11), (x0 - 0.03, 0, sill + 0.30), "plate")
    if style == "suv":
        for s in (1, -1):
            p.box((L * 0.55, 0.04, 0.04), (x0 + L * 0.42, s * (gh - 0.08), H + 0.03), "silver")
    body = p.finish(col)
    wheels = [wheel(f"wheel_{n}", r, 0.19, (x, s * (half - 0.12), r), col)
              for n, x, s in (("fl", wf, 1), ("fr", wf, -1), ("rl", wr, 1), ("rr", wr, -1))]
    return [body, *wheels]


def hatchback():
    return _car("hatchback", 3.80, 1.68, 1.52, 2.45, 0.29, "hatch", "red")


def sedan():
    return _car("sedan", 4.40, 1.73, 1.48, 2.60, 0.30, "sedan", "silver")


def suv():
    return _car("suv", 4.45, 1.82, 1.76, 2.65, 0.35, "suv", "white")


def scooter():
    col = new_collection("scooter")
    p = Part("scooter_body")
    r, wb = 0.25, 1.28
    p.box((0.62, 0.30, 0.06), (0.05, 0, 0.30), "charcoal")  # floorboard
    rear = [(-0.95, 0.40), (-0.18, 0.34), (-0.12, 0.62), (-0.40, 0.80), (-0.90, 0.78), (-1.02, 0.62)]
    p.prism(rear, -0.20, 0.20, "blue")
    p.box((0.62, 0.26, 0.08), (-0.55, 0, 0.83), "seat")
    apron = [(0.34, 0.30), (0.52, 0.34), (0.60, 0.90), (0.48, 1.00), (0.36, 0.82)]
    p.prism(apron, -0.19, 0.19, "blue")
    p.rod((0.56, 0, 0.95), (0.66, 0, 0.25), 0.06, "charcoal")  # fork
    p.box((0.10, 0.62, 0.05), (0.50, 0, 1.08), "black")  # handlebar
    p.box((0.10, 0.20, 0.12), (0.57, 0, 1.03), "blue")
    p.box((0.03, 0.12, 0.08), (0.62, 0, 1.03), "headlamp")
    p.box((0.03, 0.14, 0.05), (-1.03, 0, 0.66), "tail", brake=True)
    p.box((0.28, 0.20, 0.03), (0.66, 0, 0.52), "blue")  # front mudguard
    for s in (1, -1):
        p.box((0.05, 0.05, 0.10), (0.46, s * 0.33, 1.14), "chrome")  # mirrors
    rider(p, -0.48, 0.87, shirt="shirt_blue", helmet=True, lean=0.15, hands_x=0.46, hands_z=1.07)
    return [p.finish(col), wheel("wheel_f", r, 0.10, (wb / 2, 0, r), col, segments=14),
            wheel("wheel_r", r, 0.10, (-wb / 2, 0, r), col, segments=14)]


def motorcycle():
    col = new_collection("motorcycle")
    p = Part("motorcycle_body")
    r, wb = 0.31, 1.30
    tank = [(-0.05, 0.78), (0.42, 0.80), (0.38, 0.98), (0.02, 1.00)]
    p.prism(tank, -0.16, 0.16, "maroon")
    p.box((0.62, 0.26, 0.08), (-0.40, 0, 0.86), "seat")
    p.box((0.40, 0.24, 0.30), (0.12, 0, 0.52), "grey")  # engine
    p.cylinder(0.05, 0.80, (-0.35, -0.16, 0.36), "chrome", axis="X", segments=8)  # exhaust
    p.rod((0.02, 0, 0.60), (-0.62, 0, 0.36), 0.05, "charcoal")  # swing arm
    p.rod((0.55, 0, 1.00), (0.66, 0, 0.30), 0.06, "chrome")  # fork
    p.box((0.08, 0.70, 0.04), (0.50, 0, 1.12), "black")
    p.box((0.12, 0.18, 0.16), (0.62, 0, 0.98), "black")
    p.box((0.03, 0.14, 0.12), (0.68, 0, 0.98), "headlamp")
    p.box((0.30, 0.20, 0.05), (-0.78, 0, 0.78), "maroon")  # tail cowl
    p.box((0.03, 0.12, 0.05), (-0.93, 0, 0.78), "tail", brake=True)
    p.box((0.30, 0.16, 0.03), (0.66, 0, 0.60), "maroon")
    rider(p, -0.36, 0.90, shirt="shirt_red", helmet=True, lean=0.35, hands_x=0.48, hands_z=1.12)
    return [p.finish(col), wheel("wheel_f", r, 0.10, (wb / 2 + 0.02, 0, r), col, segments=16),
            wheel("wheel_r", r, 0.12, (-wb / 2, 0, r), col, segments=16)]


def auto_rickshaw():
    col = new_collection("auto_rickshaw")
    p = Part("auto_rickshaw_body")
    L, W = 2.63, 1.30
    base = [(-1.28, 0.28), (0.90, 0.28), (1.26, 0.40), (1.28, 0.75), (1.05, 0.80), (-1.30, 0.78)]
    p.prism(base, -W / 2, W / 2, "auto_green")
    nose = [(-0.58, 0.28), (0.58, 0.28), (0.40, 0.90), (-0.40, 0.90)]  # front is narrower (plan taper)
    p.prism(nose, 0.95, 1.30, "auto_green", axis="X")
    # canopy: rounded roof cross-section extruded along the length
    roof = [(-0.66, 1.48), (0.66, 1.48), (0.63, 1.68), (0.42, 1.80), (-0.42, 1.80), (-0.63, 1.68)]
    p.prism(roof, -1.30, 0.80, "auto_yellow", axis="X")
    p.box((0.05, 1.05, 0.66), (0.95, 0, 1.12), "glass", taper=0.08)  # windscreen
    p.box((0.08, 1.20, 0.10), (0.95, 0, 1.48), "auto_yellow")
    for s in (1, -1):
        p.rod((0.92, s * 0.58, 0.80), (0.82, s * 0.62, 1.48), 0.05, "black")  # front pillars
        p.rod((-1.25, s * 0.62, 0.78), (-1.25, s * 0.64, 1.48), 0.05, "black")  # rear pillars
        p.box((1.60, 0.03, 0.08), (-0.30, s * 0.66, 1.48), "black")  # canopy edge
        p.box((0.03, 0.10, 0.06), (-1.31, s * 0.48, 0.66), "tail", brake=True)
        p.box((0.05, 0.05, 0.08), (0.80, s * 0.55, 1.12), "chrome")
    p.box((0.70, 1.10, 0.18), (-0.80, 0, 0.88), "seat")  # passenger bench
    p.box((0.12, 1.10, 0.40), (-1.12, 0, 1.08), "seat")
    p.box((0.05, 0.16, 0.10), (1.29, 0, 0.62), "headlamp")
    p.box((0.02, 0.40, 0.09), (-1.32, 0, 0.44), "plate_yellow")  # commercial plate
    p.box((0.05, 0.60, 0.04), (0.62, 0, 1.02), "black")  # handlebar
    rider(p, 0.22, 0.74, shirt="shirt_white", helmet=False, lean=0.05, hands_x=0.62, hands_z=1.02)
    return [p.finish(col), wheel("wheel_f", 0.21, 0.10, (1.00, 0, 0.21), col, segments=12),
            wheel("wheel_rl", 0.21, 0.12, (-0.72, 0.58, 0.21), col, segments=12),
            wheel("wheel_rr", 0.21, 0.12, (-0.72, -0.58, 0.21), col, segments=12)]


def e_rickshaw():
    col = new_collection("e_rickshaw")
    p = Part("e_rickshaw_body")
    W = 1.00
    p.box((2.10, W, 0.10), (-0.20, 0, 0.38), "charcoal")  # floor
    front = [(0.72, 0.33), (1.10, 0.36), (1.18, 0.85), (1.00, 1.10), (0.78, 1.05)]
    p.prism(front, -0.42, 0.42, "e_rick_blue")
    p.box((0.04, 0.84, 0.55), (0.96, 0, 1.35), "glass_light", taper=0.05)
    roof = [(-0.54, 1.86), (0.54, 1.86), (0.50, 1.96), (-0.50, 1.96)]
    p.prism(roof, -1.30, 1.06, "e_rick_blue", axis="X")
    for x in (1.00, -1.25):
        for s in (1, -1):
            p.rod((x, s * 0.47, 0.42), (x, s * 0.49, 1.86), 0.04, "silver")
    p.box((0.70, 0.95, 0.12), (-0.55, 0, 0.78), "seat")
    p.box((0.10, 0.95, 0.38), (-0.92, 0, 1.02), "seat")
    p.box((0.50, 0.95, 0.10), (-0.05, 0, 0.78), "seat")
    for s in (1, -1):
        p.box((1.9, 0.02, 0.10), (-0.20, s * 0.50, 0.50), "white")
        p.box((0.03, 0.08, 0.06), (-1.27, s * 0.38, 0.56), "tail", brake=True)
    p.box((0.04, 0.14, 0.10), (1.17, 0, 0.72), "headlamp")
    p.box((0.02, 0.34, 0.08), (-1.27, 0, 0.46), "plate_yellow")
    rider(p, 0.30, 0.86, shirt="shirt_white", helmet=False, lean=0.0, hands_x=0.78, hands_z=1.06)
    return [p.finish(col), wheel("wheel_f", 0.22, 0.09, (0.95, 0, 0.22), col, segments=12),
            wheel("wheel_rl", 0.22, 0.10, (-0.95, 0.46, 0.22), col, segments=12),
            wheel("wheel_rr", 0.22, 0.10, (-0.95, -0.46, 0.22), col, segments=12)]


def _boxy(name: str, L: float, W: float, H: float, axles: list[float], r: float, lower: str, upper: str,
          nose: float, window_band: tuple[float, float], door_side: bool = True):
    """Buses and vans: a tall body with arches, a glass band, a raked windscreen."""
    col = new_collection(name)
    p = Part(f"{name}_body")
    x0, x1 = -L / 2, L / 2
    sill = r * 0.75
    ra = r * 1.14
    bottom = [(x0 + 0.05, sill + 0.08)]
    for ax in sorted(axles):
        bottom += _arch(ax, r, ra, sill)
    prof = bottom + [(x1 - 0.05, sill + 0.06), (x1, sill + 0.50), (x1 - nose * 0.3, window_band[0]),
                     (x1 - nose, H - 0.12), (x1 - nose - 0.25, H), (x0 + 0.20, H), (x0, H - 0.20)]
    half = W / 2
    p.prism(prof, -half, half, lower, tuck=0.04)
    zb0, zb1 = window_band
    for s in (1, -1):
        p.box((L - nose - 0.9, 0.03, zb1 - zb0), (x0 + (L - nose - 0.9) / 2 + 0.3, s * (half + 0.01), (zb0 + zb1) / 2),
              "glass")
        n_posts = int((L - nose - 1.0) / 1.25)
        for k in range(n_posts + 1):
            xp = x0 + 0.35 + k * (L - nose - 1.0) / max(1, n_posts)
            p.box((0.08, 0.035, zb1 - zb0), (xp, s * (half + 0.012), (zb0 + zb1) / 2), upper)
        p.box((L - 0.3, 0.03, 0.22), (0, s * (half + 0.012), zb0 - 0.20), upper)  # livery stripe
        p.box((0.03, 0.24, 0.16), (x0 - 0.01, s * (half - 0.20), sill + 0.60), "tail", brake=True)
        p.box((0.03, 0.28, 0.14), (x1 + 0.01, s * (half - 0.28), sill + 0.42), "headlamp")
        p.box((0.12, 0.10, 0.20), (x1 - nose * 0.4, s * (half + 0.12), zb0 + 0.15), "black")  # mirror
    p.box((0.04, W - 0.20, H - zb0 - 0.25), (x1 - nose * 0.65, 0, (zb0 + H - 0.1) / 2), "glass", rot_y=-0.25)
    p.box((0.04, W - 0.30, zb1 - zb0 - 0.2), (x0 - 0.01, 0, (zb0 + zb1) / 2), "glass")
    p.box((L - 0.4, W - 0.2, 0.06), (0, 0, H + 0.02), upper)  # roof cap
    if door_side:
        for xd in (x1 - nose - 0.9, x0 + L * 0.42):
            p.box((0.95, 0.04, H - sill - 0.35), (xd, half + 0.02, (sill + H - 0.35) / 2 + 0.1), "glass_light")
    p.box((0.10, W, 0.28), (x1, 0, sill + 0.22), "charcoal")
    p.box((0.10, W, 0.28), (x0, 0, sill + 0.22), "charcoal")
    p.box((0.02, 0.50, 0.12), (x1 + 0.06, 0, sill + 0.30), "plate_yellow")
    body = p.finish(col)
    wheels = []
    for i, ax in enumerate(sorted(axles, reverse=True)):
        for s, side in ((1, "l"), (-1, "r")):
            wheels.append(wheel(f"wheel_{i}{side}", r, 0.28, (ax, s * (half - 0.22), r), col, segments=16))
    return [body, *wheels]


def city_bus():
    return _boxy("city_bus", 12.0, 2.55, 3.20, [3.95, -3.05], 0.50, "bus_pink", "bus_white", 0.55, (1.35, 2.60))


def mini_bus():
    return _boxy("mini_bus", 6.9, 2.05, 2.62, [2.10, -1.95], 0.37, "bus_white", "blue", 1.10, (1.20, 2.10))


def lcv_tempo():
    col = new_collection("lcv_tempo")
    p = Part("lcv_tempo_body")
    r = 0.34
    cab = [(1.30, 0.40), (2.28, 0.40), (2.32, 1.10), (2.05, 1.95), (1.30, 1.98)]
    p.prism(cab, -0.86, 0.86, "white", cap_colours=["charcoal", "white", "glass", "white", "white"])
    p.box((0.03, 1.40, 0.55), (2.16, 0, 1.55), "glass", rot_y=-0.35)
    for s in (1, -1):
        p.box((0.55, 0.02, 0.45), (1.72, s * 0.87, 1.55), "glass")
        p.box((0.03, 0.24, 0.12), (2.33, s * 0.60, 0.95), "headlamp")
        p.box((0.10, 0.08, 0.16), (2.10, s * 0.95, 1.50), "black")
    p.box((3.40, 1.75, 0.12), (-0.45, 0, 0.72), "charcoal")  # chassis/bed floor
    for s in (1, -1):
        p.box((3.30, 0.05, 0.50), (-0.45, s * 0.86, 1.02), "blue")  # drop sides
        p.box((0.03, 0.12, 0.10), (-2.16, s * 0.70, 0.90), "tail", brake=True)
    p.box((0.05, 1.72, 0.50), (-2.13, 0, 1.02), "blue")  # tailgate
    p.box((0.05, 1.72, 0.80), (1.25, 0, 1.18), "white")  # headboard
    for k, c in enumerate(["beige", "brown", "beige"]):  # a generic load of sacks
        p.box((0.70, 0.75, 0.38), (-1.6 + k * 0.85, 0.35 - 0.7 * (k % 2), 0.98), c)
    p.box((0.02, 0.46, 0.11), (2.34, 0, 0.62), "plate_yellow")
    body = p.finish(col)
    return [body] + [wheel(f"wheel_{n}", r, 0.20, (x, s * 0.72, r), col)
                     for n, x, s in (("fl", 1.75, 1), ("fr", 1.75, -1), ("rl", -1.10, 1), ("rr", -1.10, -1))]


def truck():
    col = new_collection("truck")
    p = Part("truck_body")
    r = 0.52
    cab = [(2.55, 0.62), (4.45, 0.62), (4.50, 1.60), (4.30, 3.00), (2.55, 3.05)]
    p.prism(cab, -1.24, 1.24, "truck_orange", cap_colours=["charcoal", "truck_orange", "glass", "truck_orange", "truck_orange"])
    p.box((0.04, 2.0, 0.85), (4.38, 0, 2.45), "glass", rot_y=-0.12)
    for s in (1, -1):
        p.box((0.70, 0.02, 0.60), (3.55, s * 1.25, 2.45), "glass")
        p.box((0.04, 0.30, 0.16), (4.51, s * 0.85, 1.20), "headlamp")
        p.box((0.12, 0.10, 0.30), (4.30, s * 1.36, 2.40), "black")
    p.box((0.30, 2.4, 0.25), (4.45, 0, 0.75), "chrome")  # bumper
    p.box((6.9, 2.3, 0.18), (-0.95, 0, 1.00), "charcoal")  # chassis
    # cargo body: the painted, high-sided Indian truck body (generic pattern, no text)
    body_prof = [(-4.45, 1.10), (2.45, 1.10), (2.45, 3.25), (-4.45, 3.25)]
    p.prism(body_prof, -1.25, 1.25, "truck_yellow")
    for s in (1, -1):
        for k in range(5):
            p.box((1.20, 0.03, 0.12), (-3.8 + k * 1.4, s * 1.265, 2.0 + 0.4 * (k % 2)), ["red", "blue", "auto_green"][k % 3])
        p.box((6.9, 0.035, 0.10), (-1.0, s * 1.265, 3.18), "wood")
        p.box((0.03, 0.18, 0.14), (-4.47, s * 1.05, 1.30), "tail", brake=True)
    p.box((0.05, 2.45, 2.0), (-4.47, 0, 2.2), "wood_dark")  # tailgate
    p.box((0.02, 0.52, 0.12), (4.60, 0, 0.95), "plate_yellow")
    body = p.finish(col)
    wheels = []
    for i, ax in enumerate((3.40, -2.40, -3.60)):
        for s, side in ((1, "l"), (-1, "r")):
            wheels.append(wheel(f"wheel_{i}{side}", r, 0.30, (ax, s * 1.02, r), col, segments=16))
    return [body, *wheels]


def tractor():
    col = new_collection("tractor")
    p = Part("tractor_body")
    hood = [(-0.30, 0.70), (1.55, 0.70), (1.60, 1.25), (1.35, 1.40), (-0.30, 1.42)]
    p.prism(hood, -0.36, 0.36, "tractor_red")
    p.box((0.05, 0.50, 0.40), (1.62, 0, 1.00), "black")  # grille
    for s in (1, -1):
        p.box((0.04, 0.12, 0.10), (1.63, s * 0.24, 1.20), "headlamp")
    p.box((1.0, 0.60, 0.55), (-0.70, 0, 0.95), "grey")  # transmission
    for s in (1, -1):
        fender = [(-1.55, 1.20), (-0.10, 1.20), (-0.25, 1.42), (-0.80, 1.52), (-1.40, 1.44)]
        y0, y1 = (0.62, 0.98) if s > 0 else (-0.98, -0.62)
        p.prism(fender, y0, y1, "tractor_red")
        p.box((0.03, 0.08, 0.08), (-1.55, s * 0.80, 1.30), "tail", brake=True)
    p.box((0.40, 0.46, 0.10), (-0.85, 0, 1.52), "seat")
    p.box((0.10, 0.46, 0.35), (-1.05, 0, 1.72), "seat")
    p.rod((-0.25, 0, 1.45), (-0.45, 0, 1.85), 0.04, "black")
    p.cylinder(0.17, 0.03, (-0.45, 0, 1.87), "black", axis="Z", segments=12)  # steering wheel
    p.cylinder(0.05, 0.9, (0.95, 0.22, 1.85), "steel", axis="Z", segments=8)  # exhaust stack
    rider(p, -0.95, 1.55, shirt="shirt_white", helmet=False, lean=0.05, hands_x=-0.45, hands_z=1.86)
    body = p.finish(col)
    return [body,
            wheel("wheel_rl", 0.72, 0.38, (-0.80, 0.80, 0.72), col, segments=18, rim="truck_yellow"),
            wheel("wheel_rr", 0.72, 0.38, (-0.80, -0.80, 0.72), col, segments=18, rim="truck_yellow"),
            wheel("wheel_fl", 0.38, 0.18, (1.15, 0.62, 0.38), col, segments=14, rim="truck_yellow"),
            wheel("wheel_fr", 0.38, 0.18, (1.15, -0.62, 0.38), col, segments=14, rim="truck_yellow")]


def bicycle():
    col = new_collection("bicycle")
    p = Part("bicycle_body")
    r = 0.34
    rear, front, crank = (-0.52, 0, r), (0.55, 0, r), (0.0, 0, 0.30)
    seat, head = (-0.12, 0, 0.88), (0.42, 0, 0.92)
    for a, b in ((rear, crank), (crank, seat), (seat, rear), (crank, head), (seat, head), (head, front)):
        p.rod(a, b, 0.035, "black")
    p.box((0.22, 0.12, 0.05), (-0.12, 0, 0.92), "seat")
    p.box((0.05, 0.55, 0.03), (0.40, 0, 1.02), "chrome")
    p.box((0.30, 0.20, 0.03), (-0.52, 0, 0.72), "black")  # carrier
    p.box((0.02, 0.06, 0.04), (-0.68, 0, 0.72), "reflector", brake=True)
    rider(p, -0.16, 0.95, shirt="shirt_white", helmet=False, lean=0.2, hands_x=0.40, hands_z=1.02)
    return [p.finish(col), wheel("wheel_f", r, 0.04, front, col, segments=18),
            wheel("wheel_r", r, 0.04, rear, col, segments=18)]


def cycle_rickshaw():
    col = new_collection("cycle_rickshaw")
    p = Part("cycle_rickshaw_body")
    r = 0.34
    p.rod((0.95, 0, r), (0.62, 0, 1.0), 0.04, "black")  # fork
    p.rod((0.62, 0, 1.0), (0.10, 0, 0.95), 0.04, "black")
    p.rod((0.10, 0, 0.95), (0.25, 0, 0.35), 0.04, "black")
    p.rod((0.25, 0, 0.35), (-0.30, 0, 0.55), 0.05, "black")
    p.box((0.95, 1.15, 0.06), (-0.62, 0, 0.62), "wood")  # rear platform
    p.box((0.55, 1.05, 0.14), (-0.62, 0, 0.92), "seat")  # passenger seat
    p.box((0.10, 1.05, 0.45), (-0.92, 0, 1.12), "seat")
    hood = [(-0.55, 0.95), (0.55, 0.95), (0.55, 1.35), (0.42, 1.68), (-0.42, 1.68), (-0.55, 1.35)]
    p.prism(hood, -1.05, -0.62, "hood_black", axis="X")
    p.box((0.18, 0.12, 0.05), (0.10, 0, 1.00), "seat")
    p.box((0.05, 0.60, 0.03), (0.60, 0, 1.08), "chrome")
    for s in (1, -1):
        p.box((0.03, 0.06, 0.05), (-1.10, s * 0.45, 0.66), "reflector", brake=True)
    rider(p, 0.06, 1.02, shirt="shirt_white", helmet=False, lean=0.3, hands_x=0.58, hands_z=1.08)
    return [p.finish(col), wheel("wheel_f", r, 0.04, (0.95, 0, r), col, segments=16),
            wheel("wheel_rl", r, 0.05, (-0.62, 0.55, r), col, segments=16),
            wheel("wheel_rr", r, 0.05, (-0.62, -0.55, r), col, segments=16)]


def hand_cart():
    col = new_collection("hand_cart")
    p = Part("hand_cart_body")
    p.box((2.0, 1.00, 0.07), (-0.10, 0, 0.72), "wood")
    for s in (1, -1):
        p.box((2.0, 0.04, 0.16), (-0.10, s * 0.50, 0.82), "wood_dark")
        p.rod((0.90, s * 0.42, 0.72), (1.55, s * 0.42, 0.86), 0.05, "wood_dark")  # handles
        p.rod((-0.9, s * 0.40, 0.70), (-0.95, s * 0.40, 0.05), 0.04, "wood_dark")  # rest legs
    for k, c in enumerate(["gold", "red", "auto_green", "gold", "red", "gold"]):  # fruit baskets
        p.box((0.42, 0.40, 0.18), (-0.85 + (k % 3) * 0.55, 0.22 - 0.44 * (k // 3), 0.85), c, taper=0.2)
    return [p.finish(col), wheel("wheel_l", 0.34, 0.05, (0.15, 0.55, 0.34), col, segments=16),
            wheel("wheel_r", 0.34, 0.05, (0.15, -0.55, 0.34), col, segments=16)]


VEHICLES = {
    "scooter": scooter, "motorcycle": motorcycle, "auto_rickshaw": auto_rickshaw, "e_rickshaw": e_rickshaw,
    "hatchback": hatchback, "sedan": sedan, "suv": suv, "city_bus": city_bus, "mini_bus": mini_bus,
    "lcv_tempo": lcv_tempo, "truck": truck, "tractor": tractor, "bicycle": bicycle,
    "cycle_rickshaw": cycle_rickshaw, "hand_cart": hand_cart,
}
