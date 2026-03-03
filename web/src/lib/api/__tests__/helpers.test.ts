/**
 * @jest-environment jsdom
 */
import {
  getStudioId,
  getUserId,
  getAuthHeaders,
  buildStudioUrl,
} from '../helpers';

// Mock apiClient
jest.mock('@/lib/api', () => ({
  apiClient: {
    getAccessToken: jest.fn(),
  },
}));

import { apiClient } from '@/lib/api';

// Mock localStorage
const mockLocalStorage = {
  getItem: jest.fn(),
  setItem: jest.fn(),
  removeItem: jest.fn(),
  clear: jest.fn(),
};
Object.defineProperty(window, 'localStorage', { value: mockLocalStorage });

describe('helpers API utilities', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  // ----------------------------------------------------------------
  // getStudioId
  // ----------------------------------------------------------------
  describe('getStudioId', () => {
    it('restituisce il valore da localStorage quando presente', () => {
      mockLocalStorage.getItem.mockReturnValue('studio-abc-123');

      const result = getStudioId();

      expect(result).toBe('studio-abc-123');
      expect(mockLocalStorage.getItem).toHaveBeenCalledWith('studio_id');
    });

    it('restituisce null quando localStorage non ha studio_id', () => {
      mockLocalStorage.getItem.mockReturnValue(null);

      const result = getStudioId();

      expect(result).toBeNull();
      expect(mockLocalStorage.getItem).toHaveBeenCalledWith('studio_id');
    });
  });

  // ----------------------------------------------------------------
  // getUserId
  // ----------------------------------------------------------------
  describe('getUserId', () => {
    it('restituisce il valore numerico da localStorage', () => {
      mockLocalStorage.getItem.mockReturnValue('42');

      const result = getUserId();

      expect(result).toBe(42);
      expect(mockLocalStorage.getItem).toHaveBeenCalledWith('user_id');
    });

    it('restituisce null quando localStorage non ha user_id', () => {
      mockLocalStorage.getItem.mockReturnValue(null);

      const result = getUserId();

      expect(result).toBeNull();
    });

    it('restituisce NaN per valori non numerici', () => {
      mockLocalStorage.getItem.mockReturnValue('non-un-numero');

      const result = getUserId();

      expect(result).toBeNaN();
    });

    it('gestisce stringhe vuote restituendo null', () => {
      mockLocalStorage.getItem.mockReturnValue('');

      const result = getUserId();

      // Empty string is falsy, so the ternary returns null
      expect(result).toBeNull();
    });
  });

  // ----------------------------------------------------------------
  // getAuthHeaders
  // ----------------------------------------------------------------
  describe('getAuthHeaders', () => {
    it('include Content-Type, Authorization e X-Studio-Id quando presenti', () => {
      (apiClient.getAccessToken as jest.Mock).mockReturnValue(
        'access-token-xyz'
      );
      mockLocalStorage.getItem.mockImplementation((key: string) => {
        if (key === 'studio_id') return 'studio-99';
        return null;
      });

      const headers = getAuthHeaders();

      expect(headers).toEqual({
        'Content-Type': 'application/json',
        Authorization: 'Bearer access-token-xyz',
        'X-Studio-Id': 'studio-99',
      });
    });

    it('include solo Content-Type quando non ci sono token e studio_id', () => {
      (apiClient.getAccessToken as jest.Mock).mockReturnValue(null);
      mockLocalStorage.getItem.mockReturnValue(null);

      const headers = getAuthHeaders();

      expect(headers).toEqual({
        'Content-Type': 'application/json',
      });
      expect(headers).not.toHaveProperty('Authorization');
      expect(headers).not.toHaveProperty('X-Studio-Id');
    });

    it('include Authorization senza X-Studio-Id quando studio_id manca', () => {
      (apiClient.getAccessToken as jest.Mock).mockReturnValue('my-token');
      mockLocalStorage.getItem.mockReturnValue(null);

      const headers = getAuthHeaders();

      expect(headers).toEqual({
        'Content-Type': 'application/json',
        Authorization: 'Bearer my-token',
      });
      expect(headers).not.toHaveProperty('X-Studio-Id');
    });

    it('include X-Studio-Id senza Authorization quando token manca', () => {
      (apiClient.getAccessToken as jest.Mock).mockReturnValue(null);
      mockLocalStorage.getItem.mockImplementation((key: string) => {
        if (key === 'studio_id') return 'studio-abc';
        return null;
      });

      const headers = getAuthHeaders();

      expect(headers).toEqual({
        'Content-Type': 'application/json',
        'X-Studio-Id': 'studio-abc',
      });
      expect(headers).not.toHaveProperty('Authorization');
    });
  });

  // ----------------------------------------------------------------
  // buildStudioUrl
  // ----------------------------------------------------------------
  describe('buildStudioUrl', () => {
    it('costruisce URL con il percorso base', () => {
      mockLocalStorage.getItem.mockReturnValue(null);

      const url = buildStudioUrl('/api/v1/clients');

      expect(url).toBe('http://localhost:8000/api/v1/clients');
    });

    it('aggiunge studio_id come parametro query quando presente', () => {
      mockLocalStorage.getItem.mockImplementation((key: string) => {
        if (key === 'studio_id') return 'studio-55';
        return null;
      });

      const url = buildStudioUrl('/api/v1/clients');

      expect(url).toBe(
        'http://localhost:8000/api/v1/clients?studio_id=studio-55'
      );
    });

    it('aggiunge parametri extra alla query string', () => {
      mockLocalStorage.getItem.mockReturnValue(null);

      const url = buildStudioUrl('/api/v1/clients', {
        page: 1,
        page_size: 20,
        active: true,
      });

      const parsed = new URL(url);
      expect(parsed.searchParams.get('page')).toBe('1');
      expect(parsed.searchParams.get('page_size')).toBe('20');
      expect(parsed.searchParams.get('active')).toBe('true');
    });

    it('combina studio_id e parametri extra', () => {
      mockLocalStorage.getItem.mockImplementation((key: string) => {
        if (key === 'studio_id') return 'studio-77';
        return null;
      });

      const url = buildStudioUrl('/api/v1/search', { q: 'test' });

      const parsed = new URL(url);
      expect(parsed.searchParams.get('studio_id')).toBe('studio-77');
      expect(parsed.searchParams.get('q')).toBe('test');
    });

    it('filtra parametri con valore undefined', () => {
      mockLocalStorage.getItem.mockReturnValue(null);

      const url = buildStudioUrl('/api/v1/items', {
        name: 'foo',
        category: undefined,
      });

      const parsed = new URL(url);
      expect(parsed.searchParams.get('name')).toBe('foo');
      expect(parsed.searchParams.has('category')).toBe(false);
    });

    it('filtra parametri con stringa vuota', () => {
      mockLocalStorage.getItem.mockReturnValue(null);

      const url = buildStudioUrl('/api/v1/items', {
        name: 'bar',
        filter: '',
      });

      const parsed = new URL(url);
      expect(parsed.searchParams.get('name')).toBe('bar');
      expect(parsed.searchParams.has('filter')).toBe(false);
    });

    it('converte valori booleani e numerici in stringhe', () => {
      mockLocalStorage.getItem.mockReturnValue(null);

      const url = buildStudioUrl('/api/v1/data', {
        count: 100,
        enabled: false,
      });

      const parsed = new URL(url);
      expect(parsed.searchParams.get('count')).toBe('100');
      expect(parsed.searchParams.get('enabled')).toBe('false');
    });

    it('funziona senza parametri opzionali', () => {
      mockLocalStorage.getItem.mockReturnValue(null);

      const url = buildStudioUrl('/api/v1/health');

      expect(url).toBe('http://localhost:8000/api/v1/health');
    });
  });
});
