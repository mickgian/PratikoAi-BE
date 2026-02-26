import React, { useState } from "react";
import { motion, AnimatePresence } from "motion/react";
import { FileText, Check, CheckCircle } from "lucide-react";
import { Input } from "./ui/input";

interface Document {
  id: string;
  name: string;
  required: boolean;
  verified: boolean;
  verifiedDate?: string;
  verificationNote?: string;
}

interface DocumentVerificationSectionProps {
  documents: Document[];
  isClientMode: boolean;
  onToggleVerification: (docId: string) => void;
  onNoteChange: (docId: string, note: string) => void;
}

export function DocumentVerificationSection({
  documents,
  isClientMode,
  onToggleVerification,
  onNoteChange,
}: DocumentVerificationSectionProps) {
  const [showNoteInput, setShowNoteInput] = useState<{
    [key: string]: boolean;
  }>({});
  const [tempNotes, setTempNotes] = useState<{ [key: string]: string }>({});

  const verifiedCount = documents.filter((d) => d.verified).length;
  const totalCount = documents.length;

  const handleCheckboxChange = (docId: string, currentlyVerified: boolean) => {
    if (!currentlyVerified) {
      // Show note input when checking
      setShowNoteInput((prev) => ({ ...prev, [docId]: true }));
    }
    onToggleVerification(docId);
  };

  const handleNoteInputChange = (docId: string, value: string) => {
    setTempNotes((prev) => ({ ...prev, [docId]: value }));
    onNoteChange(docId, value);
  };

  return (
    <div>
      <h3 className="text-lg font-semibold text-[#2A5D67] mb-3 flex items-center">
        <FileText className="w-5 h-5 mr-2" />
        Documenti da verificare
      </h3>

      <div className="space-y-2 mb-4">
        {documents.map((doc) => (
          <div key={doc.id}>
            <motion.div
              whileHover={{ x: 4 }}
              className={`flex items-start space-x-3 p-3 rounded-lg border transition-all ${
                doc.verified
                  ? "bg-green-50 border-green-200"
                  : "bg-white border-[#C4BDB4]/20 hover:border-[#C4BDB4]"
              }`}
            >
              {/* Checkbox + FileText icon */}
              <div className="flex items-center space-x-2 flex-shrink-0">
                <input
                  type="checkbox"
                  checked={doc.verified}
                  onChange={() => handleCheckboxChange(doc.id, doc.verified)}
                  disabled={!isClientMode}
                  className="w-5 h-5 text-green-600 border-[#C4BDB4] rounded focus:ring-green-500 disabled:opacity-50"
                />
                <FileText
                  className={`w-4 h-4 ${doc.verified ? "text-green-600" : "text-[#C4BDB4]"}`}
                />
              </div>

              {/* Document info */}
              <div className="flex-1 min-w-0">
                <p
                  className={`font-medium ${
                    doc.verified ? "text-green-700" : "text-[#2A5D67]"
                  }`}
                >
                  {doc.name}
                </p>

                {doc.verified && doc.verifiedDate && (
                  <p className="text-xs text-green-600 mt-0.5">
                    Verificato il{" "}
                    {new Date(doc.verifiedDate).toLocaleDateString("it-IT")}
                  </p>
                )}

                {doc.verified && doc.verificationNote && (
                  <p className="text-xs text-[#1E293B]/70 italic mt-1">
                    {doc.verificationNote}
                  </p>
                )}

                {!doc.verified && doc.required && (
                  <p className="text-xs text-red-600 mt-0.5">Obbligatorio</p>
                )}
              </div>

              {/* Check icon on the right */}
              {doc.verified && (
                <CheckCircle className="w-5 h-5 text-green-600 flex-shrink-0" />
              )}
            </motion.div>

            {/* Optional note input (shows when checking a document) */}
            <AnimatePresence>
              {isClientMode && showNoteInput[doc.id] && !doc.verified && (
                <motion.div
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: "auto" }}
                  exit={{ opacity: 0, height: 0 }}
                  className="ml-10 mt-2 mb-2"
                >
                  <Input
                    placeholder="Nota (opzionale): es. ricevuto via email..."
                    value={tempNotes[doc.id] || ""}
                    onChange={(e) =>
                      handleNoteInputChange(doc.id, e.target.value)
                    }
                    className="text-sm"
                  />
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        ))}
      </div>

      {/* Progress indicator */}
      <div className="flex items-center justify-between p-3 bg-[#F8F5F1] rounded-lg border border-[#C4BDB4]/20">
        <div className="flex items-center space-x-2">
          <div
            className={`w-8 h-8 rounded-full flex items-center justify-center ${
              verifiedCount === totalCount ? "bg-green-100" : "bg-[#2A5D67]/10"
            }`}
          >
            {verifiedCount === totalCount ? (
              <Check className="w-5 h-5 text-green-600" />
            ) : (
              <FileText className="w-4 h-4 text-[#2A5D67]" />
            )}
          </div>
          <div>
            <p
              className={`text-sm font-semibold ${
                verifiedCount === totalCount
                  ? "text-green-700"
                  : "text-[#2A5D67]"
              }`}
            >
              {verifiedCount} di {totalCount} documenti verificati
            </p>
            {verifiedCount < totalCount && (
              <p className="text-xs text-[#1E293B]/60">
                Mancano {totalCount - verifiedCount}{" "}
                {totalCount - verifiedCount === 1 ? "documento" : "documenti"}
              </p>
            )}
          </div>
        </div>

        {/* Progress bar */}
        <div className="w-32">
          <div className="w-full h-2 bg-white rounded-full overflow-hidden">
            <motion.div
              initial={{ width: 0 }}
              animate={{ width: `${(verifiedCount / totalCount) * 100}%` }}
              className={`h-full ${
                verifiedCount === totalCount ? "bg-green-500" : "bg-[#2A5D67]"
              }`}
            />
          </div>
        </div>
      </div>
    </div>
  );
}
