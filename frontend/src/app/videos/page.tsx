import { VideoGenerator } from "@/components/videos/VideoGenerator";
import { VideoJobList } from "@/components/videos/VideoJobList";

export default function VideosPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">AI Video Generator</h1>
        <p className="text-sm text-zinc-500">MP4 vertical 1080×1920 con voz y subtítulos</p>
      </div>
      <div className="grid gap-6 lg:grid-cols-2">
        <VideoGenerator />
        <VideoJobList />
      </div>
    </div>
  );
}
