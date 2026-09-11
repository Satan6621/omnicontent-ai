'use client';

import { useEffect, useState } from 'react';
import { FileText, Video, Activity, CheckCircle2, XCircle, Clock } from 'lucide-react';
import { getDashboardStats, listPosts } from '@/lib/api';
import type { DashboardStats, SocialPost } from '@/types/api';
import { Card, CardHeader, Badge } from '@/components/ui/primitives';

function StatCard({ icon, label, value, accent }: { icon: React.ReactNode; label: string; value: number | string; accent?: string }) {
  return (
    <Card className="p-5">
      <div className="flex items-center gap-3">
        <div className={`rounded-lg p-2.5 ${accent ?? 'bg-violet-950 text-violet-400'}`}>
          {icon}
        </div>
        <div>
          <p className="text-2xl font-bold text-zinc-100">{value}</p>
          <p className="text-xs text-zinc-500">{label}</p>
        </div>
      </div>
    </Card>
  );
}

export function DashboardOverview() {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [recentPosts, setRecentPosts] = useState<SocialPost[]>([]);
  const [error, setError] = useState('');

  useEffect(() => {
    const load = async () => {
      try {
        const [s, p] = await Promise.all([getDashboardStats(), listPosts(5)]);
        setStats(s);
        setRecentPosts(p.posts);
        setError('');
      } catch (e) {
        setError(e instanceof Error ? e.message : 'Error cargando dashboard');
      }
    };
    load();
    const t = setInterval(load, 10000);
    return () => clearInterval(t);
  }, []);

  if (error) return <p className="text-sm text-red-400">✕ {error}</p>;
  if (!stats) return <p className="text-sm text-zinc-500">Cargando estadísticas…</p>;

  return (
    <div className="space-y-6">
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard icon={<FileText size={20} />} label="Posts generados" value={stats.total_posts} accent="bg-fuchsia-950 text-fuchsia-400" />
        <StatCard icon={<Video size={20} />} label="Videos totales" value={stats.total_videos} />
        <StatCard icon={<CheckCircle2 size={20} />} label="Videos completados" value={stats.videos_completed} accent="bg-emerald-950 text-emerald-400" />
        <StatCard icon={<Clock size={20} />} label="Últimos 7 días" value={`${stats.posts_last_7_days} posts · ${stats.videos_last_7_days} videos`} accent="bg-amber-950 text-amber-400" />
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        <Card>
          <CardHeader title="Estado de renders" icon={<Activity size={18} />} />
          <div className="flex flex-wrap gap-3 p-5">
            <Badge tone="yellow">{stats.videos_processing} procesando</Badge>
            <Badge tone="green">{stats.videos_completed} completados</Badge>
            <Badge tone="red">{stats.videos_failed} fallidos</Badge>
          </div>
        </Card>

        <Card>
          <CardHeader title="Posts recientes" icon={<FileText size={18} />} />
          <div className="divide-y divide-zinc-800">
            {recentPosts.length === 0 && (
              <p className="p-5 text-sm text-zinc-500">Sin posts aún — genera el primero.</p>
            )}
            {recentPosts.map((p) => (
              <div key={p.id} className="p-4">
                <p className="text-sm font-medium text-zinc-200">{p.topic}</p>
                <p className="mt-0.5 line-clamp-2 text-xs text-zinc-500">{p.content}</p>
                <div className="mt-1.5 flex gap-2 text-xs text-zinc-600">
                  <span>{p.platform}</span>
                  <span>·</span>
                  <span>{new Date(p.created_at).toLocaleString('es')}</span>
                </div>
              </div>
            ))}
          </div>
        </Card>
      </div>
    </div>
  );
}
