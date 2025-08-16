import { CroppedImage } from './machine';

export interface MachineEvent {
  id: string;
  timestamp: Date;
  eventstr: string;
  severity: number;
  original_image_path?: string;
  cropped_images?: CroppedImage[];
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
