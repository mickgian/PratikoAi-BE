/**
 * Shared response transformer utilities.
 *
 * Converts snake_case backend responses to camelCase frontend types
 * and maps enum values to Italian display strings.
 */

// --- snake_case → camelCase conversion ---

type CamelCase<S extends string> = S extends `${infer P}_${infer Q}`
  ? `${P}${Capitalize<CamelCase<Q>>}`
  : S;

type CamelCaseKeys<T> =
  T extends Array<infer U>
    ? CamelCaseKeys<U>[]
    : T extends object
      ? { [K in keyof T as K extends string ? CamelCase<K> : K]: T[K] }
      : T;

/**
 * Convert a single snake_case string to camelCase.
 */
function toCamelCase(str: string): string {
  return str.replace(/_([a-z])/g, (_, letter) => letter.toUpperCase());
}

/**
 * Recursively convert all keys in an object from snake_case to camelCase.
 */
export function snakeToCamel<T>(obj: T): CamelCaseKeys<T> {
  if (Array.isArray(obj)) {
    return obj.map(item => snakeToCamel(item)) as CamelCaseKeys<T>;
  }
  if (obj !== null && typeof obj === 'object' && !(obj instanceof Date)) {
    const result: Record<string, unknown> = {};
    for (const [key, value] of Object.entries(obj as Record<string, unknown>)) {
      result[toCamelCase(key)] = snakeToCamel(value);
    }
    return result as CamelCaseKeys<T>;
  }
  return obj as CamelCaseKeys<T>;
}

// --- Communication status maps ---

export const communicationStatusToItalian: Record<string, string> = {
  DRAFT: 'bozza',
  PENDING_REVIEW: 'in_revisione',
  APPROVED: 'approvata',
  REJECTED: 'rifiutata',
  SENT: 'inviata',
};

export const communicationStatusFromItalian: Record<string, string> = {
  bozza: 'DRAFT',
  in_revisione: 'PENDING_REVIEW',
  approvata: 'APPROVED',
  rifiutata: 'REJECTED',
  inviata: 'SENT',
};

// --- Client status maps ---

export const clientStatusToItalian: Record<string, string> = {
  ATTIVO: 'attivo',
  PROSPECT: 'prospect',
  INATTIVO: 'inattivo',
};

export const clientTypeToItalian: Record<string, string> = {
  PERSONA_FISICA: 'persona_fisica',
  DITTA_INDIVIDUALE: 'ditta_individuale',
  SOCIETA_PERSONE: 'societa_persone',
  SOCIETA_CAPITALI: 'societa_capitali',
  ENTE_NO_PROFIT: 'ente_no_profit',
};

// --- Channel maps ---

export const channelToItalian: Record<string, string> = {
  EMAIL: 'email',
  WHATSAPP: 'whatsapp',
};
