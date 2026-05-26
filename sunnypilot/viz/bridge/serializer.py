#!/usr/bin/env python3
"""Cereal -> JSON frame builder for sunnypilot viz."""
from __future__ import annotations

import math
from typing import Any


MODEL_POINTS = 33
LEAD_T_IDX = (0, 2, 4, 6, 8, 10, 12)


def _f(v: Any, default: float = 0.0) -> float:
  try:
    v = float(v)
  except (TypeError, ValueError):
    return default
  return v if math.isfinite(v) else default


def _enum(v: Any) -> str:
  try:
    return str(v).split('.')[-1]
  except Exception:
    return str(v)


def _xyz_list(xs, ys, zs, n: int = MODEL_POINTS) -> list[list[float]]:
  out: list[list[float]] = []
  for i in range(min(n, len(xs), len(ys), len(zs))):
    out.append([_f(xs[i]), _f(ys[i]), _f(zs[i])])
  return out


def serialize_model(msg) -> dict[str, Any]:
  if msg is None:
    return {}
  m = msg.modelV2
  pos = m.position
  lane_lines = []
  for i, ll in enumerate(m.laneLines):
    prob = _f(m.laneLineProbs[i]) if i < len(m.laneLineProbs) else 0.0
    lane_lines.append({"prob": prob, "pts": _xyz_list(ll.x, ll.y, ll.z)})
  road_edges = []
  for i, re_ in enumerate(m.roadEdges):
    std = _f(m.roadEdgeStds[i]) if i < len(m.roadEdgeStds) else 0.0
    road_edges.append({"std": std, "pts": _xyz_list(re_.x, re_.y, re_.z)})
  leads = []
  for ld in m.leadsV3:
    leads.append({
      "prob": _f(ld.prob),
      "probTime": _f(getattr(ld, 'probTime', 0.0)),
      "x": [_f(v) for v in ld.x[:len(LEAD_T_IDX)]],
      "y": [_f(v) for v in ld.y[:len(LEAD_T_IDX)]],
      "v": [_f(v) for v in ld.v[:len(LEAD_T_IDX)]],
      "a": [_f(v) for v in ld.a[:len(LEAD_T_IDX)]],
      "t": list(LEAD_T_IDX),
    })
  return {
    "frameId": int(getattr(m, 'frameId', 0)),
    "position": _xyz_list(pos.x, pos.y, pos.z),
    "orientation": _xyz_list(m.orientation.x, m.orientation.y, m.orientation.z),
    "velocity": _xyz_list(m.velocity.x, m.velocity.y, m.velocity.z),
    "laneLines": lane_lines,
    "roadEdges": road_edges,
    "leadsV3": leads,
    "acceleration": _xyz_list(m.acceleration.x, m.acceleration.y, m.acceleration.z),
  }


def serialize_radar(msg) -> dict[str, Any]:
  if msg is None:
    return {}
  r = msg.radarState
  def _lead(ld):
    return {
      "status": bool(ld.status),
      "dRel": _f(ld.dRel),
      "yRel": _f(ld.yRel),
      "vRel": _f(ld.vRel),
      "vLead": _f(ld.vLead),
      "aLeadK": _f(ld.aLeadK),
      "aLeadTau": _f(ld.aLeadTau),
      "modelProb": _f(ld.modelProb),
      "radar": bool(getattr(ld, 'radar', False)),
    }
  return {
    "leadOne": _lead(r.leadOne),
    "leadTwo": _lead(r.leadTwo),
  }


def serialize_live_tracks(msg) -> list[dict[str, Any]]:
  if msg is None:
    return []
  out = []
  for t in msg.liveTracks:
    out.append({
      "id": int(getattr(t, 'trackId', 0)),
      "dRel": _f(t.dRel),
      "yRel": _f(t.yRel),
      "vRel": _f(t.vRel),
      "aRel": _f(getattr(t, 'aRel', 0.0)),
    })
  return out


GEAR_LETTER = {
  "park": "P", "drive": "D", "neutral": "N", "reverse": "R",
  "sport": "S", "low": "L", "brake": "B", "eco": "E", "manumatic": "M",
}


