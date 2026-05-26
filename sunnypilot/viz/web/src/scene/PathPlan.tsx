import { useMemo } from 'react';
import * as THREE from 'three';
import type { Xyz } from '../types';

interface Props { position?: Xyz[]; velocity?: Xyz[]; }

export function PathPlan({ position, velocity }: Props) {
  const tube = useMemo(() => {
    if (!position || position.length < 2) return null;
    const v3 = position.map(([x, y, z]) => new THREE.Vector3(x, y, z + 0.04));
    const curve = new THREE.CatmullRomCurve3(v3, false, 'catmullrom', 0.2);
    return new THREE.TubeGeometry(curve, Math.min(120, position.length * 4), 0.95, 8, false);
  }, [position]);

  const speed = velocity?.[0]?.[0] ?? 0;
  const hue = Math.min(0.55, 0.45 + speed * 0.003);

  if (!tube) return null;
  return (
    <mesh geometry={tube}>
      <meshBasicMaterial color={new THREE.Color().setHSL(hue, 0.85, 0.55)} transparent opacity={0.55} depthWrite={false} />
    </mesh>
  );
}
