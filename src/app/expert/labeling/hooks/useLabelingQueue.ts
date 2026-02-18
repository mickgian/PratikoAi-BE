'use client';

import { useState, useEffect, useCallback } from 'react';
import { getLabelingQueue } from '@/lib/api/intentLabeling';
import type { QueueItem } from '@/types/intentLabeling';

export function useLabelingQueue(pageSize: number = 20) {
  const [items, setItems] = useState<QueueItem[]>([]);
  const [page, setPage] = useState(1);
  const [totalCount, setTotalCount] = useState(0);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchQueue = useCallback(
    async (pageNum: number) => {
      try {
        setIsLoading(true);
        setError(null);
        const response = await getLabelingQueue(pageNum, pageSize);
        setItems(response.items);
        setTotalCount(response.total_count);
        setPage(response.page);
      } catch (err) {
        setError(
          err instanceof Error
            ? err.message
            : 'Errore nel caricamento della coda'
        );
      } finally {
        setIsLoading(false);
      }
    },
    [pageSize]
  );

  useEffect(() => {
    fetchQueue(page);
  }, [fetchQueue, page]);

  const removeItem = useCallback((id: string) => {
    setItems(prev => prev.filter(item => item.id !== id));
    setTotalCount(prev => Math.max(0, prev - 1));
  }, []);

  const goToPage = useCallback((pageNum: number) => {
    setPage(pageNum);
  }, []);

  const refetch = useCallback(() => {
    fetchQueue(page);
  }, [fetchQueue, page]);

  const totalPages = Math.ceil(totalCount / pageSize);

  return {
    items,
    page,
    totalCount,
    totalPages,
    isLoading,
    error,
    removeItem,
    goToPage,
    refetch,
  };
}
