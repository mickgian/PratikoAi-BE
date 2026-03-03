'use client';

import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Checkbox } from '@/components/ui/checkbox';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import type { ClientFormData } from '../types';

interface ClientDetailTabLavoroProps {
  formData: ClientFormData;
  onUpdateField: (field: keyof ClientFormData, value: unknown) => void;
}

export function ClientDetailTabLavoro({
  formData,
  onUpdateField,
}: ClientDetailTabLavoroProps) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
      <div>
        <Label htmlFor="numeroDipendenti">Numero Dipendenti</Label>
        <Input
          id="numeroDipendenti"
          type="number"
          min="0"
          value={formData.numeroDipendenti}
          onChange={e => onUpdateField('numeroDipendenti', e.target.value)}
          className="mt-1 bg-[#F8F5F1]"
        />
      </div>
      <div>
        <Label htmlFor="ccnlApplicato">CCNL Applicato</Label>
        <Select
          value={formData.ccnlApplicato}
          onValueChange={value => onUpdateField('ccnlApplicato', value)}
        >
          <SelectTrigger className="mt-1 bg-[#F8F5F1]">
            <SelectValue placeholder="Seleziona CCNL" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="CCNL Commercio">CCNL Commercio</SelectItem>
            <SelectItem value="CCNL Metalmeccanici">
              CCNL Metalmeccanici
            </SelectItem>
            <SelectItem value="CCNL Edilizia">CCNL Edilizia</SelectItem>
            <SelectItem value="CCNL Studi Professionali">
              CCNL Studi Professionali
            </SelectItem>
            <SelectItem value="CCNL Terziario">CCNL Terziario</SelectItem>
            <SelectItem value="Altro">Altro</SelectItem>
          </SelectContent>
        </Select>
      </div>
      <div className="md:col-span-2 space-y-4">
        <div className="flex items-center space-x-2">
          <Checkbox
            id="haApprendisti"
            checked={formData.haApprendisti}
            onCheckedChange={checked => onUpdateField('haApprendisti', checked)}
          />
          <Label htmlFor="haApprendisti" className="cursor-pointer">
            Ha contratti di apprendistato
          </Label>
        </div>
        <div className="flex items-center space-x-2">
          <Checkbox
            id="haLavoratoriStagionali"
            checked={formData.haLavoratoriStagionali}
            onCheckedChange={checked =>
              onUpdateField('haLavoratoriStagionali', checked)
            }
          />
          <Label htmlFor="haLavoratoriStagionali" className="cursor-pointer">
            Ha lavoratori stagionali
          </Label>
        </div>
      </div>
    </div>
  );
}
