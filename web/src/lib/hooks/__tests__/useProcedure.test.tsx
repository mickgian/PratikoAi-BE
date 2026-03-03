/**
 * @jest-environment jsdom
 */
import { renderHook, waitFor, act } from '@testing-library/react';

jest.mock('@/lib/api/procedure', () => ({
  listProcedure: jest.fn(),
  listProgress: jest.fn(),
  startProgress: jest.fn(),
  advanceStep: jest.fn(),
  updateChecklist: jest.fn(),
  updateNotes: jest.fn(),
  updateDocument: jest.fn(),
}));

jest.mock('@/lib/api/helpers', () => ({
  getStudioId: jest.fn().mockReturnValue('studio-123'),
  getUserId: jest.fn().mockReturnValue(42),
  getAuthHeaders: jest.fn().mockReturnValue({}),
  buildStudioUrl: jest.fn(),
}));

import {
  listProcedure,
  listProgress,
  startProgress,
  advanceStep,
  updateChecklist,
  updateNotes,
  updateDocument,
} from '@/lib/api/procedure';
import { getStudioId } from '@/lib/api/helpers';
import {
  useProcedureList,
  useProcedureProgress,
  useProcedureDetail,
} from '../useProcedure';

const mockListProcedure = listProcedure as jest.MockedFunction<
  typeof listProcedure
>;
const mockListProgress = listProgress as jest.MockedFunction<
  typeof listProgress
>;
const mockStartProgress = startProgress as jest.MockedFunction<
  typeof startProgress
>;
const mockAdvanceStep = advanceStep as jest.MockedFunction<typeof advanceStep>;
const mockUpdateChecklist = updateChecklist as jest.MockedFunction<
  typeof updateChecklist
>;
const mockUpdateNotes = updateNotes as jest.MockedFunction<typeof updateNotes>;
const mockUpdateDocument = updateDocument as jest.MockedFunction<
  typeof updateDocument
>;
const mockGetStudioId = getStudioId as jest.MockedFunction<typeof getStudioId>;

const makeProcedura = (
  overrides: Partial<{ id: string; category: string }> = {}
) => ({
  id: overrides.id ?? 'proc-1',
  code: 'PROC-001',
  title: 'Procedura di esempio',
  description: 'Descrizione della procedura',
  category: overrides.category ?? 'fiscale',
  steps: [
    {
      title: 'Passo 1',
      checklist: ['Verifica documenti', 'Controlla dati'],
      documents: ['carta_identita.pdf'],
      notes: '',
    },
  ],
  estimated_time_minutes: 30,
  version: 1,
  is_active: true,
});

const makeProgress = (
  overrides: Partial<{
    id: string;
    current_step: number;
    completed_steps: number[];
  }> = {}
) => ({
  id: overrides.id ?? 'prog-1',
  user_id: 42,
  studio_id: 'studio-123',
  procedura_id: 'proc-1',
  client_id: 1,
  current_step: overrides.current_step ?? 0,
  completed_steps: overrides.completed_steps ?? [],
  notes: null,
  started_at: '2025-01-01T00:00:00Z',
  completed_at: null,
});

// ---------- useProcedureList ----------

