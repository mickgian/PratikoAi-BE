'use client';

import { ArrowRight, CheckCircle2, AlertCircle } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import type { ColumnMapping } from '../types';
import { ourFields } from '../data/constants';

interface ClientImportMappingStepProps {
  columnMappings: ColumnMapping[];
  detectedColumns: string[];
  onUpdateMapping: (ourField: string, yourColumn: string) => void;
}

export function ClientImportMappingStep({
  columnMappings,
  detectedColumns,
  onUpdateMapping,
}: ClientImportMappingStepProps) {
  return (
    <div className="p-8">
      <h2 className="text-xl text-[#2A5D67] mb-6">Mappa le Colonne</h2>
      <p className="text-sm text-[#1E293B] opacity-70 mb-6">
        Abbina i campi del nostro sistema alle colonne del tuo file. Le colonne riconosciute sono pre-compilate.
      </p>
      <Table>
        <TableHeader>
          <TableRow className="bg-[#F8F5F1] hover:bg-[#F8F5F1]">
            <TableHead className="text-[#2A5D67]">Campo Sistema</TableHead>
            <TableHead className="text-[#2A5D67]">&rarr;</TableHead>
            <TableHead className="text-[#2A5D67]">Colonna File</TableHead>
            <TableHead className="text-[#2A5D67]">Obbligatorio</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {ourFields.map(field => {
            const mapping = columnMappings.find(
              m => m.ourField === field.value
            );
            return (
              <TableRow key={field.value} className="border-b border-[#C4BDB4]">
                <TableCell className="text-[#1E293B]">{field.label}</TableCell>
                <TableCell>
                  <ArrowRight className="w-4 h-4 text-[#C4BDB4]" />
                </TableCell>
                <TableCell>
                  <div className="flex items-center gap-2">
                    <Select
                      value={mapping?.yourColumn || ''}
                      onValueChange={value => onUpdateMapping(field.value, value)}
                    >
                      <SelectTrigger
                        className={`bg-[#F8F5F1] ${
                          field.required && !mapping?.yourColumn
                            ? 'border-red-500'
                            : mapping?.confidence && mapping.confidence >= 0.7
                              ? 'border-emerald-400'
                              : ''
                        }`}
                      >
                        <SelectValue placeholder="Seleziona colonna" />
                      </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="">Nessuna</SelectItem>
                      {detectedColumns.map(col => (
                        <SelectItem key={col} value={col}>
                          {col}
                        </SelectItem>
                      ))}
                    </SelectContent>
                    </Select>
                    {mapping?.confidence !== undefined && mapping.confidence >= 0.7 && (
                      <CheckCircle2 className="w-4 h-4 text-emerald-500 shrink-0" />
                    )}
                    {mapping?.confidence !== undefined && mapping.confidence > 0 && mapping.confidence < 0.7 && (
                      <AlertCircle className="w-4 h-4 text-amber-500 shrink-0" />
                    )}
                  </div>
                </TableCell>
                <TableCell>
                  {field.required ? (
                    <Badge variant="destructive" className="text-xs">
                      S&igrave;
                    </Badge>
                  ) : (
                    <Badge
                      variant="outline"
                      className="text-xs border-[#C4BDB4]"
                    >
                      No
                    </Badge>
                  )}
                </TableCell>
              </TableRow>
            );
          })}
        </TableBody>
      </Table>
    </div>
  );
}
