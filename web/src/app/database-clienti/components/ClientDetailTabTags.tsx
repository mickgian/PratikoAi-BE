'use client';

import { useState } from 'react';
import { Plus, X } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Badge } from '@/components/ui/badge';
import type { ClientFormData } from '../types';

interface ClientDetailTabTagsProps {
  tags: string[];
  note: string;
  onUpdateField: (field: keyof ClientFormData, value: unknown) => void;
}

export function ClientDetailTabTags({
  tags,
  note,
  onUpdateField,
}: ClientDetailTabTagsProps) {
  const [newTag, setNewTag] = useState('');

  const handleAddTag = () => {
    const trimmed = newTag.trim();
    if (trimmed && !tags.includes(trimmed)) {
      onUpdateField('tags', [...tags, trimmed]);
      setNewTag('');
    }
  };

  const handleRemoveTag = (tagToRemove: string) => {
    onUpdateField(
      'tags',
      tags.filter(tag => tag !== tagToRemove)
    );
  };

  return (
    <div className="space-y-6">
      <div>
        <Label>Tags</Label>
        <div className="flex gap-2 mt-2">
          <Input
            value={newTag}
            onChange={e => setNewTag(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && handleAddTag()}
            className="bg-[#F8F5F1]"
            placeholder="Aggiungi tag (es. Priorità Alta)"
          />
          <Button
            onClick={handleAddTag}
            variant="outline"
            className="border-[#2A5D67] text-[#2A5D67] hover:bg-[#2A5D67] hover:text-white"
          >
            <Plus className="w-4 h-4" />
          </Button>
        </div>
        <div className="flex flex-wrap gap-2 mt-3">
          {tags.map(tag => (
            <Badge
              key={tag}
              className="bg-[#D4A574] text-[#1E293B] hover:bg-[#D4A574]/80 pr-1"
            >
              {tag}
              <button
                onClick={() => handleRemoveTag(tag)}
                className="ml-2 hover:bg-white/20 rounded-full p-0.5"
              >
                <X className="w-3 h-3" />
              </button>
            </Badge>
          ))}
        </div>
      </div>
      <div>
        <Label htmlFor="note">Note</Label>
        <Textarea
          id="note"
          value={note}
          onChange={e => onUpdateField('note', e.target.value)}
          className="mt-2 bg-[#F8F5F1] min-h-[200px]"
          placeholder="Inserisci note sul cliente, informazioni importanti, scadenze, ecc."
        />
      </div>
    </div>
  );
}