describe('useProcedureList', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('fetches procedure list on mount', async () => {
    const procedures = [
      makeProcedura({ id: 'p1' }),
      makeProcedura({ id: 'p2' }),
    ];
    mockListProcedure.mockResolvedValueOnce(procedures);

    const { result } = renderHook(() => useProcedureList());

    expect(result.current.isLoading).toBe(true);

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.procedures).toEqual(procedures);
    expect(result.current.error).toBeNull();
    expect(mockListProcedure).toHaveBeenCalledWith(undefined);
  });

  it('passes category filter', async () => {
    mockListProcedure.mockResolvedValueOnce([]);

    renderHook(() => useProcedureList('fiscale'));

    await waitFor(() => {
      expect(mockListProcedure).toHaveBeenCalledWith('fiscale');
    });
  });

  it('sets error on API failure', async () => {
    mockListProcedure.mockRejectedValueOnce(
      new Error('Errore nel recupero delle procedure')
    );

    const { result } = renderHook(() => useProcedureList());

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.procedures).toEqual([]);
    expect(result.current.error).toBe('Errore nel recupero delle procedure');
  });

  it('handles non-Error exceptions with fallback message', async () => {
    mockListProcedure.mockRejectedValueOnce(404);

    const { result } = renderHook(() => useProcedureList());

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.error).toBe('Errore');
  });

  it('refetches when category changes', async () => {
    mockListProcedure.mockResolvedValueOnce([
      makeProcedura({ category: 'fiscale' }),
    ]);

    const { result, rerender } = renderHook(
      ({ category }: { category?: string }) => useProcedureList(category),
      { initialProps: { category: 'fiscale' } }
    );

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    mockListProcedure.mockResolvedValueOnce([
      makeProcedura({ category: 'lavoro' }),
    ]);

    rerender({ category: 'lavoro' });

    await waitFor(() => {
      expect(mockListProcedure).toHaveBeenCalledWith('lavoro');
    });
  });
});

// ---------- useProcedureProgress ----------

describe('useProcedureProgress', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockGetStudioId.mockReturnValue('studio-123');
  });

  it('fetches progress list on mount', async () => {
    const progressList = [makeProgress({ id: 'pg1' })];
    mockListProgress.mockResolvedValueOnce(progressList);

    const { result } = renderHook(() => useProcedureProgress());

    expect(result.current.isLoading).toBe(true);

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.progressList).toEqual(progressList);
    expect(result.current.error).toBeNull();
  });

  it('sets error on API failure', async () => {
    mockListProgress.mockRejectedValueOnce(
      new Error('Errore nel caricamento dei progressi')
    );

    const { result } = renderHook(() => useProcedureProgress());

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.error).toBe('Errore nel caricamento dei progressi');
  });

  it('handles non-Error exceptions with fallback message', async () => {
    mockListProgress.mockRejectedValueOnce(undefined);

    const { result } = renderHook(() => useProcedureProgress());

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.error).toBe('Errore');
  });

  it('skips fetch when studio is not configured', async () => {
    mockGetStudioId.mockReturnValue(null);

    const { result } = renderHook(() => useProcedureProgress());

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(mockListProgress).not.toHaveBeenCalled();
    expect(result.current.progressList).toEqual([]);
  });

  it('startProgress creates progress and appends to list', async () => {
    mockListProgress.mockResolvedValueOnce([]);
    const newProgress = makeProgress({ id: 'pg-new' });
    mockStartProgress.mockResolvedValueOnce(newProgress);

    const { result } = renderHook(() => useProcedureProgress());

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    let started: unknown;
    await act(async () => {
      started = await result.current.startProgress('proc-1', 1);
    });

    expect(mockStartProgress).toHaveBeenCalledWith('proc-1', 1);
    expect(started).toEqual(newProgress);
    expect(result.current.progressList).toEqual([newProgress]);
  });

  it('startProgress works without clientId', async () => {
    mockListProgress.mockResolvedValueOnce([]);
    const newProgress = makeProgress({ id: 'pg-new' });
    mockStartProgress.mockResolvedValueOnce(newProgress);

    const { result } = renderHook(() => useProcedureProgress());

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    await act(async () => {
      await result.current.startProgress('proc-1');
    });

    expect(mockStartProgress).toHaveBeenCalledWith('proc-1', undefined);
  });

  it('advanceStep updates progress in list', async () => {
    const existing = makeProgress({ id: 'pg-1', current_step: 0 });
    mockListProgress.mockResolvedValueOnce([existing]);

    const advanced = makeProgress({
      id: 'pg-1',
      current_step: 1,
      completed_steps: [0],
    });
    mockAdvanceStep.mockResolvedValueOnce(advanced);

    const { result } = renderHook(() => useProcedureProgress());

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    let stepped: unknown;
    await act(async () => {
      stepped = await result.current.advanceStep('pg-1');
    });

    expect(mockAdvanceStep).toHaveBeenCalledWith('pg-1');
    expect(stepped).toEqual(advanced);
    expect(result.current.progressList[0].current_step).toBe(1);
    expect(result.current.progressList[0].completed_steps).toEqual([0]);
  });

  it('supports refresh', async () => {
    mockListProgress.mockResolvedValueOnce([makeProgress({ id: 'pg-1' })]);

    const { result } = renderHook(() => useProcedureProgress());

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.progressList).toHaveLength(1);

    const updated = [
      makeProgress({ id: 'pg-1' }),
      makeProgress({ id: 'pg-2' }),
    ];
    mockListProgress.mockResolvedValueOnce(updated);

    await act(async () => {
      await result.current.refresh();
    });

    expect(result.current.progressList).toHaveLength(2);
  });
});

