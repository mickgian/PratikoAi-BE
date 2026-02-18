/**
 * Billing API client (DEV-257).
 *
 * Functions for usage status, credits, and plan management.
 */

import { apiClient } from '@/lib/api';

// --- Types ---

export interface WindowInfo {
  window_type: string;
  current_cost_eur: number;
  limit_cost_eur: number;
  usage_percentage: number;
  reset_at: string | null;
  reset_in_minutes: number | null;
}

export interface CreditInfo {
  balance_eur: number;
  extra_usage_enabled: boolean;
}

export interface UsageStatus {
  plan_slug: string;
  plan_name: string;
  window_5h: WindowInfo;
  window_7d: WindowInfo;
  credits: CreditInfo;
  is_admin: boolean;
  message_it: string;
}

export interface BillingPlan {
  slug: string;
  name: string;
  price_eur_monthly: number;
  monthly_cost_limit_eur: number;
  window_5h_cost_limit_eur: number;
  window_7d_cost_limit_eur: number;
  credit_markup_factor: number;
  markup_percentage: number;
}

export interface CreditTransaction {
  id: number;
  transaction_type: string;
  amount_eur: number;
  balance_after_eur: number;
  description: string | null;
  created_at: string;
}

export interface CreditBalance {
  balance_eur: number;
  extra_usage_enabled: boolean;
}

export interface PlansListResponse {
  plans: BillingPlan[];
}

export interface TransactionHistoryResponse {
  transactions: CreditTransaction[];
  total: number;
}

export interface PlanSubscribedResponse {
  success: boolean;
  plan: BillingPlan;
  message_it: string;
}

// --- Admin Simulator Types ---

export interface SimulateUsageResponse {
  success: boolean;
  window_type: string;
  target_percentage: number;
  simulated_cost_eur: number;
  limit_cost_eur: number;
  message_it: string;
}

export interface ResetUsageResponse {
  success: boolean;
  windows_cleared: number;
  redis_keys_cleared: number;
  message_it: string;
}

// --- API Functions ---

const BASE = '/api/v1/billing';

export async function getUsageStatus(): Promise<UsageStatus> {
  const response = await fetch(`${apiClient['baseUrl']}${BASE}/usage`, {
    headers: { Authorization: `Bearer ${apiClient['accessToken']}` },
  });
  if (!response.ok)
    throw new Error('Errore nel recupero dello stato di utilizzo');
  return response.json();
}

export async function getCreditBalance(): Promise<CreditBalance> {
  const response = await fetch(
    `${apiClient['baseUrl']}${BASE}/credits/balance`,
    {
      headers: { Authorization: `Bearer ${apiClient['accessToken']}` },
    }
  );
  if (!response.ok) throw new Error('Errore nel recupero del saldo crediti');
  return response.json();
}

export async function rechargeCredits(
  amount_eur: number
): Promise<CreditBalance> {
  const response = await fetch(
    `${apiClient['baseUrl']}${BASE}/credits/recharge`,
    {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${apiClient['accessToken']}`,
      },
      body: JSON.stringify({ amount_eur }),
    }
  );
  if (!response.ok) {
    const data = await response.json();
    throw new Error(data.detail || 'Errore nella ricarica crediti');
  }
  return response.json();
}

export async function enableExtraUsage(enabled: boolean): Promise<void> {
  const response = await fetch(
    `${apiClient['baseUrl']}${BASE}/credits/enable-extra-usage`,
    {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${apiClient['accessToken']}`,
      },
      body: JSON.stringify({ enabled }),
    }
  );
  if (!response.ok)
    throw new Error("Errore nell'aggiornamento delle preferenze");
}

export async function getCreditTransactions(
  limit = 50,
  offset = 0
): Promise<TransactionHistoryResponse> {
  const response = await fetch(
    `${apiClient['baseUrl']}${BASE}/credits/transactions?limit=${limit}&offset=${offset}`,
    { headers: { Authorization: `Bearer ${apiClient['accessToken']}` } }
  );
  if (!response.ok) throw new Error('Errore nel recupero delle transazioni');
  return response.json();
}

export async function getBillingPlans(): Promise<PlansListResponse> {
  const response = await fetch(`${apiClient['baseUrl']}${BASE}/plans`);
  if (!response.ok) throw new Error('Errore nel recupero dei piani');
  return response.json();
}

export async function subscribeToPlan(
  planSlug: string
): Promise<PlanSubscribedResponse> {
  const response = await fetch(
    `${apiClient['baseUrl']}${BASE}/plans/${planSlug}/subscribe`,
    {
      method: 'POST',
      headers: { Authorization: `Bearer ${apiClient['accessToken']}` },
    }
  );
  if (!response.ok) {
    const data = await response.json();
    throw new Error(data.detail || 'Errore nella sottoscrizione');
  }
  return response.json();
}

// --- Admin Simulator Functions ---

export async function simulateUsage(
  window_type: string,
  target_percentage: number
): Promise<SimulateUsageResponse> {
  const response = await fetch(
    `${apiClient['baseUrl']}${BASE}/simulate-usage`,
    {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${apiClient['accessToken']}`,
      },
      body: JSON.stringify({ window_type, target_percentage }),
    }
  );
  if (!response.ok) throw new Error("Errore nella simulazione dell'utilizzo");
  return response.json();
}

export async function resetUsage(): Promise<ResetUsageResponse> {
  const response = await fetch(`${apiClient['baseUrl']}${BASE}/reset-usage`, {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${apiClient['accessToken']}`,
    },
  });
  if (!response.ok) throw new Error("Errore nel reset dell'utilizzo");
  return response.json();
}
