/**
 * @jest-environment jsdom
 */
import {
  listClients,
  getClient,
  createClient,
  updateClient,
  deleteClient,
  previewImport,
  importClients,
} from '../clients';

// Mock fetch
const mockFetch = jest.fn();
global.fetch = mockFetch;

// Mock apiClient (used by previewImport / importClients for token)
jest.mock('@/lib/api', () => ({
  apiClient: {
    getAccessToken: jest.fn().mockReturnValue('test-token'),
  },
}));

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

const mockClient = {
  id: 1,
  studio_id: 'studio-123',
  codice_fiscale: 'RSSMRA85M01H501Z',
  nome: 'Mario Rossi',
  tipo_cliente: 'persona_fisica',
  stato_cliente: 'attivo',
  comune: 'Roma',
  provincia: 'RM',
  partita_iva: null,
  email: 'mario@example.com',
  phone: null,
  indirizzo: null,
  cap: null,
  note_studio: null,
  inps_matricola: null,
  inps_status: null,
  inps_ultimo_pagamento: null,
  inail_pat: null,
  inail_status: null,
  created_at: '2024-01-01T00:00:00Z',
};

const mockClientList = {
  items: [mockClient],
  total: 1,
  offset: 0,
  limit: 50,
};

describe('clients API', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  // ---------------------------------------------------------------
  // listClients
  // ---------------------------------------------------------------
  describe('listClients', () => {
    it('should fetch clients with default params', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockClientList,
      });

      const result = await listClients();

      expect(result).toEqual(mockClientList);
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/v1/clients'),
        expect.objectContaining({
          headers: expect.objectContaining({
            Authorization: 'Bearer test-token',
          }),
        })
      );
    });

    it('should pass filter params to URL', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockClientList,
      });

      await listClients({ offset: 10, limit: 25, stato: 'attivo' });

      const { buildStudioUrl } = require('@/lib/api/helpers');
      expect(buildStudioUrl).toHaveBeenCalledWith('/api/v1/clients', {
        offset: 10,
        limit: 25,
        stato: 'attivo',
      });
    });

    it('should throw on error response', async () => {
      mockFetch.mockResolvedValueOnce({ ok: false, status: 500 });

      await expect(listClients()).rejects.toThrow(
        'Errore nel caricamento dei clienti'
      );
    });
  });

  // ---------------------------------------------------------------
  // getClient
  // ---------------------------------------------------------------
  describe('getClient', () => {
    it('should fetch a single client by ID', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockClient,
      });

      const result = await getClient(1);

      expect(result).toEqual(mockClient);
      const { buildStudioUrl } = require('@/lib/api/helpers');
      expect(buildStudioUrl).toHaveBeenCalledWith('/api/v1/clients/1');
    });

    it('should throw when client not found', async () => {
      mockFetch.mockResolvedValueOnce({ ok: false, status: 404 });

      await expect(getClient(999)).rejects.toThrow('Cliente non trovato');
    });
  });

  // ---------------------------------------------------------------
  // createClient
  // ---------------------------------------------------------------
  describe('createClient', () => {
    const createData = {
      codice_fiscale: 'RSSMRA85M01H501Z',
      nome: 'Mario Rossi',
      tipo_cliente: 'persona_fisica',
      comune: 'Roma',
      provincia: 'RM',
    };

    it('should create a client with POST', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockClient,
      });

      const result = await createClient(createData);

      expect(result).toEqual(mockClient);
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/v1/clients'),
        expect.objectContaining({
          method: 'POST',
          headers: expect.objectContaining({
            'Content-Type': 'application/json',
          }),
          body: JSON.stringify(createData),
        })
      );
    });

    it('should throw with detail from error response', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 400,
        json: async () => ({ detail: 'Codice fiscale duplicato' }),
      });

      await expect(createClient(createData)).rejects.toThrow(
        'Codice fiscale duplicato'
      );
    });

    it('should throw default message when error has no detail', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 500,
        json: async () => {
          throw new Error('parse error');
        },
      });

      await expect(createClient(createData)).rejects.toThrow(
        'Errore nella creazione del cliente'
      );
    });
  });

  // ---------------------------------------------------------------
  // updateClient
  // ---------------------------------------------------------------
  describe('updateClient', () => {
    const updateData = { nome: 'Mario Rossi Aggiornato' };

    it('should update a client with PUT', async () => {
      const updated = { ...mockClient, nome: 'Mario Rossi Aggiornato' };
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => updated,
      });

      const result = await updateClient(1, updateData);

      expect(result.nome).toBe('Mario Rossi Aggiornato');
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/v1/clients/1'),
        expect.objectContaining({
          method: 'PUT',
          body: JSON.stringify(updateData),
        })
      );
    });

    it('should throw with detail from error response', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 400,
        json: async () => ({ detail: 'Dati non validi' }),
      });

      await expect(updateClient(1, updateData)).rejects.toThrow(
        'Dati non validi'
      );
    });

    it('should throw default message when error has no detail', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 500,
        json: async () => {
          throw new Error('parse error');
        },
      });

      await expect(updateClient(1, updateData)).rejects.toThrow(
        "Errore nell'aggiornamento del cliente"
      );
    });
  });

  // ---------------------------------------------------------------
  // deleteClient
  // ---------------------------------------------------------------
  describe('deleteClient', () => {
    it('should delete a client with DELETE method', async () => {
      mockFetch.mockResolvedValueOnce({ ok: true });

      await deleteClient(1);

      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/v1/clients/1'),
        expect.objectContaining({ method: 'DELETE' })
      );
    });

    it('should throw on error response', async () => {
      mockFetch.mockResolvedValueOnce({ ok: false, status: 500 });

      await expect(deleteClient(1)).rejects.toThrow(
        "Errore nell'eliminazione del cliente"
      );
    });
  });

  // ---------------------------------------------------------------
  // previewImport
  // ---------------------------------------------------------------
  describe('previewImport', () => {
    const mockPreview = {
      detected_columns: ['codice_fiscale', 'nome'],
      total_rows: 10,
      valid_rows: 8,
      invalid_rows: 2,
      rows: [
        {
          row_number: 1,
          data: { codice_fiscale: 'ABC', nome: 'Test' },
          is_valid: true,
          errors: [],
        },
      ],
    };

    it('should upload file as FormData for preview', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockPreview,
      });

      const file = new File(['csv,data'], 'clients.csv', { type: 'text/csv' });
      const result = await previewImport(file);

      expect(result).toEqual(mockPreview);
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/v1/clients/import/preview'),
        expect.objectContaining({
          method: 'POST',
          body: expect.any(FormData),
        })
      );

      // Verify FormData contains the file
      const callArgs = mockFetch.mock.calls[0];
      const formData = callArgs[1].body as FormData;
      expect(formData.get('file')).toBeTruthy();
    });

    it('should NOT include Content-Type in headers (browser sets multipart boundary)', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockPreview,
      });

      const file = new File(['data'], 'test.csv', { type: 'text/csv' });
      await previewImport(file);

      const callArgs = mockFetch.mock.calls[0];
      const headers = callArgs[1].headers;
      expect(headers['Content-Type']).toBeUndefined();
    });

    it('should throw with detail from error response', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 400,
        json: async () => ({ detail: 'Formato file non supportato' }),
      });

      const file = new File(['data'], 'test.txt', { type: 'text/plain' });
      await expect(previewImport(file)).rejects.toThrow(
        'Formato file non supportato'
      );
    });

    it('should throw default message when error has no detail', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 500,
        json: async () => {
          throw new Error('parse error');
        },
      });

      const file = new File(['data'], 'test.csv', { type: 'text/csv' });
      await expect(previewImport(file)).rejects.toThrow(
        "Errore durante l'anteprima del file"
      );
    });
  });

  // ---------------------------------------------------------------
  // importClients
  // ---------------------------------------------------------------
  describe('importClients', () => {
    const mockImportResult = {
      total: 10,
      success_count: 8,
      error_count: 2,
      errors: [
        {
          row_number: 3,
          field: 'codice_fiscale',
          message: 'Formato non valido',
        },
      ],
      warnings: null,
    };

    it('should upload file with FormData', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockImportResult,
      });

      const file = new File(['csv,data'], 'clients.csv', { type: 'text/csv' });
      const result = await importClients(file);

      expect(result).toEqual(mockImportResult);
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/v1/clients/import'),
        expect.objectContaining({
          method: 'POST',
          body: expect.any(FormData),
        })
      );
    });

    it('should include column_mapping in FormData when provided', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockImportResult,
      });

      const file = new File(['data'], 'clients.csv', { type: 'text/csv' });
      const mapping = { CF: 'codice_fiscale', Nome: 'nome' };
      await importClients(file, mapping);

      const callArgs = mockFetch.mock.calls[0];
      const formData = callArgs[1].body as FormData;
      expect(formData.get('file')).toBeTruthy();
      expect(formData.get('column_mapping')).toBe(JSON.stringify(mapping));
    });

    it('should NOT include column_mapping when not provided', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockImportResult,
      });

      const file = new File(['data'], 'clients.csv', { type: 'text/csv' });
      await importClients(file);

      const callArgs = mockFetch.mock.calls[0];
      const formData = callArgs[1].body as FormData;
      expect(formData.get('column_mapping')).toBeNull();
    });

    it('should include X-User-Id header', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockImportResult,
      });

      const file = new File(['data'], 'clients.csv', { type: 'text/csv' });
      await importClients(file);

      const callArgs = mockFetch.mock.calls[0];
      const headers = callArgs[1].headers;
      expect(headers['X-User-Id']).toBe('42');
    });

    it('should throw with detail from error response', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 400,
        json: async () => ({ detail: 'File corrotto' }),
      });

      const file = new File(['data'], 'test.csv', { type: 'text/csv' });
      await expect(importClients(file)).rejects.toThrow('File corrotto');
    });

    it('should throw default message when error has no detail', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 500,
        json: async () => {
          throw new Error('parse error');
        },
      });

      const file = new File(['data'], 'test.csv', { type: 'text/csv' });
      await expect(importClients(file)).rejects.toThrow(
        "Errore durante l'importazione dei clienti"
      );
    });
  });
});
