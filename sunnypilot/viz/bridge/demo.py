#!/usr/bin/env python3
"""Synthetic frame generator for sunnypilot viz demo mode (no openpilot required)."""
from __future__ import annotations

import math
from typing import Any


MODEL_POINTS = 33
DX = 5.0
LEAD_T_IDX = [0, 2, 4, 6, 8, 10, 12]


def _curve_y(x: float, _t: float = 0.0) -> float:
  return 2.2 * math.sin(x * 0.022) + 0.4 * math.sin(x * 0.085)


def _curve_dy(x: float, _t: float = 0.0) -> float:
  return 2.2 * 0.022 * math.cos(x * 0.022) + 0.4 * 0.085 * math.cos(x * 0.085)


def build_demo_frame(t: float) -> dict[str, Any]:
  v_ego = 22.0 + 4.0 * math.sin(t * 0.25)
  a_ego = 4.0 * 0.25 * math.cos(t * 0.25)
  steer = -math.degrees(_curve_dy(0.0, t) * 10.0)

  xs = [i * DX for i in range(MODEL_POINTS)]
  centerline = [_curve_y(x, t) for x in xs]

  def _lane(offset: float, prob: float) -> dict[str, Any]:
    pts = [[xs[i], centerline[i] + offset, 0.0] for i in range(MODEL_POINTS)]
    return {"prob": prob, "pts": pts}

  lane_lines = [
    _lane(+5.4, 0.35),
    _lane(+1.8, 0.95),
    _lane(-1.8, 0.95),
    _lane(-5.4, 0.35),
  ]
  road_edges = [
    {"std": 0.25, "pts": [[xs[i], centerline[i] + 7.0, 0.0] for i in range(MODEL_POINTS)]},
    {"std": 0.25, "pts": [[xs[i], centerline[i] - 7.0, 0.0] for i in range(MODEL_POINTS)]},
  ]
  position = [[xs[i], centerline[i], 0.0] for i in range(MODEL_POINTS)]
  velocity = [[v_ego, 0.0, 0.0] for _ in range(MODEL_POINTS)]

  lead_d = 28.0 + 12.0 * math.sin(t * 0.18)
  lead_v = v_ego - 2.0 + 1.5 * math.cos(t * 0.18)
  lead_a = -1.5 * 0.18 * math.sin(t * 0.18)
  lead_y = _curve_y(lead_d, t)

  model_lead = {
    "prob": 0.88,
    "probTime": 0.35,
    "x": [lead_d + lead_v * dt for dt in LEAD_T_IDX],
    "y": [_curve_y(lead_d + lead_v * dt, t) for dt in LEAD_T_IDX],
    "v": [lead_v + lead_a * dt for dt in LEAD_T_IDX],
    "a": [lead_a for _ in LEAD_T_IDX],
    "t": LEAD_T_IDX,
  }

  radar_lead = {
    "status": True, "dRel": lead_d, "yRel": -lead_y, "vRel": lead_v - v_ego,
    "vLead": lead_v, "aLeadK": lead_a, "aLeadTau": 0.5, "modelProb": 0.92, "radar": True,
  }
  radar_empty = {
    "status": False, "dRel": 0.0, "yRel": 0.0, "vRel": 0.0,
    "vLead": 0.0, "aLeadK": 0.0, "aLeadTau": 0.0, "modelProb": 0.0, "radar": False,
  }

  tracks = []
  for k in range(6):
    phase = t * 0.3 + k * 1.1
    tracks.append({
      "id": k,
      "dRel": 15.0 + 12.0 * ((k * 7) % 5) + 8.0 * math.sin(phase),
      "yRel": ((-1) ** k) * (2.0 + 1.5 * math.cos(phase)),
      "vRel": -1.0 + math.sin(phase),
      "aRel": 0.0,
    })

  return {
    "t": t,
    "model": {
      "frameId": int(t * 20),
      "position": position,
      "orientation": [[0.0, 0.0, 0.0] for _ in range(MODEL_POINTS)],
      "velocity": velocity,
      "acceleration": [[a_ego, 0.0, 0.0] for _ in range(MODEL_POINTS)],
      "laneLines": lane_lines,
      "roadEdges": road_edges,
      "leadsV3": [model_lead, {"prob": 0.05, "probTime": 0.0, "x": [0.0]*7, "y": [0.0]*7, "v": [0.0]*7, "a": [0.0]*7, "t": LEAD_T_IDX}],
    },
    "radar": {"leadOne": radar_lead, "leadTwo": radar_empty},
    "tracks": tracks,
    "carState": {
      "vEgo": v_ego, "aEgo": a_ego, "steeringAngleDeg": steer, "steeringTorque": 0.4 * steer,
      "gas": max(0.0, a_ego * 0.3), "brake": max(0.0, -a_ego * 0.3),
      "gasPressed": False, "brakePressed": False,
      "leftBlinker": (int(t) % 20) < 3, "rightBlinker": False,
      "standstill": v_ego < 0.1, "cruiseEnabled": True, "cruiseSpeed": 27.0,
      "gear": "D", "fuelGauge": 0.48,
      "mads": {"available": True},
    },
    "controls": {
      "enabled": True, "active": True, "engageable": True,
      "alertText1": "", "alertText2": "", "alertStatus": "normal", "state": "enabled",
      "experimentalMode": True,
    },
    "calib": {"rpyCalib": [0.0, 0.04, 0.0], "calStatus": "calibrated"},
    "location": {"valid": True, "orientationNED": [0.0, 0.0, 0.0], "velocity": [v_ego, 0.0, 0.0], "positionGeodetic": [37.7749, -122.4194, 10.0]},
    "device": {"batteryPercent": 48, "batteryTempC": 27.0, "ambientTempC": 22.0},
    "mapd": {"speedLimitValid": True, "speedLimit": 80.0 / 3.6},
  }
