"use client";

import React, { useState } from "react";
import { motion } from "motion/react";
import {
  ArrowLeft,
  Upload,
  FileSpreadsheet,
  ArrowRight,
  Check,
  AlertCircle,
  X,
} from "lucide-react";
import { Button } from "./ui/button";
import { Progress } from "./ui/progress";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "./ui/select";
import { Badge } from "./ui/badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "./ui/table";
import { toast } from "sonner@2.0.3";

interface ClientImportPageProps {
  onBackToClients: () => void;
}

type Step = 1 | 2 | 3;

interface ColumnMapping {
  ourField: string;
  yourColumn: string;
  required: boolean;
}

interface ImportPreviewRow {
  denominazione: string;
  codiceFiscale: string;
  tipoSoggetto: string;
  regimeFiscale: string;
  codiceAteco: string;
  isValid: boolean;
  errors: string[];
}

const ourFields = [
  {
    value: "denominazione",
    label: "Denominazione / Ragione Sociale",
    required: true,
  },
  { value: "codiceFiscale", label: "Codice Fiscale", required: true },
  { value: "partitaIva", label: "Partita IVA", required: false },
  { value: "tipoSoggetto", label: "Tipo Soggetto", required: true },
  { value: "regimeFiscale", label: "Regime Fiscale", required: true },
  { value: "codiceAteco", label: "Codice ATECO", required: true },
  { value: "indirizzo", label: "Indirizzo", required: false },
  { value: "cap", label: "CAP", required: false },
  { value: "comune", label: "Comune", required: false },
  { value: "provincia", label: "Provincia", required: false },
  { value: "numeroDipendenti", label: "Numero Dipendenti", required: false },
  { value: "ccnlApplicato", label: "CCNL Applicato", required: false },
];

const mockExcelColumns = [
  "Ragione Sociale",
  "CF",
  "P.IVA",
  "Tipo",
  "Regime",
  "ATECO",
  "Via",
  "CAP",
  "Città",
  "Prov",
  "Dipendenti",
  "CCNL",
];

const mockPreviewData: ImportPreviewRow[] = [
  {
    denominazione: "Studio Legale Associato Rossi",
    codiceFiscale: "RSSMRA70A01F205X",
    tipoSoggetto: "societa_persone",
    regimeFiscale: "ordinario",
    codiceAteco: "69.10.10",
    isValid: true,
    errors: [],
  },
  {
    denominazione: "Bianchi Maria",
    codiceFiscale: "BNCMRA85B45H501Y",
    tipoSoggetto: "persona_fisica",
    regimeFiscale: "forfettario",
    codiceAteco: "62.01.00",
    isValid: true,
    errors: [],
  },
  {
    denominazione: "Verdi S.r.l.",
    codiceFiscale: "12345678901",
    tipoSoggetto: "societa_capitali",
    regimeFiscale: "ordinario",
    codiceAteco: "47.11.30",
    isValid: true,
    errors: [],
  },
  {
    denominazione: "Neri Giuseppe",
    codiceFiscale: "INVALID",
    tipoSoggetto: "ditta_individuale",
    regimeFiscale: "semplificato",
    codiceAteco: "",
    isValid: false,
    errors: ["Codice fiscale non valido", "Codice ATECO mancante"],
  },
  {
    denominazione: "",
    codiceFiscale: "GLLMRC80A01F205Z",
    tipoSoggetto: "persona_fisica",
    regimeFiscale: "",
    codiceAteco: "43.21.01",
    isValid: false,
    errors: ["Denominazione mancante", "Regime fiscale mancante"],
  },
];

