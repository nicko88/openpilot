import { useMemo } from 'react';
import * as THREE from 'three';

export function Ground() {
  const grid = useMemo(() => {
    const g = new THREE.GridHelper(400, 80, 0x1f2a3a, 0x0f1620);
    g.rotation.x = Math.PI / 2;
    (g.material as THREE.Material).transparent = true;
    (g.material as THREE.Material).opacity = 0.55;
    return g;
  }, []);
  return (
    <>
      <primitive object={grid} />
      <mesh rotation-x={0} position={[0, 0, -0.01]} receiveShadow>
        <planeGeometry args={[600, 600]} />
        <meshStandardMaterial color={0x070a10} roughness={1} metalness={0} />
      </mesh>
    </>
  );
}
