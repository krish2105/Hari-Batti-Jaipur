"""Green-wave maths: bandwidth of a band of green through every junction, and offset search."""

from sim.opt.greenwave import Junction, bandwidth, best_common_plan, common_plan, optimise_offsets


def js(offsets, green=30, cycle=60, spacing=500):
    return [Junction(f"J{i}", i * spacing, green, o) for i, o in enumerate(offsets)]


def test_one_junction_band_is_its_green():
    assert bandwidth(js([0]), cycle=60, speed_ms=10, direction="east") == 30


def test_perfect_progression_keeps_the_full_green():
    # 500 m at 10 m/s = 50 s: offsets 0, 50, 100 (mod 60 = 40) give a full-width eastbound band
    j = js([0, 50, 40])
    assert bandwidth(j, 60, 10, "east") == 30


def test_zero_offsets_lose_band_when_travel_time_is_not_a_cycle_multiple():
    assert bandwidth(js([0, 0, 0]), 60, 10, "east") < 30


def test_westbound_uses_the_opposite_travel_direction():
    j = js([40, 50, 0])  # progression built for a car starting at the east end
    assert bandwidth(j, 60, 10, "west") == 30


def test_search_beats_zero_offsets_for_both_directions():
    j = js([0, 0, 0, 0])
    best = optimise_offsets(j, 60, 10, restarts=5, seed=1)
    before = bandwidth(j, 60, 10, "east") + bandwidth(j, 60, 10, "west")
    after = bandwidth(best, 60, 10, "east") + bandwidth(best, 60, 10, "west")
    assert after >= before
    assert best[0].offset == 0  # the first junction is the reference


def test_common_plan_uses_the_longest_cycle_and_keeps_green_shares():
    plans = {"A": (60, 38, 12), "B": (117, 62, 45)}  # cycle, main green, cross green
    c, greens = common_plan(plans, intergreen_s=10)
    assert c == 120  # longest cycle, rounded up to 5 s
    main_a, cross_a = greens["A"]
    assert main_a + cross_a == c - 10
    assert abs(main_a / (main_a + cross_a) - 38 / 50) < 0.03


def test_cycle_search_finds_two_way_progression():
    # 500 m at 10 m/s = 50 s per link: a 100 s cycle lets offsets alternate for both directions
    plans = {f"J{i}": (60, 40, 10) for i in range(4)}
    xs = {f"J{i}": i * 500.0 for i in range(4)}
    cycle, js = best_common_plan(plans, xs, intergreen_s=10, speed_ms=10, max_cycle=120, restarts=3)
    assert bandwidth(js, cycle, 10, "east") > 0 and bandwidth(js, cycle, 10, "west") > 0
