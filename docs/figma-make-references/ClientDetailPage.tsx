"use client";

import React, { useState } from "react";
import { motion } from "motion/react";
import {
  ArrowLeft,
  Save,
  X,
  Plus,
  Trash2,
  Building2,
  FileText,
  Users,
  Home,
  Tag,
} from "lucide-react";
import { Button } from "./ui/button";
import { Input } from "./ui/input";
import { Label } from "./ui/label";
import { Textarea } from "./ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "./ui/select";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "./ui/tabs";
import { Badge } from "./ui/badge";
import { Checkbox } from "./ui/checkbox";
import { toast } from "sonner@2.0.3";

interface ClientDetailPageProps {
  onBackToClients: () => void;
  clientId: string;
}

interface Immobile {
  id: string;
  tipologia: string;
  indirizzo: string;
  comune: string;
  renditaCatastale: string;
}

interface FormData {
  // Tab 1 - Anagrafica
  denominazione: string;
  codiceFiscale: string;
  partitaIva: string;
  tipoSoggetto: string;
  indirizzo: string;
  cap: string;
  comune: string;
  provincia: string;

  // Tab 2 - Dati Fiscali
  regimeFiscale: string;
  codiceAteco: string;
  dataInizioAttivita: string;
  posizioneAgenziaEntrate: string;
  haCartelleEsattoriali: boolean;

  // Tab 3 - Lavoro
  numeroDipendenti: string;
  ccnlApplicato: string;
  haApprendisti: boolean;
  haLavoratoriStagionali: boolean;

  // Tab 4 - Immobili
  immobili: Immobile[];

  // Tab 5 - Tags & Note
  tags: string[];
  note: string;
}

const initialFormData: FormData = {
  denominazione: "",
  codiceFiscale: "",
  partitaIva: "",
  tipoSoggetto: "",
  indirizzo: "",
  cap: "",
  comune: "",
  provincia: "",
  regimeFiscale: "",
  codiceAteco: "",
  dataInizioAttivita: "",
  posizioneAgenziaEntrate: "",
  haCartelleEsattoriali: false,
  numeroDipendenti: "0",
  ccnlApplicato: "",
  haApprendisti: false,
  haLavoratoriStagionali: false,
  immobili: [],
  tags: [],
  note: "",
};

const mockExistingClient: FormData = {
  denominazione: "Studio Legale Associato Rossi",
  codiceFiscale: "RSSMRA70A01F205X",
  partitaIva: "12345678901",
  tipoSoggetto: "societa_persone",
  indirizzo: "Via Roma 123",
  cap: "20121",
  comune: "Milano",
  provincia: "MI",
  regimeFiscale: "ordinario",
  codiceAteco: "69.10.10",
  dataInizioAttivita: "2015-03-15",
  posizioneAgenziaEntrate: "DIR LOMBARDIA - UFF MILANO 1",
  haCartelleEsattoriali: false,
  numeroDipendenti: "8",
  ccnlApplicato: "CCNL Studi Professionali",
  haApprendisti: true,
  haLavoratoriStagionali: false,
  immobili: [
    {
      id: "1",
      tipologia: "Ufficio",
      indirizzo: "Via Roma 123",
      comune: "Milano",
      renditaCatastale: "€ 2.450,00",
    },
  ],
  tags: ["Priorità Alta", "Fiscale", "Servizi Legali"],
  note: "Cliente storico, rinnovo contratto annuale a marzo. Richiede assistenza fiscale completa e consulenza ordinistica.",
};

