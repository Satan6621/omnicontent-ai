import type {
  DashboardStats,
  PostCreateRequest,
  PostListResponse,
  PublishRequest,
  PublishResponse,
  SocialPost,
  VideoCreateRequest,
  VideoJob,
  VideoJobListResponse,
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

// ── Dashboard ─────────────────────────────────────────────
export async function getDashboardStats(): Promise<DashboardStats> {
  return request<DashboardStats>('/dashboard/stats');
}

// ── Publicación (puente a AutoSocial) ─────────────────────
export async function publishContent(req: PublishRequest): Promise<PublishResponse> {
  return request<PublishResponse>('/publish', { method: 'POST', body: JSON.stringify(req) });
}