// ---------- useProcedureDetail ----------

describe('useProcedureDetail', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('updateChecklist calls API with correct params', async () => {
    const updatedProgress = makeProgress({ id: 'pg-1' });
    mockUpdateChecklist.mockResolvedValueOnce(updatedProgress);

    const { result } = renderHook(() => useProcedureDetail('pg-1'));

    let response: unknown;
    await act(async () => {
      response = await result.current.updateChecklist(0, 1, true);
    });

    expect(mockUpdateChecklist).toHaveBeenCalledWith('pg-1', 0, 1, true);
    expect(response).toEqual(updatedProgress);
  });

  it('updateChecklist does nothing when progressId is null', async () => {
    const { result } = renderHook(() => useProcedureDetail(null));

    await act(async () => {
      const response = await result.current.updateChecklist(0, 0, true);
      expect(response).toBeUndefined();
    });

    expect(mockUpdateChecklist).not.toHaveBeenCalled();
  });

  it('updateNotes calls API with correct params', async () => {
    const updatedProgress = makeProgress({ id: 'pg-1' });
    mockUpdateNotes.mockResolvedValueOnce(updatedProgress);

    const { result } = renderHook(() => useProcedureDetail('pg-1'));

    let response: unknown;
    await act(async () => {
      response = await result.current.updateNotes('Nota aggiornata');
    });

    expect(mockUpdateNotes).toHaveBeenCalledWith('pg-1', 'Nota aggiornata');
    expect(response).toEqual(updatedProgress);
  });

  it('updateNotes does nothing when progressId is null', async () => {
    const { result } = renderHook(() => useProcedureDetail(null));

    await act(async () => {
      const response = await result.current.updateNotes('Nota');
      expect(response).toBeUndefined();
    });

    expect(mockUpdateNotes).not.toHaveBeenCalled();
  });

  it('updateDocument calls API with correct params', async () => {
    const updatedProgress = makeProgress({ id: 'pg-1' });
    mockUpdateDocument.mockResolvedValueOnce(updatedProgress);

    const { result } = renderHook(() => useProcedureDetail('pg-1'));

    let response: unknown;
    await act(async () => {
      response = await result.current.updateDocument(
        'carta_identita.pdf',
        true
      );
    });

    expect(mockUpdateDocument).toHaveBeenCalledWith(
      'pg-1',
      'carta_identita.pdf',
      true
    );
    expect(response).toEqual(updatedProgress);
  });

  it('updateDocument does nothing when progressId is null', async () => {
    const { result } = renderHook(() => useProcedureDetail(null));

    await act(async () => {
      const response = await result.current.updateDocument('doc.pdf', false);
      expect(response).toBeUndefined();
    });

    expect(mockUpdateDocument).not.toHaveBeenCalled();
  });

  it('updates progressId reactively', async () => {
    mockUpdateChecklist.mockResolvedValue(makeProgress());

    const { result, rerender } = renderHook(
      ({ progressId }: { progressId: string | null }) =>
        useProcedureDetail(progressId),
      { initialProps: { progressId: null as string | null } }
    );

    await act(async () => {
      await result.current.updateChecklist(0, 0, true);
    });
    expect(mockUpdateChecklist).not.toHaveBeenCalled();

    rerender({ progressId: 'pg-1' });

    await act(async () => {
      await result.current.updateChecklist(0, 0, true);
    });
    expect(mockUpdateChecklist).toHaveBeenCalledWith('pg-1', 0, 0, true);
  });
});
