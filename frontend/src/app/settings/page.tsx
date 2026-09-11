import type { Metadata } from 'next';
import { WebhookManager } from '@/components/settings/WebhookManager';

export const metadata: Metadata = {
  title: 'Ajustes · OmniContent AI',
};

export default function SettingsPage() {
  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <h1 className="text-xl font-bold tracking-tight">Ajustes</h1>
      <WebhookManager />
    </div>
  );
}