"""
Copyright (c) 2021-, rav4kumar, Haibin Wen, sunnypilot, and a number of other contributors.

This file is part of sunnypilot and is licensed under the MIT License.
See the LICENSE.md file in the root directory for more details.
"""

from dataclasses import dataclass

import numpy as np

from openpilot.common.params import Params
from openpilot.common.realtime import DT_MDL


_DREL_MIN = 40.0
_DREL_MAX = 150.0
_YREL_ABS_MAX = 1.6

_VREL_DEADBAND = -1.5
_VREL_FULL = -6.0

_V_EGO_MIN = 5.0

_ACTIVATE_FRAMES = 5
_DECAY_PER_MISS = 2
_DEACTIVATE_FRAMES = 10

_TTC_NONE = 10.0
_TTC_LIFT = 5.0
_TTC_BRAKE = 3.0

_A_CEIL_HIGH = 0.8
_A_CEIL_COAST = 0.0
_A_CEIL_BRAKE = -0.5
_A_CEIL_RELEASED = 2.5

_A_CEIL_RATE_DOWN = 0.6
_A_CEIL_RATE_UP = 0.8

_PARAM_REFRESH_FRAMES = max(1, int(1.0 / DT_MDL))


@dataclass
class FarLeadState:
  d_rel: float = 0.0
  v_rel: float = 0.0
  y_rel: float = 0.0
  ttc: float = float('inf')
  track_id: int = -1
  frames_seen: int = 0
  frames_lost: int = 0
  active: bool = False


