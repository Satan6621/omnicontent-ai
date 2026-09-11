import { AnalyticsPanel } from "@/components/analytics/AnalyticsPanel";

export default function AnalyticsPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Analytics</h1>
        <p className="text-sm text-zinc-500">Publicaciones, estado por red y engagement</p>
      </div>
      <AnalyticsPanel />
    </div>
  );
}