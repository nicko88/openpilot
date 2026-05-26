#!/usr/bin/env python3
"""WebSocket bridge: cereal SubMaster -> JSON frames for sunnypilot viz."""
from __future__ import annotations

import argparse
import asyncio
import json
import time
from pathlib import Path

from aiohttp import WSMsgType, web

from openpilot.sunnypilot.viz.bridge.demo import build_demo_frame
from openpilot.sunnypilot.viz.bridge.serializer import build_frame


SERVICES = [
  'modelV2',
  'radarState',
  'liveTracks',
  'carState',
  'carStateSP',
  'selfdriveState',
  'liveCalibration',
  'liveLocationKalman',
  'deviceState',
  'liveMapDataSP',
]
DEFAULT_HZ = 20.0
MAX_HZ = 30.0
ROOT = Path(__file__).resolve().parent.parent / 'web' / 'dist'


class FrameHub:
  def __init__(self, addr: str, hz: float, demo: bool = False):
    self.addr = addr
    self.dt = 1.0 / hz
    self.demo = demo
    self.clients: set[web.WebSocketResponse] = set()
    self.latest: dict | None = None
    self._stop = asyncio.Event()

  async def run(self):
    sm = None
    if not self.demo:
      import cereal.messaging as messaging
      sm = messaging.SubMaster(
        SERVICES, addr=self.addr,
        ignore_alive=SERVICES, ignore_valid=SERVICES, ignore_avg_freq=SERVICES,
      )
    loop = asyncio.get_running_loop()
    next_tick = loop.time()
    t0 = time.monotonic()
    while not self._stop.is_set():
      now = time.monotonic()
      if self.demo:
        frame = build_demo_frame(now - t0)
      else:
        await loop.run_in_executor(None, sm.update, 0)
        frame = build_frame(sm, now)
      self.latest = frame
      if self.clients:
        payload = json.dumps(frame, separators=(',', ':'))
        await asyncio.gather(*(self._send(c, payload) for c in list(self.clients)), return_exceptions=True)
      next_tick += self.dt
      sleep = next_tick - loop.time()
      if sleep < -self.dt:
        next_tick = loop.time()
      elif sleep > 0:
        await asyncio.sleep(sleep)

  async def _send(self, ws: web.WebSocketResponse, payload: str):
    if ws.closed:
      self.clients.discard(ws)
      return
    try:
      await ws.send_str(payload)
    except ConnectionResetError:
      self.clients.discard(ws)

  def stop(self):
    self._stop.set()


async def ws_handler(request: web.Request):
  ws = web.WebSocketResponse(heartbeat=15)
  await ws.prepare(request)
  hub: FrameHub = request.app['hub']
  hub.clients.add(ws)
  try:
    if hub.latest is not None:
      await ws.send_str(json.dumps(hub.latest, separators=(',', ':')))
    async for msg in ws:
      if msg.type == WSMsgType.ERROR:
        break
  finally:
    hub.clients.discard(ws)
  return ws


async def health(_: web.Request):
  return web.json_response({"ok": True, "services": SERVICES})


def make_app(addr: str, hz: float, demo: bool = False) -> web.Application:
  app = web.Application()
  hub = FrameHub(addr, hz, demo=demo)
  app['hub'] = hub
  app.router.add_get('/ws', ws_handler)
  app.router.add_get('/health', health)
  if ROOT.exists():
    app.router.add_static('/', ROOT, show_index=True)

  async def _on_start(app_: web.Application):
    app_['hub_task'] = asyncio.create_task(hub.run())

  async def _on_stop(app_: web.Application):
    hub.stop()
    task = app_.get('hub_task')
    if task:
      task.cancel()
      try:
        await task
      except asyncio.CancelledError:
        pass

  app.on_startup.append(_on_start)
  app.on_cleanup.append(_on_stop)
  return app


def main():
  p = argparse.ArgumentParser()
  p.add_argument('--host', default='0.0.0.0')
  p.add_argument('--port', type=int, default=8765)
  p.add_argument('--addr', default='127.0.0.1', help='msgq/zmq addr for SubMaster (device IP for remote)')
  p.add_argument('--hz', type=float, default=DEFAULT_HZ)
  p.add_argument('--demo', action='store_true', help='synth frames, no msgq required')
  args = p.parse_args()
  hz = min(args.hz, MAX_HZ)
  web.run_app(make_app(args.addr, hz, demo=args.demo), host=args.host, port=args.port)


if __name__ == '__main__':
  main()
