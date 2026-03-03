'use client';

import { Pencil, Trash2, Search, Download, Plus } from 'lucide-react';
import { motion } from 'motion/react';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Checkbox } from '@/components/ui/checkbox';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import type { Cliente } from '../types';
import { tipoSoggettoLabels, regimeFiscaleLabels } from '../data/constants';

interface ClientListTableProps {
  clients: Cliente[];
  selectedClients: Set<string>;
  currentPage: number;
  itemsPerPage: number;
  totalClients: number;
  onSelectAll: (checked: boolean) => void;
  onSelectClient: (clientId: string, checked: boolean) => void;
  onNavigateToDetail: (clientId: string) => void;
  onNavigateToImport: () => void;
  onPageChange: (updater: (p: number) => number) => void;
}

function maskCodiceFiscale(cf: string): string {
  if (cf.length <= 4) return cf;
  return '***' + cf.slice(-4);
}

export function ClientListTable({
  clients,
  selectedClients,
  currentPage,
  itemsPerPage,
  totalClients,
  onSelectAll,
  onSelectClient,
  onNavigateToDetail,
  onNavigateToImport,
  onPageChange,
}: ClientListTableProps) {
  const handleDeleteClient = (clientId: string, denominazione: string) => {
    void clientId;
    toast.success(`Cliente "${denominazione}" eliminato`);
  };

  if (clients.length === 0) {
    return (
      <div className="py-16 px-4 text-center">
        <div className="w-24 h-24 mx-auto mb-4 rounded-full bg-[#F8F5F1] flex items-center justify-center">
          <Search className="w-12 h-12 text-[#C4BDB4]" />
        </div>
        <h3 className="text-[#1E293B] mb-2">Nessun cliente trovato</h3>
        <p className="text-[#1E293B] opacity-70 mb-6">
          Importa un file o aggiungi manualmente il tuo primo cliente
        </p>
        <div className="flex gap-3 justify-center">
          <Button
            onClick={onNavigateToImport}
            className="bg-[#2A5D67] hover:bg-[#1E293B] text-white"
          >
            <Download className="w-4 h-4 mr-2" />
            Importa Clienti
          </Button>
          <Button
            onClick={() => onNavigateToDetail('new')}
            variant="outline"
            className="border-[#2A5D67] text-[#2A5D67] hover:bg-[#F8F5F1]"
          >
            <Plus className="w-4 h-4 mr-2" />
            Aggiungi Manualmente
          </Button>
        </div>
      </div>
    );
  }

  return (
    <>
      <Table>
        <TableHeader>
          <TableRow className="bg-[#F8F5F1] hover:bg-[#F8F5F1]">
            <TableHead className="w-12">
              <Checkbox
                checked={
                  clients.length > 0 &&
                  clients.every(c => selectedClients.has(c.id))
                }
                onCheckedChange={onSelectAll}
              />
            </TableHead>
            <TableHead className="text-[#2A5D67]">
              Nome/Ragione Sociale
            </TableHead>
            <TableHead className="text-[#2A5D67]">Codice Fiscale</TableHead>
            <TableHead className="text-[#2A5D67]">Tipo</TableHead>
            <TableHead className="text-[#2A5D67]">Regime</TableHead>
            <TableHead className="text-[#2A5D67]">ATECO</TableHead>
            <TableHead className="text-[#2A5D67]">Dipendenti</TableHead>
            <TableHead className="text-[#2A5D67]">Tags</TableHead>
            <TableHead className="text-[#2A5D67] text-right">Azioni</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {clients.map((cliente, index) => (
            <motion.tr
              key={cliente.id}
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: index * 0.05 }}
              className="border-b border-[#C4BDB4] hover:bg-[#F8F5F1] transition-colors"
            >
              <TableCell>
                <Checkbox
                  checked={selectedClients.has(cliente.id)}
                  onCheckedChange={checked =>
                    onSelectClient(cliente.id, checked as boolean)
                  }
                />
              </TableCell>
              <TableCell className="text-[#1E293B]">
                {cliente.denominazione}
              </TableCell>
              <TableCell className="text-[#1E293B] font-mono text-sm">
                {maskCodiceFiscale(cliente.codiceFiscale)}
              </TableCell>
              <TableCell>
                <span className="text-xs text-[#1E293B]">
                  {tipoSoggettoLabels[cliente.tipoSoggetto]}
                </span>
              </TableCell>
              <TableCell>
                <Badge
                  variant="outline"
                  className="border-[#2A5D67] text-[#2A5D67] bg-[#2A5D67]/5"
                >
                  {regimeFiscaleLabels[cliente.regimeFiscale]}
                </Badge>
              </TableCell>
              <TableCell className="text-[#1E293B] font-mono text-sm">
                {cliente.codiceAteco}
              </TableCell>
              <TableCell className="text-[#1E293B]">
                {cliente.nDipendenti}
              </TableCell>
              <TableCell>
                <div className="flex flex-wrap gap-1">
                  {cliente.tags.map(tag => (
                    <Badge
                      key={tag}
                      variant="secondary"
                      className="bg-[#D4A574]/20 text-[#1E293B] border-none text-xs"
                    >
                      {tag}
                    </Badge>
                  ))}
                </div>
              </TableCell>
              <TableCell>
                <div className="flex justify-end gap-1">
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => onNavigateToDetail(cliente.id)}
                    className="hover:bg-[#2A5D67]/10"
                  >
                    <Pencil className="w-4 h-4 text-[#2A5D67]" />
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() =>
                      handleDeleteClient(cliente.id, cliente.denominazione)
                    }
                    className="hover:bg-red-50"
                  >
                    <Trash2 className="w-4 h-4 text-red-600" />
                  </Button>
                </div>
              </TableCell>
            </motion.tr>
          ))}
        </TableBody>
      </Table>
      <div className="px-6 py-4 border-t border-[#C4BDB4] flex items-center justify-between">
        <p className="text-sm text-[#1E293B]">
          Mostrando {(currentPage - 1) * itemsPerPage + 1}-
          {Math.min(currentPage * itemsPerPage, totalClients)} di {totalClients}{' '}
          clienti
        </p>
        <div className="flex gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => onPageChange(p => Math.max(1, p - 1))}
            disabled={currentPage === 1}
            className="border-[#C4BDB4]"
          >
            Precedente
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() => onPageChange(p => p + 1)}
            disabled={currentPage * itemsPerPage >= totalClients}
            className="border-[#C4BDB4]"
          >
            Successivo
          </Button>
        </div>
      </div>
    </>
  );
}
