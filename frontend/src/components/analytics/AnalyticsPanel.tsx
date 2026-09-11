'use client';

import { useEffect, useState } from 'react';
import { BarChart3, Loader2, RotateCcw, ThumbsUp, Repeat2, MessageSquare, ExternalLink } from 'lucide-react';
import { getAnalytics, listPublishJobs, retryPublishJob } from '@/lib/api';
import { Button, Card, CardHeader, Badge } from '@/components/ui/primitives';
import type { AnalyticsResponse, PublishJob, PublishJobListResponse } from '@/types/api';

function jobTone(status: string): 'green' | 'yellow' | 'red' | 'zinc' {
  switch (status) {
    case 'published': return 'green';
    case 'partial': return 'yellow';
    case 'pending':
    case 'processing': return 'yellow';
    case 'failed': return 'red';
    default: return 'zinc';
  }
}

const NET_LABELS: Record<string, string> = {
  mastodon: '🐘',
  telegram: '✈️',
  bluesky: '🦋',
  instagram: '📸',
};

export function AnalyticsPanel() {
  const [analytics, setAnalytics] = useState<AnalyticsResponse | null>(null);
  const [history, setHistory] = useState<PublishJobListResponse | null>(null);
  const [busy, setBusy] = useState<number | null>(null);
  const [error, setError] = useState('');

  const load = async () => {
    try {
      const [a, h] = await Promise.all([getAnalytics(7), listPublishJobs(30)]);
      setAnalytics(a);
      setHistory(h);
      setError('');
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Error cargando analytics');
    }
  };

  useEffect(() => {
    load();
    const t = setInterval(load, 15000);
    return () => clearInterval(t);
  }, []);

  const retry = async (job: PublishJob) => {
    setBusy(job.id);
    setError('');
    try {
      await retryPublishJob(job.id);
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Error reintentando');
    } finally {
      setBusy(null);
    }
  };

  const summary = analytics?.publish_summary;

  return (
    <div className="space-y-6">
      {error && <p className="text-sm text-red-400">✕ {error}</p>}

      {/* Resumen */}
      <div className="grid gap-4 sm:grid-cols-3">
        <Card className="p-5">
          <p className="text-2xl font-bold text-zinc-100">{summary?.total_published ?? 0}</p>
          <p className="text-xs text-zinc-500">Publicados (7 días)</p>
        </Card>
        <Card className="p-5">
          <p className="text-2xl font-bold text-emerald-400">{summary?.total_succeeded ?? 0}</p>
          <p className="text-xs text-zinc-500">Redes exitosas</p>
        </Card>
        <Card className="p-5">
          <p className="text-2xl font-bold text-red-400">{summary?.total_failed ?? 0}</p>
          <p className="text-xs text-zinc-500">Fallidas</p>
        </Card>
      </div>

      {/* Por plataforma */}
      <Card>
        <CardHeader title="Estado por red" icon={<BarChart3 size={18} />} />
        <div className="grid gap-2 p-5 sm:grid-cols-2">
          {Object.entries(summary?.per_platform ?? {}).map(([plat, agg]) => (
            <div key={plat} className="flex items-center justify-between rounded-lg border border-zinc-800 bg-zinc-950 p-3 text-sm">
              <div className="flex items-center gap-2">
                <span>{NET_LABELS[plat] ?? plat}</span>
                <span className="font-medium text-zinc-300">{plat}</span>
              </div>
              <div className="flex items-center gap-3 text-xs">
                <span className="text-emerald-400">✓ {agg.published}</span>
                <span className="text-red-400">✕ {agg.failed}</span>
              </div>
            </div>
          ))}
          {Object.keys(summary?.per_platform ?? {}).length === 0 && (
            <p className="text-sm text-zinc-500">Sin publicaciones en los últimos 7 días.</p>
          )}
        </div>
      </Card>

      {/* Engagement (de AutoSocial) */}
      {analytics?.publish_summary.engagement?.length ? (
        <Card>
          <CardHeader title="Engagement reciente" icon={<ThumbsUp size={18} />} />
          <div className="divide-y divide-zinc-800">
            {analytics.publish_summary.engagement.slice(0, 10).map((item, i) => (
              <div key={i} className="flex items-center justify-between gap-3 p-3 text-sm">
                <span className="line-clamp-1 text-xs text-zinc-400">{item.content}</span>
                <div className="flex shrink-0 items-center gap-3 text-xs text-zinc-500">
                  <span className="flex items-center gap-1"><ThumbsUp size={12} /> {item.likes ?? 0}</span>
                  <span className="flex items-center gap-1"><Repeat2 size={12} /> {item.reposts ?? 0}</span>
                  <span className="flex items-center gap-1"><MessageSquare size={12} /> {item.replies ?? 0}</span>
                  {item.url && (
                    <a href={item.url} target="_blank" rel="noreferrer" className="text-violet-400 hover:underline">
                      <ExternalLink size={12} />
                    </a>
                  )}
                </div>
              </div>
            ))}
          </div>
        </Card>
      ) : null}

      {/* Historial con retry por red */}
      <Card>
        <CardHeader title="Historial de publicaciones" icon={<BarChart3 size={18} />} />
        <div className="divide-y divide-zinc-800">
          {history?.jobs.length === 0 && (
            <p className="p-5 text-sm text-zinc-500">Sin publicaciones aún.</p>
          )}
          {history?.jobs.map((job) => (
            <div key={job.id} className="p-4">
              <div className="flex flex-wrap items-center gap-2">
                <Badge tone={jobTone(job.status)}>{job.status}</Badge>
                {job.source !== 'api' && (
                  <span className="text-[11px] text-zinc-600">fuente: {job.source}</span>
                )}
                {job.scheduled_at && (
                  <span className="text-[11px] text-zinc-500">⏰ programado {new Date(job.scheduled_at).toLocaleString('es')}</span>
                )}
                {job.published_at && (
                  <span className="text-[11px] text-zinc-600">publicado {new Date(job.published_at).toLocaleString('es')}</span>
                )}
              </div>
              <p className="mt-1.5 line-clamp-2 text-xs text-zinc-400">{job.content}</p>
              <div className="mt-2 flex flex-wrap items-center gap-2">
                {job.platforms.map((p) => {
                  const r = job.per_network?.[p];
                  const ok = r && (r.success || r.url);
                  return (
                    <span key={p} className={`rounded-full border px-2 py-0.5 text-[11px] ${
                      ok ? 'border-emerald-800 bg-emerald-950/40 text-emerald-300'
                      : 'border-red-800 bg-red-950/40 text-red-300'
                    }`}>
                      {NET_LABELS[p] ?? p} {ok ? '✓' : '✕'}
                    </span>
                  );
                })}
                {(job.status === 'failed' || job.status === 'partial') && (
                  <Button variant="secondary" size="sm" onClick={() => retry(job)} disabled={busy === job.id}>
                    {busy === job.id ? <Loader2 size={12} className="animate-spin" /> : <RotateCcw size={12} />}
                    Reintentar
                  </Button>
                )}
                {job.error && <span className="text-[11px] text-red-400">{job.error}</span>}
                {job.per_network && Object.entries(job.per_network).map(([p, r]) =>
                  r.success && r.url ? (
                    <a key={p} href={r.url} target="_blank" rel="noreferrer" className="text-[11px] text-violet-400 hover:underline">
                      ↗ {p}
                    </a>
                  ) : null,
                )}
              </div>
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
}