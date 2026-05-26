import { OrbitControls } from '@react-three/drei';
import { useFrame, useThree } from '@react-three/fiber';
import { useRef } from 'react';
import * as THREE from 'three';
import type { CameraMode } from '../App';
import type { Frame } from '../types';
import { Ego } from './Ego';
import { Ground } from './Ground';
import { LaneLines } from './LaneLines';
import { RoadEdges } from './RoadEdges';
import { PathPlan } from './PathPlan';
import { Leads } from './Leads';
import { RadarTracks } from './RadarTracks';

interface Props { frame: Frame | null; cameraMode: CameraMode; }

export function Scene({ frame, cameraMode }: Props) {
  return (
    <>
      <ambientLight intensity={0.55} />
      <directionalLight position={[20, 30, 40]} intensity={0.9} castShadow />
      <hemisphereLight args={[0x6a8aff, 0x1a1410, 0.35]} />

      <Ground />
      {cameraMode !== 'cockpit' && <Ego carState={frame?.carState} />}
      <LaneLines lanes={frame?.model?.laneLines} />
      <RoadEdges edges={frame?.model?.roadEdges} />
      <PathPlan position={frame?.model?.position} velocity={frame?.model?.velocity} />
      <Leads modelLeads={frame?.model?.leadsV3} radar={frame?.radar} />
      <RadarTracks tracks={frame?.tracks} />

      <CameraRig mode={cameraMode} steerDeg={frame?.carState?.steeringAngleDeg ?? 0} />
    </>
  );
}

const CHASE = { pos: new THREE.Vector3(-9, 0, 4.2), target: new THREE.Vector3(25, 0, 0.5) };
const TOPDOWN = { pos: new THREE.Vector3(28, 0, 80), target: new THREE.Vector3(28, 0, 0) };
const COCKPIT_POS = new THREE.Vector3(1.4, 0.4, 1.22);

function CameraRig({ mode, steerDeg }: { mode: CameraMode; steerDeg: number }) {
  const { camera } = useThree();
  const target = useRef(new THREE.Vector3(20, 0, 0));

  useFrame(() => {
    if (mode === 'orbit') return;
    if (mode === 'cockpit') {
      camera.position.lerp(COCKPIT_POS, 0.25);
      camera.up.set(0, 0, 1);
      const yaw = -steerDeg * (Math.PI / 180) * 0.05;
      const lookX = COCKPIT_POS.x + Math.cos(yaw) * 40;
      const lookY = COCKPIT_POS.y + Math.sin(yaw) * 40;
      target.current.lerp(new THREE.Vector3(lookX, lookY, 0.6), 0.25);
      camera.lookAt(target.current);
      return;
    }
    const want = mode === 'topdown' ? TOPDOWN : CHASE;
    camera.position.lerp(want.pos, 0.08);
    target.current.lerp(want.target, 0.08);
    camera.up.set(mode === 'topdown' ? 1 : 0, 0, mode === 'topdown' ? 0 : 1);
    camera.lookAt(target.current);
  });

  if (mode !== 'orbit') return null;
  return (
    <OrbitControls
      target={[20, 0, 0]}
      enableDamping
      dampingFactor={0.1}
      minDistance={4}
      maxDistance={200}
      maxPolarAngle={Math.PI / 2 - 0.05}
    />
  );
}
