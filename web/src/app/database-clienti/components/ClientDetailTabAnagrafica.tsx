'use client';

import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import type { ClientFormData } from '../types';

interface ClientDetailTabAnagraficaProps {
  formData: ClientFormData;
  errors: Record<string, string>;
  onUpdateField: (field: keyof ClientFormData, value: unknown) => void;
}

export function ClientDetailTabAnagrafica({
  formData,
  errors,
  onUpdateField,
}: ClientDetailTabAnagraficaProps) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
      <div className="md:col-span-2">
        <Label htmlFor="denominazione">Denominazione / Ragione Sociale *</Label>
        <Input
          id="denominazione"
          value={formData.denominazione}
          onChange={e => onUpdateField('denominazione', e.target.value)}
          className={`mt-1 bg-[#F8F5F1] ${errors.denominazione ? 'border-red-500' : ''}`}
          placeholder="Es. Studio Legale Rossi"
        />
        {errors.denominazione && (
          <p className="text-red-500 text-sm mt-1">{errors.denominazione}</p>
        )}
      </div>
      <div>
        <Label htmlFor="codiceFiscale">Codice Fiscale *</Label>
        <Input
          id="codiceFiscale"
          value={formData.codiceFiscale}
          onChange={e =>
            onUpdateField('codiceFiscale', e.target.value.toUpperCase())
          }
          className={`mt-1 bg-[#F8F5F1] font-mono ${errors.codiceFiscale ? 'border-red-500' : ''}`}
          placeholder="RSSMRA70A01F205X"
          maxLength={16}
        />
        {errors.codiceFiscale && (
          <p className="text-red-500 text-sm mt-1">{errors.codiceFiscale}</p>
        )}
      </div>
      <div>
        <Label htmlFor="partitaIva">Partita IVA</Label>
        <Input
          id="partitaIva"
          value={formData.partitaIva}
          onChange={e => onUpdateField('partitaIva', e.target.value)}
          className="mt-1 bg-[#F8F5F1] font-mono"
          placeholder="12345678901"
          maxLength={11}
        />
      </div>
      <div>
        <Label htmlFor="tipoSoggetto">Tipo Soggetto *</Label>
        <Select
          value={formData.tipoSoggetto}
          onValueChange={value => onUpdateField('tipoSoggetto', value)}
        >
          <SelectTrigger
            className={`mt-1 bg-[#F8F5F1] ${errors.tipoSoggetto ? 'border-red-500' : ''}`}
          >
            <SelectValue placeholder="Seleziona tipo" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="persona_fisica">Persona Fisica</SelectItem>
            <SelectItem value="ditta_individuale">Ditta Individuale</SelectItem>
            <SelectItem value="societa_persone">Società di Persone</SelectItem>
            <SelectItem value="societa_capitali">
              Società di Capitali
            </SelectItem>
            <SelectItem value="ente_no_profit">Ente No Profit</SelectItem>
          </SelectContent>
        </Select>
        {errors.tipoSoggetto && (
          <p className="text-red-500 text-sm mt-1">{errors.tipoSoggetto}</p>
        )}
      </div>
      <div className="md:col-span-2">
        <Label htmlFor="indirizzo">Indirizzo</Label>
        <Input
          id="indirizzo"
          value={formData.indirizzo}
          onChange={e => onUpdateField('indirizzo', e.target.value)}
          className="mt-1 bg-[#F8F5F1]"
          placeholder="Via, Piazza, ecc."
        />
      </div>
      <div>
        <Label htmlFor="cap">CAP</Label>
        <Input
          id="cap"
          value={formData.cap}
          onChange={e => onUpdateField('cap', e.target.value)}
          className="mt-1 bg-[#F8F5F1]"
          placeholder="20121"
          maxLength={5}
        />
      </div>
      <div>
        <Label htmlFor="comune">Comune</Label>
        <Input
          id="comune"
          value={formData.comune}
          onChange={e => onUpdateField('comune', e.target.value)}
          className="mt-1 bg-[#F8F5F1]"
          placeholder="Milano"
        />
      </div>
      <div>
        <Label htmlFor="provincia">Provincia</Label>
        <Input
          id="provincia"
          value={formData.provincia}
          onChange={e =>
            onUpdateField('provincia', e.target.value.toUpperCase())
          }
          className="mt-1 bg-[#F8F5F1]"
          placeholder="MI"
          maxLength={2}
        />
      </div>
    </div>
  );
}
