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
  // data: {
  //   status: string;
  //   lastSeen: string;
  //   suspiciousEvents?: Array<SuspiciousEvent>;
  //   healthEvents?: Array<HealthEvent>;
  // };
}

export interface MachineData {
  status: string;
  lastSeen: string;
  suspiciousEvents?: Array<SuspiciousEvent>;
  healthEvents?: Array<HealthEvent>;
}

// {
//   id: 191,
//   name: 'Watchmen-001',
//   type: 'watchmen',
//   machine_uid: 'm-zr5coiogf6',
//   machine_model_details: [Object],
//   specifications: {},
//   mfg_date: '2025-06-04',
//   activation_date: '2025-06-04',
//   end_of_service_date: null,
//   current_owner: 1,
//   current_owner_name: 'Vyom OS',
//   machine_status: 'active',
//   connection_status: 'live',
//   last_location: [Object],
//   camera_feed: 'camera',
//   created_at: '2025-06-04T06:48:21.709629Z',
//   updated_at: '2025-06-04T06:48:21.736124Z',
//   model_id: 53,
//   model_uid: 'netrajaal-watchmen',
//   manufacturer_id: 1,
//   modal_specifications: {}
// }
