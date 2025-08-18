export interface CroppedImage {
  class_name: string;
  confidence: number;
  image_file_path: string;
}

export interface EventFeedFilters {
  search_query: string;
  severity_levels: number[];
  tag_ids: number[];
}

export interface FeedEvent {
  original_image_path: string;
  annotated_image_path: string;
  cropped_images: CroppedImage[];
  timestamp: number;
  machine_id: number;
  severity: number;
}

export interface S3EventFeedResponse {
  success: boolean;
  events: FeedEvent[];
  chunk: number;
  events_per_chunk: number;
  total_events: number;
  total_chunks: number;
  has_next: boolean;
  applied_filters: EventFeedFilters;
  date_range: {
    start_date: string;
    end_date: string;
  };
}
