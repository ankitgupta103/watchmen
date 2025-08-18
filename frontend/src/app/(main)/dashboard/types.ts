// Dashboard Types
export interface MachineTag {
  id: number;
  name: string;
  description?: string;
  color?: string;
}

export interface MachineLocation {
  lat: number;
  long: number;
}

export interface Machine {
  id: number;
  name: string;
  type: string;
  created_at: string;
  updated_at: string;
  last_location?: MachineLocation;
  tags?: MachineTag[];
  is_online?: boolean;
  last_seen?: string;
}

export interface CroppedImage {
  class_name: string;
  confidence: number;
  image_file_path: string;
  bounding_box?: {
    x: number;
    y: number;
    width: number;
    height: number;
  };
}

export interface RawEvent {
  timestamp: number | Date;
  machine_id: number;
  eventstr?: string;
  original_image_path?: string;
  cropped_images?: CroppedImage[];
  severity: number;
}

export interface FeedEvent extends RawEvent {
  id: string;
  machineId: number;
  machineName: string;
  machineType: string;
  timestamp: Date;
  imagesLoaded: boolean;
  fullImageUrl?: string;
  croppedImageUrls?: string[];
}

export interface EventFilters {
  searchQuery: string;
  severityLevels: number[];
  tagIds: number[];
  machineId?: number;
}

export interface DateRange {
  startDate: Date;
  endDate: Date;
}

export interface S3EventsResponse {
  success: boolean;
  events: RawEvent[];
  chunk: number;
  events_per_chunk: number;
  total_events: number;
  total_chunks: number;
  has_next: boolean;
  applied_filters: {
    search_query: string;
    severity_levels: number[];
    tag_ids: number[];
  };
  date_range: {
    start_date: string;
    end_date: string;
  };
}

export interface DashboardPageProps {
  machines: Machine[];
  organizationId: number;
}

export interface SeverityInfo {
  label: string;
  className: string;
  description: string;
}
