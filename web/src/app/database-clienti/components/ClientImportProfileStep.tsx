'use client';

import { Info } from 'lucide-react';
import { Input } from '@/components/ui/input';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import type { ProfileOverride, ProfileOverrides } from '../types';
import type { ImportPreviewRow } from '@/lib/api/clients';

/** Empty override template for new rows. */
const EMPTY_OVERRIDE: ProfileOverride = {
  regime_fiscale: '',
  codice_ateco_principale: '',
  data_inizio_attivita: '',
  n_dipendenti: '',
  ccnl_applicato: '',
};

interface ClientImportProfileStepProps {
  rows: ImportPreviewRow[];
  profileOverrides: ProfileOverrides;
  onUpdate: (
    codiceFiscale: string,
    field: keyof ProfileOverride,
    value: string
  ) => void;
  /** Mapping from file column name to backend field name (reversed column_mapping). */
  columnMapping: Record<string, string>;
}

/**
 * Resolve a backend field name from preview row data using the column mapping.
 * Falls back to direct key lookup if no mapping exists.
 */
function resolveField(
  data: Record<string, string | null>,
  backendField: string,
  columnMapping: Record<string, string>
): string {
  // Direct lookup (if data already uses backend field names)
  if (data[backendField] !== undefined && data[backendField] !== null) {
    return data[backendField] ?? '';
  }
  // Look up via column mapping: find the file column that maps to this backend field
  for (const [fileCol, targetField] of Object.entries(columnMapping)) {
    if (targetField === backendField && data[fileCol] !== undefined) {
      return data[fileCol] ?? '';
    }
  }
  return '';
}

export function ClientImportProfileStep({
  rows,
  profileOverrides,
  onUpdate,
  columnMapping,
}: ClientImportProfileStepProps) {
  const validRows = rows.filter(r => r.is_valid);

  return (
    <div className="p-8">
      <h2 className="text-xl text-[#2A5D67] mb-2">Profilo Aziendale</h2>
      <p className="text-sm text-[#1E293B] opacity-70 mb-6">
        Il tuo file non contiene i dati del profilo aziendale. Compila i campi
        per ogni cliente per abilitare il matching normativo.
      </p>

      <div className="mb-6 p-4 bg-blue-50 border border-blue-200 rounded-lg flex gap-3">
        <Info className="w-5 h-5 text-blue-600 shrink-0 mt-0.5" />
        <p className="text-sm text-blue-800">
          Puoi lasciare vuoti i campi se non hai i dati disponibili. Potrai
          completarli in seguito dalla scheda di ogni cliente.
        </p>
      </div>

      <div className="overflow-x-auto border border-[#C4BDB4] rounded-lg">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-[#F8F5F1] border-b border-[#C4BDB4]">
              <th className="text-left px-3 py-2 text-[#1E293B] font-medium whitespace-nowrap">
                Nome
              </th>
              <th className="text-left px-3 py-2 text-[#1E293B] font-medium whitespace-nowrap">
                Cod. Fiscale
              </th>
              <th className="text-left px-3 py-2 text-[#1E293B] font-medium whitespace-nowrap">
                Regime Fiscale
              </th>
              <th className="text-left px-3 py-2 text-[#1E293B] font-medium whitespace-nowrap">
                Codice ATECO
              </th>
              <th className="text-left px-3 py-2 text-[#1E293B] font-medium whitespace-nowrap">
                Data Inizio Attività
              </th>
            </tr>
          </thead>
          <tbody>
            {validRows.map(row => {
              const cf = resolveField(
                row.data,
                'codice_fiscale',
                columnMapping
              );
              const nome = resolveField(row.data, 'nome', columnMapping);
              const override = profileOverrides[cf] ?? EMPTY_OVERRIDE;

              return (
                <tr
                  key={row.row_number}
                  className="border-b border-[#C4BDB4] last:border-b-0 hover:bg-[#FAFAF8]"
                >
                  <td className="px-3 py-2 text-[#1E293B] whitespace-nowrap max-w-[200px] truncate">
                    {nome || '-'}
                  </td>
                  <td className="px-3 py-2 text-[#1E293B] font-mono text-xs whitespace-nowrap">
                    {cf || '-'}
                  </td>
                  <td className="px-3 py-2">
                    <Select
                      value={override.regime_fiscale || undefined}
                      onValueChange={v => onUpdate(cf, 'regime_fiscale', v)}
                    >
                      <SelectTrigger className="bg-[#F8F5F1] h-8 text-xs w-[140px]">
                        <SelectValue placeholder="Seleziona" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="ordinario">Ordinario</SelectItem>
                        <SelectItem value="semplificato">
                          Semplificato
                        </SelectItem>
                        <SelectItem value="forfettario">Forfettario</SelectItem>
                        <SelectItem value="agricolo">Agricolo</SelectItem>
                        <SelectItem value="minimi">Minimi</SelectItem>
                      </SelectContent>
                    </Select>
                  </td>
                  <td className="px-3 py-2">
                    <Input
                      placeholder="es. 62.01.00"
                      value={override.codice_ateco_principale}
                      onChange={e =>
                        onUpdate(cf, 'codice_ateco_principale', e.target.value)
                      }
                      className="bg-[#F8F5F1] h-8 text-xs w-[120px]"
                    />
                  </td>
                  <td className="px-3 py-2">
                    <Input
                      type="date"
                      value={override.data_inizio_attivita}
                      onChange={e =>
                        onUpdate(cf, 'data_inizio_attivita', e.target.value)
                      }
                      className="bg-[#F8F5F1] h-8 text-xs w-[140px]"
                    />
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {validRows.length > 10 && (
        <p className="text-xs text-[#1E293B] opacity-50 mt-2">
          {validRows.length} clienti da completare
        </p>
      )}
    </div>
  );
}
