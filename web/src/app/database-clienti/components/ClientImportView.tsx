'use client';

import { useState, useMemo } from 'react';
import {
  ArrowLeft,
  ArrowRight,
  Check,
  Loader2,
  SkipForward,
} from 'lucide-react';
import { motion } from 'motion/react';
import { useRouter } from 'next/navigation';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
import {
  importClients,
  previewImport,
  type ImportPreviewResponse,
  type SuggestedMapping,
} from '@/lib/api/clients';
import type {
  ColumnMapping,
  ProfileOverride,
  ProfileOverrides,
} from '../types';
import { ourFields } from '../data/constants';
import { ClientImportUploadStep } from './ClientImportUploadStep';
import { ClientImportMappingStep } from './ClientImportMappingStep';
import { ClientImportProfileStep } from './ClientImportProfileStep';
import { ClientImportPreviewStep } from './ClientImportPreviewStep';

/** Backend profile field names that indicate profile data is in the file. */
const PROFILE_BACKEND_FIELDS = [
  'regime_fiscale',
  'codice_ateco_principale',
  'data_inizio_attivita',
];

/** Map backend target field names to frontend ourField values. */
const BACKEND_TO_FRONTEND: Record<string, string> = {
  nome: 'denominazione',
  codice_fiscale: 'codiceFiscale',
  partita_iva: 'partitaIva',
  tipo_cliente: 'tipoSoggetto',
  comune: 'comune',
  provincia: 'provincia',
  indirizzo: 'indirizzo',
  cap: 'cap',
  regime_fiscale: 'regimeFiscale',
  codice_ateco_principale: 'codiceAteco',
  n_dipendenti: 'numeroDipendenti',
  ccnl_applicato: 'ccnlApplicato',
  data_inizio_attivita: 'dataInizioAttivita',
};

const AUTO_SKIP_CONFIDENCE = 0.7;

const EMPTY_PROFILE_OVERRIDE: ProfileOverride = {
  regime_fiscale: '',
  codice_ateco_principale: '',
  data_inizio_attivita: '',
  n_dipendenti: '',
  ccnl_applicato: '',
};

function applyAutoMappings(
  suggested: Record<string, SuggestedMapping>,
  detectedColumns: string[]
): ColumnMapping[] {
  return ourFields.map(field => {
    const backendField = Object.entries(BACKEND_TO_FRONTEND).find(
      ([, fe]) => fe === field.value
    )?.[0];
    const suggestion = backendField ? suggested[backendField] : undefined;
    const hasMatch =
      suggestion && detectedColumns.includes(suggestion.file_column);
    return {
      ourField: field.value,
      yourColumn: hasMatch ? suggestion.file_column : '',
      required: field.required,
      confidence: hasMatch ? suggestion.confidence : undefined,
      matchMethod: hasMatch ? suggestion.match_method : undefined,
    };
  });
}

/** Only check required fields the backend can auto-detect. */
const MAPPABLE_FIELDS = new Set(Object.values(BACKEND_TO_FRONTEND));

function canAutoSkip(mappings: ColumnMapping[]): boolean {
  return mappings
    .filter(m => m.required && MAPPABLE_FIELDS.has(m.ourField))
    .every(m => m.yourColumn && (m.confidence ?? 0) >= AUTO_SKIP_CONFIDENCE);
}

/** Check if all 3 required profile fields are mapped from file columns. */
function hasProfileFieldsMapped(
  suggested: Record<string, SuggestedMapping>
): boolean {
  return PROFILE_BACKEND_FIELDS.every(f => suggested[f]?.file_column);
}

/** Check if any profile overrides have data worth sending. */
function hasProfileOverrides(overrides: ProfileOverrides): boolean {
  return Object.values(overrides).some(
    o =>
      o.regime_fiscale !== '' ||
      o.codice_ateco_principale !== '' ||
      o.data_inizio_attivita !== ''
  );
}

