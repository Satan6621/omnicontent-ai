import type {
  AnalyticsResponse,
  ApiKeyCreateRequest,
  ApiKeyCreateResponse,
  ApiKeyResponse,
  DashboardStats,
  PostCreateRequest,
  PostListResponse,
  PublishJobListResponse,
  PublishRequest,
  PublishResponse,
  SocialPost,
  VideoCreateRequest,
  VideoEditRequest,
  VideoJob,
  VideoJobListResponse,
  VideoScriptRequest,
} from '@/types/api';

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';
const API_PREFIX = '/api/v1';

function headers(): HeadersInit {
  const h: Record<string, string> = { 'Content-Type': 'application/json' };
  const key = process.env.NEXT_PUBLIC_API_KEY;
  if (key) h['X-API-Key'] = key;
  return h;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${API_PREFIX}${path}`, {
    ...init,
    headers: { ...headers(), ...(init?.headers ?? {}) },
    cache: 'no-store',
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(body.detail ?? `HTTP ${res.status}`);
  }
  return res.json() as Promise<T>;
}

// ── Posts ─────────────────────────────────────────────────
export async function createPost(req: PostCreateRequest): Promise<SocialPost> {
  return request<SocialPost>('/posts', { method: 'POST', body: JSON.stringify(req) });
}

export async function listPosts(limit = 20): Promise<PostListResponse> {
  return request<PostListResponse>(`/posts?limit=${limit}`);
}

// ── Videos ────────────────────────────────────────────────
export async function createVideoJob(req: VideoCreateRequest): Promise<VideoJob> {
  return request<VideoJob>('/videos', { method: 'POST', body: JSON.stringify(req) });
}

export async function getVideoJob(id: number): Promise<VideoJob> {
  return request<VideoJob>(`/videos/${id}`);
}

export async function listVideoJobs(limit = 20): Promise<VideoJobListResponse> {
  return request<VideoJobListResponse>(`/videos?limit=${limit}`);
}

export async function retryVideoJob(id: number): Promise<VideoJob> {
  return request<VideoJob>(`/videos/${id}/retry`, { method: 'POST' });
}

// ── F5: draft mode + edit ─────────────────────────────────
export async function createVideoDraft(req: VideoScriptRequest): Promise<VideoJob> {
  return request<VideoJob>('/videos/draft', { method: 'POST', body: JSON.stringify(req) });
}

export async function editVideoJob(id: number, req: VideoEditRequest): Promise<VideoJob> {
  return request<VideoJob>(`/videos/${id}/edit`, { method: 'POST', body: JSON.stringify(req) });
}

export async function renderVideoJob(id: number): Promise<VideoJob> {
  return request<VideoJob>(`/videos/${id}/render`, { method: 'POST' });
}

// ── Dashboard ─────────────────────────────────────────────
export async function getDashboardStats(): Promise<DashboardStats> {
  return request<DashboardStats>('/dashboard/stats');
}

// ── Publicación (puente a AutoSocial) ─────────────────────
export async function publishContent(req: PublishRequest): Promise<PublishResponse> {
  return request<PublishResponse>('/publish', { method: 'POST', body: JSON.stringify(req) });
}

export async function listPublishJobs(limit = 30): Promise<PublishJobListResponse> {
  return request<PublishJobListResponse>(`/publish/jobs?limit=${limit}`);
}

export async function retryPublishJob(id: number): Promise<PublishResponse> {
  return request<PublishResponse>(`/publish/jobs/${id}/retry`, { method: 'POST' });
}

// ── Analytics (F6) ────────────────────────────────────────
export async function getAnalytics(periodDays = 7): Promise<AnalyticsResponse> {
  return request<AnalyticsResponse>(`/analytics?period_days=${periodDays}`);
}

// ── API Keys multi-cliente (E5) ───────────────────────────
export async function listApiKeys(): Promise<ApiKeyResponse[]> {
  return request<ApiKeyResponse[]>('/apikeys');
}

export async function createApiKey(req: ApiKeyCreateRequest): Promise<ApiKeyCreateResponse> {
  return request<ApiKeyCreateResponse>('/apikeys', { method: 'POST', body: JSON.stringify(req) });
}

export async function deleteApiKey(id: number): Promise<void> {
  await request<unknown>(`/apikeys/${id}`, { method: 'DELETE' });
}