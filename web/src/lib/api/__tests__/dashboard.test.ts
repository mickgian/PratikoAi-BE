/**
 * @jest-environment jsdom
 */
import { getDashboardData } from '../dashboard';

// Mock fetch
const mockFetch = jest.fn();
global.fetch = mockFetch;

// Mock helpers
jest.mock('@/lib/api/helpers', () => ({
  getStudioId: jest.fn().mockReturnValue('studio-123'),
  getUserId: jest.fn().mockReturnValue(42),
  getAuthHeaders: jest.fn().mockReturnValue({
    Authorization: 'Bearer test-token',
    'X-Studio-Id': 'studio-123',
    'Content-Type': 'application/json',
  }),
  buildStudioUrl: jest.fn().mockImplementation((path, params) => {
    const url = new URL(`http://localhost:8000${path}`);
    url.searchParams.set('studio_id', 'studio-123');
    if (params)
      Object.entries(params).forEach(([k, v]) => {
        if (v !== undefined) url.searchParams.set(k, String(v));
      });
    return url.toString();
  }),
}));

// --- Fixtures ---

const mockDashboard = {
  clients: { total: 150 },
  communications: { total: 45, pending_review: 5 },
  procedures: { total: 20, active: 12 },
  matches: { active_rules: 8 },
  roi: { hours_saved: 120, breakdown: {} },
  distributions: {
    by_regime: [{ regime: 'ordinario', count: 80 }],
    by_ateco: [{ ateco: '69.20.11', count: 50 }],
    by_status: [{ status: 'attivo', count: 130 }],
  },
  matching: {
    total_matches: 35,
    conversion_rate: 0.72,
    pending_reviews: 3,
  },
  period: 'month',
};

describe('dashboard API', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  // ---------------------------------------------------------------
  // getDashboardData
  // ---------------------------------------------------------------
  describe('getDashboardData', () => {
    it('should fetch dashboard data with default period (month)', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockDashboard,
      });

      const result = await getDashboardData();

      expect(result).toEqual(mockDashboard);
      const { buildStudioUrl } = require('@/lib/api/helpers');
      expect(buildStudioUrl).toHaveBeenCalledWith('/api/v1/dashboard', {
        period: 'month',
      });
    });

    it('should fetch dashboard data with week period', async () => {
      const weekDashboard = { ...mockDashboard, period: 'week' };
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => weekDashboard,
      });

      const result = await getDashboardData('week');

      expect(result.period).toBe('week');
      const { buildStudioUrl } = require('@/lib/api/helpers');
      expect(buildStudioUrl).toHaveBeenCalledWith('/api/v1/dashboard', {
        period: 'week',
      });
    });

    it('should fetch dashboard data with year period', async () => {
      const yearDashboard = { ...mockDashboard, period: 'year' };
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => yearDashboard,
      });

      const result = await getDashboardData('year');

      expect(result.period).toBe('year');
      const { buildStudioUrl } = require('@/lib/api/helpers');
      expect(buildStudioUrl).toHaveBeenCalledWith('/api/v1/dashboard', {
        period: 'year',
      });
    });

    it('should use correct auth headers', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockDashboard,
      });

      await getDashboardData();

      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/v1/dashboard'),
        expect.objectContaining({
          headers: expect.objectContaining({
            Authorization: 'Bearer test-token',
            'X-Studio-Id': 'studio-123',
          }),
        })
      );
    });

    it('should throw on error response', async () => {
      mockFetch.mockResolvedValueOnce({ ok: false, status: 500 });

      await expect(getDashboardData()).rejects.toThrow(
        'Errore nel caricamento della dashboard'
      );
    });

    it('should throw on error response for specific period', async () => {
      mockFetch.mockResolvedValueOnce({ ok: false, status: 403 });

      await expect(getDashboardData('year')).rejects.toThrow(
        'Errore nel caricamento della dashboard'
      );
    });
  });
});