def serialize_car_state(msg, msg_sp=None) -> dict[str, Any]:
  if msg is None:
    return {}
  cs = msg.carState
  gear_enum = _enum(cs.gearShifter)
  out = {
    "vEgo": _f(cs.vEgo),
    "aEgo": _f(cs.aEgo),
    "steeringAngleDeg": _f(cs.steeringAngleDeg),
    "steeringTorque": _f(cs.steeringTorque),
    "gas": _f(cs.gas),
    "brake": _f(cs.brake),
    "gasPressed": bool(cs.gasPressed),
    "brakePressed": bool(cs.brakePressed),
    "leftBlinker": bool(cs.leftBlinker),
    "rightBlinker": bool(cs.rightBlinker),
    "standstill": bool(cs.standstill),
    "cruiseEnabled": bool(cs.cruiseState.enabled),
    "cruiseSpeed": _f(cs.cruiseState.speed),
    "gear": GEAR_LETTER.get(gear_enum, "?"),
    "fuelGauge": _f(getattr(cs, 'fuelGauge', 0.0)),
  }
  if msg_sp is not None:
    sp = msg_sp.carStateSP
    out["mads"] = {
      "available": bool(getattr(sp, 'madsEnabled', False)),
    }
  return out


def serialize_controls(msg, msg_sp=None) -> dict[str, Any]:
  if msg is None:
    return {}
  c = msg.selfdriveState
  out = {
    "enabled": bool(c.enabled),
    "active": bool(c.active),
    "engageable": bool(c.engageable),
    "alertText1": str(c.alertText1),
    "alertText2": str(c.alertText2),
    "alertStatus": _enum(c.alertStatus),
    "state": _enum(c.state),
    "experimentalMode": bool(getattr(c, 'experimentalMode', False)),
  }
  return out


def serialize_device(msg) -> dict[str, Any]:
  if msg is None:
    return {}
  d = msg.deviceState
  return {
    "batteryPercent": int(getattr(d, 'batteryPercent', -1)),
    "batteryTempC": _f(getattr(d, 'batteryTempC', 0.0)),
    "ambientTempC": _f(getattr(d, 'ambientTempC', 0.0)),
  }


def serialize_mapd(msg) -> dict[str, Any]:
  if msg is None:
    return {}
  m = msg.liveMapDataSP
  return {
    "speedLimitValid": bool(m.speedLimitValid),
    "speedLimit": _f(m.speedLimit),
  }


def serialize_calib(msg) -> dict[str, Any]:
  if msg is None:
    return {}
  lc = msg.liveCalibration
  return {
    "rpyCalib": [_f(v) for v in lc.rpyCalib],
    "calStatus": _enum(getattr(lc, 'calStatus', 0)),
  }


def serialize_location(msg) -> dict[str, Any]:
  if msg is None:
    return {}
  k = msg.liveLocationKalman
  ori = k.orientationNED
  vel = k.velocityCalibrated if k.velocityCalibrated.valid else k.velocityDevice
  return {
    "valid": bool(k.gpsOK),
    "orientationNED": [_f(v) for v in ori.value],
    "velocity": [_f(v) for v in vel.value],
    "positionGeodetic": [_f(v) for v in k.positionGeodetic.value],
  }


def build_frame(sm, t_mono: float) -> dict[str, Any]:
  return {
    "t": t_mono,
    "model": serialize_model(sm['modelV2']) if sm.updated.get('modelV2') or sm.seen.get('modelV2') else {},
    "radar": serialize_radar(sm['radarState']) if sm.seen.get('radarState') else {},
    "tracks": serialize_live_tracks(sm['liveTracks']) if sm.seen.get('liveTracks') else [],
    "carState": serialize_car_state(
      sm['carState'] if sm.seen.get('carState') else None,
      sm['carStateSP'] if sm.seen.get('carStateSP') else None,
    ),
    "controls": serialize_controls(
      sm['selfdriveState'] if sm.seen.get('selfdriveState') else None,
    ),
    "calib": serialize_calib(sm['liveCalibration'] if sm.seen.get('liveCalibration') else None),
    "location": serialize_location(sm['liveLocationKalman'] if sm.seen.get('liveLocationKalman') else None),
    "device": serialize_device(sm['deviceState'] if sm.seen.get('deviceState') else None),
    "mapd": serialize_mapd(sm['liveMapDataSP'] if sm.seen.get('liveMapDataSP') else None),
  }
