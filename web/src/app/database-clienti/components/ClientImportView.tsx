'use client';

import { useState } from 'react';
import { ArrowLeft, ArrowRight, Check, Loader2 } from 'lucide-react';
import { motion } from 'motion/react';
import { useRouter } from 'next/navigation';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
import {
  importClients,
  previewImport,
  type ImportPreviewResponse,
} from '@/lib/api/clients';
import type { ColumnMapping } from '../types';
import { ourFields } from '../data/constants';
import { ClientImportUploadStep } from './ClientImportUploadStep';
import { ClientImportMappingStep } from './ClientImportMappingStep';
import { ClientImportPreviewStep } from './ClientImportPreviewStep';

type Step = 1 | 2 | 3;

const STEP_LABELS: Record<Step, string> = {
  1: 'Carica File',
  2: 'Mappa Colonne',
  3: 'Anteprima e Conferma',
};

export function ClientImportView() {
  const router = useRouter();
  const [currentStep, setCurrentStep] = useState<Step>(1);
  const [uploadedFile, setUploadedFile] = useState<File | null>(null);
  const [dragActive, setDragActive] = useState(false);
  const [isLoadingPreview, setIsLoadingPreview] = useState(false);
  const [preview, setPreview] = useState<ImportPreviewResponse | null>(null);
  const [columnMappings, setColumnMappings] = useState<ColumnMapping[]>(
    ourFields.map(field => ({
      ourField: field.value,
      yourColumn: '',
      required: field.required,
    }))
  );

  const validRows = preview?.valid_rows ?? 0;
  const invalidRows = preview?.invalid_rows ?? 0;

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    if (e.dataTransfer.files?.[0]) {
      handleFile(e.dataTransfer.files[0]);
    }
  };

  const handleFile = (file: File) => {
    const validTypes = [
      'application/vnd.ms-excel',
      'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
      'text/csv',
      'application/pdf',
    ];
    if (
      validTypes.includes(file.type) ||
      file.name.endsWith('.csv') ||
      file.name.endsWith('.xlsx') ||
      file.name.endsWith('.pdf')
    ) {
      setUploadedFile(file);
      setPreview(null);
      toast.success(`File "${file.name}" caricato con successo`);
    } else {
      toast.error(
        'Formato file non supportato. Usa Excel (.xlsx), CSV (.csv) o PDF (.pdf)'
      );
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files?.[0]) handleFile(e.target.files[0]);
  };

  const handleNext = async () => {
    if (currentStep === 1) {
      if (!uploadedFile) {
        toast.error('Carica un file prima di procedere');
        return;
      }
      // Call preview API when moving from step 1 to step 2
      setIsLoadingPreview(true);
      try {
        const result = await previewImport(uploadedFile);
        setPreview(result);
        setCurrentStep(2);
      } catch (err) {
        toast.error(
          err instanceof Error
            ? err.message
            : "Errore durante l'analisi del file"
        );
      } finally {
        setIsLoadingPreview(false);
      }
      return;
    }
    if (currentStep === 2) {
      const missing = columnMappings.filter(m => m.required && !m.yourColumn);
      if (missing.length > 0) {
        toast.error('Mappa tutti i campi obbligatori prima di procedere');
        return;
      }
    }
    if (currentStep < 3) setCurrentStep((currentStep + 1) as Step);
  };

  const handleBack = () => {
    if (currentStep > 1) setCurrentStep((currentStep - 1) as Step);
  };

  const [isImporting, setIsImporting] = useState(false);

  const handleImport = async () => {
    if (!uploadedFile) return;
    setIsImporting(true);
    try {
      // Build column mapping from user selections
      const mapping: Record<string, string> = {};
      for (const m of columnMappings) {
        if (m.yourColumn) {
          mapping[m.yourColumn.toLowerCase()] = m.ourField;
        }
      }

      const result = await importClients(
        uploadedFile,
        Object.keys(mapping).length > 0 ? mapping : undefined
      );

      if (result.error_count > 0) {
        toast.warning(
          `${result.success_count} clienti importati, ${result.error_count} errori.`
        );
      } else {
        toast.success(
          `${result.success_count} clienti importati con successo!`
        );
      }

      // Show post-import warnings about incomplete profiles
      if (result.warnings && result.warnings.clients_without_profile > 0) {
        toast.info(
          `${result.warnings.clients_without_profile} clienti necessitano del profilo aziendale per il matching normativo`,
          { duration: 8000 }
        );
      }

      setTimeout(() => router.push('/database-clienti'), 1500);
    } catch (err) {
      toast.error(
        err instanceof Error ? err.message : "Errore durante l'importazione"
      );
    } finally {
      setIsImporting(false);
    }
  };

  const updateMapping = (ourField: string, yourColumn: string) => {
    setColumnMappings(prev =>
      prev.map(m => (m.ourField === ourField ? { ...m, yourColumn } : m))
    );
  };

  return (
    <div className="min-h-screen bg-[#F8F5F1]">
      <motion.header
        initial={{ y: -20, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        className="bg-white border-b border-[#C4BDB4] sticky top-0 z-30"
      >
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center gap-4">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => router.push('/database-clienti')}
              className="text-[#2A5D67] hover:bg-[#F8F5F1]"
            >
              <ArrowLeft className="w-4 h-4 mr-2" />
              Indietro
            </Button>
            <div>
              <h1 className="text-2xl text-[#2A5D67]">Importa Clienti</h1>
              <p className="text-sm text-[#1E293B] opacity-70">
                Importa i tuoi clienti da file Excel, CSV o PDF
              </p>
            </div>
          </div>
        </div>
      </motion.header>

      <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <motion.div
          initial={{ y: 20, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          className="mb-8"
        >
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm text-[#1E293B]">
              Step {currentStep} di 3
            </span>
            <span className="text-sm text-[#1E293B]">
              {STEP_LABELS[currentStep]}
            </span>
          </div>
          <Progress value={(currentStep / 3) * 100} className="h-2" />
        </motion.div>

        <motion.div
          key={currentStep}
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          exit={{ opacity: 0, x: -20 }}
          className="bg-white rounded-lg shadow-sm border border-[#C4BDB4] overflow-hidden"
        >
          {currentStep === 1 && (
            <ClientImportUploadStep
              uploadedFile={uploadedFile}
              dragActive={dragActive}
              onDrag={handleDrag}
              onDrop={handleDrop}
              onFileChange={handleFileChange}
              onRemoveFile={() => {
                setUploadedFile(null);
                setPreview(null);
              }}
            />
          )}
          {currentStep === 2 && (
            <ClientImportMappingStep
              columnMappings={columnMappings}
              detectedColumns={preview?.detected_columns ?? []}
              onUpdateMapping={updateMapping}
            />
          )}
          {currentStep === 3 && preview && (
            <ClientImportPreviewStep
              rows={preview.rows}
              validRows={validRows}
              invalidRows={invalidRows}
            />
          )}

          <div className="px-8 pb-8 flex justify-between">
            <Button
              onClick={handleBack}
              variant="outline"
              disabled={currentStep === 1}
              className="border-[#C4BDB4] text-[#1E293B]"
            >
              Indietro
            </Button>
            {currentStep < 3 ? (
              <Button
                onClick={handleNext}
                disabled={isLoadingPreview}
                className="bg-[#2A5D67] hover:bg-[#1E293B] text-white"
              >
                {isLoadingPreview ? (
                  <>
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                    Analisi in corso...
                  </>
                ) : (
                  <>
                    Avanti
                    <ArrowRight className="w-4 h-4 ml-2" />
                  </>
                )}
              </Button>
            ) : (
              <Button
                onClick={handleImport}
                disabled={validRows === 0 || isImporting}
                className="bg-[#2A5D67] hover:bg-[#1E293B] text-white"
              >
                <Check className="w-4 h-4 mr-2" />
                {isImporting
                  ? 'Importazione in corso...'
                  : `Importa ${validRows} ${validRows === 1 ? 'Cliente' : 'Clienti'}`}
              </Button>
            )}
          </div>
        </motion.div>
      </div>
    </div>
  );
}
