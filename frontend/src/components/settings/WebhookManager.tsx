'use client';

import { useCallback, useEffect, useState } from 'react';
import { Webhook, Plus, Trash2, Play, Loader2 } from 'lucide-react';
import {
  createWebhook,
  deleteWebhook,
  listWebhooks,
  testWebhook,
  updateWebhook,
} from '@/lib/api';
import type { WebhookEventType, WebhookSubscription } from '@/types/api';
import { Button, Card, CardHeader, Input, Select, Badge } from '@/components/ui/primitives';

const EVENT_TYPES: { id: WebhookEventType; label: string }[] = [
  { id: 'video.completed', label: 'Video completado' },
  { id: 'video.failed', label: 'Video fallido' },
  { id: 'publish.succeeded', label: 'Publicación exitosa' },
  { id: 'publish.failed', label: 'Publicación fallida' },
];

export function WebhookManager() {
  const [webhooks, setWebhooks] = useState<WebhookSubscription[]>([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [url, setUrl] = useState('');
  const [eventType, setEventType] = useState<WebhookEventType>('video.completed');
  const [testingId, setTestingId] = useState<number | null>(null);
  const [testMsg, setTestMsg] = useState<Record<number, { ok: boolean; msg: string }>>({});

  const refresh = useCallback(async () => {
    try {
      setWebhooks(await listWebhooks());
      setError('');
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Error cargando webhooks');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const add = async () => {
    if (!url.trim()) {
      setError('Indica la URL del webhook');
      return;
    }
    setBusy(true);
    setError('');
    try {
      await createWebhook({ url: url.trim(), event_type: eventType, active: true });
      setUrl('');
      await refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Error creando webhook');
    } finally {
      setBusy(false);
    }
  };

  const toggle = async (w: WebhookSubscription) => {
    try {
      await updateWebhook(w.id, { active: !w.active });
      await refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Error actualizando webhook');
    }
  };

  const test = async (w: WebhookSubscription) => {
    setTestingId(w.id);
    setTestMsg({});
    try {
      await testWebhook(w.id);
      setTestMsg({ [w.id]: { ok: true, msg: `HTTP ${w.last_status ?? 'ok'}` } });
    } catch (e) {
      setTestMsg({ [w.id]: { ok: false, msg: e instanceof Error ? e.message : 'Error de prueba' } });
    } finally {
      setTestingId(null);
      await refresh();
    }
  };

  const remove = async (id: number) => {
    try {
      await deleteWebhook(id);
      await refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Error eliminando webhook');
    }
  };

  return (
    <Card>
      <CardHeader
        title="Webhooks salientes"
        subtitle="Recibe POST cuando un video termina o se publica (integraciones n8n / Make)"
        icon={<Webhook size={18} />}
      />
      <div className="space-y-4 p-5">
        <div className="grid gap-3 sm:grid-cols-[1fr_220px_auto]">
          <Input
            placeholder="https://hook.example.com/endpoint"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
          />
          <Select value={eventType} onChange={(e) => setEventType(e.target.value as WebhookEventType)}>
            {EVENT_TYPES.map((ev) => (
              <option key={ev.id} value={ev.id}>{ev.label}</option>
            ))}
          </Select>
          <Button onClick={add} disabled={busy}>
            {busy ? <Loader2 size={15} className="animate-spin" /> : <Plus size={15} />}
            Agregar
          </Button>
        </div>

        {error && <p className="text-sm text-red-400">✕ {error}</p>}

        {loading ? (
          <p className="text-sm text-zinc-500">Cargando…</p>
        ) : webhooks.length === 0 ? (
          <p className="text-sm text-zinc-500">Sin webhooks configurados.</p>
        ) : (
          <ul className="space-y-2">
            {webhooks.map((w) => (
              <li key={w.id} className="flex flex-wrap items-center gap-3 rounded-lg border border-zinc-800 bg-zinc-950/60 px-4 py-3">
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm text-zinc-200">{w.url}</p>
                  <p className="mt-0.5 text-xs text-zinc-500">
                    {EVENT_TYPES.find((e) => e.id === w.event_type)?.label ?? w.event_type}
                    {w.last_sent_at && ` · último envío ${new Date(w.last_sent_at).toLocaleString('es')}`}
                  </p>
                </div>
                {w.last_status && (
                  <Badge tone={w.last_status === 'ok' ? 'green' : 'red'}>
                    {w.last_status === 'ok' ? 'OK' : w.last_status}
                  </Badge>
                )}
                {testMsg[w.id] && !testMsg[w.id].ok && (
                  <span className="text-xs text-red-400" title={testMsg[w.id].msg}>✕ {testMsg[w.id].msg}</span>
                )}
                <button
                  onClick={() => toggle(w)}
                  className="rounded-full border px-2.5 py-1 text-[11px] transition-colors"
                  style={w.active
                    ? { borderColor: 'rgb(139 92 246 / .5)', color: '#c4b5fd', backgroundColor: 'rgb(76 29 149 / .6)' }
                    : { borderColor: '#3f3f46', color: '#71717a', backgroundColor: '#18181b' }}
                >
                  {w.active ? 'Activo' : 'Inactivo'}
                </button>
                <Button variant="ghost" size="sm" onClick={() => test(w)} disabled={testingId === w.id || !w.active}>
                  {testingId === w.id ? <Loader2 size={13} className="animate-spin" /> : <Play size={13} />}
                  Probar
                </Button>
                <Button variant="destructive" size="sm" onClick={() => remove(w.id)}>
                  <Trash2 size={13} />
                </Button>
              </li>
            ))}
          </ul>
        )}
      </div>
    </Card>
  );
}