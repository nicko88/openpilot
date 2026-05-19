"""
Copyright (c) 2021-, rav4kumar, Haibin Wen, sunnypilot, and a number of other contributors.

This file is part of sunnypilot and is licensed under the MIT License.
See the LICENSE.md file in the root directory for more details.
"""
from openpilot.sunnypilot.selfdrive.controls.lib.radar_distance.radar_distance import (
  RadarDistanceController,
  _ACTIVATE_FRAMES,
  _A_CEIL_COAST,
  _DEACTIVATE_FRAMES,
)


class FakePoint:
  def __init__(self, track_id, d_rel, y_rel, v_rel, measured=True):
    self.trackId = track_id
    self.dRel = d_rel
    self.yRel = y_rel
    self.vRel = v_rel
    self.aRel = 0.0
    self.yvRel = 0.0
    self.measured = measured


class FakeTracks:
  def __init__(self, points):
    self.points = points


class FakeLead:
  def __init__(self, status=False):
    self.status = status


class FakeRadarState:
  def __init__(self, lead_status=False):
    self.leadOne = FakeLead(lead_status)
    self.leadTwo = FakeLead(False)


class FakeCarState:
  def __init__(self, v_ego):
    self.vEgo = v_ego


class FakeSM:
  def __init__(self, v_ego=20.0, lead_status=False):
    self._data = {
      'carState': FakeCarState(v_ego),
      'radarState': FakeRadarState(lead_status),
    }

  def __getitem__(self, k):
    return self._data[k]

  @property
  def data(self):
    return self._data


class FakeSmSp:
  def __init__(self, points):
    self._data = {'liveTracks': FakeTracks(points)}

  def __getitem__(self, k):
    return self._data[k]

  @property
  def data(self):
    return self._data


def _make(enabled=True):
  c = RadarDistanceController()
  c.set_enabled(enabled)
  return c


class TestRadarDistanceController:
  def test_disabled_returns_none(self):
    c = _make(enabled=False)
    c.update(FakeSM(), FakeSmSp([FakePoint(1, 80.0, 0.0, -3.0)]))
    assert c.get_accel_ceiling(20.0) is None

  def test_no_sm_safe(self):
    c = _make()
    c.update(None, None)
    assert c.get_accel_ceiling(20.0) is None

  def test_no_tracks_no_action(self):
    c = _make()
    c.update(FakeSM(), FakeSmSp([]))
    assert c.get_accel_ceiling(20.0) is None
    assert not c.active

  def test_lead_one_active_handoff(self):
    c = _make()
    pts = [FakePoint(7, 80.0, 0.0, -4.0)]
    for _ in range(_ACTIVATE_FRAMES + 2):
      c.update(FakeSM(lead_status=True), FakeSmSp(pts))
    assert c.get_accel_ceiling(20.0) is None

  def test_low_speed_no_action(self):
    c = _make()
    pts = [FakePoint(1, 80.0, 0.0, -4.0)]
    for _ in range(_ACTIVATE_FRAMES + 2):
      c.update(FakeSM(v_ego=2.0), FakeSmSp(pts))
    assert c.get_accel_ceiling(20.0) is None

  def test_off_lane_track_rejected(self):
    c = _make()
    pts = [FakePoint(1, 80.0, 3.0, -4.0)]  # |yRel| > 1.6
    for _ in range(_ACTIVATE_FRAMES + 5):
      c.update(FakeSM(), FakeSmSp(pts))
    assert c.get_accel_ceiling(20.0) is None

  def test_diverging_track_rejected(self):
    c = _make()
    pts = [FakePoint(1, 80.0, 0.0, 2.0)]  # opening, not closing
    for _ in range(_ACTIVATE_FRAMES + 5):
      c.update(FakeSM(), FakeSmSp(pts))
    assert c.get_accel_ceiling(20.0) is None

  def test_out_of_range_rejected(self):
    c = _make()
    near = [FakePoint(1, 20.0, 0.0, -4.0)]   # < 40m
    far = [FakePoint(2, 200.0, 0.0, -4.0)]   # > 150m
    for _ in range(_ACTIVATE_FRAMES + 5):
      c.update(FakeSM(), FakeSmSp(near))
    assert c.get_accel_ceiling(20.0) is None
    for _ in range(_ACTIVATE_FRAMES + 5):
      c.update(FakeSM(), FakeSmSp(far))
    assert c.get_accel_ceiling(20.0) is None

  def test_persistence_required(self):
    c = _make()
    pts = [FakePoint(1, 80.0, 0.0, -4.0)]  # ttc = 20s
    for _ in range(_ACTIVATE_FRAMES - 1):
      c.update(FakeSM(), FakeSmSp(pts))
    assert not c.active

  def test_lifts_gas_in_band(self):
    c = _make()
    pts = [FakePoint(1, 50.0, 0.0, -7.0)]  # ttc ~ 7.1s -> in 5-10 band
    for _ in range(_ACTIVATE_FRAMES + 60):
      c.update(FakeSM(), FakeSmSp(pts))
    ceiling = c.get_accel_ceiling(20.0)
    assert ceiling is not None
    assert ceiling <= 0.8
    assert ceiling >= _A_CEIL_COAST - 0.01

  def test_brake_band(self):
    c = _make()
    pts = [FakePoint(1, 45.0, 0.0, -12.0)]  # dRel in range, ttc = 3.75s -> brake band
    for _ in range(_ACTIVATE_FRAMES + 100):
      c.update(FakeSM(), FakeSmSp(pts))
    ceiling = c.get_accel_ceiling(20.0)
    assert ceiling is not None
    assert ceiling < _A_CEIL_COAST

  def test_releases_after_track_lost(self):
    c = _make()
    pts = [FakePoint(1, 50.0, 0.0, -7.0)]
    for _ in range(_ACTIVATE_FRAMES + 30):
      c.update(FakeSM(), FakeSmSp(pts))
    assert c.active
    for _ in range(_DEACTIVATE_FRAMES + 5):
      c.update(FakeSM(), FakeSmSp([]))
    assert not c.active
    assert c.get_accel_ceiling(20.0) is None

  def test_picks_lowest_ttc(self):
    c = _make()
    pts = [
      FakePoint(1, 100.0, 0.0, -2.0),  # ttc 50s
      FakePoint(2, 60.0,  0.0, -10.0), # ttc 6s
      FakePoint(3, 80.0,  0.0, -3.0),  # ttc ~27s
    ]
    for _ in range(_ACTIVATE_FRAMES + 5):
      c.update(FakeSM(), FakeSmSp(pts))
    assert c.track_id == 2
    assert c.ttc < 10.0

  def test_rate_limit_on_ceiling(self):
    c = _make()
    released = c.ceiling
    pts = [FakePoint(1, 30.0, 0.0, -8.0)]
    c.update(FakeSM(), FakeSmSp(pts))
    first_tick = c.ceiling
    assert abs(first_tick - released) < 0.05

  def test_unmeasured_track_rejected(self):
    c = _make()
    pts = [FakePoint(1, 80.0, 0.0, -4.0, measured=False)]
    for _ in range(_ACTIVATE_FRAMES + 5):
      c.update(FakeSM(), FakeSmSp(pts))
    assert not c.active