export function ClientImportView() {
  const router = useRouter();
  const [currentStep, setCurrentStep] = useState(1);
  const [uploadedFile, setUploadedFile] = useState<File | null>(null);
  const [dragActive, setDragActive] = useState(false);
  const [isLoadingPreview, setIsLoadingPreview] = useState(false);
  const [preview, setPreview] = useState<ImportPreviewResponse | null>(null);
  const [autoMapped, setAutoMapped] = useState(false);
  const [showProfileStep, setShowProfileStep] = useState(false);
  const [profileOverrides, setProfileOverrides] = useState<ProfileOverrides>(
    {}
  );
  const [columnMappings, setColumnMappings] = useState<ColumnMapping[]>(
    ourFields.map(field => ({
      ourField: field.value,
      yourColumn: '',
      required: field.required,
    }))
  );

  const totalSteps = showProfileStep ? 4 : 3;
  const previewStep = showProfileStep ? 4 : 3;
  const profileStep = showProfileStep ? 3 : -1;

  const stepLabels = useMemo(() => {
    if (showProfileStep) {
      return {
        1: 'Carica File',
        2: 'Mappa Colonne',
        3: 'Profilo Aziendale',
        4: 'Anteprima e Conferma',
      } as Record<number, string>;
    }
    return {
      1: 'Carica File',
      2: 'Mappa Colonne',
      3: 'Anteprima e Conferma',
    } as Record<number, string>;
  }, [showProfileStep]);

  const validRows = preview?.valid_rows ?? 0;

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
      setAutoMapped(false);
      setShowProfileStep(false);
      setProfileOverrides({});
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
      setIsLoadingPreview(true);
      try {
        const result = await previewImport(uploadedFile);
        setPreview(result);

        const suggested = result.suggested_mappings ?? {};
        const newMappings = applyAutoMappings(
          suggested,
          result.detected_columns
        );
        setColumnMappings(newMappings);

        // Determine if profile step is needed
        const profileInFile = hasProfileFieldsMapped(suggested);
        setShowProfileStep(!profileInFile);

        if (canAutoSkip(newMappings)) {
          setAutoMapped(true);
          toast.success('Colonne riconosciute automaticamente', {
            description:
              'Puoi modificare la mappatura dalla schermata di anteprima.',
          });
          // Skip mapping — step 3 is either profile or preview depending on showProfileStep
          setCurrentStep(3);
        } else {
          const mappedCount = newMappings.filter(m => m.yourColumn).length;
          if (mappedCount > 0) {
            toast.info(
              `${mappedCount} colonne riconosciute automaticamente. Completa le rimanenti.`
            );
          }
          setCurrentStep(2);
        }
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

    if (currentStep < totalSteps) {
      setCurrentStep(currentStep + 1);
    }
  };

  const handleBack = () => {
    if (currentStep > 1) {
      setAutoMapped(false);
      setCurrentStep(currentStep - 1);
    }
  };

  const handleSkipProfile = () => {
    setProfileOverrides({});
    setCurrentStep(previewStep);
  };

  const updateProfileOverride = (
    codiceFiscale: string,
    field: keyof ProfileOverride,
    value: string
  ) => {
    setProfileOverrides(prev => ({
      ...prev,
      [codiceFiscale]: {
        ...(prev[codiceFiscale] ?? EMPTY_PROFILE_OVERRIDE),
        [field]: value,
      },
    }));
  };

  /** Build reversed column mapping: file_column -> backend_field for the profile step. */
  const buildColumnMapping = (): Record<string, string> => {
    const result: Record<string, string> = {};
    for (const m of columnMappings) {
      if (m.yourColumn) {
        const backendField = Object.entries(BACKEND_TO_FRONTEND).find(
          ([, fe]) => fe === m.ourField
        )?.[0];
        if (backendField) {
          result[m.yourColumn] = backendField;
        }
      }
    }
    return result;
  };

  const [isImporting, setIsImporting] = useState(false);

  const handleImport = async () => {
    if (!uploadedFile) return;
    setIsImporting(true);
    try {
      const mapping: Record<string, string> = {};
      for (const m of columnMappings) {
        if (m.yourColumn) {
          mapping[m.yourColumn.toLowerCase()] = m.ourField;
        }
      }

      // Only send profile overrides if any client has data filled
      const overrides = hasProfileOverrides(profileOverrides)
        ? profileOverrides
        : undefined;

      const result = await importClients(
        uploadedFile,
        Object.keys(mapping).length > 0 ? mapping : undefined,
        overrides
      );

      if (result.error_count > 0) {
        toast.warning(
          `${result.success_count} clienti importati, ${result.error_count} errori.`
        );
      } else {
        const profileMsg =
          result.profiles_created > 0
            ? ` (${result.profiles_created} profili aziendali creati)`
            : '';
        toast.success(
          `${result.success_count} clienti importati con successo!${profileMsg}`
        );
      }

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
      prev.map(m =>
        m.ourField === ourField
          ? { ...m, yourColumn, confidence: undefined, matchMethod: undefined }
          : m
      )
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
              Step {currentStep} di {totalSteps}
            </span>
            <span className="text-sm text-[#1E293B]">
              {stepLabels[currentStep]}
            </span>
          </div>
          <Progress value={(currentStep / totalSteps) * 100} className="h-2" />
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
                setAutoMapped(false);
                setShowProfileStep(false);
                setProfileOverrides({});
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
          {currentStep === profileStep && preview && (
            <ClientImportProfileStep
              rows={preview.rows}
              profileOverrides={profileOverrides}
              onUpdate={updateProfileOverride}
              columnMapping={buildColumnMapping()}
            />
          )}
          {currentStep === previewStep && preview && (
            <>
              {autoMapped && (
                <div className="mx-8 mt-6 p-3 bg-emerald-50 border border-emerald-200 rounded-lg flex items-center justify-between">
                  <span className="text-sm text-emerald-800">
                    Mappatura colonne confermata automaticamente
                  </span>
                  <Button
                    variant="link"
                    size="sm"
                    onClick={() => {
                      setAutoMapped(false);
                      setCurrentStep(2);
                    }}
                    className="text-emerald-700 underline text-sm h-auto p-0"
                  >
                    Modifica mappatura
                  </Button>
                </div>
              )}
              <ClientImportPreviewStep
                rows={preview.rows}
                validRows={validRows}
                invalidRows={preview?.invalid_rows ?? 0}
              />
            </>
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

            <div className="flex gap-3">
              {currentStep === profileStep && (
                <Button
                  onClick={handleSkipProfile}
                  variant="outline"
                  className="border-[#C4BDB4] text-[#1E293B]"
                >
                  <SkipForward className="w-4 h-4 mr-2" />
                  Salta
                </Button>
              )}

              {currentStep < previewStep ? (
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
          </div>
        </motion.div>
      </div>
    </div>
  );
}
