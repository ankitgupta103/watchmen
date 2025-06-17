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

export interface SuspiciousEvent {
  timestamp: string;
  type: string;
  confidence: number;
  marked?: 'noted' | 'ignored' | 'unreviewed';
  url?: string;
}

export interface HealthEvent {
  timestamp: string;
  type:
    | 'offline'
    | 'hardware_failure'
    | 'low_battery'
    | 'gps_failure'
    | 'camera_failure';
  severity: 'low' | 'medium' | 'high' | 'critical';
}

export interface MQTTEvent {
  id: string;
  timestamp: Date;
  eventstr: string;
  image_c_key?: string;
  image_f_key?: string;
  cropped_image_url?: string;
  full_image_url?: string;
  images_loaded?: boolean;
}

export interface MachineData {
  machine_id: number;
  health_status: number;
  status: 'online' | 'offline' | 'maintenance';
  location: {
    lat: number;
    lng: number;
  };
  last_updated: string;
  lastSeen?: string;
  is_live: boolean;
  suspiciousEvents?: SuspiciousEvent[];
  healthEvents?: HealthEvent[];
  events?: MQTTEvent[];
  event_count?: number;
  last_event?: MQTTEvent;
  alert_status?: boolean;
  error_count?: number;
  warning_count?: number;
}

export interface MachineStats {
  buffer: number;
  data: {
    message: Partial<MachineData>;
  } | null;
}
