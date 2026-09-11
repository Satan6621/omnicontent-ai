'use client';

import { useState } from 'react';
import { Send, Loader2, CheckCircle2, XCircle, CalendarClock, RotateCcw } from 'lucide-react';
import { publishContent, retryPublishJob } from '@/lib/api';
import { Button, Input } from '@/components/ui/primitives';
import type { PublishResponse } from '@/types/api';

export const SOCIAL_PLATFORMS = [
  { id: 'mastodon', label: '🐘 Mastodon' },
  { id: 'telegram', label: '✈️ Telegram' },
  { id: 'bluesky', label: '🦋 Bluesky' },
  { id: 'instagram', label: '📸 Instagram' },
];

// F4: solo las redes que el usuario usa vienen seleccionadas por defecto
const DEFAULT_SELECTED: Record<string, boolean> = {
  mastodon: true,
  telegram: true,
  bluesky: false,
  instagram: false,
};

interface SocialPublisherProps {
  content: string;
  hashtags?: string;
  videoUrl?: string | null;
  disabled?: boolean;
  compact?: boolean;
}

export function SocialPublisher({ content, hashtags = '', videoUrl, disabled, compact }: SocialPublisherProps) {
  const [selected, setSelected] = useState<Record<string, boolean>>(DEFAULT_SELECTED);
  const [scheduleTime, setScheduleTime] = useState('');
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<PublishResponse | null>(null);
  const [error, setError] = useState('');

  const platforms = Object.entries(selected).filter(([, v]) => v).map(([k]) => k);

  const publish = async () => {
    if (!platforms.length) {
      setError('Elige al menos una red');
      return;
    }
    if (!content.trim()) {
      setError('No hay contenido para publicar');
      return;
    }
    if (scheduleTime && isNaN(new Date(scheduleTime).getTime())) {
      setError('Formato de fecha inválido');
      return;
    }
    setBusy(true);
    setError('');
    setResult(null);
    try {
      const scheduled_at = scheduleTime ? new Date(scheduleTime).toISOString() : undefined;
      const resp = await publishContent({
        content,
        hashtags,
        platforms,
        video_url: videoUrl ?? undefined,
        scheduled_at,
      });
      setResult(resp);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Error publicando');
    } finally {
      setBusy(false);
    }
  };

  // F7: retry solo redes fallidas
  const retry = async () => {
    if (!result?.job_id) return;
    setBusy(true);
    setError('');
    try {
      const resp = await retryPublishJob(result.job_id);
      setResult(resp);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Error reintentando');
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap gap-1.5">
        {SOCIAL_PLATFORMS.map((p) => (
          <button
            key={p.id}
            type="button"
            onClick={() => setSelected({ ...selected, [p.id]: !selected[p.id] })}
            className={`rounded-full border px-3 py-1.5 text-xs transition-colors ${
              selected[p.id]
                ? 'border-violet-500 bg-violet-950/60 text-violet-300'
                : 'border-zinc-700 bg-zinc-900 text-zinc-500 hover:text-zinc-300'
            }`}
          >
            {p.label}
          </button>
        ))}
      </div>

      {/* F1: publicación programada */}
      <div className="flex items-center gap-2 rounded-lg border border-zinc-800 bg-zinc-950 p-2.5">
        <CalendarClock size={15} className="shrink-0 text-zinc-500" />
        <div className="flex-1">
          <label className="block text-[11px] text-zinc-500">
            Programar (opcional): deja vacío para publicar ahora
          </label>
          <Input
            type="datetime-local"
            value={scheduleTime}
            onChange={(e) => setScheduleTime(e.target.value)}
            className="mt-1"
          />
        </div>
      </div>

      <div className="flex items-center gap-2">
        <Button onClick={publish} disabled={busy || disabled} size={compact ? 'sm' : 'md'}>
          {busy ? <Loader2 size={15} className="animate-spin" /> : <Send size={15} />}
          {busy ? 'Publicando…' : scheduleTime ? 'Programar' : 'Publicar'}
        </Button>
        {videoUrl && (
          <span className="text-xs text-zinc-500">📹 el video se adjunta automáticamente</span>
        )}
      </div>

      {error && <p className="text-sm text-red-400">✕ {error}</p>}

      {result && result.succeeded === 0 && !result.errors.length && result.job_id && scheduleTime && (
        <p className="text-sm text-zinc-400">
          ✅ Programado para el {new Date(scheduleTime).toLocaleString('es')}
        </p>
      )}

      {result && result.succeeded === 0 && !result.errors.length && result.job_id && !scheduleTime && (
        <p className="text-sm text-zinc-400">
          Si hay redes configuradas se publicaron de inmediato (job #{result.job_id}).
        </p>
      )}

      {result && (
        <div className="space-y-1.5 rounded-lg border border-zinc-800 bg-zinc-950 p-3 text-sm">
          {result.succeeded > 0 && (
            <p className="flex items-center gap-1.5 text-emerald-400">
              <CheckCircle2 size={14} /> Publicado en {result.succeeded}/{result.requested}
            </p>
          )}
          {result.errors.length > 0 && (
            <p className="flex items-start gap-1.5 text-red-400">
              <XCircle size={14} className="mt-0.5 shrink-0" /> {result.errors.join(' · ')}
            </p>
          )}
          {Object.entries(result.results).map(([plat, r]) =>
            r.success && r.url ? (
              <a
                key={plat}
                href={r.url}
                target="_blank"
                rel="noreferrer"
                className="block text-xs text-violet-400 hover:underline"
              >
                ↗ {plat}: ver post
              </a>
            ) : r.success ? (
              <p key={plat} className="text-xs text-emerald-400">✓ {plat}</p>
            ) : null,
          )}
          {/* F7: retry de redes fallidas */}
          {result.errors.length > 0 && result.job_id && (
            <div className="flex items-center gap-2 pt-1">
              <Button variant="secondary" size="sm" onClick={retry} disabled={busy}>
                <RotateCcw size={13} /> Reintentar fallidas
              </Button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}