export function ClientImportPage({ onBackToClients }: ClientImportPageProps) {
  const [currentStep, setCurrentStep] = useState<Step>(1);
  const [uploadedFile, setUploadedFile] = useState<File | null>(null);
  const [dragActive, setDragActive] = useState(false);
  const [columnMappings, setColumnMappings] = useState<ColumnMapping[]>(
    ourFields.map((field) => ({
      ourField: field.value,
      yourColumn: "",
      required: field.required,
    })),
  );

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFile(e.dataTransfer.files[0]);
    }
  };

  const handleFileInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      handleFile(e.target.files[0]);
    }
  };

  const handleFile = (file: File) => {
    const validTypes = [
      "application/vnd.ms-excel",
      "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
      "text/csv",
    ];
    if (
      validTypes.includes(file.type) ||
      file.name.endsWith(".csv") ||
      file.name.endsWith(".xlsx")
    ) {
      setUploadedFile(file);
      toast.success(`File "${file.name}" caricato con successo`);
    } else {
      toast.error(
        "Formato file non supportato. Usa Excel (.xlsx) o CSV (.csv)",
      );
    }
  };

  const handleNext = () => {
    if (currentStep === 1 && !uploadedFile) {
      toast.error("Carica un file prima di procedere");
      return;
    }
    if (currentStep === 2) {
      const missingMappings = columnMappings.filter(
        (m) => m.required && !m.yourColumn,
      );
      if (missingMappings.length > 0) {
        toast.error("Mappa tutti i campi obbligatori prima di procedere");
        return;
      }
    }
    if (currentStep < 3) {
      setCurrentStep((currentStep + 1) as Step);
    }
  };

  const handleBack = () => {
    if (currentStep > 1) {
      setCurrentStep((currentStep - 1) as Step);
    }
  };

  const handleImport = () => {
    const validRows = mockPreviewData.filter((row) => row.isValid).length;
    toast.success(`${validRows} clienti importati con successo!`);
    setTimeout(() => {
      onBackToClients();
    }, 1500);
  };

  const updateMapping = (ourField: string, yourColumn: string) => {
    setColumnMappings((prev) =>
      prev.map((mapping) =>
        mapping.ourField === ourField ? { ...mapping, yourColumn } : mapping,
      ),
    );
  };

  const validRows = mockPreviewData.filter((row) => row.isValid).length;
  const invalidRows = mockPreviewData.length - validRows;

  return (
    <div className="min-h-screen bg-[#F8F5F1]">
      {/* Header */}
      <motion.header
        initial={{ y: -20, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        className="bg-white border-b border-[#C4BDB4] sticky top-0 z-30"
      >
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <Button
                variant="ghost"
                size="sm"
                onClick={onBackToClients}
                className="text-[#2A5D67] hover:bg-[#F8F5F1]"
              >
                <ArrowLeft className="w-4 h-4 mr-2" />
                Indietro
              </Button>
              <div>
                <h1 className="text-2xl text-[#2A5D67]">Importa Clienti</h1>
                <p className="text-sm text-[#1E293B] opacity-70">
                  Importa i tuoi clienti da file Excel o CSV
                </p>
              </div>
            </div>
          </div>
        </div>
      </motion.header>

      <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Progress Bar */}
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
              {currentStep === 1 && "Carica File"}
              {currentStep === 2 && "Mappa Colonne"}
              {currentStep === 3 && "Anteprima e Conferma"}
            </span>
          </div>
          <Progress value={(currentStep / 3) * 100} className="h-2" />
        </motion.div>

        {/* Step Content */}
        <motion.div
          key={currentStep}
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          exit={{ opacity: 0, x: -20 }}
          className="bg-white rounded-lg shadow-sm border border-[#C4BDB4] overflow-hidden"
        >
          {/* Step 1: File Upload */}
          {currentStep === 1 && (
            <div className="p-8">
              <h2 className="text-xl text-[#2A5D67] mb-6">
                Carica File Excel o CSV
              </h2>
              <div
                onDragEnter={handleDrag}
                onDragLeave={handleDrag}
                onDragOver={handleDrag}
                onDrop={handleDrop}
                className={`border-2 border-dashed rounded-lg p-12 text-center transition-colors ${dragActive ? "border-[#2A5D67] bg-[#2A5D67]/5" : "border-[#C4BDB4] bg-[#F8F5F1]"}`}
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
                      onClick={() => setUploadedFile(null)}
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
                      Trascina qui il file Excel o CSV
                    </h3>
                    <p className="text-sm text-[#1E293B] opacity-70 mb-6">
                      Oppure clicca per selezionare un file dal tuo computer
                    </p>
                    <label>
                      <input
                        type="file"
                        accept=".xlsx,.xls,.csv"
                        onChange={handleFileInput}
                        className="hidden"
                      />
                      <Button
                        as="span"
                        className="bg-[#2A5D67] hover:bg-[#1E293B] text-white cursor-pointer"
                      >
                        <FileSpreadsheet className="w-4 h-4 mr-2" />
                        Sfoglia
                      </Button>
                    </label>
                    <p className="text-xs text-[#1E293B] opacity-70 mt-4">
                      Formati supportati: .xlsx, .xls, .csv
                    </p>
                  </>
                )}
              </div>
            </div>
          )}

          {/* Step 2: Column Mapping */}
          {currentStep === 2 && (
            <div className="p-8">
              <h2 className="text-xl text-[#2A5D67] mb-6">Mappa le Colonne</h2>
              <p className="text-sm text-[#1E293B] opacity-70 mb-6">
                Abbina i campi del nostro sistema alle colonne del tuo file
              </p>
              <Table>
                <TableHeader>
                  <TableRow className="bg-[#F8F5F1] hover:bg-[#F8F5F1]">
                    <TableHead className="text-[#2A5D67]">
                      Campo Sistema
                    </TableHead>
                    <TableHead className="text-[#2A5D67]">→</TableHead>
                    <TableHead className="text-[#2A5D67]">
                      Colonna File
                    </TableHead>
                    <TableHead className="text-[#2A5D67]">
                      Obbligatorio
                    </TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {ourFields.map((field) => {
                    const mapping = columnMappings.find(
                      (m) => m.ourField === field.value,
                    );
                    return (
                      <TableRow
                        key={field.value}
                        className="border-b border-[#C4BDB4]"
                      >
                        <TableCell className="text-[#1E293B]">
                          {field.label}
                        </TableCell>
                        <TableCell>
                          <ArrowRight className="w-4 h-4 text-[#C4BDB4]" />
                        </TableCell>
                        <TableCell>
                          <Select
                            value={mapping?.yourColumn || ""}
                            onValueChange={(value) =>
                              updateMapping(field.value, value)
                            }
                          >
                            <SelectTrigger
                              className={`bg-[#F8F5F1] ${field.required && !mapping?.yourColumn ? "border-red-500" : ""}`}
                            >
                              <SelectValue placeholder="Seleziona colonna" />
                            </SelectTrigger>
                            <SelectContent>
                              <SelectItem value="">Nessuna</SelectItem>
                              {mockExcelColumns.map((col) => (
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
                              Sì
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
          )}

          {/* Step 3: Preview and Validation */}
          {currentStep === 3 && (
            <div className="p-8">
              <div className="flex items-center justify-between mb-6">
                <div>
                  <h2 className="text-xl text-[#2A5D67]">
                    Anteprima Importazione
                  </h2>
                  <p className="text-sm text-[#1E293B] opacity-70 mt-1">
                    Verifica i dati prima di importare
                  </p>
                </div>
                <div className="flex gap-4">
                  <div className="text-right">
                    <div className="flex items-center gap-2">
                      <Check className="w-5 h-5 text-green-600" />
                      <span className="text-2xl text-green-600">
                        {validRows}
                      </span>
                    </div>
                    <p className="text-xs text-[#1E293B] opacity-70">Validi</p>
                  </div>
                  <div className="text-right">
                    <div className="flex items-center gap-2">
                      <AlertCircle className="w-5 h-5 text-red-600" />
                      <span className="text-2xl text-red-600">
                        {invalidRows}
                      </span>
                    </div>
                    <p className="text-xs text-[#1E293B] opacity-70">Errori</p>
                  </div>
                </div>
              </div>
              <div className="overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow className="bg-[#F8F5F1] hover:bg-[#F8F5F1]">
                      <TableHead className="text-[#2A5D67]">Stato</TableHead>
                      <TableHead className="text-[#2A5D67]">
                        Denominazione
                      </TableHead>
                      <TableHead className="text-[#2A5D67]">
                        Cod. Fiscale
                      </TableHead>
                      <TableHead className="text-[#2A5D67]">Tipo</TableHead>
                      <TableHead className="text-[#2A5D67]">Regime</TableHead>
                      <TableHead className="text-[#2A5D67]">ATECO</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {mockPreviewData.map((row, index) => (
                      <TableRow
                        key={index}
                        className={`border-b border-[#C4BDB4] ${!row.isValid ? "bg-red-50" : ""}`}
                      >
                        <TableCell>
                          {row.isValid ? (
                            <Check className="w-5 h-5 text-green-600" />
                          ) : (
                            <AlertCircle className="w-5 h-5 text-red-600" />
                          )}
                        </TableCell>
                        <TableCell
                          className={
                            !row.denominazione
                              ? "text-red-600"
                              : "text-[#1E293B]"
                          }
                        >
                          {row.denominazione || "(vuoto)"}
                        </TableCell>
                        <TableCell
                          className={
                            row.codiceFiscale === "INVALID"
                              ? "text-red-600 font-mono"
                              : "text-[#1E293B] font-mono"
                          }
                        >
                          {row.codiceFiscale}
                        </TableCell>
                        <TableCell className="text-[#1E293B] text-xs">
                          {row.tipoSoggetto}
                        </TableCell>
                        <TableCell
                          className={
                            !row.regimeFiscale
                              ? "text-red-600"
                              : "text-[#1E293B]"
                          }
                        >
                          {row.regimeFiscale || "(vuoto)"}
                        </TableCell>
                        <TableCell
                          className={
                            !row.codiceAteco
                              ? "text-red-600 font-mono"
                              : "text-[#1E293B] font-mono"
                          }
                        >
                          {row.codiceAteco || "(vuoto)"}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
              {invalidRows > 0 && (
                <div className="mt-6 p-4 bg-red-50 rounded-lg border border-red-200">
                  <div className="flex items-start gap-3">
                    <AlertCircle className="w-5 h-5 text-red-600 mt-0.5 flex-shrink-0" />
                    <div>
                      <h4 className="text-sm text-red-900 mb-2">
                        {invalidRows} righe con errori non verranno importate
                      </h4>
                      <ul className="text-sm text-red-800 space-y-1">
                        <li>Verifica i campi evidenziati in rosso</li>
                        <li>
                          Correggi il file e ricaricalo per importare tutte le
                          righe
                        </li>
                      </ul>
                    </div>
                  </div>
                </div>
              )}
              {validRows > 0 && (
                <div className="mt-4 p-4 bg-green-50 rounded-lg border border-green-200">
                  <div className="flex items-center gap-3">
                    <Check className="w-5 h-5 text-green-600 flex-shrink-0" />
                    <p className="text-sm text-green-900">
                      {validRows}{" "}
                      {validRows === 1 ? "cliente pronto" : "clienti pronti"}{" "}
                      per l'importazione
                    </p>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Navigation Buttons */}
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
                className="bg-[#2A5D67] hover:bg-[#1E293B] text-white"
              >
                Avanti
                <ArrowRight className="w-4 h-4 ml-2" />
              </Button>
            ) : (
              <Button
                onClick={handleImport}
                disabled={validRows === 0}
                className="bg-[#2A5D67] hover:bg-[#1E293B] text-white"
              >
                <Check className="w-4 h-4 mr-2" />
                Importa {validRows} {validRows === 1 ? "Cliente" : "Clienti"}
              </Button>
            )}
          </div>
        </motion.div>
      </div>
    </div>
  );
}
