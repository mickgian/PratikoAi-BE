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

interface ClientDetailTabFiscaliProps {
  formData: ClientFormData;
  errors: Record<string, string>;
  onUpdateField: (field: keyof ClientFormData, value: unknown) => void;
}

export function ClientDetailTabFiscali({
  formData,
  errors,
  onUpdateField,
}: ClientDetailTabFiscaliProps) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
      <div>
        <Label htmlFor="regimeFiscale">Regime Fiscale *</Label>
        <Select
          value={formData.regimeFiscale}
          onValueChange={value => onUpdateField('regimeFiscale', value)}
        >
          <SelectTrigger
            className={`mt-1 bg-[#F8F5F1] ${errors.regimeFiscale ? 'border-red-500' : ''}`}
          >
            <SelectValue placeholder="Seleziona regime" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="ordinario">Ordinario</SelectItem>
            <SelectItem value="semplificato">Semplificato</SelectItem>
            <SelectItem value="forfettario">Forfettario</SelectItem>
          </SelectContent>
        </Select>
        {errors.regimeFiscale && (
          <p className="text-red-500 text-sm mt-1">{errors.regimeFiscale}</p>
        )}
      </div>
      <div>
        <Label htmlFor="codiceAteco">Codice ATECO *</Label>
        <Input
          id="codiceAteco"
          value={formData.codiceAteco}
          onChange={e => onUpdateField('codiceAteco', e.target.value)}
          className={`mt-1 bg-[#F8F5F1] font-mono ${errors.codiceAteco ? 'border-red-500' : ''}`}
          placeholder="69.10.10"
        />
        {errors.codiceAteco && (
          <p className="text-red-500 text-sm mt-1">{errors.codiceAteco}</p>
        )}
        <p className="text-sm text-[#1E293B] opacity-70 mt-1">
          Inserisci il codice o cerca per descrizione
        </p>
      </div>
      <div>
        <Label htmlFor="dataInizioAttivita">Data Inizio Attività</Label>
        <Input
          id="dataInizioAttivita"
          type="date"
          value={formData.dataInizioAttivita}
          onChange={e => onUpdateField('dataInizioAttivita', e.target.value)}
          className="mt-1 bg-[#F8F5F1]"
        />
      </div>
      <div>
        <Label htmlFor="posizioneAgenziaEntrate">
          Posizione Agenzia delle Entrate
        </Label>
        <Input
          id="posizioneAgenziaEntrate"
          value={formData.posizioneAgenziaEntrate}
          onChange={e =>
            onUpdateField('posizioneAgenziaEntrate', e.target.value)
          }
          className="mt-1 bg-[#F8F5F1]"
          placeholder="DIR LOMBARDIA - UFF MILANO 1"
        />
      </div>
      <div className="md:col-span-2">
        <div className="flex items-center space-x-2">
          <Checkbox
            id="haCartelleEsattoriali"
            checked={formData.haCartelleEsattoriali}
            onCheckedChange={checked =>
              onUpdateField('haCartelleEsattoriali', checked)
            }
          />
          <Label htmlFor="haCartelleEsattoriali" className="cursor-pointer">
            Ha cartelle esattoriali pendenti
          </Label>
        </div>
      </div>
    </div>
  );
}
