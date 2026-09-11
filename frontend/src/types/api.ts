export type JobStatus = 'PENDING' | 'PROCESSING' | 'COMPLETED' | 'FAILED';

export type PublishStatus = 'pending' | 'processing' | 'published' | 'partial' | 'failed' | 'cancelled';

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
  storage_url: string | null;
  duration_seconds: number | null;
  error: string | null;
  auto_publish: boolean;
  publish_platforms: string[];
  style_preset: string;
  scheduled_for: string | null;
  published_at: string | null;
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
  style_preset?: string;
  scheduled_for?: string | null;
  script?: string | null;
  auto_publish?: boolean;
  publish_platforms?: string[];
  publish_content?: string;
  publish_hashtags?: string;
}

export interface VideoEditRequest {
  script?: string;
  auto_publish?: boolean;
  publish_platforms?: string[];
  publish_content?: string;
  publish_hashtags?: string;
  visual_style?: string;
  music_style?: string | null;
  voice?: string;
  style_preset?: string;
  scheduled_for?: string | null;
}

export interface VideoScriptRequest {
  prompt: string;
}

export interface PublishRequest {
  content: string;
  platforms: string[];
  hashtags?: string;
  video_url?: string | null;
  image_data_uri?: string | null;
  scheduled_at?: string | null;
}

export interface PublishResponse {
  results: Record<string, { success: boolean; url?: string; error?: string }>;
  requested: number;
  succeeded: number;
  errors: string[];
  job_id?: number | null;
}

export interface PublishJob {
  id: number;
  content: string;
  platforms: string[];
  hashtags: string;
  video_url: string | null;
  status: PublishStatus;
  per_network: Record<string, { success: boolean; url?: string; error?: string }> | null;
  error: string | null;
  scheduled_at: string | null;
  published_at: string | null;
  source: string;
  created_at: string;
}

export interface PublishJobListResponse {
  jobs: PublishJob[];
  count: number;
}

export interface DashboardStats {
  total_posts: number;
  total_videos: number;
  videos_completed: number;
  videos_processing: number;
  videos_failed: number;
  posts_last_7_days: number;
  videos_last_7_days: number;
  publishes_last_7_days: number;
}

export interface PlatformAnalytics {
  total_published: number;
  total_succeeded: number;
  total_failed: number;
  per_platform: Record<string, { published: number; failed: number; last: string | null }>;
  engagement: AnalyticsItem[];
}

export interface AnalyticsItem {
  id?: number;
  content?: string;
  published_at?: string;
  metrics?: {
    likes: number;
    reposts: number;
    replies: number;
    url?: string | null;
  };
  platform?: string;
  url?: string;
  likes?: number;
  reposts?: number;
  replies?: number;
}

export interface AnalyticsResponse {
  period_days: number;
  publish_summary: PlatformAnalytics;
  top_posts: PublishJob[];
}

export interface ApiKeyResponse {
  id: number;
  name: string;
  scopes: string[];
  active: boolean;
  created_at: string;
  last_used_at: string | null;
  key_preview: string;
}

export interface ApiKeyCreateResponse {
  id: number;
  name: string;
  scopes: string[];
  key: string;
}

export interface ApiKeyCreateRequest {
  name: string;
  scopes?: string[];
}

// ── Webhooks salientes (Feature 3) ────────────────────────
export type WebhookEventType =
  | 'video.completed'
  | 'video.failed'
  | 'publish.succeeded'
  | 'publish.failed';

export interface WebhookSubscription {
  id: number;
  url: string;
  event_type: WebhookEventType;
  active: boolean;
  last_status: string | null;
  last_sent_at: string | null;
  last_error: string | null;
  created_at: string;
}

export interface WebhookCreateRequest {
  url: string;
  event_type: WebhookEventType;
  active?: boolean;
}

export interface WebhookUpdateRequest {
  url?: string;
  event_type?: WebhookEventType;
  active?: boolean;
}