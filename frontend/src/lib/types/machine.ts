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
  tags?: string[]; // Add tags field
}

export interface CroppedImage {
  class_name: string;
  confidence: number;
  image_file_path: string;
}

export interface S3EventData {
  original_image_path: string;
  cropped_images: CroppedImage[];
  timestamp?: number; // Epoch seconds (e.g., 1754382946)
  eventstr?: string;
  event_severity?: string;
  image_c_key?: string;
  image_f_key?: string;
  machine_id?: number;
}

export interface S3EventsResponse {
  success: boolean;
  events: S3EventData[];
  chunk: number;
  events_per_chunk: number;
  total_events: number;
  total_chunks: number;
  has_next: boolean;
}

export interface FeedEvent extends Omit<S3EventData, 'timestamp'> {
  id: string;
  machineId: number;
  machineName: string;
  machineType: string;
  timestamp: Date;
  croppedImageUrls?: string[];
  fullImageUrl?: string;
  imagesLoaded: boolean;
  severity: number;
}

export interface MQTTEvent {
  id: string;
  timestamp: Date;
  original_image_path: string;
  cropped_images: CroppedImage[];
  full_image_url?: string;
  images_loaded?: boolean;
  severity?: number;
}

export interface MachineData {
  machine_id: number;
  events: MachineEvent[];
  event_count: number;
  last_event?: MachineEvent; // This will now use the correct type
  last_updated: string;
  is_online: boolean;
  location: {
    lat: number;
    long: number;
    timestamp: string;
  };
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  stats_data?: any;
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
