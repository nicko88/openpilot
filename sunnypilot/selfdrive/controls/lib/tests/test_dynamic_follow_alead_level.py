"""
Copyright (c) 2021-, rav4kumar, Haibin Wen, sunnypilot, and a number of other contributors.

This file is part of sunnypilot and is licensed under the MIT License.
See the LICENSE.md file in the root directory for more details.
"""
from openpilot.sunnypilot.selfdrive.controls.lib.dynamic_personality.dynamic_follow import (
  FollowDistanceController,
  ALEAD_LEVEL_DELTA,
)


class FakeLead:
  def __init__(self, d_rel=40.0, v_lead=19.0, a_lead=-0.6, a_tau=0.0, model_prob=1.0):
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


class TestAleadLevelAnticipator:
  def test_fires_on_sustained_mild_brake(self):
    df = _make()
    _run(df, dict(d_rel=40.0, v_lead=19.0, a_lead=-0.6, model_prob=1.0), 20.0, 15)
    assert df._alead_level_armed
    assert df._dbg.alead_level == ALEAD_LEVEL_DELTA

  def test_fires_at_refined_threshold(self):
    df = _make()
    _run(df, dict(d_rel=40.0, v_lead=19.0, a_lead=-0.46, model_prob=1.0), 20.0, 15)
    assert df._alead_level_armed

  def test_blocked_by_weak_vrel(self):
    df = _make()
    _run(df, dict(d_rel=40.0, v_lead=19.9, a_lead=-0.6, model_prob=1.0), 20.0, 15)
    assert not df._alead_level_armed
    assert df._dbg.alead_level == 0.0

  def test_blocked_by_low_mprob(self):
    df = _make()
    _run(df, dict(d_rel=40.0, v_lead=19.0, a_lead=-0.6, model_prob=0.7), 20.0, 15)
    assert not df._alead_level_armed

  def test_blocked_when_too_far(self):
    df = _make()
    _run(df, dict(d_rel=95.0, v_lead=19.0, a_lead=-0.6, model_prob=1.0), 20.0, 15)
    assert not df._alead_level_armed

  def test_blocked_when_too_near(self):
    df = _make()
    _run(df, dict(d_rel=8.0, v_lead=7.0, a_lead=-0.6, model_prob=1.0), 20.0, 15)
    assert not df._alead_level_armed

  def test_fires_at_refined_drel_min(self):
    df = _make()
    _run(df, dict(d_rel=11.0, v_lead=11.0, a_lead=-0.6, model_prob=1.0), 13.0, 15)
    assert df._alead_level_armed

  def test_blocked_at_low_speed(self):
    df = _make()
    _run(df, dict(d_rel=40.0, v_lead=4.0, a_lead=-0.6, model_prob=1.0), 5.0, 15)
    assert not df._alead_level_armed

  def test_ignores_single_frame_spike(self):
    df = _make()
    df.update()
    _run(df, dict(d_rel=40.0, v_lead=19.0, a_lead=-0.2, model_prob=1.0), 20.0, 5)
    lead = FakeLead(d_rel=40.0, v_lead=19.0, a_lead=-2.0, model_prob=1.0)
    df.update()
    df.get_follow_distance_multiplier(20.0, FakeRadarState(lead))
    _run(df, dict(d_rel=40.0, v_lead=19.0, a_lead=-0.2, model_prob=1.0), 20.0, 2)
    assert not df._alead_level_armed

  def test_cooldown_blocks_immediate_retrigger(self):
    df = _make()
    _run(df, dict(d_rel=40.0, v_lead=19.0, a_lead=-0.6, model_prob=1.0), 20.0, 15)
    assert df._alead_level_armed
    _run(df, dict(d_rel=40.0, v_lead=19.0, a_lead=0.0, model_prob=1.0), 20.0, 10)
    assert not df._alead_level_armed
    assert df._alead_level_cooldown > 0
    _run(df, dict(d_rel=40.0, v_lead=19.0, a_lead=-0.6, model_prob=1.0), 20.0, 5)
    assert not df._alead_level_armed

  def test_output_capped_at_delta(self):
    df = _make()
    df.update()
    peak = 0.0
    for _ in range(20):
      lead = FakeLead(d_rel=40.0, v_lead=19.0, a_lead=-4.0, model_prob=1.0)
      df.update()
      df.get_follow_distance_multiplier(20.0, FakeRadarState(lead))
      peak = max(peak, df._dbg.alead_level)
    assert peak <= ALEAD_LEVEL_DELTA + 1e-6
    assert peak > 0.0

  def test_disarm_requires_sustained_release(self):
    df = _make()
    _run(df, dict(d_rel=40.0, v_lead=19.0, a_lead=-0.6, model_prob=1.0), 20.0, 15)
    assert df._alead_level_armed
    lead = FakeLead(d_rel=40.0, v_lead=19.0, a_lead=0.0, model_prob=1.0)
    df.update()
    df.get_follow_distance_multiplier(20.0, FakeRadarState(lead))
    lead = FakeLead(d_rel=40.0, v_lead=19.0, a_lead=-0.6, model_prob=1.0)
    df.update()
    df.get_follow_distance_multiplier(20.0, FakeRadarState(lead))
    assert df._alead_level_armed

  def test_state_resets_when_lead_lost(self):
    df = _make()
    _run(df, dict(d_rel=40.0, v_lead=19.0, a_lead=-0.6, model_prob=1.0), 20.0, 15)
    assert df._alead_level_armed
    for _ in range(30):
      df.update()
      df.get_follow_distance_multiplier(20.0, None)
    assert not df._alead_level_armed
    assert df._alead_level_sustain == 0
    assert df._alead_level_cooldown == 0

  def test_boost_path_engages_on_armed(self):
    df = _make()
    df.update()
    _run(df, dict(d_rel=40.0, v_lead=19.0, a_lead=-0.2, model_prob=1.0), 20.0, 10)
    baseline_boost = df._alead_rate_boost
    _run(df, dict(d_rel=40.0, v_lead=19.0, a_lead=-0.6, model_prob=1.0), 20.0, 25)
    assert df._alead_level_armed
    assert df._alead_rate_boost > baseline_boost + 0.05
