'use client';

import { useState } from 'react';
import { useUsageStatus } from '@/lib/hooks/useUsageStatus';
import { useCreditTransactions } from '@/lib/hooks/useCreditTransactions';
import {
  rechargeCredits,
  enableExtraUsage,
  type CreditTransaction,
} from '@/lib/api/billing';

const RECHARGE_AMOUNTS = [5, 10, 25, 50, 100];

function TransactionRow({ tx }: { tx: CreditTransaction }) {
  const typeLabel: Record<string, string> = {
    recharge: 'Ricarica',
    consumption: 'Consumo',
    refund: 'Rimborso',
  };
  const typeColor: Record<string, string> = {
    recharge: 'text-green-600',
    consumption: 'text-red-600',
    refund: 'text-blue-600',
  };

  return (
    <tr className="border-t border-gray-100">
      <td className="py-2 text-sm text-gray-600">
        {new Date(tx.created_at).toLocaleDateString('it-IT', {
          day: '2-digit',
          month: '2-digit',
          year: 'numeric',
          hour: '2-digit',
          minute: '2-digit',
        })}
      </td>
      <td className="py-2 text-sm">
        <span className={typeColor[tx.transaction_type] ?? 'text-gray-600'}>
          {typeLabel[tx.transaction_type] ?? tx.transaction_type}
        </span>
      </td>
      <td className="py-2 text-sm text-right font-medium">
        {tx.amount_eur >= 0 ? '+' : ''}
        {tx.amount_eur.toFixed(2)} EUR
      </td>
      <td className="py-2 text-sm text-right text-gray-500">
        {tx.balance_after_eur.toFixed(2)} EUR
      </td>
    </tr>
  );
}

export default function CreditiPage() {
  const { data: usage, refetch: refetchUsage } = useUsageStatus();
  const {
    transactions,
    loading: txLoading,
    refetch: refetchTx,
  } = useCreditTransactions();
  const [recharging, setRecharging] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  const handleRecharge = async (amount: number) => {
    setRecharging(true);
    setMessage(null);
    try {
      await rechargeCredits(amount);
      setMessage(`Ricarica di ${amount} EUR completata.`);
      refetchUsage();
      refetchTx();
    } catch (e) {
      setMessage(e instanceof Error ? e.message : 'Errore sconosciuto');
    } finally {
      setRecharging(false);
    }
  };

  const handleToggleExtra = async () => {
    if (!usage) return;
    try {
      await enableExtraUsage(!usage.credits.extra_usage_enabled);
      refetchUsage();
    } catch (e) {
      setMessage(e instanceof Error ? e.message : 'Errore sconosciuto');
    }
  };

  if (!usage)
    return (
      <div className="text-center py-12 text-gray-500">Caricamento...</div>
    );

  return (
    <div className="space-y-8">
      {/* Balance card */}
      <div className="bg-white rounded-xl p-6 border border-[#C4BDB4]">
        <h3 className="text-sm font-medium text-gray-500 mb-2">
          Saldo crediti
        </h3>
        <div className="flex items-baseline gap-3">
          <span className="text-3xl font-bold text-[#2A5D67]">
            {usage.credits.balance_eur.toFixed(2)} EUR
          </span>
          <button
            onClick={handleToggleExtra}
            className={`text-xs px-3 py-1 rounded-full transition-colors ${
              usage.credits.extra_usage_enabled
                ? 'bg-green-100 text-green-700 hover:bg-green-200'
                : 'bg-gray-100 text-gray-500 hover:bg-gray-200'
            }`}
          >
            {usage.credits.extra_usage_enabled
              ? 'Consumo automatico attivo'
              : 'Consumo automatico disattivato'}
          </button>
        </div>
        <p className="text-xs text-gray-400 mt-2">
          {usage.credits.extra_usage_enabled
            ? 'I crediti verranno consumati automaticamente quando superi i limiti del piano.'
            : 'Attiva il consumo automatico per continuare a usare PratikoAI oltre i limiti del piano.'}
        </p>
      </div>

      {/* Recharge */}
      <div className="bg-white rounded-xl p-6 border border-[#C4BDB4]">
        <h3 className="text-sm font-medium text-gray-500 mb-4">
          Ricarica crediti
        </h3>
        <div className="flex flex-wrap gap-3">
          {RECHARGE_AMOUNTS.map(amount => (
            <button
              key={amount}
              onClick={() => handleRecharge(amount)}
              disabled={recharging}
              className="px-4 py-2 rounded-lg border border-[#2A5D67] text-[#2A5D67] text-sm font-medium hover:bg-[#2A5D67] hover:text-white transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {amount} EUR
            </button>
          ))}
        </div>
        {message && <p className="mt-3 text-sm text-blue-600">{message}</p>}
      </div>

      {/* Transaction history */}
      <div className="bg-white rounded-xl p-6 border border-[#C4BDB4]">
        <h3 className="text-sm font-medium text-gray-500 mb-4">
          Storico transazioni
        </h3>
        {txLoading ? (
          <p className="text-sm text-gray-400">Caricamento...</p>
        ) : transactions.length === 0 ? (
          <p className="text-sm text-gray-400">Nessuna transazione.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="text-xs text-gray-400 text-left">
                  <th className="pb-2 font-medium">Data</th>
                  <th className="pb-2 font-medium">Tipo</th>
                  <th className="pb-2 font-medium text-right">Importo</th>
                  <th className="pb-2 font-medium text-right">Saldo</th>
                </tr>
              </thead>
              <tbody>
                {transactions.map(tx => (
                  <TransactionRow key={tx.id} tx={tx} />
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
