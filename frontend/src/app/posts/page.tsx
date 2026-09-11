import { PostGenerator } from "@/components/posts/PostGenerator";
import { RecentPosts } from "@/components/posts/RecentPosts";

export default function PostsPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">AI Post Generator</h1>
        <p className="text-sm text-zinc-500">Tema → post listo para publicar con hashtags</p>
      </div>
      <div className="grid gap-6 lg:grid-cols-2">
        <PostGenerator />
        <RecentPosts />
      </div>
    </div>
  );
}
