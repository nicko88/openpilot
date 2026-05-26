export type Xyz = [number, number, number];

export interface LaneLine { prob: number; pts: Xyz[]; }
export interface RoadEdge { std: number; pts: Xyz[]; }
export interface LeadV3 {
  prob: number; probTime: number;
  x: number[]; y: number[]; v: number[]; a: number[]; t: number[];
}
export interface ModelFrame {
  frameId?: number;
  position?: Xyz[];
  orientation?: Xyz[];
  velocity?: Xyz[];
  acceleration?: Xyz[];
  laneLines?: LaneLine[];
  roadEdges?: RoadEdge[];
  leadsV3?: LeadV3[];
}
export interface RadarLead {
  status: boolean; dRel: number; yRel: number; vRel: number;
  vLead: number; aLeadK: number; aLeadTau: number; modelProb: number; radar: boolean;
}
export interface RadarFrame { leadOne?: RadarLead; leadTwo?: RadarLead; }
export interface Track { id: number; dRel: number; yRel: number; vRel: number; aRel: number; }
export interface CarStateFrame {
  vEgo?: number; aEgo?: number; steeringAngleDeg?: number; steeringTorque?: number;
  gas?: number; brake?: number; gasPressed?: boolean; brakePressed?: boolean;
  leftBlinker?: boolean; rightBlinker?: boolean; standstill?: boolean;
  cruiseEnabled?: boolean; cruiseSpeed?: number;
  gear?: string; fuelGauge?: number;
  mads?: { available?: boolean };
}
export interface ControlsFrame {
  enabled?: boolean; active?: boolean; engageable?: boolean;
  alertText1?: string; alertText2?: string; alertStatus?: string; state?: string;
  experimentalMode?: boolean;
}
export interface DeviceFrame {
  batteryPercent?: number; batteryTempC?: number; ambientTempC?: number;
}
export interface MapdFrame {
  speedLimitValid?: boolean; speedLimit?: number;
}
export interface CalibFrame { rpyCalib?: number[]; calStatus?: string; }
export interface LocationFrame {
  valid?: boolean; orientationNED?: number[]; velocity?: number[]; positionGeodetic?: number[];
}
export interface Frame {
  t: number;
  model?: ModelFrame;
  radar?: RadarFrame;
  tracks?: Track[];
  carState?: CarStateFrame;
  controls?: ControlsFrame;
  calib?: CalibFrame;
  location?: LocationFrame;
  device?: DeviceFrame;
  mapd?: MapdFrame;
}
export type ConnStatus = 'connecting' | 'open' | 'closed' | 'error';
