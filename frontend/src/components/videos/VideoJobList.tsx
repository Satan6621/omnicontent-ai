'use client';

import { Download, RotateCcw, Send } from 'lucide-react';
import { retryVideoJob } from '@/lib/api';
import { useVideoJobsList } from '@/hooks/useVideoJob';
import { Badge, Button, Card, CardHeader } from '@/components/ui/primitives';

function statusTone(status: string): 'green' | 'yellow' | 'red' | 'zinc' {
  switch (status) {
    case 'COMPLETED': return 'green';
    case 'PROCESSING': return 'yellow';
    case 'FAILED': return 'red';
    default: return 'zinc';
  }
}

export function VideoJobList() {
  const { jobs, loading, error, refresh } = useVideoJobsList();

  const retry = async (id: number) => {
    try {
      await retryVideoJob(id);
      refresh();
    } catch {
      // el polling refrescará el estado
    }
  };

  return (
    <Card>
      <CardHeader title="Renders" subtitle={`${jobs.length} jobs`} />
      <div className="divide-y divide-zinc-800">
        {loading && <p className="p-5 text-sm text-zinc-500">Cargando…</p>}
        {error && <p className="p-5 text-sm text-red-400">✕ {error}</p>}
        {!loading && !error && jobs.length === 0 && (
          <p className="p-5 text-sm text-zinc-500">Sin renders todavía — genera el primero.</p>
        )}
        {jobs.map((j) => (
          <div key={j.id} className="space-y-2 p-4">
            <div className="flex flex-wrap items-center gap-2">
              <Badge tone={statusTone(j.status)}>{j.status}</Badge>
              <span className="line-clamp-1 text-sm text-zinc-300">{j.prompt}</span>
              <span className="ml-auto text-xs text-zinc-600">
                {new Date(j.created_at).toLocaleString('es')}
              </span>
            </div>
            <div className="flex items-center gap-2 text-xs text-zinc-500">
              <span>{j.status_detail}</span>
              {j.duration_seconds != null && <span>· {j.duration_seconds}s</span>}
              {j.auto_publish && (
                <Badge tone="green">
                  <Send size={10} /> auto-pub
                </Badge>
              )}
              {j.status === 'COMPLETED' && j.video_url && (
                <a href={j.video_url} download className="ml-auto">
                  <Button variant="ghost" size="sm">
                    <Download size={13} /> MP4
                  </Button>
                </a>
              )}
              {j.status === 'FAILED' && (
                <Button variant="ghost" size="sm" className="ml-auto" onClick={() => retry(j.id)}>
                  <RotateCcw size={13} /> Reintentar
                </Button>
              )}
            </div>
          </div>
        ))}
      </div>
    </Card>
  );
}
