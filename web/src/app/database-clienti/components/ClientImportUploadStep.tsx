'use client';

import { Upload, FileSpreadsheet, Check, X } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { toast } from 'sonner';

interface ClientImportUploadStepProps {
  uploadedFile: File | null;
  dragActive: boolean;
  onDrag: (e: React.DragEvent) => void;
  onDrop: (e: React.DragEvent) => void;
  onFileChange: (e: React.ChangeEvent<HTMLInputElement>) => void;
  onRemoveFile: () => void;
}

export function ClientImportUploadStep({
  uploadedFile,
  dragActive,
  onDrag,
  onDrop,
  onFileChange,
  onRemoveFile,
}: ClientImportUploadStepProps) {
  void toast;

  return (
    <div className="p-8">
      <h2 className="text-xl text-[#2A5D67] mb-6">Carica File</h2>
      <div
        onDragEnter={onDrag}
        onDragLeave={onDrag}
        onDragOver={onDrag}
        onDrop={onDrop}
        className={`border-2 border-dashed rounded-lg p-12 text-center transition-colors ${
          dragActive
            ? 'border-[#2A5D67] bg-[#2A5D67]/5'
            : 'border-[#C4BDB4] bg-[#F8F5F1]'
        }`}
      >
        {uploadedFile ? (
          <div className="space-y-4">
            <div className="w-16 h-16 mx-auto rounded-full bg-green-100 flex items-center justify-center">
              <Check className="w-8 h-8 text-green-600" />
            </div>
            <div>
              <p className="text-[#1E293B] mb-1">{uploadedFile.name}</p>
              <p className="text-sm text-[#1E293B] opacity-70">
                {(uploadedFile.size / 1024).toFixed(2)} KB
              </p>
            </div>
            <Button
              onClick={onRemoveFile}
              variant="outline"
              size="sm"
              className="border-[#C4BDB4] text-[#1E293B]"
            >
              <X className="w-4 h-4 mr-2" />
              Rimuovi file
            </Button>
          </div>
        ) : (
          <>
            <Upload className="w-16 h-16 mx-auto mb-4 text-[#C4BDB4]" />
            <h3 className="text-[#1E293B] mb-2">
              Trascina qui il file da importare
            </h3>
            <p className="text-sm text-[#1E293B] opacity-70 mb-6">
              Oppure clicca per selezionare un file dal tuo computer
            </p>
            <label className="inline-flex items-center gap-2 px-4 py-2 bg-[#2A5D67] hover:bg-[#1E293B] text-white rounded-md cursor-pointer transition-colors text-sm font-medium">
              <FileSpreadsheet className="w-4 h-4" />
              Sfoglia
              <input
                type="file"
                accept=".xlsx,.xls,.csv,.pdf"
                onChange={onFileChange}
                className="hidden"
              />
            </label>
            <p className="text-xs text-[#1E293B] opacity-70 mt-4">
              Formati supportati: .xlsx, .xls, .csv, .pdf
            </p>
          </>
        )}
      </div>
    </div>
  );
}
