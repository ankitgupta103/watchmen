export interface MachineEvent {
  id: string;
  timestamp: Date;
  eventstr: string;
  image_c_key?: string;
  image_f_key?: string;
  cropped_image_url?: string;
  full_image_url?: string;
  images_loaded?: boolean;
  event_severity?: string;
}

export interface EventMessage {
  image_c_key: string;
  image_f_key: string;
  eventstr: string;
  event_severity: number;
  meta: {
    node_id: string;
    hb_count: string;
    last_hb_time: string;
    photos_taken: string;
    events_seen: string;
  };
}
