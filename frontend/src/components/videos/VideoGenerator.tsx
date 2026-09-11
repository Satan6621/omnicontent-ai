'use client';

import { useState } from 'react';
import { Clapperboard, Loader2, RotateCcw, Download, PencilLine, Wand2, CalendarClock } from 'lucide-react';
import { createVideoDraft, createVideoJob, editVideoJob, renderVideoJob, retryVideoJob } from '@/lib/api';
import { useVideoJobPolling } from '@/hooks/useVideoJob';
import { Button, Card, CardHeader, Input, Progress, Select, Badge, Textarea } from '@/components/ui/primitives';
import { SOCIAL_PLATFORMS, SocialPublisher } from '@/components/social/SocialPublisher';

const VOICES = [
  { id: 'es-MX-JorgeNeural', label: 'Jorge (es-MX)' },
  { id: 'es-ES-AlvaroNeural', label: 'Álvaro (es-ES)' },
  { id: 'es-AR-TomasNeural', label: 'Tomás (es-AR)' },
  { id: 'en-US-GuyNeural', label: 'Guy (en-US)' },
];

const STYLES = ['cinematic', 'minimalist', 'vibrant', 'corporate'];

const STYLE_PRESETS = [
  { id: 'cinematic', label: 'Cinematic' },
  { id: 'minimalist', label: 'Minimalista' },
  { id: 'bold_contrast', label: 'Bold Contrast' },
  { id: 'retro', label: 'Retro' },
];

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
  const [stylePreset, setStylePreset] = useState('cinematic');
  const [music, setMusic] = useState('lofi');
  // Feature 1: programar el render (datetime-local → ISO con zona)
  const [scheduleTime, setScheduleTime] = useState('');
  const [scheduledFor, setScheduledFor] = useState<string | null>(null);
  // F5: draft/edición de script
  const [draftScript, setDraftScript] = useState('');
  const [editing, setEditing] = useState(false);
  // F2: auto-publicar al completar
  const [autoPublish, setAutoPublish] = useState(false);
  const [publishNets, setPublishNets] = useState<Record<string, boolean>>({
    mastodon: true, telegram: true, bluesky: false, instagram: false,
  });
  const [jobId, setJobId] = useState<number | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  const { job } = useVideoJobPolling(jobId);

  // F5 paso 1: generar solo el guion (sin render)
  const generateDraft = async () => {
    if (prompt.trim().length < 5) {
      setError('Describe tu video (mínimo 5 caracteres)');
      return;
    }
    setBusy(true);
    setError('');
    try {
      const draft = await createVideoDraft({ prompt: prompt.trim() });
      setDraftScript(draft.script || '');
      setEditing(true);
      setJobId(draft.id);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Error generando guion');
    } finally {
      setBusy(false);
    }
  };

  // F2 + F5 + Feature 1: guardar editado y renderizar (inmediato o programado)
  const render = async () => {
    if (!jobId || !draftScript.trim()) {
      setError('Primero genera el guion');
      return;
    }
    setBusy(true);
    setError('');
    const nets = Object.entries(publishNets).filter(([, v]) => v).map(([k]) => k);
    try {
      await editVideoJob(jobId, {
        script: draftScript.trim(),
        auto_publish: autoPublish,
        publish_platforms: autoPublish ? nets : [],
        publish_content: prompt.trim(),
        publish_hashtags: '#shorts #viral',
        visual_style: style,
        music_style: music || null,
        voice,
        style_preset: stylePreset,
        scheduled_for: scheduledFor,
      });
      if (!scheduledFor) {
        const r = await renderVideoJob(jobId);
        setJobId(r.id);
        setError('');
      } else {
        setError('');
      }
      setEditing(false);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Error renderizando');
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
        subtitle="Prompt → guion editable → voz + visuales + subtítulos → MP4"
        icon={<Clapperboard size={18} />}
      />
      <div className="space-y-4 p-5">
        <div>
          <label className="mb-1.5 block text-xs font-medium text-zinc-400">Prompt del video</label>
          <Input
            placeholder="Ej: hábitos digitales que te roban tiempo"
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
          />
        </div>

        {!editing ? (
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
            <div className="flex items-end gap-1.5">
              {/* F5: dos botones — draft para editar, o directo */}
              <Button onClick={generateDraft} disabled={busy || isRendering} className="w-full">
                {busy ? <Loader2 size={16} className="animate-spin" /> : <PencilLine size={16} />}
                Guion & editar
              </Button>
            </div>
          </div>
        ) : (
          <div className="space-y-3 rounded-lg border border-violet-900/50 bg-violet-950/10 p-4">
            <div className="flex items-center gap-2">
              <Wand2 size={14} className="text-violet-400" />
              <p className="text-xs font-medium text-violet-300">Paso 2 — Revisa y edita el guion antes de renderizar</p>
            </div>
            <Textarea
              rows={6}
              value={draftScript}
              onChange={(e) => setDraftScript(e.target.value)}
              className="w-full rounded-lg border border-zinc-800 bg-zinc-950 p-3 text-sm"
            />
            {/* F2 + Feature 2: auto-publicar al completar + preset de estilo */}
            <div className="grid gap-3 sm:grid-cols-2">
              <div>
                <label className="mb-1.5 block text-xs font-medium text-zinc-400">Preset de subtítulos</label>
                <Select value={stylePreset} onChange={(e) => setStylePreset(e.target.value)}>
                  {STYLE_PRESETS.map((s) => (
                    <option key={s.id} value={s.id}>{s.label}</option>
                  ))}
                </Select>
              </div>
              <div>
                <label className="mb-1.5 block text-xs font-medium text-zinc-400">Programar render (opcional)</label>
                <Input
                  type="datetime-local"
                  value={scheduleTime}
                  onChange={(e) => {
                    setScheduleTime(e.target.value);
                    setScheduledFor(
                      e.target.value
                        ? new Date(e.target.value).toISOString()
                        : null
                    );
                  }}
                />
                {scheduledFor && (
                  <p className="mt-1 text-[11px] text-violet-400">
                    Se renderizará automáticamente el{' '}
                    {new Date(scheduledFor).toLocaleString('es', {
                      dateStyle: 'short',
                      timeStyle: 'short',
                    })}
                  </p>
                )}
              </div>
            </div>
            {/* F2: auto-publicar al completar */}
            <label className="flex items-center gap-2 text-xs text-zinc-400">
              <input
                type="checkbox"
                checked={autoPublish}
                onChange={(e) => setAutoPublish(e.target.checked)}
                className="accent-violet-500"
              />
              Auto-publicar al completar
            </label>
            {autoPublish && (
              <div className="flex flex-wrap gap-1.5">
                {SOCIAL_PLATFORMS.map((p) => (
                  <button
                    key={p.id}
                    type="button"
                    onClick={() => setPublishNets({ ...publishNets, [p.id]: !publishNets[p.id] })}
                    className={`rounded-full border px-2.5 py-1 text-[11px] transition-colors ${
                      publishNets[p.id]
                        ? 'border-violet-500 bg-violet-950/60 text-violet-300'
                        : 'border-zinc-700 bg-zinc-900 text-zinc-500'
                    }`}
                  >
                    {p.label}
                  </button>
                ))}
              </div>
            )}
            <div className="flex gap-2">
              <Button onClick={render} disabled={busy || isRendering}>
                {busy ? <Loader2 size={15} className="animate-spin" /> : <CalendarClock size={15} />}
                {scheduledFor ? 'Programar render' : 'Renderizar video'}
              </Button>
              <Button variant="secondary" onClick={() => { setEditing(false); setDraftScript(''); setScheduledFor(null); setScheduleTime(''); }}>
                Cancelar
              </Button>
            </div>
          </div>
        )}

        {error && <p className="text-sm text-red-400">✕ {error}</p>}

        {job && (
          <div className="space-y-4 rounded-lg border border-zinc-800 bg-zinc-950 p-4">
            <div className="flex flex-wrap items-center gap-2">
              <Badge tone={statusTone(job.status)}>{job.status}</Badge>
              <span className="text-xs text-zinc-500">{job.status_detail}</span>
              {job.duration_seconds != null && (
                <span className="text-xs text-zinc-500">· {job.duration_seconds}s</span>
              )}
              {job.auto_publish && (
                <Badge tone="green">auto-publicar ON</Badge>
              )}
              {job.scheduled_for && (
                <Badge tone="violet">
                  Programado · {new Date(job.scheduled_for).toLocaleString('es', { dateStyle: 'short', timeStyle: 'short' })}
                </Badge>
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