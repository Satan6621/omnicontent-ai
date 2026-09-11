import { DashboardOverview } from "@/components/dashboard/DashboardOverview";

export default function Home() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Dashboard</h1>
        <p className="text-sm text-zinc-500">Resumen de tu contenido generado con IA</p>
      </div>
      <DashboardOverview />
    </div>
  );
}
