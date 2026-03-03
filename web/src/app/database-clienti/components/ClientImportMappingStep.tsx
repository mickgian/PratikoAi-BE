'use client';

import { ArrowRight } from 'lucide-react';
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
        Abbina i campi del nostro sistema alle colonne del tuo file
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
                  <Select
                    value={mapping?.yourColumn || ''}
                    onValueChange={value => onUpdateMapping(field.value, value)}
                  >
                    <SelectTrigger
                      className={`bg-[#F8F5F1] ${
                        field.required && !mapping?.yourColumn
                          ? 'border-red-500'
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
