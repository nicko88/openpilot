"""
Copyright (c) 2021-, rav4kumar, Haibin Wen, sunnypilot, and a number of other contributors.

This file is part of sunnypilot and is licensed under the MIT License.
See the LICENSE.md file in the root directory for more details.

Verify production param->controller path: UI writes Params directly, and
controllers pick up the change inside their own update() loop within
PARAM_REFRESH_FRAMES (~1s @ DT_MDL). No set_enabled() call required.
"""
from cereal import custom, log

from openpilot.common.params import Params

from openpilot.sunnypilot.selfdrive.controls.lib.accel_personality.accel_controller import (
  AccelPersonalityController,
  PARAM_REFRESH_FRAMES as ACCEL_REFRESH,
)
from openpilot.sunnypilot.selfdrive.controls.lib.dynamic_personality.dynamic_follow import (
  FollowDistanceController,
  PARAM_REFRESH_FRAMES as DF_REFRESH,
)
from openpilot.sunnypilot.selfdrive.controls.lib.radar_distance.radar_distance import (
  RadarDistanceController,
  _PARAM_REFRESH_FRAMES as RD_REFRESH,
)

AccelPersonality = custom.LongitudinalPlanSP.AccelerationPersonality
LongPersonality = log.LongitudinalPersonality


class FakeCarState:
  def __init__(self, v_cruise=30.0):
    self.vCruise = v_cruise


class FakeSM:
  def __init__(self, v_cruise=30.0):
    self._data = {'carState': FakeCarState(v_cruise)}

  def __getitem__(self, k):
    return self._data[k]


class TestAccelPersonalityLiveFlip:
  def test_enable_via_param(self):
    Params().put_bool('AccelPersonalityEnabled', False)
    c = AccelPersonalityController()
    assert not c.is_enabled()

    Params().put_bool('AccelPersonalityEnabled', True)
    for _ in range(ACCEL_REFRESH + 1):
      c.update(FakeSM())
    assert c.is_enabled()

  def test_enable_transition_snaps_to_target(self):
    """Toggling OFF→ON mid-route must snap a_min/a_max to fresh targets,
    not rate-limit from stale state left over from prior activation."""
    Params().put_bool('AccelPersonalityEnabled', True)
    Params().put('AccelPersonality', AccelPersonality.sport)
    c = AccelPersonalityController()
    for _ in range(ACCEL_REFRESH + 1):
      c.update(FakeSM(v_cruise=35.0))
    c.get_accel_limits(25.0)  # warm

    Params().put_bool('AccelPersonalityEnabled', False)
    for _ in range(ACCEL_REFRESH + 1):
      c.update(FakeSM(v_cruise=35.0))
    assert not c.is_enabled()

    Params().put('AccelPersonality', AccelPersonality.eco)
    Params().put_bool('AccelPersonalityEnabled', True)
    for _ in range(ACCEL_REFRESH + 1):
      c.update(FakeSM(v_cruise=35.0))
    assert c._first  # reset on transition so next step snaps

  def test_vcruise_unset_treated_as_zero(self):
    """When carState.vCruise = V_CRUISE_UNSET (cruise not engaged), _v_cruise
    must clamp to 0 instead of being read as ~70 m/s and misdriving the
    cruise-deficit logic."""
    from openpilot.selfdrive.car.cruise import V_CRUISE_UNSET
    Params().put_bool('AccelPersonalityEnabled', True)
    c = AccelPersonalityController()
    c.update(FakeSM(v_cruise=V_CRUISE_UNSET))
    assert c._v_cruise == 0.0

  def test_disable_via_param(self):
    Params().put_bool('AccelPersonalityEnabled', True)
    c = AccelPersonalityController()
    assert c.is_enabled()

    Params().put_bool('AccelPersonalityEnabled', False)
    for _ in range(ACCEL_REFRESH + 1):
      c.update(FakeSM())
    assert not c.is_enabled()

  def test_personality_change_via_param(self):
    Params().put('AccelPersonality', AccelPersonality.normal)
    c = AccelPersonalityController()
    assert c.get_accel_personality() == AccelPersonality.normal

    Params().put('AccelPersonality', AccelPersonality.sport)
    for _ in range(ACCEL_REFRESH + 1):
      c.update(FakeSM())
    assert c.get_accel_personality() == AccelPersonality.sport

  def test_refresh_boundary_below_threshold(self):
    Params().put_bool('AccelPersonalityEnabled', False)
    c = AccelPersonalityController()
    Params().put_bool('AccelPersonalityEnabled', True)
    for _ in range(ACCEL_REFRESH - 1):
      c.update(FakeSM())
    assert not c.is_enabled()


class TestDynamicFollowLiveFlip:
  def test_enable_via_param(self):
    Params().put_bool('DynamicFollow', False)
    df = FollowDistanceController()
    assert not df.is_enabled()

    Params().put_bool('DynamicFollow', True)
    for _ in range(DF_REFRESH + 1):
      df.update()
    assert df.is_enabled()

  def test_disable_via_param(self):
    Params().put_bool('DynamicFollow', True)
    df = FollowDistanceController()
    assert df.is_enabled()

    Params().put_bool('DynamicFollow', False)
    for _ in range(DF_REFRESH + 1):
      df.update()
    assert not df.is_enabled()

  def test_personality_change_via_param_triggers_cooldown(self):
    Params().put('LongitudinalPersonality', LongPersonality.standard)
    df = FollowDistanceController()
    starting = df._personality

    Params().put('LongitudinalPersonality', LongPersonality.aggressive)
    for _ in range(DF_REFRESH + 1):
      df.update()
    assert df._personality == LongPersonality.aggressive
    assert df._personality != starting
    assert df._cooldown > 0


class TestRadarDistanceLiveFlip:
  def test_enable_via_param(self):
    Params().put_bool('RadarDistance', False)
    c = RadarDistanceController()
    assert not c.is_enabled()

    Params().put_bool('RadarDistance', True)
    for _ in range(RD_REFRESH + 1):
      c.update(None, None)
    assert c.is_enabled()

  def test_disable_via_param(self):
    Params().put_bool('RadarDistance', True)
    c = RadarDistanceController()
    assert c.is_enabled()

    Params().put_bool('RadarDistance', False)
    for _ in range(RD_REFRESH + 1):
      c.update(None, None)
    assert not c.is_enabled()