class RadarDistanceController:
  def __init__(self):
    self.params = Params()
    self._frame = 0
    self._enabled = self.params.get_bool('RadarDistance')

    self._state = FarLeadState()
    self._track_persistence: dict[int, int] = {}

    self._ceiling = _A_CEIL_RELEASED
    self._first = True

  def is_enabled(self) -> bool:
    return self._enabled

  def set_enabled(self, enabled: bool):
    self._enabled = bool(enabled)
    self.params.put_bool('RadarDistance', self._enabled)

  def toggle(self) -> bool:
    self.set_enabled(not self._enabled)
    return self._enabled

  def update(self, sm=None, sm_sp=None) -> None:
    self._frame += 1
    if self._frame % _PARAM_REFRESH_FRAMES == 0:
      self._enabled = self.params.get_bool('RadarDistance')

    if sm is None or not self._enabled:
      self._release()
      return

    try:
      v_ego = float(sm['carState'].vEgo)
    except Exception:
      v_ego = 0.0

    radarstate = sm['radarState'] if 'radarState' in sm.data else None
    if radarstate is not None and radarstate.leadOne.status:
      self._release()
      return

    tracks = self._extract_tracks(sm_sp)
    self._tick_radar(tracks, v_ego)
    self._step_ceiling()

  def reset(self) -> None:
    self._state = FarLeadState()
    self._track_persistence.clear()
    self._ceiling = _A_CEIL_RELEASED
    self._first = True

  def get_accel_ceiling(self, v_ego: float) -> float | None:
    if not self._enabled or not self._state.active:
      return None
    return self._ceiling

  @property
  def ttc(self) -> float:
    return self._state.ttc

  @property
  def active(self) -> bool:
    return self._state.active

  @property
  def d_rel(self) -> float:
    return self._state.d_rel

  @property
  def track_id(self) -> int:
    return self._state.track_id

  @property
  def ceiling(self) -> float:
    return self._ceiling

  @staticmethod
  def _extract_tracks(sm_sp):
    if sm_sp is None:
      return []
    try:
      if 'liveTracks' not in sm_sp.data:
        return []
      return list(sm_sp['liveTracks'].points)
    except Exception:
      return []

  def _tick_radar(self, tracks, v_ego: float) -> None:
    if v_ego < _V_EGO_MIN or not tracks:
      self._decay_unseen(seen_ids=set())
      self._lose_track()
      return

    seen_ids: set[int] = set()
    best: tuple[float, float, float, float, int] | None = None

    for t in tracks:
      if not t.measured:
        continue
      d_rel = float(t.dRel)
      if not (_DREL_MIN < d_rel < _DREL_MAX):
        continue
      y_rel = float(t.yRel)
      if abs(y_rel) > _YREL_ABS_MAX:
        continue
      v_rel = float(t.vRel)
      if v_rel >= _VREL_DEADBAND:
        continue

      tid = int(t.trackId)
      seen_ids.add(tid)
      self._track_persistence[tid] = self._track_persistence.get(tid, 0) + 1

      if self._track_persistence[tid] >= _ACTIVATE_FRAMES:
        ttc = d_rel / max(0.1, -v_rel)
        if best is None or ttc < best[0]:
          best = (ttc, d_rel, v_rel, y_rel, tid)

    self._decay_unseen(seen_ids)

    if best is None:
      self._lose_track()
      return

    self._state.ttc = best[0]
    self._state.d_rel = best[1]
    self._state.v_rel = best[2]
    self._state.y_rel = best[3]
    self._state.track_id = best[4]
    self._state.frames_seen = self._track_persistence[best[4]]
    self._state.frames_lost = 0
    self._state.active = True

  def _decay_unseen(self, seen_ids: set[int]) -> None:
    for tid in list(self._track_persistence.keys()):
      if tid in seen_ids:
        continue
      self._track_persistence[tid] -= _DECAY_PER_MISS
      if self._track_persistence[tid] <= 0:
        del self._track_persistence[tid]

  def _lose_track(self) -> None:
    self._state.frames_seen = 0
    self._state.frames_lost += 1
    if self._state.frames_lost >= _DEACTIVATE_FRAMES:
      self._state.active = False
      self._state.ttc = float('inf')
      self._state.track_id = -1

  def _target_ceiling(self) -> float:
    if not self._state.active:
      return _A_CEIL_RELEASED

    ttc = self._state.ttc
    if ttc >= _TTC_NONE:
      return _A_CEIL_RELEASED
    if ttc >= _TTC_LIFT:
      t = float(np.clip((_TTC_NONE - ttc) / (_TTC_NONE - _TTC_LIFT), 0.0, 1.0))
      return (1.0 - t) * _A_CEIL_HIGH + t * _A_CEIL_COAST
    if ttc >= _TTC_BRAKE:
      t = float(np.clip((_TTC_LIFT - ttc) / (_TTC_LIFT - _TTC_BRAKE), 0.0, 1.0))
      closing = float(np.clip(
        (self._state.v_rel - _VREL_DEADBAND) / (_VREL_FULL - _VREL_DEADBAND), 0.0, 1.0))
      return _A_CEIL_COAST + t * closing * (_A_CEIL_BRAKE - _A_CEIL_COAST)
    return _A_CEIL_RELEASED

  def _step_ceiling(self) -> None:
    target = self._target_ceiling()
    if self._first:
      self._ceiling = target
      self._first = False
      return
    rate = _A_CEIL_RATE_DOWN if target < self._ceiling else _A_CEIL_RATE_UP
    step = rate * DT_MDL
    self._ceiling = float(np.clip(target, self._ceiling - step, self._ceiling + step))

  def _release(self) -> None:
    self._track_persistence.clear()
    self._state.frames_seen = 0
    if self._state.frames_lost < _DEACTIVATE_FRAMES:
      self._state.frames_lost += 1
    if self._state.frames_lost >= _DEACTIVATE_FRAMES:
      self._state.active = False
      self._state.ttc = float('inf')
      self._state.track_id = -1
    target = _A_CEIL_RELEASED
    if self._first:
      self._ceiling = target
      self._first = False
      return
    step = _A_CEIL_RATE_UP * DT_MDL
    self._ceiling = float(np.clip(target, self._ceiling - step, self._ceiling + step))
