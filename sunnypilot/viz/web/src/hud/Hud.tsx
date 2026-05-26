import { useEffect, useState } from 'react';
import type { CameraMode } from '../App';
import type { ConnStatus, Frame } from '../types';

const MS_TO_KMH = 3.6;

interface Props {
  frame: Frame | null;
  status: ConnStatus;
  cameraMode: CameraMode;
  setCameraMode: (m: CameraMode) => void;
}

const CYAN = '#3fbfff';
const DIM = 'rgba(216, 225, 234, 0.55)';

function fmtInt(v: number | undefined): string {
  if (v === undefined || !isFinite(v)) return '—';
  return Math.round(v).toString();
}

function usePhoneBattery() {
  const [pct, setPct] = useState<number | null>(null);
  useEffect(() => {
    const nav = navigator as Navigator & { getBattery?: () => Promise<{ level: number; addEventListener: (k: string, fn: () => void) => void }> };
    if (!nav.getBattery) return;
    let bat: { level: number; addEventListener: (k: string, fn: () => void) => void } | null = null;
    const onChange = () => bat && setPct(Math.round(bat.level * 100));
    nav.getBattery().then((b) => { bat = b; onChange(); b.addEventListener('levelchange', onChange); });
  }, []);
  return pct;
}

export function Hud({ frame, status, cameraMode, setCameraMode }: Props) {
  const cs = frame?.carState;
  const ctrl = frame?.controls;
  const phonePct = usePhoneBattery();

  const speedKmh = cs?.vEgo !== undefined ? cs.vEgo * MS_TO_KMH : undefined;
  const cruiseKmh = cs?.cruiseSpeed !== undefined && cs.cruiseSpeed > 0 ? cs.cruiseSpeed * MS_TO_KMH : undefined;
  const mapd = frame?.mapd;
  const speedLimit = mapd?.speedLimitValid && mapd.speedLimit ? mapd.speedLimit * MS_TO_KMH : undefined;
  const gear = cs?.gear && cs.gear !== '?' ? cs.gear : 'D';
  const fuelPct = cs?.fuelGauge !== undefined && cs.fuelGauge > 0 ? Math.round(cs.fuelGauge * 100) : undefined;
  const dev = frame?.device;
  const carBattPct = dev?.batteryPercent !== undefined && dev.batteryPercent >= 0 ? dev.batteryPercent : undefined;
  const carBattTempC = dev?.batteryTempC;
  const madsActive = !!cs?.mads?.available;
  const experimental = !!ctrl?.experimentalMode;

  return (
    <>
      {/* Top-right: phone / car battery + temp */}
      <div style={{ position: 'absolute', top: 18, right: 24, display: 'flex', alignItems: 'center', gap: 14, fontSize: 14, color: '#d8e1ea', fontVariantNumeric: 'tabular-nums' }}>
        <BatteryBlock label="Phone" pct={phonePct ?? undefined} color="#5aa9ff" />
        <span style={{ opacity: 0.35 }}>|</span>
        <BatteryBlock label="Car" pct={carBattPct} color="#3fdc7a" />
        <span style={{ opacity: 0.7 }}>{carBattTempC !== undefined ? `${Math.round(carBattTempC)}°C` : '—°C'}</span>
      </div>

      {/* Left column: vertical accent + speed + gear + MADS wheel */}
      <div style={{ position: 'absolute', top: 0, bottom: 0, left: 40, display: 'flex', alignItems: 'center' }}>
        <div style={{ width: 2, height: 360, background: 'rgba(216,225,234,0.18)', borderRadius: 2, marginRight: 36 }} />
        <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
          <div style={{ display: 'flex', alignItems: 'flex-end', gap: 6, lineHeight: 1 }}>
            <span style={{ fontSize: 140, fontWeight: 300, color: '#f1f5f9', letterSpacing: -4 }}>{fmtInt(speedKmh)}</span>
            <span style={{ fontSize: 22, color: DIM, paddingBottom: 18 }}>km/h</span>
          </div>
          <GearPill gear={gear} />
          <SteeringWheelIcon active={madsActive} />
        </div>
      </div>

      {/* Right column: cruise set + speed limit sign */}
      <div style={{ position: 'absolute', top: 220, right: 60, display: 'flex', alignItems: 'center', gap: 24 }}>
        <div style={{ display: 'flex', alignItems: 'flex-end', gap: 4, lineHeight: 1 }}>
          <span style={{ fontSize: 88, fontWeight: 300, color: CYAN, letterSpacing: -2 }}>{fmtInt(cruiseKmh)}</span>
          <span style={{ fontSize: 18, color: CYAN, opacity: 0.7, paddingBottom: 10 }}>max</span>
        </div>
        <SpeedLimitSign limit={speedLimit} />
      </div>

      {/* Bottom-left: fuel/charge gauge */}
      <div style={{ position: 'absolute', bottom: 28, left: 40, fontSize: 18, color: DIM, fontVariantNumeric: 'tabular-nums' }}>
        {fuelPct !== undefined ? `fuel ${fuelPct}%` : ''}
      </div>

      {/* Bottom-right: experimental atom */}
      <div style={{ position: 'absolute', bottom: 28, right: 48, opacity: experimental ? 1 : 0.25 }}>
        <ExperimentalAtom on={experimental} />
      </div>

      {/* Blinker arrows */}
      {cs?.leftBlinker ? <BlinkerArrow side="left" /> : null}
      {cs?.rightBlinker ? <BlinkerArrow side="right" /> : null}

      {/* Dev strip: camera mode + ws status */}
      <div style={{ position: 'absolute', top: 18, left: '50%', transform: 'translateX(-50%)', display: 'flex', gap: 4, padding: '4px 6px', background: 'rgba(8,12,18,0.55)', borderRadius: 8, border: '1px solid rgba(120,200,255,0.15)' }}>
        <CamButton mode="chase" cur={cameraMode} setMode={setCameraMode} label="3D" />
        <CamButton mode="topdown" cur={cameraMode} setMode={setCameraMode} label="Top" />
        <CamButton mode="cockpit" cur={cameraMode} setMode={setCameraMode} label="Cockpit" />
        <CamButton mode="orbit" cur={cameraMode} setMode={setCameraMode} label="Orbit" />
      </div>
      <div style={{ position: 'absolute', bottom: 8, left: 8, fontSize: 10, opacity: 0.45, color: '#d8e1ea' }}>
        ws: <span style={{ color: status === 'open' ? '#3ee07e' : '#e06b6b' }}>{status}</span>
        {frame ? <span style={{ marginLeft: 8 }}>t={frame.t.toFixed(2)}</span> : null}
      </div>
    </>
  );
}

