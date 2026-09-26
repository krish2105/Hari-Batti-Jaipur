"""Distil an adaptive controller into a fixed plan per time of day (readable for officers).

From the stage chosen at every decision step: keep stages used at least 5% of the time (in ring
order), cycle = time / number of times the most-used stage starts again (60-180 s, 5-s steps),
greens shared in proportion to the time each stage was held, never below the minimum green.
"""

from collections import Counter

MIN_SHARE = 0.05


def distil(
    seq: list[int], dt: float, intergreen_s: int, min_green_s: int
) -> tuple[int, list[tuple[int, int]]]:
    """(cycle s, [(stage, green s), ...]) from a sequence of chosen stages, one per dt seconds."""
    total = len(seq) * dt
    share = {s: n / len(seq) for s, n in Counter(seq).items()}
    kept = sorted(s for s, v in share.items() if v >= MIN_SHARE)
    main = max(kept, key=lambda s: share[s])
    starts = sum(1 for i, s in enumerate(seq) if s == main and (i == 0 or seq[i - 1] != main))
    cycle = int(min(180, max(60, round(total / max(1, starts) / 5) * 5)))
    green = cycle - intergreen_s * len(kept)
    w = sum(share[s] for s in kept)
    greens = {s: max(min_green_s, round(green * share[s] / w)) for s in kept}
    greens[main] += green - sum(greens.values())  # keep the cycle exact
    return cycle, [(s, greens[s]) for s in kept]


def intergreen_states(a: str, b: str) -> tuple[str, str]:
    """Amber and all-red states between stage a and stage b: movements green in a but not in b
    turn amber, then red; movements green in both keep their green."""
    amber = "".join(
        "y" if x in "Gg" and y not in "Gg" else (x if x in "Gg" else "r") for x, y in zip(a, b, strict=True)
    )
    allred = "".join(x if x in "Gg" and y in "Gg" else "r" for x, y in zip(a, b, strict=True))
    return amber, allred
