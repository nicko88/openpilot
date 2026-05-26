import { Billboard, Text } from '@react-three/drei';
import type { LeadV3, RadarFrame } from '../types';

interface Props { modelLeads?: LeadV3[]; radar?: RadarFrame; }

export function Leads({ modelLeads, radar }: Props) {
  return (
    <>
      {modelLeads?.map((l, i) => (l.prob > 0.3 ? <ModelLead key={i} lead={l} idx={i} /> : null))}
      {radar?.leadOne?.status ? <RadarLeadBox lead={radar.leadOne} primary /> : null}
      {radar?.leadTwo?.status ? <RadarLeadBox lead={radar.leadTwo} /> : null}
    </>
  );
}

function ModelLead({ lead, idx }: { lead: LeadV3; idx: number }) {
  const x = lead.x[0] ?? 0;
  const y = lead.y[0] ?? 0;
  const color = idx === 0 ? 0x6effa8 : 0x5ad0ff;
  return (
    <group position={[x, y, 0]}>
      <mesh position={[0, 0, 0.75]}>
        <boxGeometry args={[1.8, 1.6, 1.5]} />
        <meshBasicMaterial color={color} transparent opacity={0.18} wireframe />
      </mesh>
      <mesh position={[0, 0, 0.01]}>
        <ringGeometry args={[0.95, 1.05, 32]} />
        <meshBasicMaterial color={color} transparent opacity={0.55} />
      </mesh>
    </group>
  );
}

function RadarLeadBox({ lead, primary = false }: { lead: NonNullable<RadarFrame['leadOne']>; primary?: boolean }) {
  const color = primary ? 0xff5a8a : 0xffae3d;
  return (
    <group position={[lead.dRel, -lead.yRel, 0]}>
      <mesh position={[0, 0, 0.75]}>
        <boxGeometry args={[2.0, 1.8, 1.5]} />
        <meshBasicMaterial color={color} transparent opacity={0.32} />
      </mesh>
      <Billboard position={[0, 0, 2.0]}>
        <Text fontSize={0.6} color={color} anchorX="center" anchorY="middle">
          {`${lead.dRel.toFixed(1)}m · ${lead.vRel >= 0 ? '+' : ''}${lead.vRel.toFixed(1)}`}
        </Text>
      </Billboard>
    </group>
  );
}
