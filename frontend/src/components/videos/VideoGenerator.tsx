'use client';

import { useState } from 'react';
import { Clapperboard, Loader2, RotateCcw, Download } from 'lucide-react';
import { createVideoJob, retryVideoJob } from '@/lib/api';
import { useVideoJobPolling } from '@/hooks/useVideoJob';
import { Button, Card, CardHeader, Input, Progress, Select, Badge } from '@/components/ui/primitives';
import { SocialPublisher } from '@/components/social/SocialPublisher';

const VOICES = [
  { id: 'es-MX-JorgeNeural', label: 'Jorge (es-MX)' },
  { id: 'es-ES-AlvaroNeural', label: 'Álvaro (es-ES)' },
  { id: 'es-AR-TomasNeural', label: 'Tomás (es-AR)' },
  { id: 'en-US-GuyNeural', label: 'Guy (en-US)' },
];

const STYLES = ['cinematic', 'minimalist', 'vibrant', 'corporate'];

const MUSIC_STYLES = [
  { id: '', label: 'Sin música' },
  { id: 'ambient', label: '🎵 Ambient' },
  { id: 'lofi', label: '🎵 Lo-fi' },
  { id: 'upbeat', label: '🎵 Upbeat' },
];

function statusTone(status: string): 'green' | 'yellow' | 'red' | 'zinc' {
  switch (status) {
    case 'COMPLETED': return 'green';
    case 'PROCESSING': return 'yellow';
    case 'FAILED': return 'red';
    default: return 'zinc';
  }
}

export function VideoGenerator() {
  const [prompt, setPrompt] = useState('');
  const [voice, setVoice] = useState(VOICES[0].id);
  const [style, setStyle] = useState('cinematic');
  const [music, setMusic] = useState('lofi');
  const [jobId, setJobId] = useState<number | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  const { job } = useVideoJobPolling(jobId);

  const generate = async () => {
    if (prompt.trim().length < 5) {
      setError('Describe tu video (mínimo 5 caracteres)');
      return;
    }
    setBusy(true);
    setError('');
    try {
      const created = await createVideoJob({
        prompt: prompt.trim(),
        voice,
        visual_style: style,
        music_style: music || null,
      });
      setJobId(created.id);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Error creando job');
    } finally {
      setBusy(false);
    }
  };

  const retry = async () => {
    if (jobId == null) return;
    setBusy(true);
    setError('');
    try {
      await retryVideoJob(jobId);
      setJobId(jobId);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Error reintentando');
    } finally {
      setBusy(false);
    }
  };

  const isRendering = job?.status === 'PROCESSING' || job?.status === 'PENDING';

  return (
    <Card>
      <CardHeader
        title="AI Video Generator"
        subtitle="Prompt → guion + voz + visuales + subtítulos → MP4 1080×1920"
        icon={<Clapperboard size={18} />}
      />
      <div className="space-y-4 p-5">
        <div>
          <label className="mb-1.5 block text-xs font-medium text-zinc-400">Prompt del video</label>
          <Input
            placeholder="Ej: hábitos digitales que te roban tiempo"
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && !busy && generate()}
          />
        </div>
        <div className="grid gap-3 sm:grid-cols-4">
          <div>
            <label className="mb-1.5 block text-xs font-medium text-zinc-400">Voz</label>
            <Select value={voice} onChange={(e) => setVoice(e.target.value)}>
              {VOICES.map((v) => (
                <option key={v.id} value={v.id}>{v.label}</option>
              ))}
            </Select>
          </div>
          <div>
            <label className="mb-1.5 block text-xs font-medium text-zinc-400">Estilo visual</label>
            <Select value={style} onChange={(e) => setStyle(e.target.value)}>
              {STYLES.map((s) => (
                <option key={s} value={s}>{s}</option>
              ))}
            </Select>
          </div>
          <div>
            <label className="mb-1.5 block text-xs font-medium text-zinc-400">Música</label>
            <Select value={music} onChange={(e) => setMusic(e.target.value)}>
              {MUSIC_STYLES.map((m) => (
                <option key={m.id} value={m.id}>{m.label}</option>
              ))}
            </Select>
          </div>
          <div className="flex items-end">
            <Button onClick={generate} disabled={busy || isRendering} className="w-full">
              {busy ? <Loader2 size={16} className="animate-spin" /> : <Clapperboard size={16} />}
              Generar video
            </Button>
          </div>
        </div>

        {error && <p className="text-sm text-red-400">✕ {error}</p>}

        {job && (
          <div className="space-y-4 rounded-lg border border-zinc-800 bg-zinc-950 p-4">
            <div className="flex flex-wrap items-center gap-2">
              <Badge tone={statusTone(job.status)}>{job.status}</Badge>
              <span className="text-xs text-zinc-500">{job.status_detail}</span>
              {job.duration_seconds != null && (
                <span className="text-xs text-zinc-500">· {job.duration_seconds}s</span>
              )}
            </div>

            {(isRendering || job.status === 'COMPLETED') && (
              <Progress value={job.progress} />
            )}
            {isRendering && (
              <p className="text-center text-xs text-zinc-500">
                {job.progress}% — {job.status_detail}…
              </p>
            )}

            {job.status === 'COMPLETED' && job.video_url && (
              <div className="space-y-3">
                <video
                  controls
                  className="mx-auto max-h-[480px] w-full max-w-[300px] rounded-lg border border-zinc-800"
                  src={job.video_url}
                />
                <div className="flex justify-center gap-2">
                  <a href={job.video_url} download>
                    <Button variant="secondary" size="sm">
                      <Download size={14} /> Descargar MP4
                    </Button>
                  </a>
                </div>
                <div className="border-t border-zinc-800 pt-3">
                  <p className="mb-2 text-xs font-medium uppercase tracking-wide text-zinc-500">
                    Publicar el video en redes (vía AutoSocial)
                  </p>
                  <SocialPublisher
                    content={job.prompt}
                    hashtags="#shorts #viral"
                    videoUrl={job.video_url}
                  />
                </div>
              </div>
            )}

            {job.status === 'FAILED' && (
              <div className="space-y-2">
                <p className="text-sm text-red-400">✕ {job.error}</p>
                <Button variant="secondary" size="sm" onClick={retry} disabled={busy}>
                  <RotateCcw size={14} /> Reintentar
                </Button>
              </div>
            )}
          </div>
        )}
      </div>
    </Card>
  );
}
