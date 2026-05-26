import { useMemo } from 'react';
import * as THREE from 'three';
import type { LaneLine } from '../types';

interface Props { lanes?: LaneLine[]; }

const COLORS = [0x4a6a8a, 0x9be7ff, 0x9be7ff, 0x4a6a8a];

export function LaneLines({ lanes }: Props) {
  if (!lanes?.length) return null;
  return (
    <>
      {lanes.map((ln, i) => <Ribbon key={i} lane={ln} color={COLORS[i] ?? 0x9be7ff} />)}
    </>
  );
}

function Ribbon({ lane, color }: { lane: LaneLine; color: number }) {
  const geom = useMemo(() => {
    const half = 0.08;
    const pts = lane.pts;
    if (pts.length < 2) return null;
    const positions: number[] = [];
    const indices: number[] = [];
    for (let i = 0; i < pts.length; i++) {
      const [x, y, z] = pts[i];
      positions.push(x, y - half, z + 0.02, x, y + half, z + 0.02);
    }
    for (let i = 0; i < pts.length - 1; i++) {
      const a = i * 2;
      indices.push(a, a + 1, a + 2, a + 1, a + 3, a + 2);
    }
    const g = new THREE.BufferGeometry();
    g.setAttribute('position', new THREE.Float32BufferAttribute(positions, 3));
    g.setIndex(indices);
    g.computeVertexNormals();
    return g;
  }, [lane.pts]);
  if (!geom) return null;
  const opacity = 0.25 + 0.65 * Math.max(0, Math.min(1, lane.prob));
  return (
    <mesh geometry={geom}>
      <meshBasicMaterial color={color} transparent opacity={opacity} side={THREE.DoubleSide} />
    </mesh>
  );
}
