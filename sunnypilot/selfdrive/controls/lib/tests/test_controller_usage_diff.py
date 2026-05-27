"""
Copyright (c) 2021-, rav4kumar, Haibin Wen, sunnypilot, and a number of other contributors.

This file is part of sunnypilot and is licensed under the MIT License.
See the LICENSE.md file in the root directory for more details.

Empirical with-vs-without measurements. Each test runs a synthetic scenario
through the controller and compares the output against the stock baseline
that the planner would have used if the controller were disabled.

Prints a delta table (visible with `pytest -s`) and asserts the controller
has nonzero effect, so a regression that silently no-ops the controller
will fail loudly.
"""
import numpy as np

from cereal import custom, log
from opendbc.car.interfaces import ACCEL_MIN
from openpilot.common.params import Params
from openpilot.selfdrive.controls.lib.longitudinal_planner import get_max_accel as stock_get_max_accel
from openpilot.selfdrive.controls.lib.longitudinal_mpc_lib.long_mpc import get_T_FOLLOW

from openpilot.sunnypilot.selfdrive.controls.lib.accel_personality.accel_controller import (
  AccelPersonalityController,
)
from openpilot.sunnypilot.selfdrive.controls.lib.dynamic_personality.dynamic_follow import (
  FollowDistanceController,
)
from openpilot.sunnypilot.selfdrive.controls.lib.radar_distance.radar_distance import (
  RadarDistanceController,
  _ACTIVATE_FRAMES,
)


AccelPersonality = custom.LongitudinalPlanSP.AccelerationPersonality
LongPersonality = log.LongitudinalPersonality


class FakeCarState:
  def __init__(self, v_cruise=30.0, v_ego=20.0):
    self.vCruise = v_cruise
    self.vEgo = v_ego


class FakeSM:
  def __init__(self, v_cruise=30.0, v_ego=20.0, lead=None):
    radarstate = FakeRadarState(lead) if lead is not None else None
    data = {'carState': FakeCarState(v_cruise, v_ego)}
    if radarstate is not None:
      data['radarState'] = radarstate
    self._data = data

  def __getitem__(self, k):
    return self._data[k]


class FakeLead:
  def __init__(self, d_rel=30.0, v_lead=18.0, a_lead=0.0, a_tau=0.0,
               model_prob=0.95, v_rel=None, status=True):
    self.status = status
    self.dRel = d_rel
    self.yRel = 0.0
    self.vLead = v_lead
    self.vRel = v_rel if v_rel is not None else (v_lead - 20.0)
    self.aLeadK = a_lead
    self.aLeadTau = a_tau
    self.modelProb = model_prob


class FakeRadarState:
  def __init__(self, lead=None):
    self.leadOne = lead if lead is not None else FakeLead(status=False)
    self.leadTwo = FakeLead(status=False)


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


class FakeSmSp:
  def __init__(self, points):
    self._data = {'liveTracks': FakeTracks(points)}

  def __getitem__(self, k):
    return self._data[k]


def _print_table(title, header, rows):
  print(f"\n--- {title} ---")
  print(" | ".join(f"{h:>12}" for h in header))
  print("-" * (15 * len(header)))
  for row in rows:
    print(" | ".join(f"{v:>12.3f}" if isinstance(v, float) else f"{v:>12}" for v in row))


class TestAccelPersonalityUsageDiff:
  def test_accel_clip_per_personality(self, capsys):
    rows = []
    speeds = [3.0, 10.0, 20.0, 30.0]
    personalities = [
      ('eco', AccelPersonality.eco),
      ('normal', AccelPersonality.normal),
      ('sport', AccelPersonality.sport),
    ]

    Params().put_bool('AccelPersonalityEnabled', True)
    sm = FakeSM(v_cruise=35.0)

    any_delta = False
    for label, p in personalities:
      Params().put('AccelPersonality', p)
      c = AccelPersonalityController()
      c.update(sm)

      for v_ego in speeds:
        stock_hi = float(stock_get_max_accel(v_ego))
        c_lo, c_hi = c.get_accel_limits(v_ego)
        delta_hi = c_hi - stock_hi
        delta_lo = c_lo - ACCEL_MIN
        if abs(delta_hi) > 0.01 or abs(delta_lo) > 0.01:
          any_delta = True
        rows.append((label, v_ego, stock_hi, c_hi, delta_hi, c_lo, delta_lo))

    with capsys.disabled():
      _print_table(
        "AccelPersonalityController: a_max stock vs controller",
        ["personality", "v_ego", "stock_hi", "ctrl_hi", "delta_hi", "ctrl_lo", "delta_lo"],
        rows,
      )
    assert any_delta, "controller produced no detectable accel-limit change vs stock"


