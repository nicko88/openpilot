"""
Copyright (c) 2021-, rav4kumar, Haibin Wen, sunnypilot, and a number of other contributors.

This file is part of sunnypilot and is licensed under the MIT License.
See the LICENSE.md file in the root directory for more details.
"""
from openpilot.sunnypilot.selfdrive.controls.lib.dynamic_personality.dynamic_follow import (
  FollowDistanceController,
  CLOSING_BOOST_DELTA,
)


class FakeLead:
  def __init__(self, d_rel=40.0, v_lead=15.0, a_lead=0.0, a_tau=0.0, model_prob=1.0):
    self.status = True
    self.dRel = d_rel
    self.vLead = v_lead
    self.vRel = 0.0
    self.aLeadK = a_lead
    self.aLeadTau = a_tau
    self.modelProb = model_prob


class FakeRadarState:
  def __init__(self, lead=None):
    self.leadOne = lead if lead is not None else FakeLead()


def _make():
  df = FollowDistanceController()
  df.set_enabled(True)
  return df


def _run(df, lead_kwargs, v_ego, n_frames):
  for _ in range(n_frames):
    lead = FakeLead(**lead_kwargs)
    df.update()
    df.get_follow_distance_multiplier(v_ego, FakeRadarState(lead))


class TestClosingBoost:
  def test_fires_at_strong_closing(self):
    df = _make()
    _run(df, dict(d_rel=50.0, v_lead=15.0, a_lead=-0.1, model_prob=1.0), 20.0, 5)
    assert df._dbg.closing_boost > 0.0

  def test_saturates_at_delta(self):
    df = _make()
    _run(df, dict(d_rel=50.0, v_lead=10.0, a_lead=-0.1, model_prob=1.0), 20.0, 5)
    assert abs(df._dbg.closing_boost - CLOSING_BOOST_DELTA) < 1e-6

  def test_blocked_by_mild_closing(self):
    df = _make()
    _run(df, dict(d_rel=50.0, v_lead=18.0, a_lead=-0.1, model_prob=1.0), 20.0, 5)
    assert df._dbg.closing_boost == 0.0

  def test_blocked_by_low_mprob(self):
    df = _make()
    _run(df, dict(d_rel=50.0, v_lead=15.0, a_lead=-0.1, model_prob=0.7), 20.0, 5)
    assert df._dbg.closing_boost == 0.0

  def test_blocked_when_too_far(self):
    df = _make()
    _run(df, dict(d_rel=120.0, v_lead=15.0, a_lead=-0.1, model_prob=1.0), 20.0, 5)
    assert df._dbg.closing_boost == 0.0

  def test_blocked_at_low_speed(self):
    df = _make()
    _run(df, dict(d_rel=50.0, v_lead=2.0, a_lead=-0.1, model_prob=1.0), 5.0, 5)
    assert df._dbg.closing_boost == 0.0

  def test_boost_path_includes_closing(self):
    df = _make()
    df.update()
    _run(df, dict(d_rel=50.0, v_lead=18.0, a_lead=0.0, model_prob=1.0), 20.0, 5)
    baseline = df._alead_rate_boost
    _run(df, dict(d_rel=50.0, v_lead=15.0, a_lead=0.0, model_prob=1.0), 20.0, 25)
    assert df._dbg.closing_boost > 0.0
    assert df._alead_rate_boost > baseline + 0.05
