# sunnypilot viz

Tesla/Waymo-style 3D view driven entirely from the openpilot driving model. Live cereal stream → WebSocket → react-three-fiber.

```
┌────────────┐  msgq    ┌─────────────────┐  ws (json) ┌─────────────────┐
│ openpilot  │ ────────▶│ bridge/server.py│ ─────────▶ │ web (R3F)       │
│ daemons    │          │ SubMaster + WS  │            │ scene + HUD     │
└────────────┘          └─────────────────┘            └─────────────────┘
```

## Subscribed services

`modelV2`, `radarState`, `liveTracks`, `carState`, `carStateSP`, `selfdriveState`, `liveCalibration`, `liveLocationKalman`.

## Run — demo (no openpilot required)

```bash
.venv/bin/python -m openpilot.sunnypilot.viz.bridge.server --demo
cd sunnypilot/viz/web && npm install && npm run dev
# open http://127.0.0.1:5173
```

Synth: curving 4-lane road, 1 moving lead, 6 radar tracks, oscillating vEgo, engagement light on.

## Run — bridge (live)

Local (op running on same box):

```bash
python -m openpilot.sunnypilot.viz.bridge.server --host 127.0.0.1 --port 8765 --hz 20
```

Remote device (replace IP with comma3):

```bash
python -m openpilot.sunnypilot.viz.bridge.server --addr 192.168.x.x --port 8765
```

Endpoints:

- `GET /health` — service list + ok flag
- `GET /ws`     — WebSocket frame stream

## Run — frontend (dev)

```bash
cd sunnypilot/viz/web
npm install
npm run dev
```

Vite serves on `http://127.0.0.1:5173`. `/ws` is proxied to `127.0.0.1:8765`.

## Build for static serve

```bash
cd sunnypilot/viz/web
npm run build
```

Bridge serves `dist/` at `/` when present, so `python -m openpilot.sunnypilot.viz.bridge.server` alone is enough in prod.

## Coord frame

Scene uses openpilot device frame: `x` forward, `y` left, `z` up. Camera up-axis set to z.

Lead positions: model `leadsV3.x/y` are device-frame; radar `dRel` forward / `yRel` lateral (note sign — `-yRel` so positive y stays "left").

## Files

```
sunnypilot/viz/
├── bridge/
│   ├── serializer.py   # cereal → json
│   └── server.py       # aiohttp ws + static
└── web/
    ├── package.json
    ├── vite.config.ts
    ├── tsconfig.json
    ├── index.html
    └── src/
        ├── main.tsx, App.tsx, types.ts
        ├── net/useFrameStream.ts
        ├── hud/Hud.tsx
        └── scene/
            ├── Scene.tsx
            ├── Ego.tsx, Ground.tsx
            ├── LaneLines.tsx, RoadEdges.tsx, PathPlan.tsx
            └── Leads.tsx, RadarTracks.tsx
```

## Knobs

| Where | What |
|---|---|
| `bridge/server.py --hz` | push rate (cap 30) |
| `scene/Scene.tsx` `OrbitControls` | camera target / clamps |
| `scene/PathPlan.tsx` tube radius | path thickness |
| `scene/Leads.tsx` `prob > 0.3` | model lead show threshold |
| `scene/RadarTracks.tsx` `MAX_TRACKS` | instanced cap |
