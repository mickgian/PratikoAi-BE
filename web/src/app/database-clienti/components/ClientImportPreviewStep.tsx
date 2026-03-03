'use client';

import { Check, AlertCircle } from 'lucide-react';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import type { ImportPreviewRow } from '@/lib/api/clients';

interface ClientImportPreviewStepProps {
  rows: ImportPreviewRow[];
  validRows: number;
  invalidRows: number;
}

/** Display a cell value — show (vuoto) in red for empty values. */
function CellValue({ value }: { value: string | null | undefined }) {
  if (!value) {
    return <span className="text-red-600">(vuoto)</span>;
  }
  return <span className="text-[#1E293B]">{value}</span>;
}

export function ClientImportPreviewStep({
  rows,
  validRows,
  invalidRows,
}: ClientImportPreviewStepProps) {
  return (
    <div className="p-8">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-xl text-[#2A5D67]">Anteprima Importazione</h2>
          <p className="text-sm text-[#1E293B] opacity-70 mt-1">
            Verifica i dati prima di importare
          </p>
        </div>
        <div className="flex gap-4">
          <div className="text-right">
            <div className="flex items-center gap-2">
              <Check className="w-5 h-5 text-green-600" />
              <span className="text-2xl text-green-600">{validRows}</span>
            </div>
            <p className="text-xs text-[#1E293B] opacity-70">Validi</p>
          </div>
          <div className="text-right">
            <div className="flex items-center gap-2">
              <AlertCircle className="w-5 h-5 text-red-600" />
              <span className="text-2xl text-red-600">{invalidRows}</span>
            </div>
            <p className="text-xs text-[#1E293B] opacity-70">Errori</p>
          </div>
        </div>
      </div>
      <div className="overflow-x-auto">
        <Table>
          <TableHeader>
            <TableRow className="bg-[#F8F5F1] hover:bg-[#F8F5F1]">
              <TableHead className="text-[#2A5D67]">Stato</TableHead>
              <TableHead className="text-[#2A5D67]">Nome</TableHead>
              <TableHead className="text-[#2A5D67]">Cod. Fiscale</TableHead>
              <TableHead className="text-[#2A5D67]">Tipo</TableHead>
              <TableHead className="text-[#2A5D67]">Comune</TableHead>
              <TableHead className="text-[#2A5D67]">Provincia</TableHead>
              <TableHead className="text-[#2A5D67]">P. IVA</TableHead>
              <TableHead className="text-[#2A5D67]">Email</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {rows.map(row => (
              <TableRow
                key={row.row_number}
                className={`border-b border-[#C4BDB4] ${!row.is_valid ? 'bg-red-50' : ''}`}
              >
                <TableCell>
                  {row.is_valid ? (
                    <Check className="w-5 h-5 text-green-600" />
                  ) : (
                    <AlertCircle className="w-5 h-5 text-red-600" />
                  )}
                </TableCell>
                <TableCell>
                  <CellValue value={row.data.nome} />
                </TableCell>
                <TableCell className="font-mono text-sm">
                  <CellValue value={row.data.codice_fiscale} />
                </TableCell>
                <TableCell className="text-xs">
                  <CellValue value={row.data.tipo_cliente} />
                </TableCell>
                <TableCell>
                  <CellValue value={row.data.comune} />
                </TableCell>
                <TableCell>
                  <CellValue value={row.data.provincia} />
                </TableCell>
                <TableCell className="font-mono text-sm">
                  <CellValue value={row.data.partita_iva} />
                </TableCell>
                <TableCell>
                  <CellValue value={row.data.email} />
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
      {invalidRows > 0 && (
        <div className="mt-6 p-4 bg-red-50 rounded-lg border border-red-200">
          <div className="flex items-start gap-3">
            <AlertCircle className="w-5 h-5 text-red-600 mt-0.5 flex-shrink-0" />
            <div>
              <h4 className="text-sm text-red-900 mb-2">
                {invalidRows} righe con errori non verranno importate
              </h4>
              <ul className="text-sm text-red-800 space-y-1">
                <li>Verifica i campi evidenziati in rosso</li>
                <li>
                  Correggi il file e ricaricalo per importare tutte le righe
                </li>
              </ul>
            </div>
          </div>
        </div>
      )}
      {validRows > 0 && (
        <div className="mt-4 p-4 bg-green-50 rounded-lg border border-green-200">
          <div className="flex items-center gap-3">
            <Check className="w-5 h-5 text-green-600 flex-shrink-0" />
            <p className="text-sm text-green-900">
              {validRows}{' '}
              {validRows === 1 ? 'cliente pronto' : 'clienti pronti'} per
              l&apos;importazione
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
