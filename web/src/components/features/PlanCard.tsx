'use client';

import type { BillingPlan } from '@/lib/api/billing';

interface PlanCardProps {
  plan: BillingPlan;
  isCurrentPlan: boolean;
  onSelect: (slug: string) => void;
}

const featuresByPlan: Record<string, string[]> = {
  base: [
    'Uso occasionale',
    'Accesso a tutte le funzionalità',
    'Supporto via email',
  ],
  pro: [
    'Uso quotidiano',
    'Accesso a tutte le funzionalità',
    'Supporto prioritario',
    'Limiti di utilizzo aumentati',
  ],
  premium: [
    'Uso intensivo',
    'Accesso a tutte le funzionalità',
    'Supporto dedicato',
    'Limiti di utilizzo massimi',
  ],
};

export function PlanCard({ plan, isCurrentPlan, onSelect }: PlanCardProps) {
  const isPopular = plan.slug === 'pro';
  const features = featuresByPlan[plan.slug] ?? [];

  return (
    <div
      className={`relative rounded-xl border-2 p-6 bg-white transition-shadow hover:shadow-lg ${
        isCurrentPlan
          ? 'border-[#2A5D67] shadow-md'
          : isPopular
            ? 'border-[#D4A574]'
            : 'border-[#C4BDB4]'
      }`}
    >
      {isPopular && (
        <span className="absolute -top-3 left-1/2 -translate-x-1/2 bg-[#D4A574] text-white text-xs font-bold px-3 py-1 rounded-full">
          Popolare
        </span>
      )}
      {isCurrentPlan && (
        <span className="absolute -top-3 left-1/2 -translate-x-1/2 bg-[#2A5D67] text-white text-xs font-bold px-3 py-1 rounded-full">
          Piano attuale
        </span>
      )}

      <h3 className="text-lg font-bold text-[#1E293B] mt-2">{plan.name}</h3>
      <div className="mt-2">
        <span className="text-3xl font-bold text-[#2A5D67]">
          {plan.price_eur_monthly}
        </span>
        <span className="text-gray-500 text-sm"> EUR/mese</span>
      </div>

      <ul className="mt-4 space-y-2 text-sm text-gray-600">
        {features.map(f => (
          <li key={f} className="flex items-center gap-2">
            <svg
              className="h-4 w-4 text-[#2A5D67] flex-shrink-0"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M5 13l4 4L19 7"
              />
            </svg>
            {f}
          </li>
        ))}
      </ul>

      <button
        onClick={() => onSelect(plan.slug)}
        disabled={isCurrentPlan}
        className={`mt-6 w-full py-2 rounded-lg text-sm font-medium transition-colors ${
          isCurrentPlan
            ? 'bg-gray-100 text-gray-400 cursor-not-allowed'
            : 'bg-[#2A5D67] text-white hover:bg-[#1E4A52]'
        }`}
      >
        {isCurrentPlan ? 'Piano attuale' : 'Seleziona piano'}
      </button>
    </div>
  );
}
