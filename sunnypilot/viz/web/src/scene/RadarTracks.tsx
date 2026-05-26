import { useMemo } from 'react';
import * as THREE from 'three';
import type { Track } from '../types';

interface Props { tracks?: Track[]; }

const MAX_TRACKS = 64;

export function RadarTracks({ tracks }: Props) {
  const inst = useMemo(() => {
    const geo = new THREE.SphereGeometry(0.35, 12, 8);
    const mat = new THREE.MeshBasicMaterial({ color: 0xffd770, transparent: true, opacity: 0.85 });
    return new THREE.InstancedMesh(geo, mat, MAX_TRACKS);
  }, []);

  useMemo(() => {
    const m = new THREE.Matrix4();
    const list = (tracks ?? []).slice(0, MAX_TRACKS);
    for (let i = 0; i < MAX_TRACKS; i++) {
      if (i < list.length) {
        const t = list[i];
        m.makeTranslation(t.dRel, -t.yRel, 0.3);
      } else {
        m.makeScale(0, 0, 0);
      }
      inst.setMatrixAt(i, m);
    }
    inst.instanceMatrix.needsUpdate = true;
    inst.count = MAX_TRACKS;
  }, [tracks, inst]);

  return <primitive object={inst} />;
}
