"use client";

import React, { useState } from "react";
import { motion, AnimatePresence } from "motion/react";
import {
  MessageCircle,
  UserSearch,
  FileUser,
  PlayCircle,
  X,
  Building2,
  User,
  TrendingUp,
  CheckCircle2,
  Clock,
  AlertCircle,
} from "lucide-react";
import { Card } from "./ui/card";
import { type Client } from "./ClientMentionAutocomplete";

const regimeConfig = {
  Forfettario: {
    color: "text-green-700",
    bg: "bg-green-50",
    border: "border-green-200",
  },
  Ordinario: {
    color: "text-blue-700",
    bg: "bg-blue-50",
    border: "border-blue-200",
  },
  Semplificato: {
    color: "text-orange-700",
    bg: "bg-orange-50",
    border: "border-orange-200",
  },
};

interface ClientActionPickerProps {
  client: Client;
  onSelectAction: (
    action: "generic" | "specific" | "profile" | "procedure",
  ) => void;
  onClose: () => void;
}

export function ClientActionPicker({
  client,
  onSelectAction,
  onClose,
}: ClientActionPickerProps) {
  const regime = regimeConfig[client.regimeFiscale];

  const actions = [
    {
      id: "generic" as const,
      icon: MessageCircle,
      title: "Domanda generica",
      description: "Fai una domanda con il contesto del cliente",
      color: "text-[#2A5D67]",
      bgColor: "bg-[#2A5D67]/10",
      hoverColor: "hover:bg-[#2A5D67]",
    },
    {
      id: "specific" as const,
      icon: UserSearch,
      title: "Domanda sul cliente",
      description: "Info specifiche: scadenze, pagamenti, immobili...",
      color: "text-[#D4A574]",
      bgColor: "bg-[#D4A574]/10",
      hoverColor: "hover:bg-[#D4A574]",
    },
    {
      id: "profile" as const,
      icon: FileUser,
      title: "Scheda cliente",
      description: "Visualizza anagrafica, regime, ATECO e procedure attive",
      color: "text-[#1E293B]",
      bgColor: "bg-[#1E293B]/10",
      hoverColor: "hover:bg-[#1E293B]",
    },
    {
      id: "procedure" as const,
      icon: PlayCircle,
      title: "Avvia procedura",
      description: "Seleziona e avvia una procedura guidata per questo cliente",
      color: "text-emerald-600",
      bgColor: "bg-emerald-50",
      hoverColor: "hover:bg-emerald-600",
    },
  ];

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -20 }}
      className="mb-6"
    >
      <Card className="border-[#2A5D67]/30 overflow-hidden">
        {/* Header */}
        <div className="bg-gradient-to-r from-[#2A5D67] to-[#1E293B] px-5 py-4 flex items-center justify-between">
          <div className="flex items-center space-x-3">
            {client.name.includes("S.r.l.") ||
            client.name.includes("S.p.A.") ? (
              <div className="w-10 h-10 bg-white/20 rounded-lg flex items-center justify-center">
                <Building2 className="w-5 h-5 text-white" />
              </div>
            ) : (
              <div className="w-10 h-10 bg-white/20 rounded-lg flex items-center justify-center">
                <User className="w-5 h-5 text-white" />
              </div>
            )}
            <div>
              <h3 className="font-semibold text-white text-lg">
                {client.name}
              </h3>
              <div className="flex items-center space-x-2 mt-1">
                <span
                  className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium border ${regime.bg} ${regime.color} ${regime.border}`}
                >
                  {client.regimeFiscale}
                </span>
                <span className="text-xs text-white/70">
                  {client.posizione}
                </span>
              </div>
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-white/70 hover:text-white transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="p-5 bg-gradient-to-br from-[#F8F5F1] to-white">
          <p className="text-sm text-[#1E293B]/70 mb-4">
            Cosa vuoi fare con questo cliente?
          </p>

          {/* Action Grid */}
          <div className="grid grid-cols-2 gap-3">
            {actions.map((action) => {
              const Icon = action.icon;
              return (
                <button
                  key={action.id}
                  onClick={() => onSelectAction(action.id)}
                  className={`group relative bg-white rounded-xl p-4 border border-[#C4BDB4]/20 hover:border-[#2A5D67]/30 transition-all hover:shadow-lg text-left`}
                >
                  <div
                    className={`w-12 h-12 ${action.bgColor} rounded-lg flex items-center justify-center mb-3 ${action.hoverColor} group-hover:text-white transition-colors`}
                  >
                    <Icon
                      className={`w-6 h-6 ${action.color} group-hover:text-white transition-colors`}
                    />
                  </div>
                  <h4 className="font-semibold text-[#1E293B] mb-1 text-sm">
                    {action.title}
                  </h4>
                  <p className="text-xs text-[#1E293B]/60 leading-relaxed">
                    {action.description}
                  </p>
                </button>
              );
            })}
          </div>
        </div>
      </Card>
    </motion.div>
  );
}

