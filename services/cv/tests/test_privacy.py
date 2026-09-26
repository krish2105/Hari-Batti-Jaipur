"""Privacy zones: plates on motor vehicles, heads of riders and pedestrians; pixelation changes only them."""

import numpy as np

from hbcv.privacy import pixelate, zones


def test_car_gets_a_plate_band_but_no_head_zone():
    z = zones(np.array([[100, 100, 300, 200]]), ["Sedan"])
    assert len(z) == 1
    x1, y1, x2, y2 = z[0]
    assert y2 == 200 and 150 <= y1 <= 170 and x1 > 100 and x2 < 300


def test_two_wheeler_gets_plate_and_head_zones_bicycle_only_head():
    assert len(zones(np.array([[0, 0, 50, 100]]), ["Two-wheeler"])) == 2
    z = zones(np.array([[0, 0, 50, 100]]), ["Bicycle"])
    assert z == [(0, 0, 50, 40)]


def test_person_head_zone():
    assert zones(np.zeros((0, 4)), [], persons=np.array([[10, 10, 30, 110]])) == [(10, 10, 30, 38)]


def test_pixelate_changes_only_the_zone():
    rng = np.random.default_rng(0)
    frame = rng.integers(0, 255, (100, 100, 3), dtype=np.uint8)
    before = frame.copy()
    pixelate(frame, (20, 20, 60, 60))
    assert not np.array_equal(frame[20:60, 20:60], before[20:60, 20:60])
    assert np.array_equal(frame[:20], before[:20]) and np.array_equal(frame[60:], before[60:])
