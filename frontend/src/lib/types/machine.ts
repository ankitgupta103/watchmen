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
  machine_id: number;
  timestamp: string;
  type: HealthEventType;
  severity: HealthEventSeverity;
}
export interface SuspiciousEvent {
  machine_id: number;
  timestamp: string;
  url?: string;
  confidence: number;
  type: SuspiciousEventType;
  marked?: SuspiciousEventMarked;
}

export interface Machine {
  id: number;
  name: string;
  type: string;
  machine_uid: string;
  specifications: Record<string, unknown>;
  mfg_date: string;
  activation_date: string;
  end_of_service_date: string | null;
  current_owner: number;
  current_owner_name: string;
  machine_status: string;
  connection_status: string;
  last_location: { lat: number; lng: number };
  created_at: string;
  updated_at: string;
  model_id: number;
  model_uid: string;
  manufacturer_id: number;
  model_specifications: Record<string, unknown>;
}

export interface MachineData {
  status: string;
  lastSeen: string;
  suspiciousEvents?: Array<SuspiciousEvent>;
  healthEvents?: Array<HealthEvent>;
}
