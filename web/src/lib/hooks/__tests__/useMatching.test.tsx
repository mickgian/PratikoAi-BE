/**
 * @jest-environment jsdom
 */
import { renderHook, waitFor, act } from '@testing-library/react';

jest.mock('@/lib/api/matching', () => ({
  listSuggestions: jest.fn(),
  markAsRead: jest.fn(),
  dismissSuggestion: jest.fn(),
}));

jest.mock('@/lib/api/helpers', () => ({
  getStudioId: jest.fn().mockReturnValue('studio-123'),
  getUserId: jest.fn().mockReturnValue(42),
  getAuthHeaders: jest.fn().mockReturnValue({}),
  buildStudioUrl: jest.fn(),
}));

import {
  listSuggestions,
  markAsRead,
  dismissSuggestion,
} from '@/lib/api/matching';
import { getStudioId } from '@/lib/api/helpers';
import { useMatching } from '../useMatching';

const mockListSuggestions = listSuggestions as jest.MockedFunction<
  typeof listSuggestions
>;
const mockMarkAsRead = markAsRead as jest.MockedFunction<typeof markAsRead>;
const mockDismissSuggestion = dismissSuggestion as jest.MockedFunction<
  typeof dismissSuggestion
>;
const mockGetStudioId = getStudioId as jest.MockedFunction<typeof getStudioId>;

const makeSuggestion = (
  overrides: Partial<{
    id: string;
    is_read: boolean;
    is_dismissed: boolean;
  }> = {}
) => ({
  id: overrides.id ?? 'sug-1',
  studio_id: 'studio-123',
  knowledge_item_id: 10,
  matched_client_ids: [1, 2],
  match_score: 0.85,
  suggestion_text: 'Nuova normativa applicabile',
  is_read: overrides.is_read ?? false,
  is_dismissed: overrides.is_dismissed ?? false,
  created_at: '2025-01-01T00:00:00Z',
});

describe('useMatching', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockGetStudioId.mockReturnValue('studio-123');
  });

  it('fetches suggestions on mount', async () => {
    const suggestions = [
      makeSuggestion({ id: 's1' }),
      makeSuggestion({ id: 's2' }),
    ];
    mockListSuggestions.mockResolvedValueOnce(suggestions);

    const { result } = renderHook(() => useMatching());

    expect(result.current.isLoading).toBe(true);

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.suggestions).toEqual(suggestions);
    expect(result.current.error).toBeNull();
  });

  it('sets error on API failure', async () => {
    mockListSuggestions.mockRejectedValueOnce(
      new Error('Errore nel caricamento dei suggerimenti')
    );

    const { result } = renderHook(() => useMatching());

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.suggestions).toEqual([]);
    expect(result.current.error).toBe(
      'Errore nel caricamento dei suggerimenti'
    );
  });

  it('handles non-Error exceptions with fallback message', async () => {
    mockListSuggestions.mockRejectedValueOnce(null);

    const { result } = renderHook(() => useMatching());

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.error).toBe('Errore nel caricamento');
  });

  it('sets error when studio is not configured', async () => {
    mockGetStudioId.mockReturnValue(null);

    const { result } = renderHook(() => useMatching());

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.error).toBe('Studio non configurato');
    expect(mockListSuggestions).not.toHaveBeenCalled();
  });

  it('markAsRead updates suggestions locally', async () => {
    const suggestions = [
      makeSuggestion({ id: 's1', is_read: false }),
      makeSuggestion({ id: 's2', is_read: false }),
    ];
    mockListSuggestions.mockResolvedValueOnce(suggestions);
    mockMarkAsRead.mockResolvedValue(
      makeSuggestion({ id: 's1', is_read: true })
    );

    const { result } = renderHook(() => useMatching());

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    await act(async () => {
      await result.current.markAsRead(['s1']);
    });

    expect(mockMarkAsRead).toHaveBeenCalledWith('s1');
    expect(result.current.suggestions[0].is_read).toBe(true);
    expect(result.current.suggestions[1].is_read).toBe(false);
  });

  it('markAsRead handles multiple IDs', async () => {
    const suggestions = [
      makeSuggestion({ id: 's1', is_read: false }),
      makeSuggestion({ id: 's2', is_read: false }),
      makeSuggestion({ id: 's3', is_read: false }),
    ];
    mockListSuggestions.mockResolvedValueOnce(suggestions);
    mockMarkAsRead.mockResolvedValue(makeSuggestion());

    const { result } = renderHook(() => useMatching());

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    await act(async () => {
      await result.current.markAsRead(['s1', 's3']);
    });

    expect(mockMarkAsRead).toHaveBeenCalledTimes(2);
    expect(mockMarkAsRead).toHaveBeenCalledWith('s1');
    expect(mockMarkAsRead).toHaveBeenCalledWith('s3');
    expect(result.current.suggestions[0].is_read).toBe(true);
    expect(result.current.suggestions[1].is_read).toBe(false);
    expect(result.current.suggestions[2].is_read).toBe(true);
  });

  it('dismiss updates suggestions locally', async () => {
    const suggestions = [
      makeSuggestion({ id: 's1', is_dismissed: false }),
      makeSuggestion({ id: 's2', is_dismissed: false }),
    ];
    mockListSuggestions.mockResolvedValueOnce(suggestions);
    mockDismissSuggestion.mockResolvedValue(
      makeSuggestion({ id: 's2', is_dismissed: true })
    );

    const { result } = renderHook(() => useMatching());

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    await act(async () => {
      await result.current.dismiss(['s2']);
    });

    expect(mockDismissSuggestion).toHaveBeenCalledWith('s2');
    expect(result.current.suggestions[0].is_dismissed).toBe(false);
    expect(result.current.suggestions[1].is_dismissed).toBe(true);
  });

  it('dismiss handles multiple IDs', async () => {
    const suggestions = [
      makeSuggestion({ id: 's1' }),
      makeSuggestion({ id: 's2' }),
    ];
    mockListSuggestions.mockResolvedValueOnce(suggestions);
    mockDismissSuggestion.mockResolvedValue(makeSuggestion());

    const { result } = renderHook(() => useMatching());

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    await act(async () => {
      await result.current.dismiss(['s1', 's2']);
    });

    expect(mockDismissSuggestion).toHaveBeenCalledTimes(2);
    expect(result.current.suggestions[0].is_dismissed).toBe(true);
    expect(result.current.suggestions[1].is_dismissed).toBe(true);
  });

  it('supports refresh', async () => {
    mockListSuggestions.mockResolvedValueOnce([makeSuggestion({ id: 's1' })]);

    const { result } = renderHook(() => useMatching());

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.suggestions).toHaveLength(1);

    const newSuggestions = [
      makeSuggestion({ id: 's1' }),
      makeSuggestion({ id: 's2' }),
    ];
    mockListSuggestions.mockResolvedValueOnce(newSuggestions);

    await act(async () => {
      await result.current.refresh();
    });

    expect(result.current.suggestions).toHaveLength(2);
  });

  it('starts with empty suggestions', () => {
    mockListSuggestions.mockReturnValue(new Promise(() => {}));

    const { result } = renderHook(() => useMatching());

    expect(result.current.suggestions).toEqual([]);
    expect(result.current.isLoading).toBe(true);
  });
});
