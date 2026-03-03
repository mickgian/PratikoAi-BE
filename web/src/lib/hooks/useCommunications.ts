/**
 * Hooks for communication management.
 */

'use client';

import { useCallback, useEffect, useState } from 'react';
import {
  CommunicationResponse,
  CommunicationCreateRequest,
  approveCommunication,
  createCommunication,
  deleteCommunication,
  listCommunications,
  rejectCommunication,
  sendCommunication,
  submitForReview,
} from '@/lib/api/communications';
import { ClientResponse, listClients } from '@/lib/api/clients';
import { getStudioId } from '@/lib/api/helpers';
import { communicationStatusToItalian } from '@/lib/api/transformers';

export function useCommunications(statusFilter?: string) {
  const [communications, setCommunications] = useState<CommunicationResponse[]>(
    []
  );
  const [clientMap, setClientMap] = useState<Map<number, string>>(new Map());
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
      const [commsResult, clientsResult] = await Promise.all([
        listCommunications({
          status: statusFilter,
        }),
        listClients({ limit: 200 }),
      ]);
      setCommunications(commsResult);

      const map = new Map<number, string>();
      clientsResult.items.forEach((c: ClientResponse) => map.set(c.id, c.nome));
      setClientMap(map);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Errore nel caricamento');
    } finally {
      setIsLoading(false);
    }
  }, [statusFilter]);

  useEffect(() => {
    fetch();
  }, [fetch]);

  const getClientName = useCallback(
    (clientId: number | null) => {
      if (!clientId) return 'N/A';
      return clientMap.get(clientId) ?? `Cliente #${clientId}`;
    },
    [clientMap]
  );

  const getItalianStatus = useCallback((status: string) => {
    return communicationStatusToItalian[status] ?? status;
  }, []);

  const stats = {
    bozze: communications.filter(c => c.status === 'DRAFT').length,
    in_revisione: communications.filter(c => c.status === 'PENDING_REVIEW')
      .length,
    approvate: communications.filter(c => c.status === 'APPROVED').length,
    inviate: communications.filter(c => c.status === 'SENT').length,
  };

  /** Client list as {id, name} for use in editor dropdowns. */
  const clients = Array.from(clientMap.entries()).map(([id, name]) => ({
    id,
    name,
  }));

  return {
    communications,
    clients,
    stats,
    isLoading,
    error,
    refresh: fetch,
    getClientName,
    getItalianStatus,
  };
}

export function useCommunicationActions(onRefresh: () => void) {
  const create = useCallback(
    async (data: CommunicationCreateRequest) => {
      const result = await createCommunication(data);
      onRefresh();
      return result;
    },
    [onRefresh]
  );

  const submit = useCallback(
    async (id: string) => {
      const result = await submitForReview(id);
      onRefresh();
      return result;
    },
    [onRefresh]
  );

  const approve = useCallback(
    async (id: string) => {
      const result = await approveCommunication(id);
      onRefresh();
      return result;
    },
    [onRefresh]
  );

  const reject = useCallback(
    async (id: string) => {
      const result = await rejectCommunication(id);
      onRefresh();
      return result;
    },
    [onRefresh]
  );

  const send = useCallback(
    async (id: string) => {
      const result = await sendCommunication(id);
      onRefresh();
      return result;
    },
    [onRefresh]
  );

  const remove = useCallback(
    async (id: string) => {
      await deleteCommunication(id);
      onRefresh();
    },
    [onRefresh]
  );

  return { create, submit, approve, reject, send, remove };
}