function BatteryBlock({ label, pct, color }: { label: string; pct?: number; color: string }) {
  const v = pct !== undefined && isFinite(pct) ? pct : undefined;
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
      <span style={{ opacity: 0.8 }}>{label}</span>
      <BatteryIcon pct={v} color={color} />
      <span style={{ fontWeight: 600 }}>{v !== undefined ? `${v}%` : '—%'}</span>
    </div>
  );
}

function BatteryIcon({ pct, color }: { pct?: number; color: string }) {
  const fill = Math.max(0, Math.min(100, pct ?? 0));
  return (
    <span style={{ position: 'relative', display: 'inline-flex', width: 30, height: 14, border: '1.5px solid rgba(216,225,234,0.55)', borderRadius: 3, padding: 1.5, boxSizing: 'border-box' }}>
      <span style={{ position: 'absolute', right: -4, top: 3, width: 2.5, height: 6, background: 'rgba(216,225,234,0.55)', borderRadius: 1 }} />
      <span style={{ width: `${fill}%`, height: '100%', background: pct === undefined ? 'transparent' : color, borderRadius: 1 }} />
    </span>
  );
}

function GearPill({ gear }: { gear: string }) {
  return (
    <div style={{ width: 70, padding: '8px 0', textAlign: 'center', background: 'rgba(200,210,220,0.55)', color: '#0c1219', fontSize: 28, fontWeight: 500, borderRadius: 6 }}>
      {gear}
    </div>
  );
}

function SteeringWheelIcon({ active }: { active: boolean }) {
  const c = active ? CYAN : 'rgba(216,225,234,0.35)';
  return (
    <svg width="56" height="56" viewBox="0 0 64 64" fill="none">
      <circle cx="32" cy="32" r="26" stroke={c} strokeWidth="5" />
      <circle cx="32" cy="32" r="6" fill={c} />
      <path d="M32 38 L32 56" stroke={c} strokeWidth="5" strokeLinecap="round" />
      <path d="M10 30 L26 30" stroke={c} strokeWidth="5" strokeLinecap="round" />
      <path d="M38 30 L54 30" stroke={c} strokeWidth="5" strokeLinecap="round" />
    </svg>
  );
}

function SpeedLimitSign({ limit }: { limit?: number }) {
  return (
    <div style={{ width: 96, height: 96, borderRadius: '50%', border: '9px solid #e23838', background: '#f5f5f5', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#111', fontSize: 38, fontWeight: 700, fontVariantNumeric: 'tabular-nums' }}>
      {limit !== undefined ? Math.round(limit) : '—'}
    </div>
  );
}

function ExperimentalAtom({ on }: { on: boolean }) {
  const c = on ? '#ff7a18' : 'rgba(216,225,234,0.4)';
  return (
    <svg width="52" height="52" viewBox="0 0 64 64" fill="none">
      <ellipse cx="32" cy="32" rx="26" ry="10" stroke={c} strokeWidth="3" />
      <ellipse cx="32" cy="32" rx="26" ry="10" stroke={c} strokeWidth="3" transform="rotate(60 32 32)" />
      <ellipse cx="32" cy="32" rx="26" ry="10" stroke={c} strokeWidth="3" transform="rotate(120 32 32)" />
      <circle cx="32" cy="32" r="5" fill={c} />
    </svg>
  );
}

function BlinkerArrow({ side }: { side: 'left' | 'right' }) {
  const pos = side === 'left' ? { left: 180 } : { right: 180 };
  return (
    <div style={{ position: 'absolute', top: '50%', ...pos, transform: 'translateY(-50%)', color: '#3fdc7a', fontSize: 64, fontWeight: 700, animation: 'blinkerPulse 0.7s steps(2, end) infinite' }}>
      {side === 'left' ? '◀' : '▶'}
    </div>
  );
}

function CamButton({ mode, cur, setMode, label }: { mode: CameraMode; cur: CameraMode; setMode: (m: CameraMode) => void; label: string }) {
  const active = mode === cur;
  return (
    <button
      onClick={() => setMode(mode)}
      style={{
        background: active ? 'rgba(78, 160, 255, 0.25)' : 'transparent',
        border: `1px solid ${active ? '#4ea0ff' : 'rgba(120, 200, 255, 0.18)'}`,
        color: active ? '#9be7ff' : '#d8e1ea',
        padding: '3px 10px',
        borderRadius: 6,
        cursor: 'pointer',
        fontSize: 11,
        fontWeight: 600,
        letterSpacing: 0.5,
      }}
    >
      {label}
    </button>
  );
}
