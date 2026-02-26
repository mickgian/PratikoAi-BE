import {
  getVersion,
  getReleaseNotes,
  getLatestReleaseNote,
  getUnseenReleaseNote,
  getReleaseNotesFull,
  updateUserNotes,
  markReleaseNoteSeen,
} from '../release-notes';

const mockFetch = jest.fn();
global.fetch = mockFetch;

const localStorageMock = {
  getItem: jest.fn(),
  setItem: jest.fn(),
  clear: jest.fn(),
  removeItem: jest.fn(),
  length: 0,
  key: jest.fn(),
};
Object.defineProperty(window, 'localStorage', { value: localStorageMock });

describe('release-notes API', () => {
  const mockToken = 'test-token-123';

  beforeEach(() => {
    jest.clearAllMocks();
    localStorageMock.getItem.mockReturnValue(mockToken);
  });

  describe('getVersion', () => {
    it('returns version info on success', async () => {
      const data = { version: '1.2.0', environment: 'production' };
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(data),
      });

      const result = await getVersion();
      expect(result).toEqual(data);
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/v1/release-notes/version')
      );
    });

    it('throws on failure', async () => {
      mockFetch.mockResolvedValueOnce({ ok: false });
      await expect(getVersion()).rejects.toThrow(
        'Errore nel recupero della versione'
      );
    });
  });

  describe('getReleaseNotes', () => {
    it('returns paginated release notes', async () => {
      const data = { items: [], total: 0, page: 1, page_size: 10 };
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(data),
      });

      const result = await getReleaseNotes(1, 10);
      expect(result).toEqual(data);
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('page=1&page_size=10')
      );
    });

    it('uses default parameters', async () => {
      const data = { items: [], total: 0, page: 1, page_size: 10 };
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(data),
      });

      await getReleaseNotes();
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('page=1&page_size=10')
      );
    });

    it('throws on failure', async () => {
      mockFetch.mockResolvedValueOnce({ ok: false });
      await expect(getReleaseNotes()).rejects.toThrow(
        'Errore nel recupero delle note di rilascio'
      );
    });
  });

  describe('getLatestReleaseNote', () => {
    it('returns latest release note', async () => {
      const note = {
        version: '1.0.0',
        released_at: '2026-01-01',
        user_notes: 'test',
      };
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(note),
      });

      const result = await getLatestReleaseNote();
      expect(result).toEqual(note);
    });

    it('returns null when no data', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(null),
      });

      const result = await getLatestReleaseNote();
      expect(result).toBeNull();
    });

    it('throws on failure', async () => {
      mockFetch.mockResolvedValueOnce({ ok: false });
      await expect(getLatestReleaseNote()).rejects.toThrow(
        "Errore nel recupero dell'ultima nota di rilascio"
      );
    });
  });

  describe('getUnseenReleaseNote', () => {
    it('returns unseen note with auth', async () => {
      const note = {
        version: '1.0.0',
        released_at: null,
        user_notes: 'new',
        technical_notes: 'tech',
      };
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(note),
      });

      const result = await getUnseenReleaseNote();
      expect(result).toEqual(note);
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/unseen'),
        expect.objectContaining({
          headers: { Authorization: `Bearer ${mockToken}` },
        })
      );
    });

    it('returns null when no token', async () => {
      localStorageMock.getItem.mockReturnValue(null);
      const result = await getUnseenReleaseNote();
      expect(result).toBeNull();
      expect(mockFetch).not.toHaveBeenCalled();
    });

    it('returns null on 401', async () => {
      mockFetch.mockResolvedValueOnce({ ok: false, status: 401 });
      const result = await getUnseenReleaseNote();
      expect(result).toBeNull();
    });

    it('throws on non-401 failure', async () => {
      mockFetch.mockResolvedValueOnce({ ok: false, status: 500 });
      await expect(getUnseenReleaseNote()).rejects.toThrow(
        'Errore nel recupero delle novità'
      );
    });

    it('returns null when response is empty', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(null),
      });
      const result = await getUnseenReleaseNote();
      expect(result).toBeNull();
    });
  });

  describe('getReleaseNotesFull', () => {
    it('returns full release notes with auth', async () => {
      const data = { items: [], total: 0, page: 1, page_size: 10 };
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(data),
      });

      const result = await getReleaseNotesFull();
      expect(result).toEqual(data);
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/full?page=1&page_size=10'),
        expect.objectContaining({
          headers: { Authorization: `Bearer ${mockToken}` },
        })
      );
    });

    it('throws when no token', async () => {
      localStorageMock.getItem.mockReturnValue(null);
      await expect(getReleaseNotesFull()).rejects.toThrow('Non autenticato');
    });

    it('throws on failure', async () => {
      mockFetch.mockResolvedValueOnce({ ok: false });
      await expect(getReleaseNotesFull()).rejects.toThrow(
        'Errore nel recupero delle note di rilascio complete'
      );
    });
  });

  describe('updateUserNotes', () => {
    it('sends PATCH with user notes', async () => {
      const response = { success: true, message_it: 'Aggiornato' };
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(response),
      });

      const result = await updateUserNotes('1.0.0', 'My notes');
      expect(result).toEqual(response);
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/1.0.0/user-notes'),
        expect.objectContaining({
          method: 'PATCH',
          headers: expect.objectContaining({
            'Content-Type': 'application/json',
          }),
          body: JSON.stringify({ user_notes: 'My notes' }),
        })
      );
    });

    it('throws when no token', async () => {
      localStorageMock.getItem.mockReturnValue(null);
      await expect(updateUserNotes('1.0.0', 'notes')).rejects.toThrow(
        'Non autenticato'
      );
    });

    it('throws on failure', async () => {
      mockFetch.mockResolvedValueOnce({ ok: false });
      await expect(updateUserNotes('1.0.0', 'notes')).rejects.toThrow(
        "Errore nell'aggiornamento delle note utente"
      );
    });
  });

  describe('markReleaseNoteSeen', () => {
    it('sends POST to mark seen', async () => {
      const response = { success: true, message_it: 'Visto' };
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(response),
      });

      const result = await markReleaseNoteSeen('1.0.0');
      expect(result).toEqual(response);
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/1.0.0/seen'),
        expect.objectContaining({
          method: 'POST',
          headers: expect.objectContaining({
            Authorization: `Bearer ${mockToken}`,
          }),
        })
      );
    });

    it('throws when no token', async () => {
      localStorageMock.getItem.mockReturnValue(null);
      await expect(markReleaseNoteSeen('1.0.0')).rejects.toThrow(
        'Non autenticato'
      );
    });

    it('throws on failure', async () => {
      mockFetch.mockResolvedValueOnce({ ok: false });
      await expect(markReleaseNoteSeen('1.0.0')).rejects.toThrow(
        'Errore nel segnare come visto'
      );
    });
  });
});
