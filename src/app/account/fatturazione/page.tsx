'use client';

import { useUsageStatus } from '@/lib/hooks/useUsageStatus';

export default function FatturazionePage() {
  const { data, loading } = useUsageStatus();

  if (loading)
    return (
      <div className="text-center py-12 text-gray-500">Caricamento...</div>
    );

  return (
    <div className="space-y-8">
      <div>
        <h2 className="text-lg font-semibold text-[#1E293B]">Fatturazione</h2>
        <p className="text-sm text-gray-500 mt-1">
          Gestisci le tue fatture e i metodi di pagamento.
        </p>
      </div>

      <div className="bg-white rounded-xl p-6 border border-[#C4BDB4]">
        <h3 className="text-sm font-medium text-gray-500 mb-2">
          Piano attuale
        </h3>
        <p className="text-lg font-semibold text-[#1E293B]">
          {data?.plan_name ?? '—'}
        </p>
      </div>

      <div className="bg-white rounded-xl p-6 border border-[#C4BDB4]">
        <h3 className="text-sm font-medium text-gray-500 mb-4">
          Storico fatture
        </h3>
        <p className="text-sm text-gray-400">
          Nessuna fattura disponibile al momento.
        </p>
      </div>
    </div>
  );
}
