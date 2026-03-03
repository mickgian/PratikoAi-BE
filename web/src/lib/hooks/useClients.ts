/**
 * Hooks for client data management.
 */

'use client';

import { useCallback, useEffect, useState } from 'react';
import {
  ClientListParams,
  ClientListResponse,
  ClientResponse,
  ClientUpdateRequest,
  createClient as apiCreateClient,
  deleteClient as apiDeleteClient,
  getClient as apiGetClient,
  listClients as apiListClients,
  updateClient as apiUpdateClient,
  ClientCreateRequest,
} from '@/lib/api/clients';
import { getStudioId } from '@/lib/api/helpers';

export function useClients(params?: ClientListParams) {
  const [data, setData] = useState<ClientListResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetch = useCallback(async () => {
    if (!getStudioId()) {
      setError('Studio non configurato');
      setIsLoading(false);
      return;
    }
    setIsLoading(true);
    setError(null);
    try {
      const result = await apiListClients(params);
      setData(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Errore nel caricamento');
    } finally {
      setIsLoading(false);
    }
  }, [params?.offset, params?.limit, params?.stato, params?.search]);

  useEffect(() => {
    fetch();
  }, [fetch]);

  return {
    clients: data?.items ?? [],
    total: data?.total ?? 0,
    isLoading,
    error,
    refresh: fetch,
  };
}

export function useClient(clientId: string | number | null) {
  const [client, setClient] = useState<ClientResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!clientId || clientId === 'new') {
      setIsLoading(false);
      return;
    }
    const id = typeof clientId === 'string' ? parseInt(clientId, 10) : clientId;
    if (isNaN(id)) {
      setIsLoading(false);
      return;
    }

    setIsLoading(true);
    setError(null);
    apiGetClient(id)
      .then(setClient)
      .catch(err => setError(err instanceof Error ? err.message : 'Errore'))
      .finally(() => setIsLoading(false));
  }, [clientId]);

  const save = useCallback(
    async (data: ClientUpdateRequest | ClientCreateRequest) => {
      if (!clientId || clientId === 'new') {
        return apiCreateClient(data as ClientCreateRequest);
      }
      const id =
        typeof clientId === 'string' ? parseInt(clientId, 10) : clientId;
      const updated = await apiUpdateClient(id, data);
      setClient(updated);
      return updated;
    },
    [clientId]
  );

  const remove = useCallback(async () => {
    if (!clientId || clientId === 'new') return;
    const id = typeof clientId === 'string' ? parseInt(clientId, 10) : clientId;
    await apiDeleteClient(id);
  }, [clientId]);

  return { client, isLoading, error, save, remove };
}
