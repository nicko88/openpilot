import type { CarStateFrame } from '../types';

interface Props { carState?: CarStateFrame; }

export function Ego({ carState }: Props) {
  const yaw = -(carState?.steeringAngleDeg ?? 0) * (Math.PI / 180) * 0.04;
  return (
    <group rotation={[0, 0, yaw]}>
      <mesh position={[0.5, 0, 0.55]} castShadow>
        <boxGeometry args={[4.7, 1.85, 1.45]} />
        <meshStandardMaterial color={0x4ea0ff} emissive={0x102036} metalness={0.6} roughness={0.35} />
      </mesh>
      <mesh position={[0.5, 0, 1.2]}>
        <boxGeometry args={[2.4, 1.7, 0.45]} />
        <meshStandardMaterial color={0x0a1626} transparent opacity={0.6} metalness={0.8} roughness={0.1} />
      </mesh>
      <mesh position={[2.6, 0, 0.55]}>
        <coneGeometry args={[0.18, 0.5, 4]} />
        <meshBasicMaterial color={0x9be7ff} />
      </mesh>
    </group>
  );
}
