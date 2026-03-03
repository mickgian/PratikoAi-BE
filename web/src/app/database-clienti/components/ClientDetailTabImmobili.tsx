'use client';

import { Plus, Trash2 } from 'lucide-react';
import { motion } from 'motion/react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import type { ClientFormData, Immobile } from '../types';

interface ClientDetailTabImmobiliProps {
  immobili: Immobile[];
  onUpdateField: (field: keyof ClientFormData, value: unknown) => void;
}

export function ClientDetailTabImmobili({
  immobili,
  onUpdateField,
}: ClientDetailTabImmobiliProps) {
  const handleAdd = () => {
    const newImmobile: Immobile = {
      id: Date.now().toString(),
      tipologia: '',
      indirizzo: '',
      comune: '',
      renditaCatastale: '',
    };
    onUpdateField('immobili', [...immobili, newImmobile]);
  };

  const handleRemove = (id: string) => {
    onUpdateField(
      'immobili',
      immobili.filter(imm => imm.id !== id)
    );
  };

  const handleUpdate = (id: string, field: keyof Immobile, value: string) => {
    onUpdateField(
      'immobili',
      immobili.map(imm => (imm.id === id ? { ...imm, [field]: value } : imm))
    );
  };

  return (
    <div className="space-y-4">
      <div className="flex justify-between items-center">
        <h3 className="text-[#1E293B]">Immobili di Proprietà</h3>
        <Button
          onClick={handleAdd}
          variant="outline"
          size="sm"
          className="border-[#2A5D67] text-[#2A5D67] hover:bg-[#2A5D67] hover:text-white"
        >
          <Plus className="w-4 h-4 mr-2" />
          Aggiungi Immobile
        </Button>
      </div>
      {immobili.length === 0 ? (
        <div className="text-center py-8 bg-[#F8F5F1] rounded-lg">
          <p className="text-[#1E293B] opacity-70">
            Nessun immobile registrato
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          {immobili.map((immobile, index) => (
            <motion.div
              key={immobile.id}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              className="p-4 border border-[#C4BDB4] rounded-lg bg-[#F8F5F1]"
            >
              <div className="flex justify-between items-start mb-4">
                <h4 className="text-[#1E293B]">Immobile {index + 1}</h4>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => handleRemove(immobile.id)}
                  className="text-red-600 hover:bg-red-50"
                >
                  <Trash2 className="w-4 h-4" />
                </Button>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <Label>Tipologia</Label>
                  <Select
                    value={immobile.tipologia}
                    onValueChange={value =>
                      handleUpdate(immobile.id, 'tipologia', value)
                    }
                  >
                    <SelectTrigger className="mt-1 bg-white">
                      <SelectValue placeholder="Seleziona tipologia" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="Abitazione">Abitazione</SelectItem>
                      <SelectItem value="Ufficio">Ufficio</SelectItem>
                      <SelectItem value="Negozio">Negozio</SelectItem>
                      <SelectItem value="Magazzino">Magazzino</SelectItem>
                      <SelectItem value="Terreno">Terreno</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div>
                  <Label>Comune</Label>
                  <Input
                    value={immobile.comune}
                    onChange={e =>
                      handleUpdate(immobile.id, 'comune', e.target.value)
                    }
                    className="mt-1 bg-white"
                    placeholder="Milano"
                  />
                </div>
                <div className="md:col-span-2">
                  <Label>Indirizzo</Label>
                  <Input
                    value={immobile.indirizzo}
                    onChange={e =>
                      handleUpdate(immobile.id, 'indirizzo', e.target.value)
                    }
                    className="mt-1 bg-white"
                    placeholder="Via Roma 123"
                  />
                </div>
                <div>
                  <Label>Rendita Catastale</Label>
                  <Input
                    value={immobile.renditaCatastale}
                    onChange={e =>
                      handleUpdate(
                        immobile.id,
                        'renditaCatastale',
                        e.target.value
                      )
                    }
                    className="mt-1 bg-white"
                    placeholder="€ 2.450,00"
                  />
                </div>
              </div>
            </motion.div>
          ))}
        </div>
      )}
    </div>
  );
}
