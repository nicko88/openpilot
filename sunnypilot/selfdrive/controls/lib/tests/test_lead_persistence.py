"""
Copyright (c) 2021-, rav4kumar, Haibin Wen, sunnypilot, and a number of other contributors.

This file is part of sunnypilot and is licensed under the MIT License.
See the LICENSE.md file in the root directory for more details.
"""
from openpilot.sunnypilot.selfdrive.controls.lib.lead_persistence.lead_persistence import (
  LeadPersistence,
  _HOLD_FRAMES,
)


class FakeLead:
  def __init__(self, status=False, d_rel=0.0, v_rel=0.0, v_lead=0.0,
               a_lead=0.0, a_tau=0.0, model_prob=0.0, y_rel=0.0, a_rel=0.0, fcw=False):
    self.status = status
    self.dRel = d_rel
    self.yRel = y_rel
    self.vRel = v_rel
    self.vLead = v_lead
    self.aLeadK = a_lead
    self.aLeadTau = a_tau
    self.modelProb = model_prob
    self.aRel = a_rel
    self.fcw = fcw


class FakeRadarState:
  def __init__(self, lead_one=None, lead_two=None, extra='ok'):
    self.leadOne = lead_one or FakeLead()
    self.leadTwo = lead_two or FakeLead()
    self.extra = extra


def _make():
  return LeadPersistence()


class TestLeadPersistence:
  def test_disabled_passthrough(self):
    lp = _make()
    raw = FakeRadarState(lead_one=FakeLead(status=True, d_rel=30.0))
    lp.update(raw, force_enabled=False)
    out = lp.smooth(raw, force_enabled=False)
    assert out is raw

  def test_status_true_passthrough(self):
    lp = _make()
    raw = FakeRadarState(lead_one=FakeLead(status=True, d_rel=30.0, v_lead=20.0))
    for _ in range(3):
      lp.update(raw)
    out = lp.smooth(raw)
    # leadOne still truly present → passthrough (or wrapper with same .status=True)
    assert out.leadOne.status is True
    assert out.leadOne.dRel == 30.0

  def test_dropout_held(self):
    lp = _make()
    raw_on = FakeRadarState(lead_one=FakeLead(status=True, d_rel=30.0, v_lead=20.0, a_lead=-1.0))
    for _ in range(5):
      lp.update(raw_on)
    raw_off = FakeRadarState(lead_one=FakeLead(status=False))
    lp.update(raw_off)
    out = lp.smooth(raw_off)
    assert out.leadOne.status is True
    assert out.leadOne.dRel == 30.0
    assert out.leadOne.aLeadK == -1.0

  def test_dropout_expires(self):
    lp = _make()
    raw_on = FakeRadarState(lead_one=FakeLead(status=True, d_rel=30.0))
    for _ in range(5):
      lp.update(raw_on)
    raw_off = FakeRadarState(lead_one=FakeLead(status=False))
    for _ in range(_HOLD_FRAMES + 2):
      lp.update(raw_off)
    out = lp.smooth(raw_off)
    assert out.leadOne.status is False

  def test_reappearance_resets_hold(self):
    lp = _make()
    raw_on = FakeRadarState(lead_one=FakeLead(status=True, d_rel=30.0))
    for _ in range(5):
      lp.update(raw_on)
    raw_off = FakeRadarState(lead_one=FakeLead(status=False))
    for _ in range(3):
      lp.update(raw_off)
    raw_on2 = FakeRadarState(lead_one=FakeLead(status=True, d_rel=28.0))
    lp.update(raw_on2)
    out = lp.smooth(raw_on2)
    assert out.leadOne.status is True
    assert out.leadOne.dRel == 28.0

  def test_other_attrs_passthrough(self):
    lp = _make()
    raw_on = FakeRadarState(lead_one=FakeLead(status=True, d_rel=30.0), extra='special')
    for _ in range(3):
      lp.update(raw_on)
    raw_off = FakeRadarState(lead_one=FakeLead(status=False), extra='special2')
    lp.update(raw_off)
    out = lp.smooth(raw_off)
    assert out.extra == 'special2'

  def test_stability_high_on_solid_lead(self):
    lp = _make()
    raw = FakeRadarState(lead_one=FakeLead(status=True, d_rel=30.0))
    for _ in range(10):
      lp.update(raw)
    assert lp.stability >= 0.9

  def test_stability_low_on_churn(self):
    lp = _make()
    on = FakeRadarState(lead_one=FakeLead(status=True, d_rel=30.0))
    off = FakeRadarState(lead_one=FakeLead(status=False))
    for _ in range(10):
      lp.update(on)
      lp.update(off)
    assert lp.stability < 0.5

  def test_leadtwo_independent(self):
    lp = _make()
    raw_on = FakeRadarState(
      lead_one=FakeLead(status=True, d_rel=30.0),
      lead_two=FakeLead(status=True, d_rel=80.0),
    )
    for _ in range(5):
      lp.update(raw_on)
    raw_off2 = FakeRadarState(
      lead_one=FakeLead(status=True, d_rel=30.0),
      lead_two=FakeLead(status=False),
    )
    lp.update(raw_off2)
    out = lp.smooth(raw_off2)
    assert out.leadOne.status is True
    assert out.leadOne.dRel == 30.0
    assert out.leadTwo.status is True
    assert out.leadTwo.dRel == 80.0

  def test_reset(self):
    lp = _make()
    raw = FakeRadarState(lead_one=FakeLead(status=True, d_rel=30.0))
    for _ in range(5):
      lp.update(raw)
    lp.reset()
    raw_off = FakeRadarState(lead_one=FakeLead(status=False))
    lp.update(raw_off)
    out = lp.smooth(raw_off)
    assert out.leadOne.status is False

  def test_none_radarstate_decays_held_lead(self):
    """If radard daemon stops publishing, we must not serve a stale lead
    forever — the alive counters should decay frame by frame until expiry."""
    lp = _make()
    raw_on = FakeRadarState(lead_one=FakeLead(status=True, d_rel=30.0))
    for _ in range(5):
      lp.update(raw_on)
    assert lp._alive_one == _HOLD_FRAMES

    for i in range(_HOLD_FRAMES):
      lp.update(None)
      assert lp._alive_one == _HOLD_FRAMES - (i + 1)
    assert lp._alive_one == 0

  def test_disabled_clears_state_even_when_radarstate_none(self):
    lp = _make()
    raw_on = FakeRadarState(lead_one=FakeLead(status=True, d_rel=30.0))
    for _ in range(5):
      lp.update(raw_on)
    lp.update(None, force_enabled=False)
    assert lp._alive_one == 0
    assert lp._last_one is None
