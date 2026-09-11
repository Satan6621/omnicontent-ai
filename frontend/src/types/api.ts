export type JobStatus = 'PENDING' | 'PROCESSING' | 'COMPLETED' | 'FAILED';

export interface SocialPost {
  id: number;
  topic: string;
  platform: string;
  content: string;
  hashtags: string;
  llm_provider: string;
  created_at: string;
}

export interface PostListResponse {
  posts: SocialPost[];
  count: number;
}

export interface PostCreateRequest {
  topic: string;
  platform: string;
  tone: string;
}

export interface VideoJob {
  id: number;
  prompt: string;
  script: string;
  status: JobStatus;
  progress: number;
  status_detail: string;
  video_path: string | null;
  video_url: string | null;
  duration_seconds: number | null;
  error: string | null;
  created_at: string;
}

export interface VideoJobListResponse {
  jobs: VideoJob[];
  count: number;
}

export interface VideoCreateRequest {
  prompt: string;
  voice?: string;
  visual_style?: string;
  music_style?: string | null;
}

export interface PublishRequest {
  content: string;
  platforms: string[];
  hashtags?: string;
  video_url?: string | null;
}

export interface PublishResponse {
  results: Record<string, { success: boolean; url?: string; error?: string }>;
  requested: number;
  succeeded: number;
  errors: string[];
}

export interface DashboardStats {
  total_posts: number;
  total_videos: number;
  videos_completed: number;
  videos_processing: number;
  videos_failed: number;
  posts_last_7_days: number;
  videos_last_7_days: number;
}
