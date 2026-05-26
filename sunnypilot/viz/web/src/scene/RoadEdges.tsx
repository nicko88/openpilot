import { useMemo } from 'react';
import * as THREE from 'three';
import type { RoadEdge } from '../types';

interface Props { edges?: RoadEdge[]; }

export function RoadEdges({ edges }: Props) {
  if (!edges?.length) return null;
  return (
    <>
      {edges.map((e, i) => <EdgeLine key={i} edge={e} />)}
    </>
  );
}

function EdgeLine({ edge }: { edge: RoadEdge }) {
  const geom = useMemo(() => {
    if (edge.pts.length < 2) return null;
    const g = new THREE.BufferGeometry();
    const arr: number[] = [];
    for (const [x, y, z] of edge.pts) arr.push(x, y, z + 0.05);
    g.setAttribute('position', new THREE.Float32BufferAttribute(arr, 3));
    return g;
  }, [edge.pts]);
  if (!geom) return null;
  const conf = Math.max(0, 1 - Math.min(edge.std, 1));
  const opacity = 0.35 + 0.55 * conf;
  return (
    <line>
      <primitive object={geom} attach="geometry" />
      <lineBasicMaterial color={0xff8b3d} transparent opacity={opacity} />
    </line>
  );
}
