import { MachineEvent } from './activity';

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
  last_location: { lat: number; long: number; timestamp: string };
  created_at: string;
  updated_at: string;
  model_id: number;
  model_uid: string;
  manufacturer_id: number;
  model_specifications: Record<string, unknown>;
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
  events: MachineEvent[];
  event_count: number;
  last_event?: MachineEvent;
  last_updated: string;
  is_online: boolean;
  location: { lat: number; lng: number; timestamp: string };
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  stats_data: any;
  buffer_size: number;
  is_pulsating: boolean;
  is_critical: boolean;
}

export interface MachineStats {
  buffer: number;
  data: {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    message: any;
  } | null;
}

export interface MarkerColors {
  bg: string;
  border: string;
  text: string;
}