// Full Client Profile Card Component
interface ClientProfileCardProps {
  client: Client;
  onClose: () => void;
}

export function ClientProfileCard({ client, onClose }: ClientProfileCardProps) {
  const regime = regimeConfig[client.regimeFiscale];

  // Mock P.IVA for companies
  const piva =
    client.name.includes("S.r.l.") || client.name.includes("S.p.A.")
      ? `IT${client.codiceFiscale.substring(0, 11)}`
      : null;

  // Mock INPS/INAIL data
  const posizioneContributiva = {
    inps: {
      status: "attiva",
      matricola: `${Math.floor(Math.random() * 9000000) + 1000000}`,
      ultimoPagamento: "15/01/2024",
    },
    inail: {
      status:
        client.name.includes("S.r.l.") || client.name.includes("S.p.A.")
          ? "attiva"
          : "non_richiesta",
      pat:
        client.name.includes("S.r.l.") || client.name.includes("S.p.A.")
          ? `${Math.floor(Math.random() * 90000000) + 10000000}`
          : null,
    },
  };

  // Mock procedure progress
  const procedureProgress =
    client.activeProcedures?.map((proc) => ({
      name: proc,
      progress: Math.floor(Math.random() * 60) + 40, // 40-100%
      status: Math.random() > 0.5 ? "in_corso" : "completato",
    })) || [];

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -20 }}
      className="mb-6"
    >
      <Card className="border-[#2A5D67]/30 overflow-hidden">
        {/* Header */}
        <div className="bg-gradient-to-r from-[#2A5D67] to-[#1E293B] px-5 py-4">
          <div className="flex items-center space-x-3">
            {client.name.includes("S.r.l.") ||
            client.name.includes("S.p.A.") ? (
              <div className="w-12 h-12 bg-white/20 rounded-xl flex items-center justify-center">
                <Building2 className="w-6 h-6 text-white" />
              </div>
            ) : (
              <div className="w-12 h-12 bg-white/20 rounded-xl flex items-center justify-center">
                <User className="w-6 h-6 text-white" />
              </div>
            )}
            <div>
              <h3 className="font-semibold text-white text-lg">
                Scheda Cliente
              </h3>
              <p className="text-xs text-white/70">
                Informazioni complete e procedure attive
              </p>
            </div>
          </div>
        </div>

        {/* Content */}
        <div className="p-5 bg-gradient-to-br from-[#F8F5F1] to-white space-y-4">
          {/* Anagrafica */}
          <div>
            <h4 className="text-sm font-semibold text-[#2A5D67] mb-3 flex items-center space-x-2">
              <div className="w-1 h-4 bg-[#2A5D67] rounded-full" />
              <span>Anagrafica</span>
            </h4>
            <div className="bg-white rounded-lg p-4 border border-[#C4BDB4]/20 space-y-3">
              <div>
                <p className="text-xs text-[#1E293B]/60 mb-1">
                  Denominazione / Nome
                </p>
                <p className="font-semibold text-[#1E293B]">{client.name}</p>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <p className="text-xs text-[#1E293B]/60 mb-1">
                    Codice Fiscale
                  </p>
                  <p className="text-sm font-mono text-[#1E293B]">
                    {client.codiceFiscale}
                  </p>
                </div>
                {piva && (
                  <div>
                    <p className="text-xs text-[#1E293B]/60 mb-1">
                      Partita IVA
                    </p>
                    <p className="text-sm font-mono text-[#1E293B]">{piva}</p>
                  </div>
                )}
              </div>
              <div>
                <p className="text-xs text-[#1E293B]/60 mb-1">Sede</p>
                <p className="text-sm text-[#1E293B]">{client.posizione}</p>
              </div>
            </div>
          </div>

          {/* Regime Fiscale */}
          <div>
            <h4 className="text-sm font-semibold text-[#2A5D67] mb-3 flex items-center space-x-2">
              <div className="w-1 h-4 bg-[#D4A574] rounded-full" />
              <span>Regime Fiscale</span>
            </h4>
            <div className="bg-white rounded-lg p-4 border border-[#C4BDB4]/20">
              <div className="flex items-center justify-between">
                <span
                  className={`inline-flex items-center px-3 py-1.5 rounded-full text-sm font-medium border ${regime.bg} ${regime.color} ${regime.border}`}
                >
                  {client.regimeFiscale}
                </span>
                <p className="text-xs text-[#1E293B]/60">
                  {client.regimeFiscale === "Forfettario" &&
                    "Regime agevolato L. 190/2014"}
                  {client.regimeFiscale === "Ordinario" &&
                    "Regime ordinario TUIR"}
                  {client.regimeFiscale === "Semplificato" &&
                    "Regime semplificato"}
                </p>
              </div>
            </div>
          </div>

          {/* Codice ATECO */}
          <div>
            <h4 className="text-sm font-semibold text-[#2A5D67] mb-3 flex items-center space-x-2">
              <div className="w-1 h-4 bg-[#1E293B] rounded-full" />
              <span>Codice ATECO</span>
            </h4>
            <div className="bg-white rounded-lg p-4 border border-[#C4BDB4]/20">
              <div className="flex items-start space-x-3">
                <div className="w-10 h-10 bg-[#2A5D67]/10 rounded-lg flex items-center justify-center flex-shrink-0">
                  <TrendingUp className="w-5 h-5 text-[#2A5D67]" />
                </div>
                <div className="flex-1">
                  <p className="font-semibold text-[#2A5D67] mb-1">
                    {client.ateco}
                  </p>
                  <p className="text-sm text-[#1E293B]/70">
                    {client.atecoDescription}
                  </p>
                </div>
              </div>
            </div>
          </div>

          {/* Posizione Contributiva */}
          <div>
            <h4 className="text-sm font-semibold text-[#2A5D67] mb-3 flex items-center space-x-2">
              <div className="w-1 h-4 bg-emerald-600 rounded-full" />
              <span>Posizione Contributiva</span>
            </h4>
            <div className="space-y-2">
              {/* INPS */}
              <div className="bg-white rounded-lg p-3 border border-[#C4BDB4]/20 flex items-center justify-between">
                <div className="flex items-center space-x-3">
                  <div className="w-8 h-8 bg-blue-50 rounded-lg flex items-center justify-center">
                    <CheckCircle2 className="w-4 h-4 text-blue-600" />
                  </div>
                  <div>
                    <p className="text-sm font-semibold text-[#1E293B]">INPS</p>
                    <p className="text-xs text-[#1E293B]/60">
                      Matr. {posizioneContributiva.inps.matricola}
                    </p>
                  </div>
                </div>
                <div className="text-right">
                  <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-green-50 text-green-700 border border-green-200">
                    Attiva
                  </span>
                  <p className="text-xs text-[#1E293B]/60 mt-1">
                    Ult. pag: {posizioneContributiva.inps.ultimoPagamento}
                  </p>
                </div>
              </div>

              {/* INAIL */}
              <div className="bg-white rounded-lg p-3 border border-[#C4BDB4]/20 flex items-center justify-between">
                <div className="flex items-center space-x-3">
                  <div
                    className={`w-8 h-8 rounded-lg flex items-center justify-center ${
                      posizioneContributiva.inail.status === "attiva"
                        ? "bg-orange-50"
                        : "bg-gray-50"
                    }`}
                  >
                    {posizioneContributiva.inail.status === "attiva" ? (
                      <CheckCircle2 className="w-4 h-4 text-orange-600" />
                    ) : (
                      <AlertCircle className="w-4 h-4 text-gray-400" />
                    )}
                  </div>
                  <div>
                    <p className="text-sm font-semibold text-[#1E293B]">
                      INAIL
                    </p>
                    {posizioneContributiva.inail.pat && (
                      <p className="text-xs text-[#1E293B]/60">
                        PAT {posizioneContributiva.inail.pat}
                      </p>
                    )}
                  </div>
                </div>
                <span
                  className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${
                    posizioneContributiva.inail.status === "attiva"
                      ? "bg-green-50 text-green-700 border border-green-200"
                      : "bg-gray-50 text-gray-600 border border-gray-200"
                  }`}
                >
                  {posizioneContributiva.inail.status === "attiva"
                    ? "Attiva"
                    : "Non richiesta"}
                </span>
              </div>
            </div>
          </div>

          {/* Procedure Attive */}
          {client.activeProcedures && client.activeProcedures.length > 0 && (
            <div>
              <h4 className="text-sm font-semibold text-[#2A5D67] mb-3 flex items-center space-x-2">
                <div className="w-1 h-4 bg-[#D4A574] rounded-full" />
                <span>Procedure Attive</span>
              </h4>
              <div className="space-y-2">
                {procedureProgress.map((proc, index) => (
                  <div
                    key={index}
                    className="bg-white rounded-lg p-3 border border-[#C4BDB4]/20"
                  >
                    <div className="flex items-center justify-between mb-2">
                      <div className="flex items-center space-x-2">
                        <div
                          className={`w-2 h-2 rounded-full ${
                            proc.status === "completato"
                              ? "bg-green-500"
                              : "bg-blue-500"
                          }`}
                        />
                        <p className="text-sm font-medium text-[#1E293B]">
                          {proc.name}
                        </p>
                      </div>
                      <span className="text-xs font-semibold text-[#2A5D67]">
                        {proc.progress}%
                      </span>
                    </div>
                    <div className="w-full bg-[#F8F5F1] rounded-full h-1.5 overflow-hidden">
                      <motion.div
                        initial={{ width: 0 }}
                        animate={{ width: `${proc.progress}%` }}
                        transition={{ duration: 0.8, ease: "easeOut" }}
                        className={`h-full rounded-full ${
                          proc.status === "completato"
                            ? "bg-green-500"
                            : "bg-gradient-to-r from-[#2A5D67] to-[#D4A574]"
                        }`}
                      />
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Procedure Suggerite */}
          {client.suggestedProcedures &&
            client.suggestedProcedures.length > 0 && (
              <div>
                <h4 className="text-sm font-semibold text-[#D4A574] mb-3 flex items-center space-x-2">
                  <div className="w-1 h-4 bg-[#D4A574] rounded-full" />
                  <span>Procedure Suggerite</span>
                </h4>
                <div className="space-y-2">
                  {client.suggestedProcedures.map((proc, index) => (
                    <div
                      key={index}
                      className="bg-white rounded-lg p-3 border border-[#D4A574]/20 flex items-center justify-between group hover:bg-[#F8F5F1] transition-colors cursor-pointer"
                    >
                      <div className="flex items-center space-x-2">
                        <div className="w-2 h-2 bg-[#D4A574] rounded-full" />
                        <p className="text-sm text-[#1E293B]">{proc}</p>
                      </div>
                      <PlayCircle className="w-4 h-4 text-[#D4A574] opacity-0 group-hover:opacity-100 transition-opacity" />
                    </div>
                  ))}
                </div>
              </div>
            )}
        </div>

        {/* Footer */}
        <div className="px-5 py-4 bg-[#F8F5F1] border-t border-[#C4BDB4]/20 flex justify-end">
          <button
            onClick={onClose}
            className="px-4 py-2 bg-[#2A5D67] text-white rounded-lg hover:bg-[#1E293B] transition-colors font-medium text-sm"
          >
            Chiudi
          </button>
        </div>
      </Card>
    </motion.div>
  );
}
