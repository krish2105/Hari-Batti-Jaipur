"""Distilling an adaptive policy's stage choices into a fixed plan an officer can key in."""

from sim.opt.distil import distil, intergreen_states


def test_two_stage_policy_gives_its_split_and_cycle():
    # stage 0 for 10 decisions, stage 1 for 5, repeated 4 times; 6 s per decision
    seq = ([0] * 10 + [1] * 5) * 4
    cycle, greens = distil(seq, dt=6, intergreen_s=5, min_green_s=10)
    assert cycle == 90  # 360 s / 4 cycles
    assert [s for s, _ in greens] == [0, 1]
    g0, g1 = (g for _, g in greens)
    assert g0 + g1 == 90 - 2 * 5
    assert abs(g0 / (g0 + g1) - 2 / 3) < 0.05


def test_rarely_used_stages_are_dropped_and_min_green_holds():
    seq = ([0] * 20 + [2] * 1 + [1] * 3) * 5  # stage 2 is ~4% of the time
    cycle, greens = distil(seq, dt=6, intergreen_s=5, min_green_s=10)
    assert [s for s, _ in greens] == [0, 1]
    assert min(g for _, g in greens) >= 10
    assert 60 <= cycle <= 180


def test_amber_only_for_movements_that_lose_green():
    amber, allred = intergreen_states("GGrrg", "rGGrg")
    assert amber == "yGrrg"  # link 0 loses green; links 1 and 4 keep it
    assert allred == "rGrrg"
