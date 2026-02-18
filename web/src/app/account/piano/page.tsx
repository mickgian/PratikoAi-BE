'use client';

import { useState } from 'react';
import { useBillingPlans } from '@/lib/hooks/useBillingPlans';
import { useUsageStatus } from '@/lib/hooks/useUsageStatus';
import { PlanCard } from '@/components/features/PlanCard';
import { subscribeToPlan } from '@/lib/api/billing';

export default function PianoPage() {
  const { plans, loading, error } = useBillingPlans();
  const { data: usage } = useUsageStatus();
  const [subscribing, setSubscribing] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  const handleSelect = async (slug: string) => {
    setSubscribing(true);
    setMessage(null);
    try {
      const result = await subscribeToPlan(slug);
      setMessage(result.message_it);
    } catch (e) {
      setMessage(e instanceof Error ? e.message : 'Errore sconosciuto');
    } finally {
      setSubscribing(false);
    }
  };

  if (loading)
    return (
      <div className="text-center py-12 text-gray-500">Caricamento...</div>
    );
  if (error)
    return <div className="text-center py-12 text-red-500">{error}</div>;

  return (
    <div className="space-y-8">
      <div>
        <h2 className="text-lg font-semibold text-[#1E293B]">
          Scegli il tuo piano
        </h2>
        <p className="text-sm text-gray-500 mt-1">
          Seleziona il piano più adatto alle tue esigenze.
        </p>
      </div>

      {message && (
        <div className="bg-blue-50 border border-blue-200 text-blue-700 px-4 py-3 rounded-lg text-sm">
          {message}
        </div>
      )}

      <div className="grid gap-6 md:grid-cols-3">
        {plans.map(plan => (
          <PlanCard
            key={plan.slug}
            plan={plan}
            isCurrentPlan={usage?.plan_slug === plan.slug}
            onSelect={handleSelect}
          />
        ))}
      </div>

      {subscribing && (
        <div className="text-center text-sm text-gray-500">
          Sottoscrizione in corso...
        </div>
      )}
    </div>
  );
}
