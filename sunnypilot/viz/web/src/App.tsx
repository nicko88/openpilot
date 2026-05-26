import { useState } from 'react';
import { Canvas } from '@react-three/fiber';
import { Scene } from './scene/Scene';
import { Hud } from './hud/Hud';
import { useFrameStream } from './net/useFrameStream';

export type CameraMode = 'chase' | 'topdown' | 'orbit' | 'cockpit';

export default function App() {
  const { frame, status } = useFrameStream('/ws');
  const [cameraMode, setCameraMode] = useState<CameraMode>('chase');
  return (
    <div style={{ position: 'fixed', inset: 0 }}>
      <Canvas
        camera={{ position: [-8, -6, 4], fov: 55, up: [0, 0, 1], near: 0.1, far: 600 }}
        gl={{ antialias: true, powerPreference: 'high-performance' }}
        dpr={[1, 2]}
      >
        <color attach="background" args={[0.02, 0.03, 0.05]} />
        <fog attach="fog" args={[0x05070a, 50, 280]} />
        <Scene frame={frame} cameraMode={cameraMode} />
      </Canvas>
      <Hud frame={frame} status={status} cameraMode={cameraMode} setCameraMode={setCameraMode} />
    </div>
  );
}