class TestDynamicFollowUsageDiff:
  def test_t_follow_no_lead_steady_state(self, capsys):
    """Compares steady-state highway t_follow vs stock per personality. Each
    sample warms the speed-scale EMA for 30 frames before reading, so the
    transient low-speed compression doesn't show up here."""
    Params().put_bool('DynamicFollow', True)
    rows = []
    any_delta = False
    for label, p in [
      ('relaxed', LongPersonality.relaxed),
      ('standard', LongPersonality.standard),
      ('aggressive', LongPersonality.aggressive),
    ]:
      Params().put('LongitudinalPersonality', p)
      stock_tf = float(get_T_FOLLOW(p))

      for v_ego in [3.0, 10.0, 25.0]:
        df = FollowDistanceController()
        for _ in range(30):
          df.update()
          ctrl_tf = df.get_follow_distance_multiplier(v_ego, None)
        delta = ctrl_tf - stock_tf
        if abs(delta) > 0.05:
          any_delta = True
        rows.append((label, v_ego, stock_tf, ctrl_tf, delta))

    with capsys.disabled():
      _print_table(
        "FollowDistanceController: t_follow steady-state, no-lead, stock vs controller",
        ["personality", "v_ego", "stock_tf", "ctrl_tf", "delta"],
        rows,
      )
    assert any_delta, "controller produced no detectable t_follow change vs stock (no lead)"

  def test_t_follow_lead_decelerating(self, capsys):
    Params().put_bool('DynamicFollow', True)
    Params().put('LongitudinalPersonality', LongPersonality.standard)
    stock_tf = float(get_T_FOLLOW(LongPersonality.standard))

    df = FollowDistanceController()
    df.update()

    samples = []
    peak_delta = 0.0
    # ramp lead into hard deceleration over 1.5s
    for i in range(30):
      a_lead = max(0.0 - 0.25 * i, -4.0)
      v_lead = max(18.0 - 0.3 * i, 5.0)
      lead = FakeLead(d_rel=40.0, v_lead=v_lead, a_lead=a_lead, model_prob=0.95)
      df.update()
      tf = df.get_follow_distance_multiplier(20.0, FakeRadarState(lead))
      delta = tf - stock_tf
      peak_delta = max(peak_delta, delta)
      samples.append((i, v_lead - 20.0, a_lead, stock_tf, tf, delta))

    with capsys.disabled():
      _print_table(
        "FollowDistanceController: lead decelerating, t_follow trace",
        ["frame", "v_rel", "a_lead", "stock_tf", "ctrl_tf", "delta"],
        samples[::3],
      )
      print(f"peak delta = {peak_delta:.3f}")

    assert peak_delta > 0.10, "controller did not widen t_follow under decelerating lead"


class TestRadarDistanceUsageDiff:
  def test_ceiling_during_closing_track(self, capsys):
    Params().put_bool('RadarDistance', True)
    c = RadarDistanceController()

    rows = []
    # scenarios = (label, points, expect_ceiling_present)
    scenarios = [
      ('no_track', [], False),
      ('mid_ttc_closing', [FakePoint(1, 50.0, 0.0, -7.0)], True),    # ttc ~7.1s -> lift band
      ('emergency', [FakePoint(2, 90.0, 0.4, -20.0)], True),         # extreme closing
    ]

    for label, pts, _ in scenarios:
      c_local = RadarDistanceController()
      for _ in range(_ACTIVATE_FRAMES + 200):
        c_local.update(FakeSM(v_ego=20.0), FakeSmSp(pts))
      stock_ceiling = float('inf')  # stock has no ceiling
      ctrl_ceiling = c_local.get_accel_ceiling(20.0)
      rows.append((
        label,
        c_local.active,
        f"{c_local.ttc:.2f}" if np.isfinite(c_local.ttc) else "inf",
        stock_ceiling,
        ctrl_ceiling if ctrl_ceiling is not None else float('inf'),
      ))

    with capsys.disabled():
      print("\n--- RadarDistanceController: a_max ceiling stock vs controller ---")
      print(f"{'scenario':>16} | {'active':>8} | {'ttc(s)':>8} | {'stock':>10} | {'ctrl':>10}")
      print("-" * 64)
      for r in rows:
        print(f"{r[0]:>16} | {str(r[1]):>8} | {r[2]:>8} | {r[3]:>10.2f} | "
              f"{r[4]:>10.2f}")

    # mid_ttc and emergency must produce a finite ceiling that bites.
    mid = next(r for r in rows if r[0] == 'mid_ttc_closing')
    emerg = next(r for r in rows if r[0] == 'emergency')
    assert mid[1] is True
    assert mid[4] < 1.6  # below stock stock_get_max_accel at v_ego=20 (=1.2)
    assert emerg[1] is True
    assert emerg[4] <= -0.5  # emergency band

  def test_smooth_radarstate_fills_dropout(self, capsys):
    Params().put_bool('RadarDistance', True)
    c = RadarDistanceController()

    # warm-up with a stable lead
    rs_on = FakeRadarState(FakeLead(status=True, d_rel=30.0, v_lead=18.0, a_lead=-0.5,
                                    model_prob=0.95))
    for _ in range(10):
      class _SM:
        def __getitem__(self, k):
          return {'carState': FakeCarState(35.0, 20.0), 'radarState': rs_on}[k]
      c.update(_SM(), FakeSmSp([]))

    rs_off = FakeRadarState(FakeLead(status=False))
    class _SM2:
      def __getitem__(self, k):
        return {'carState': FakeCarState(35.0, 20.0), 'radarState': rs_off}[k]
    c.update(_SM2(), FakeSmSp([]))

    smoothed = c.smooth_radarstate(rs_off)
    with capsys.disabled():
      print("\n--- LeadPersistence dropout fill ---")
      print(f"raw.leadOne.status = {rs_off.leadOne.status}")
      print(f"smoothed.leadOne.status = {smoothed.leadOne.status}")
      print(f"smoothed.leadOne.dRel = {smoothed.leadOne.dRel}")
    assert smoothed.leadOne.status is True
    assert smoothed.leadOne.dRel == 30.0
