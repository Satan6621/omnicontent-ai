'use client';

import { useState } from 'react';
import { Copy, Sparkles, Loader2 } from 'lucide-react';
import { createPost } from '@/lib/api';
import { useContentStore } from '@/store/contentStore';
import { Button, Card, CardHeader, Input, Select, Textarea } from '@/components/ui/primitives';
import { SocialPublisher } from '@/components/social/SocialPublisher';
import type { SocialPost } from '@/types/api';

const PLATFORMS = ['generic', 'instagram', 'twitter', 'mastodon', 'linkedin', 'tiktok'];
const TONES = ['professional', 'casual', 'inspirational', 'provocative'];

export function PostGenerator() {
  const [topic, setTopic] = useState('');
  const [platform, setPlatform] = useState('generic');
  const [tone, setTone] = useState('professional');
  const [post, setPost] = useState<SocialPost | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [copied, setCopied] = useState(false);
  const setLastPost = useContentStore((s) => s.setLastPost);

  const generate = async () => {
    if (topic.trim().length < 3) {
      setError('Escribe un tema (mínimo 3 caracteres)');
      return;
    }
    setBusy(true);
    setError('');
    try {
      const created = await createPost({ topic: topic.trim(), platform, tone });
      setPost(created);
      setLastPost(created);
      setCopied(false);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Error generando post');
    } finally {
      setBusy(false);
    }
  };

  const copyAll = async () => {
    if (!post) return;
    const text = `${post.content}\n\n${post.hashtags}`;
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      setError('No se pudo copiar al portapapeles');
    }
  };

  return (
    <Card>
      <CardHeader
        title="AI Post Generator"
        subtitle="Tema → post formateado con hashtags"
        icon={<Sparkles size={18} />}
      />
      <div className="space-y-4 p-5">
        <div className="grid gap-3 sm:grid-cols-3">
          <div className="sm:col-span-3">
            <label className="mb-1.5 block text-xs font-medium text-zinc-400">Tema</label>
            <Input
              placeholder="Ej: productividad para emprendedores"
              value={topic}
              onChange={(e) => setTopic(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && !busy && generate()}
            />
          </div>
          <div>
            <label className="mb-1.5 block text-xs font-medium text-zinc-400">Plataforma</label>
            <Select value={platform} onChange={(e) => setPlatform(e.target.value)}>
              {PLATFORMS.map((p) => (
                <option key={p} value={p}>{p}</option>
              ))}
            </Select>
          </div>
          <div>
            <label className="mb-1.5 block text-xs font-medium text-zinc-400">Tono</label>
            <Select value={tone} onChange={(e) => setTone(e.target.value)}>
              {TONES.map((t) => (
                <option key={t} value={t}>{t}</option>
              ))}
            </Select>
          </div>
          <div className="flex items-end">
            <Button onClick={generate} disabled={busy} className="w-full">
              {busy ? <Loader2 size={16} className="animate-spin" /> : <Sparkles size={16} />}
              Generar
            </Button>
          </div>
        </div>

        {error && <p className="text-sm text-red-400">✕ {error}</p>}

        {post && (
          <div className="space-y-3 rounded-lg border border-zinc-800 bg-zinc-950 p-4">
            <Textarea
              value={post.content}
              readOnly
              className="min-h-[140px] bg-zinc-900"
            />
            <p className="text-sm text-violet-400">{post.hashtags}</p>
            <div className="flex items-center gap-2">
              <Button variant="secondary" size="sm" onClick={copyAll}>
                <Copy size={14} />
                {copied ? '¡Copiado!' : 'Copiar post + hashtags'}
              </Button>
              <span className="text-xs text-zinc-500">via {post.llm_provider}</span>
            </div>
            <div className="border-t border-zinc-800 pt-3">
              <p className="mb-2 text-xs font-medium uppercase tracking-wide text-zinc-500">
                Publicar en redes (vía AutoSocial)
              </p>
              <SocialPublisher content={post.content} hashtags={post.hashtags} />
            </div>
          </div>
        )}
      </div>
    </Card>
  );
}
