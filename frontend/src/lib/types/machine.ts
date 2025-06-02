export type HealthEventType =
  | 'offline'
  | 'hardware_failure'
  | 'low_battery'
  | 'gps_failure'
  | 'camera_failure';

export type HealthEventSeverity = 'low' | 'medium' | 'high' | 'critical';

export type SuspiciousEventType =
  | 'human_detection'
  | 'weapon_detection'
  | 'unusual_activity';

export type SuspiciousEventMarked = 'ignored' | 'noted' | 'unreviewed';

export interface HealthEvent {
  timestamp: string;
  type: HealthEventType;
  severity: HealthEventSeverity;
}
export interface SuspiciousEvent {
  url?: string;
  timestamp: string;
  confidence: number;
  type: SuspiciousEventType;
  marked?: SuspiciousEventMarked;
}

export interface Machine {
  id: number;
  name: string;
  type: string;
  location: { lat: number; lng: number };
  data: {
    status: string;
    lastSeen: string;
    suspiciousEvents?: Array<SuspiciousEvent>;
    healthEvents?: Array<HealthEvent>;
  };
}
