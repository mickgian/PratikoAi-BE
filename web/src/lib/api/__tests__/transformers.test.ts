/**
 * @jest-environment jsdom
 */
import {
  snakeToCamel,
  communicationStatusToItalian,
  communicationStatusFromItalian,
  clientStatusToItalian,
  clientTypeToItalian,
  channelToItalian,
} from '../transformers';

describe('transformers utilities', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  // ----------------------------------------------------------------
  // snakeToCamel
  // ----------------------------------------------------------------
  describe('snakeToCamel', () => {
    it('restituisce null quando input e null', () => {
      expect(snakeToCamel(null)).toBeNull();
    });

    it('restituisce undefined quando input e undefined', () => {
      expect(snakeToCamel(undefined)).toBeUndefined();
    });

    it('restituisce valori primitivi senza modifiche', () => {
      expect(snakeToCamel(42)).toBe(42);
      expect(snakeToCamel('hello_world')).toBe('hello_world');
      expect(snakeToCamel(true)).toBe(true);
      expect(snakeToCamel(0)).toBe(0);
      expect(snakeToCamel('')).toBe('');
    });

    it('converte le chiavi di un oggetto semplice da snake_case a camelCase', () => {
      const input = {
        first_name: 'Mario',
        last_name: 'Rossi',
        email_address: 'mario@example.com',
      };

      const result = snakeToCamel(input);

      expect(result).toEqual({
        firstName: 'Mario',
        lastName: 'Rossi',
        emailAddress: 'mario@example.com',
      });
    });

    it('converte ricorsivamente oggetti annidati', () => {
      const input = {
        user_data: {
          first_name: 'Luigi',
          contact_info: {
            phone_number: '123456',
          },
        },
      };

      const result = snakeToCamel(input);

      expect(result).toEqual({
        userData: {
          firstName: 'Luigi',
          contactInfo: {
            phoneNumber: '123456',
          },
        },
      });
    });

    it('converte elementi di un array ricorsivamente', () => {
      const input = [
        { first_name: 'Anna', last_name: 'Bianchi' },
        { first_name: 'Marco', last_name: 'Verdi' },
      ];

      const result = snakeToCamel(input);

      expect(result).toEqual([
        { firstName: 'Anna', lastName: 'Bianchi' },
        { firstName: 'Marco', lastName: 'Verdi' },
      ]);
    });

    it('gestisce array vuoti', () => {
      expect(snakeToCamel([])).toEqual([]);
    });

    it('gestisce oggetti vuoti', () => {
      expect(snakeToCamel({})).toEqual({});
    });

    it('preserva istanze Date senza convertirle', () => {
      const date = new Date('2025-01-15T10:30:00Z');
      const input = {
        created_at: date,
        user_name: 'Test',
      };

      const result = snakeToCamel(input);

      expect(result).toEqual({
        createdAt: date,
        userName: 'Test',
      });
      expect((result as any).createdAt).toBeInstanceOf(Date);
    });

    it('gestisce annidamento profondo (3+ livelli)', () => {
      const input = {
        level_one: {
          level_two: {
            level_three: {
              deep_value: 'found',
            },
          },
        },
      };

      const result = snakeToCamel(input);

      expect(result).toEqual({
        levelOne: {
          levelTwo: {
            levelThree: {
              deepValue: 'found',
            },
          },
        },
      });
    });

    it('converte array annidati dentro oggetti', () => {
      const input = {
        client_list: [
          { tax_code: 'ABC123', is_active: true },
          { tax_code: 'DEF456', is_active: false },
        ],
      };

      const result = snakeToCamel(input);

      expect(result).toEqual({
        clientList: [
          { taxCode: 'ABC123', isActive: true },
          { taxCode: 'DEF456', isActive: false },
        ],
      });
    });

    it('non modifica chiavi gia in camelCase', () => {
      const input = { firstName: 'Test', alreadyCamel: true };

      const result = snakeToCamel(input);

      expect(result).toEqual({ firstName: 'Test', alreadyCamel: true });
    });

    it('gestisce chiavi con underscore multipli', () => {
      const input = { some_long_key_name: 'value' };

      const result = snakeToCamel(input);

      expect(result).toEqual({ someLongKeyName: 'value' });
    });

    it('gestisce valori null dentro oggetti', () => {
      const input = { some_key: null, other_key: 'value' };

      const result = snakeToCamel(input);

      expect(result).toEqual({ someKey: null, otherKey: 'value' });
    });
  });

  // ----------------------------------------------------------------
  // communicationStatusToItalian / communicationStatusFromItalian
  // ----------------------------------------------------------------
  describe('communicationStatusToItalian', () => {
    it('mappa DRAFT a bozza', () => {
      expect(communicationStatusToItalian['DRAFT']).toBe('bozza');
    });

    it('mappa PENDING_REVIEW a in_revisione', () => {
      expect(communicationStatusToItalian['PENDING_REVIEW']).toBe(
        'in_revisione'
      );
    });

    it('mappa APPROVED a approvata', () => {
      expect(communicationStatusToItalian['APPROVED']).toBe('approvata');
    });

    it('mappa REJECTED a rifiutata', () => {
      expect(communicationStatusToItalian['REJECTED']).toBe('rifiutata');
    });

    it('mappa SENT a inviata', () => {
      expect(communicationStatusToItalian['SENT']).toBe('inviata');
    });

    it('contiene esattamente 5 mappature', () => {
      expect(Object.keys(communicationStatusToItalian)).toHaveLength(5);
    });
  });

  describe('communicationStatusFromItalian', () => {
    it('mappa bozza a DRAFT', () => {
      expect(communicationStatusFromItalian['bozza']).toBe('DRAFT');
    });

    it('mappa in_revisione a PENDING_REVIEW', () => {
      expect(communicationStatusFromItalian['in_revisione']).toBe(
        'PENDING_REVIEW'
      );
    });

    it('contiene esattamente 5 mappature', () => {
      expect(Object.keys(communicationStatusFromItalian)).toHaveLength(5);
    });

    it('le mappature sono bidirezionali con communicationStatusToItalian', () => {
      for (const [english, italian] of Object.entries(
        communicationStatusToItalian
      )) {
        expect(communicationStatusFromItalian[italian]).toBe(english);
      }
    });
  });

  // ----------------------------------------------------------------
  // clientStatusToItalian
  // ----------------------------------------------------------------
  describe('clientStatusToItalian', () => {
    it('mappa ATTIVO a attivo', () => {
      expect(clientStatusToItalian['ATTIVO']).toBe('attivo');
    });

    it('mappa PROSPECT a prospect', () => {
      expect(clientStatusToItalian['PROSPECT']).toBe('prospect');
    });

    it('mappa INATTIVO a inattivo', () => {
      expect(clientStatusToItalian['INATTIVO']).toBe('inattivo');
    });

    it('contiene esattamente 3 mappature', () => {
      expect(Object.keys(clientStatusToItalian)).toHaveLength(3);
    });
  });

  // ----------------------------------------------------------------
  // clientTypeToItalian
  // ----------------------------------------------------------------
  describe('clientTypeToItalian', () => {
    it('mappa PERSONA_FISICA a persona_fisica', () => {
      expect(clientTypeToItalian['PERSONA_FISICA']).toBe('persona_fisica');
    });

    it('mappa DITTA_INDIVIDUALE a ditta_individuale', () => {
      expect(clientTypeToItalian['DITTA_INDIVIDUALE']).toBe(
        'ditta_individuale'
      );
    });

    it('mappa SOCIETA_PERSONE a societa_persone', () => {
      expect(clientTypeToItalian['SOCIETA_PERSONE']).toBe('societa_persone');
    });

    it('mappa SOCIETA_CAPITALI a societa_capitali', () => {
      expect(clientTypeToItalian['SOCIETA_CAPITALI']).toBe('societa_capitali');
    });

    it('mappa ENTE_NO_PROFIT a ente_no_profit', () => {
      expect(clientTypeToItalian['ENTE_NO_PROFIT']).toBe('ente_no_profit');
    });

    it('contiene esattamente 5 mappature', () => {
      expect(Object.keys(clientTypeToItalian)).toHaveLength(5);
    });
  });

  // ----------------------------------------------------------------
  // channelToItalian
  // ----------------------------------------------------------------
  describe('channelToItalian', () => {
    it('mappa EMAIL a email', () => {
      expect(channelToItalian['EMAIL']).toBe('email');
    });

    it('mappa WHATSAPP a whatsapp', () => {
      expect(channelToItalian['WHATSAPP']).toBe('whatsapp');
    });

    it('contiene esattamente 2 mappature', () => {
      expect(Object.keys(channelToItalian)).toHaveLength(2);
    });
  });
});