export function ClientDetailPage({
  onBackToClients,
  clientId,
}: ClientDetailPageProps) {
  const isNewClient = clientId === "new";
  const [formData, setFormData] = useState<FormData>(
    isNewClient ? initialFormData : mockExistingClient,
  );
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [newTag, setNewTag] = useState("");
  const [activeTab, setActiveTab] = useState("anagrafica");

  const updateField = (field: keyof FormData, value: any) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
    if (errors[field]) {
      setErrors((prev) => {
        const newErrors = { ...prev };
        delete newErrors[field];
        return newErrors;
      });
    }
  };

  const validateForm = () => {
    const newErrors: Record<string, string> = {};
    if (!formData.denominazione.trim()) {
      newErrors.denominazione = "Denominazione obbligatoria";
    }
    if (!formData.codiceFiscale.trim()) {
      newErrors.codiceFiscale = "Codice fiscale obbligatorio";
    } else if (
      !/^[A-Z0-9]{11,16}$/.test(formData.codiceFiscale.toUpperCase())
    ) {
      newErrors.codiceFiscale = "Formato codice fiscale non valido";
    }
    if (!formData.tipoSoggetto) {
      newErrors.tipoSoggetto = "Seleziona tipo soggetto";
    }
    if (!formData.regimeFiscale) {
      newErrors.regimeFiscale = "Seleziona regime fiscale";
    }
    if (!formData.codiceAteco.trim()) {
      newErrors.codiceAteco = "Codice ATECO obbligatorio";
    }
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSave = () => {
    if (!validateForm()) {
      toast.error("Correggi gli errori nel form prima di salvare");
      return;
    }
    const action = isNewClient ? "aggiunto" : "aggiornato";
    toast.success(`Cliente "${formData.denominazione}" ${action} con successo`);
    setTimeout(() => onBackToClients(), 1000);
  };

  const handleAddTag = () => {
    if (newTag.trim() && !formData.tags.includes(newTag.trim())) {
      updateField("tags", [...formData.tags, newTag.trim()]);
      setNewTag("");
    }
  };

  const handleRemoveTag = (tagToRemove: string) => {
    updateField(
      "tags",
      formData.tags.filter((tag) => tag !== tagToRemove),
    );
  };

  const handleAddImmobile = () => {
    const newImmobile: Immobile = {
      id: Date.now().toString(),
      tipologia: "",
      indirizzo: "",
      comune: "",
      renditaCatastale: "",
    };
    updateField("immobili", [...formData.immobili, newImmobile]);
  };

  const handleRemoveImmobile = (id: string) => {
    updateField(
      "immobili",
      formData.immobili.filter((imm) => imm.id !== id),
    );
  };

  const handleUpdateImmobile = (
    id: string,
    field: keyof Immobile,
    value: string,
  ) => {
    updateField(
      "immobili",
      formData.immobili.map((imm) =>
        imm.id === id ? { ...imm, [field]: value } : imm,
      ),
    );
  };

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
                <h1 className="text-2xl text-[#2A5D67]">
                  {isNewClient ? "Nuovo Cliente" : "Modifica Cliente"}
                </h1>
                <p className="text-sm text-[#1E293B] opacity-70">
                  {isNewClient
                    ? "Inserisci i dati del nuovo cliente"
                    : "Aggiorna le informazioni del cliente"}
                </p>
              </div>
            </div>
            <div className="flex gap-2">
              <Button
                variant="outline"
                onClick={onBackToClients}
                className="border-[#C4BDB4] text-[#1E293B] hover:bg-[#F8F5F1]"
              >
                <X className="w-4 h-4 mr-2" />
                Annulla
              </Button>
              <Button
                onClick={handleSave}
                className="bg-[#2A5D67] hover:bg-[#1E293B] text-white"
              >
                <Save className="w-4 h-4 mr-2" />
                Salva
              </Button>
            </div>
          </div>
        </div>
      </motion.header>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <motion.div
          initial={{ y: 20, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          transition={{ delay: 0.1 }}
          className="bg-white rounded-lg shadow-sm border border-[#C4BDB4] overflow-hidden"
        >
          <Tabs
            value={activeTab}
            onValueChange={setActiveTab}
            className="w-full"
          >
            <TabsList className="w-full justify-start bg-[#F8F5F1] border-b border-[#C4BDB4] rounded-none h-auto p-0">
              <TabsTrigger
                value="anagrafica"
                className="data-[state=active]:bg-white data-[state=active]:border-b-2 data-[state=active]:border-[#2A5D67] rounded-none py-3 px-6"
              >
                <Building2 className="w-4 h-4 mr-2" />
                Anagrafica
              </TabsTrigger>
              <TabsTrigger
                value="fiscali"
                className="data-[state=active]:bg-white data-[state=active]:border-b-2 data-[state=active]:border-[#2A5D67] rounded-none py-3 px-6"
              >
                <FileText className="w-4 h-4 mr-2" />
                Dati Fiscali
              </TabsTrigger>
              <TabsTrigger
                value="lavoro"
                className="data-[state=active]:bg-white data-[state=active]:border-b-2 data-[state=active]:border-[#2A5D67] rounded-none py-3 px-6"
              >
                <Users className="w-4 h-4 mr-2" />
                Lavoro
              </TabsTrigger>
              <TabsTrigger
                value="immobili"
                className="data-[state=active]:bg-white data-[state=active]:border-b-2 data-[state=active]:border-[#2A5D67] rounded-none py-3 px-6"
              >
                <Home className="w-4 h-4 mr-2" />
                Immobili
              </TabsTrigger>
              <TabsTrigger
                value="tags"
                className="data-[state=active]:bg-white data-[state=active]:border-b-2 data-[state=active]:border-[#2A5D67] rounded-none py-3 px-6"
              >
                <Tag className="w-4 h-4 mr-2" />
                Tags & Note
              </TabsTrigger>
            </TabsList>

            {/* Tab 1: Anagrafica */}
            <TabsContent value="anagrafica" className="p-6">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div className="md:col-span-2">
                  <Label htmlFor="denominazione">
                    Denominazione / Ragione Sociale *
                  </Label>
                  <Input
                    id="denominazione"
                    value={formData.denominazione}
                    onChange={(e) =>
                      updateField("denominazione", e.target.value)
                    }
                    className={`mt-1 bg-[#F8F5F1] ${errors.denominazione ? "border-red-500" : ""}`}
                    placeholder="Es. Studio Legale Rossi"
                  />
                  {errors.denominazione && (
                    <p className="text-red-500 text-sm mt-1">
                      {errors.denominazione}
                    </p>
                  )}
                </div>
                <div>
                  <Label htmlFor="codiceFiscale">Codice Fiscale *</Label>
                  <Input
                    id="codiceFiscale"
                    value={formData.codiceFiscale}
                    onChange={(e) =>
                      updateField("codiceFiscale", e.target.value.toUpperCase())
                    }
                    className={`mt-1 bg-[#F8F5F1] font-mono ${errors.codiceFiscale ? "border-red-500" : ""}`}
                    placeholder="RSSMRA70A01F205X"
                    maxLength={16}
                  />
                  {errors.codiceFiscale && (
                    <p className="text-red-500 text-sm mt-1">
                      {errors.codiceFiscale}
                    </p>
                  )}
                </div>
                <div>
                  <Label htmlFor="partitaIva">Partita IVA</Label>
                  <Input
                    id="partitaIva"
                    value={formData.partitaIva}
                    onChange={(e) => updateField("partitaIva", e.target.value)}
                    className="mt-1 bg-[#F8F5F1] font-mono"
                    placeholder="12345678901"
                    maxLength={11}
                  />
                </div>
                <div>
                  <Label htmlFor="tipoSoggetto">Tipo Soggetto *</Label>
                  <Select
                    value={formData.tipoSoggetto}
                    onValueChange={(value) =>
                      updateField("tipoSoggetto", value)
                    }
                  >
                    <SelectTrigger
                      className={`mt-1 bg-[#F8F5F1] ${errors.tipoSoggetto ? "border-red-500" : ""}`}
                    >
                      <SelectValue placeholder="Seleziona tipo" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="persona_fisica">
                        Persona Fisica
                      </SelectItem>
                      <SelectItem value="ditta_individuale">
                        Ditta Individuale
                      </SelectItem>
                      <SelectItem value="societa_persone">
                        Società di Persone
                      </SelectItem>
                      <SelectItem value="societa_capitali">
                        Società di Capitali
                      </SelectItem>
                      <SelectItem value="ente_no_profit">
                        Ente No Profit
                      </SelectItem>
                    </SelectContent>
                  </Select>
                  {errors.tipoSoggetto && (
                    <p className="text-red-500 text-sm mt-1">
                      {errors.tipoSoggetto}
                    </p>
                  )}
                </div>
                <div className="md:col-span-2">
                  <Label htmlFor="indirizzo">Indirizzo</Label>
                  <Input
                    id="indirizzo"
                    value={formData.indirizzo}
                    onChange={(e) => updateField("indirizzo", e.target.value)}
                    className="mt-1 bg-[#F8F5F1]"
                    placeholder="Via, Piazza, ecc."
                  />
                </div>
                <div>
                  <Label htmlFor="cap">CAP</Label>
                  <Input
                    id="cap"
                    value={formData.cap}
                    onChange={(e) => updateField("cap", e.target.value)}
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
                    onChange={(e) => updateField("comune", e.target.value)}
                    className="mt-1 bg-[#F8F5F1]"
                    placeholder="Milano"
                  />
                </div>
                <div>
                  <Label htmlFor="provincia">Provincia</Label>
                  <Input
                    id="provincia"
                    value={formData.provincia}
                    onChange={(e) =>
                      updateField("provincia", e.target.value.toUpperCase())
                    }
                    className="mt-1 bg-[#F8F5F1]"
                    placeholder="MI"
                    maxLength={2}
                  />
                </div>
              </div>
            </TabsContent>

            {/* Tab 2: Dati Fiscali */}
            <TabsContent value="fiscali" className="p-6">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div>
                  <Label htmlFor="regimeFiscale">Regime Fiscale *</Label>
                  <Select
                    value={formData.regimeFiscale}
                    onValueChange={(value) =>
                      updateField("regimeFiscale", value)
                    }
                  >
                    <SelectTrigger
                      className={`mt-1 bg-[#F8F5F1] ${errors.regimeFiscale ? "border-red-500" : ""}`}
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
                    <p className="text-red-500 text-sm mt-1">
                      {errors.regimeFiscale}
                    </p>
                  )}
                </div>
                <div>
                  <Label htmlFor="codiceAteco">Codice ATECO *</Label>
                  <Input
                    id="codiceAteco"
                    value={formData.codiceAteco}
                    onChange={(e) => updateField("codiceAteco", e.target.value)}
                    className={`mt-1 bg-[#F8F5F1] font-mono ${errors.codiceAteco ? "border-red-500" : ""}`}
                    placeholder="69.10.10"
                  />
                  {errors.codiceAteco && (
                    <p className="text-red-500 text-sm mt-1">
                      {errors.codiceAteco}
                    </p>
                  )}
                  <p className="text-sm text-[#1E293B] opacity-70 mt-1">
                    Inserisci il codice o cerca per descrizione
                  </p>
                </div>
                <div>
                  <Label htmlFor="dataInizioAttivita">
                    Data Inizio Attività
                  </Label>
                  <Input
                    id="dataInizioAttivita"
                    type="date"
                    value={formData.dataInizioAttivita}
                    onChange={(e) =>
                      updateField("dataInizioAttivita", e.target.value)
                    }
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
                    onChange={(e) =>
                      updateField("posizioneAgenziaEntrate", e.target.value)
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
                      onCheckedChange={(checked) =>
                        updateField("haCartelleEsattoriali", checked)
                      }
                    />
                    <Label
                      htmlFor="haCartelleEsattoriali"
                      className="cursor-pointer"
                    >
                      Ha cartelle esattoriali pendenti
                    </Label>
                  </div>
                </div>
              </div>
            </TabsContent>

            {/* Tab 3: Lavoro */}
            <TabsContent value="lavoro" className="p-6">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div>
                  <Label htmlFor="numeroDipendenti">Numero Dipendenti</Label>
                  <Input
                    id="numeroDipendenti"
                    type="number"
                    min="0"
                    value={formData.numeroDipendenti}
                    onChange={(e) =>
                      updateField("numeroDipendenti", e.target.value)
                    }
                    className="mt-1 bg-[#F8F5F1]"
                  />
                </div>
                <div>
                  <Label htmlFor="ccnlApplicato">CCNL Applicato</Label>
                  <Select
                    value={formData.ccnlApplicato}
                    onValueChange={(value) =>
                      updateField("ccnlApplicato", value)
                    }
                  >
                    <SelectTrigger className="mt-1 bg-[#F8F5F1]">
                      <SelectValue placeholder="Seleziona CCNL" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="CCNL Commercio">
                        CCNL Commercio
                      </SelectItem>
                      <SelectItem value="CCNL Metalmeccanici">
                        CCNL Metalmeccanici
                      </SelectItem>
                      <SelectItem value="CCNL Edilizia">
                        CCNL Edilizia
                      </SelectItem>
                      <SelectItem value="CCNL Studi Professionali">
                        CCNL Studi Professionali
                      </SelectItem>
                      <SelectItem value="CCNL Terziario">
                        CCNL Terziario
                      </SelectItem>
                      <SelectItem value="Altro">Altro</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="md:col-span-2 space-y-4">
                  <div className="flex items-center space-x-2">
                    <Checkbox
                      id="haApprendisti"
                      checked={formData.haApprendisti}
                      onCheckedChange={(checked) =>
                        updateField("haApprendisti", checked)
                      }
                    />
                    <Label htmlFor="haApprendisti" className="cursor-pointer">
                      Ha contratti di apprendistato
                    </Label>
                  </div>
                  <div className="flex items-center space-x-2">
                    <Checkbox
                      id="haLavoratoriStagionali"
                      checked={formData.haLavoratoriStagionali}
                      onCheckedChange={(checked) =>
                        updateField("haLavoratoriStagionali", checked)
                      }
                    />
                    <Label
                      htmlFor="haLavoratoriStagionali"
                      className="cursor-pointer"
                    >
                      Ha lavoratori stagionali
                    </Label>
                  </div>
                </div>
              </div>
            </TabsContent>

            {/* Tab 4: Immobili */}
            <TabsContent value="immobili" className="p-6">
              <div className="space-y-4">
                <div className="flex justify-between items-center">
                  <h3 className="text-[#1E293B]">Immobili di Proprietà</h3>
                  <Button
                    onClick={handleAddImmobile}
                    variant="outline"
                    size="sm"
                    className="border-[#2A5D67] text-[#2A5D67] hover:bg-[#2A5D67] hover:text-white"
                  >
                    <Plus className="w-4 h-4 mr-2" />
                    Aggiungi Immobile
                  </Button>
                </div>
                {formData.immobili.length === 0 ? (
                  <div className="text-center py-8 bg-[#F8F5F1] rounded-lg">
                    <p className="text-[#1E293B] opacity-70">
                      Nessun immobile registrato
                    </p>
                  </div>
                ) : (
                  <div className="space-y-4">
                    {formData.immobili.map((immobile, index) => (
                      <motion.div
                        key={immobile.id}
                        initial={{ opacity: 0, y: 10 }}
                        animate={{ opacity: 1, y: 0 }}
                        className="p-4 border border-[#C4BDB4] rounded-lg bg-[#F8F5F1]"
                      >
                        <div className="flex justify-between items-start mb-4">
                          <h4 className="text-[#1E293B]">
                            Immobile {index + 1}
                          </h4>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => handleRemoveImmobile(immobile.id)}
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
                              onValueChange={(value) =>
                                handleUpdateImmobile(
                                  immobile.id,
                                  "tipologia",
                                  value,
                                )
                              }
                            >
                              <SelectTrigger className="mt-1 bg-white">
                                <SelectValue placeholder="Seleziona tipologia" />
                              </SelectTrigger>
                              <SelectContent>
                                <SelectItem value="Abitazione">
                                  Abitazione
                                </SelectItem>
                                <SelectItem value="Ufficio">Ufficio</SelectItem>
                                <SelectItem value="Negozio">Negozio</SelectItem>
                                <SelectItem value="Magazzino">
                                  Magazzino
                                </SelectItem>
                                <SelectItem value="Terreno">Terreno</SelectItem>
                              </SelectContent>
                            </Select>
                          </div>
                          <div>
                            <Label>Comune</Label>
                            <Input
                              value={immobile.comune}
                              onChange={(e) =>
                                handleUpdateImmobile(
                                  immobile.id,
                                  "comune",
                                  e.target.value,
                                )
                              }
                              className="mt-1 bg-white"
                              placeholder="Milano"
                            />
                          </div>
                          <div className="md:col-span-2">
                            <Label>Indirizzo</Label>
                            <Input
                              value={immobile.indirizzo}
                              onChange={(e) =>
                                handleUpdateImmobile(
                                  immobile.id,
                                  "indirizzo",
                                  e.target.value,
                                )
                              }
                              className="mt-1 bg-white"
                              placeholder="Via Roma 123"
                            />
                          </div>
                          <div>
                            <Label>Rendita Catastale</Label>
                            <Input
                              value={immobile.renditaCatastale}
                              onChange={(e) =>
                                handleUpdateImmobile(
                                  immobile.id,
                                  "renditaCatastale",
                                  e.target.value,
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
            </TabsContent>

            {/* Tab 5: Tags & Note */}
            <TabsContent value="tags" className="p-6">
              <div className="space-y-6">
                <div>
                  <Label>Tags</Label>
                  <div className="flex gap-2 mt-2">
                    <Input
                      value={newTag}
                      onChange={(e) => setNewTag(e.target.value)}
                      onKeyPress={(e) => e.key === "Enter" && handleAddTag()}
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
                    {formData.tags.map((tag) => (
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
                    value={formData.note}
                    onChange={(e) => updateField("note", e.target.value)}
                    className="mt-2 bg-[#F8F5F1] min-h-[200px]"
                    placeholder="Inserisci note sul cliente, informazioni importanti, scadenze, ecc."
                  />
                </div>
              </div>
            </TabsContent>
          </Tabs>
        </motion.div>
      </div>
    </div>
  );
}
