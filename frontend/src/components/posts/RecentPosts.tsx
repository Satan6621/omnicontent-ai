'use client';

import { useEffect, useState } from 'react';
import { Copy } from 'lucide-react';
import { listPosts } from '@/lib/api';
import type { SocialPost } from '@/types/api';
import { Button, Card, CardHeader, Badge } from '@/components/ui/primitives';

export function RecentPosts() {
  const [posts, setPosts] = useState<SocialPost[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const load = async () => {
    try {
      const data = await listPosts(20);
      setPosts(data.posts);
      setError('');
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Error cargando posts');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
    const t = setInterval(load, 15000);
    return () => clearInterval(t);
  }, []);

  return (
    <Card>
      <CardHeader title="Historial de posts" subtitle={`${posts.length} generados`} />
      <div className="divide-y divide-zinc-800">
        {loading && <p className="p-5 text-sm text-zinc-500">Cargando…</p>}
        {error && <p className="p-5 text-sm text-red-400">✕ {error}</p>}
        {!loading && !error && posts.length === 0 && (
          <p className="p-5 text-sm text-zinc-500">Sin posts todavía — genera el primero.</p>
        )}
        {posts.map((p) => (
          <div key={p.id} className="space-y-2 p-4">
            <div className="flex flex-wrap items-center gap-2">
              <Badge tone="violet">{p.platform}</Badge>
              <span className="text-xs text-zinc-600">
                {new Date(p.created_at).toLocaleString('es')}
              </span>
              <button
                className="ml-auto rounded p-1 text-zinc-500 hover:bg-zinc-800 hover:text-zinc-300"
                title="Copiar contenido"
                onClick={() =>
                  navigator.clipboard.writeText(`${p.content}\n\n${p.hashtags}`).catch(() => {})
                }
              >
                <Copy size={14} />
              </button>
            </div>
            <p className="line-clamp-3 text-sm text-zinc-300">{p.content}</p>
            <p className="text-xs text-violet-400">{p.hashtags}</p>
          </div>
        ))}
      </div>
    </Card>
  );
}
