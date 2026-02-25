import React, { useEffect } from "react";
import { motion } from "motion/react";
import { Button } from "./ui/button";
import {
  ArrowLeft,
  Brain,
  Shield,
  Lock,
  FileText,
  Users,
  Eye,
  Download,
  Trash2,
  Edit,
  AlertCircle,
} from "lucide-react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "./ui/card";
import { Separator } from "./ui/separator";
import { Badge } from "./ui/badge";
import { Progress } from "./ui/progress";

interface GDPRCompliancePageProps {
  onBackToHome: () => void;
}

export function GDPRCompliancePage({ onBackToHome }: GDPRCompliancePageProps) {
  // Ensure page starts at top
  useEffect(() => {
    window.scrollTo(0, 0);
  }, []);

  const complianceAreas = [
    {
      id: "lawfulness",
      title: "Base Giuridica del Trattamento",
      icon: FileText,
      compliance: 95,
      status: "Conforme",
      description:
        "Tutti i trattamenti di dati personali sono basati su fondamenti giuridici validi secondo l'Art. 6 GDPR.",
      details: [
        "Consenso esplicito per dati marketing (Art. 6.1.a)",
        "Esecuzione contratto per servizi (Art. 6.1.b)",
        "Interesse legittimo per analytics (Art. 6.1.f)",
        "Obblighi legali per conservazione fiscale (Art. 6.1.c)",
      ],
    },
    {
      id: "rights",
      title: "Diritti degli Interessati",
      icon: Users,
      compliance: 92,
      status: "Conforme",
      description:
        "Implementazione completa di tutti i diritti GDPR con procedure automatizzate.",
      details: [
        "Diritto di accesso - risposta entro 30 giorni",
        "Diritto di rettifica - correzione immediata",
        "Diritto alla cancellazione - eliminazione sicura",
        "Diritto alla portabilità - export dati strutturati",
      ],
    },
    {
      id: "security",
      title: "Sicurezza e Protezione Dati",
      icon: Lock,
      compliance: 98,
      status: "Conforme",
      description:
        "Misure tecniche e organizzative avanzate per la protezione dei dati personali.",
      details: [
        "Crittografia AES-256 per dati a riposo",
        "TLS 1.3 per dati in transito",
        "Autenticazione multi-fattore obbligatoria",
        "Backup crittografati e testati regolarmente",
      ],
    },
    {
      id: "transparency",
      title: "Trasparenza e Informativa",
      icon: Eye,
      compliance: 90,
      status: "Conforme",
      description:
        "Informazioni chiare e accessibili sul trattamento dei dati personali.",
      details: [
        "Privacy Policy dettagliata e aggiornata",
        "Notifiche proattive per modifiche",
        "Linguaggio semplice e comprensibile",
        "Informazioni disponibili in italiano",
      ],
    },
  ];

  const userRights = [
    {
      right: "Diritto di Accesso",
      icon: Eye,
      description:
        "Ottenere conferma che i tuoi dati sono trattati e ricevere copia dei dati",
      action: "Richiedi Accesso",
      timeframe: "30 giorni",
    },
    {
      right: "Diritto di Rettifica",
      icon: Edit,
      description:
        "Correggere dati personali inesatti o completare dati incompleti",
      action: "Richiedi Correzione",
      timeframe: "Immediato",
    },
    {
      right: "Diritto alla Cancellazione",
      icon: Trash2,
      description:
        'Richiedere la cancellazione dei tuoi dati personali ("diritto all\'oblio")',
      action: "Richiedi Cancellazione",
      timeframe: "30 giorni",
    },
    {
      right: "Diritto alla Portabilità",
      icon: Download,
      description:
        "Ricevere i tuoi dati in formato strutturato e trasmetterli ad altro titolare",
      action: "Esporta Dati",
      timeframe: "30 giorni",
    },
  ];

  const getStatusColor = (status: string) => {
    switch (status) {
      case "Conforme":
        return "bg-green-100 text-green-800";
      case "In Progress":
        return "bg-yellow-100 text-yellow-800";
      default:
        return "bg-gray-100 text-gray-800";
    }
  };

  return (
    <div className="min-h-screen bg-white">
      {/* Header */}
      <header className="bg-white border-b border-[#C4BDB4]/20 sticky top-0 z-40">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center justify-between">
            <Button
              onClick={onBackToHome}
              variant="ghost"
              className="flex items-center space-x-2 text-[#2A5D67] hover:bg-[#F8F5F1] transition-all duration-200"
            >
              <ArrowLeft className="w-4 h-4" />
              <span>Torna alla Home</span>
            </Button>

            <motion.div
              initial={{ opacity: 0, scale: 0.8 }}
              animate={{ opacity: 1, scale: 1 }}
              className="flex items-center space-x-2"
            >
              <div className="w-8 h-8 bg-[#2A5D67] rounded-lg flex items-center justify-center">
                <Brain className="w-5 h-5 text-white" />
              </div>
              <span className="text-xl font-bold text-[#2A5D67]">
                PratikoAI
              </span>
            </motion.div>
          </div>
        </div>
      </header>

      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.5 }}
        className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-12"
      >
        {/* Page Header */}
        <div className="text-center mb-12">
          <motion.div
            initial={{ y: 20, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            transition={{ delay: 0.1 }}
            className="w-16 h-16 bg-[#2A5D67] rounded-full flex items-center justify-center mx-auto mb-6"
          >
            <Shield className="w-8 h-8 text-white" />
          </motion.div>

          <motion.h1
            initial={{ y: 20, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            transition={{ delay: 0.2 }}
            className="text-4xl font-bold text-[#2A5D67] mb-4"
          >
            GDPR Compliance
          </motion.h1>

          <motion.p
            initial={{ y: 20, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            transition={{ delay: 0.3 }}
            className="text-xl text-[#1E293B] max-w-2xl mx-auto mb-6"
          >
            La nostra conformità al Regolamento Generale sulla Protezione dei
            Dati
          </motion.p>

          <motion.div
            initial={{ y: 20, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            transition={{ delay: 0.4 }}
            className="flex items-center justify-center space-x-4"
          >
            <Badge className="bg-green-100 text-green-800 px-4 py-2">
              ✓ Certificato GDPR
            </Badge>
            <Badge className="bg-blue-100 text-blue-800 px-4 py-2">
              🇪🇺 EU Compliant
            </Badge>
            <Badge className="bg-purple-100 text-purple-800 px-4 py-2">
              🇮🇹 Made in Italy
            </Badge>
          </motion.div>
        </div>

        {/* Compliance Overview */}
        <motion.div
          initial={{ y: 20, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          transition={{ delay: 0.5 }}
          className="mb-12"
        >
          <Card className="border-[#C4BDB4]/20">
            <CardHeader>
              <CardTitle className="text-2xl text-[#2A5D67]">
                Stato della Conformità GDPR
              </CardTitle>
              <CardDescription>
                Monitoraggio continuo della nostra compliance al Regolamento
                Europeo
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                {complianceAreas.map((area, index) => (
                  <motion.div
                    key={area.id}
                    initial={{ y: 20, opacity: 0 }}
                    animate={{ y: 0, opacity: 1 }}
                    transition={{ delay: 0.6 + index * 0.1 }}
                    className="text-center"
                  >
                    <div className="w-16 h-16 bg-[#F8F5F1] rounded-full flex items-center justify-center mx-auto mb-3">
                      <area.icon className="w-8 h-8 text-[#2A5D67]" />
                    </div>
                    <h3 className="font-semibold text-[#2A5D67] mb-2">
                      {area.title}
                    </h3>
                    <div className="space-y-2">
                      <Progress value={area.compliance} className="h-2" />
                      <p className="text-sm text-[#1E293B]">
                        {area.compliance}%
                      </p>
                      <Badge className={getStatusColor(area.status)}>
                        {area.status}
                      </Badge>
                    </div>
                  </motion.div>
                ))}
              </div>
            </CardContent>
          </Card>
        </motion.div>

        {/* Detailed Compliance Areas */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 mb-12">
          {complianceAreas.map((area, index) => (
            <motion.div
              key={area.id}
              initial={{ y: 30, opacity: 0 }}
              animate={{ y: 0, opacity: 1 }}
              transition={{ delay: 0.7 + index * 0.1 }}
            >
              <Card className="border-[#C4BDB4]/20 h-full">
                <CardHeader>
                  <CardTitle className="flex items-center space-x-3 text-[#2A5D67]">
                    <area.icon className="w-6 h-6" />
                    <span>{area.title}</span>
                  </CardTitle>
                  <CardDescription>{area.description}</CardDescription>
                </CardHeader>
                <CardContent>
                  <ul className="space-y-3">
                    {area.details.map((detail, detailIndex) => (
                      <li
                        key={detailIndex}
                        className="flex items-start space-x-3"
                      >
                        <div className="w-2 h-2 bg-[#D4A574] rounded-full mt-2 flex-shrink-0" />
                        <span className="text-[#1E293B] text-sm">{detail}</span>
                      </li>
                    ))}
                  </ul>
                </CardContent>
              </Card>
            </motion.div>
          ))}
        </div>

        <Separator className="my-12" />

        {/* User Rights Section */}
        <motion.div
          initial={{ y: 30, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          transition={{ delay: 1.1 }}
          className="mb-12"
        >
          <div className="text-center mb-8">
            <h2 className="text-3xl font-bold text-[#2A5D67] mb-4">
              I Tuoi Diritti GDPR
            </h2>
            <p className="text-[#1E293B] max-w-2xl mx-auto">
              Esercita i tuoi diritti in modo semplice e rapido. Tutte le
              richieste sono gestite secondo i tempi previsti dal GDPR.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {userRights.map((userRight, index) => (
              <motion.div
                key={index}
                initial={{ y: 20, opacity: 0 }}
                animate={{ y: 0, opacity: 1 }}
                transition={{ delay: 1.2 + index * 0.1 }}
              >
                <Card className="border-[#C4BDB4]/20 hover:shadow-lg transition-all duration-200">
                  <CardHeader>
                    <CardTitle className="flex items-center space-x-3 text-[#2A5D67]">
                      <div className="w-10 h-10 bg-[#F8F5F1] rounded-lg flex items-center justify-center">
                        <userRight.icon className="w-5 h-5 text-[#2A5D67]" />
                      </div>
                      <span>{userRight.right}</span>
                    </CardTitle>
                    <CardDescription>{userRight.description}</CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="flex items-center justify-between">
                      <div className="text-sm text-[#1E293B]">
                        <strong>Tempo di risposta:</strong>{" "}
                        {userRight.timeframe}
                      </div>
                      <Button
                        variant="outline"
                        size="sm"
                        className="border-[#2A5D67] text-[#2A5D67] hover:bg-[#2A5D67] hover:text-white"
                      >
                        {userRight.action}
                      </Button>
                    </div>
                  </CardContent>
                </Card>
              </motion.div>
            ))}
          </div>
        </motion.div>

        {/* Data Protection Measures */}
        <motion.div
          initial={{ y: 30, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          transition={{ delay: 1.6 }}
          className="mb-12"
        >
          <Card className="border-[#C4BDB4]/20">
            <CardHeader>
              <CardTitle className="text-2xl text-[#2A5D67]">
                Misure di Protezione Implementate
              </CardTitle>
              <CardDescription>
                Le nostre misure tecniche e organizzative per la protezione dei
                dati
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <div className="space-y-4">
                  <h4 className="font-semibold text-[#2A5D67]">
                    Misure Tecniche
                  </h4>
                  <ul className="space-y-2 text-sm text-[#1E293B]">
                    <li>• Crittografia end-to-end</li>
                    <li>• Pseudonimizzazione dati</li>
                    <li>• Controlli accesso granulari</li>
                    <li>• Monitoraggio sicurezza 24/7</li>
                    <li>• Backup automatici crittografati</li>
                  </ul>
                </div>

                <div className="space-y-4">
                  <h4 className="font-semibold text-[#2A5D67]">
                    Misure Organizzative
                  </h4>
                  <ul className="space-y-2 text-sm text-[#1E293B]">
                    <li>• Data Protection Officer dedicato</li>
                    <li>• Formazione privacy per staff</li>
                    <li>• Procedure incident response</li>
                    <li>• Audit periodici conformità</li>
                    <li>• Contratti DPA con fornitori</li>
                  </ul>
                </div>

                <div className="space-y-4">
                  <h4 className="font-semibold text-[#2A5D67]">
                    Certificazioni
                  </h4>
                  <ul className="space-y-2 text-sm text-[#1E293B]">
                    <li>• ISO 27001:2022</li>
                    <li>• SOC 2 Type II</li>
                    <li>• GDPR Compliance Certificate</li>
                    <li>• Privacy Shield Framework</li>
                    <li>• Cloud Security Alliance</li>
                  </ul>
                </div>
              </div>
            </CardContent>
          </Card>
        </motion.div>

        {/* Contact DPO */}
        <motion.div
          initial={{ y: 30, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          transition={{ delay: 1.8 }}
          className="bg-[#F8F5F1] rounded-xl p-8 text-center"
        >
          <div className="w-12 h-12 bg-[#2A5D67] rounded-full flex items-center justify-center mx-auto mb-4">
            <Users className="w-6 h-6 text-white" />
          </div>

          <h3 className="text-2xl font-bold text-[#2A5D67] mb-4">
            Contatta il nostro Data Protection Officer
          </h3>

          <p className="text-[#1E293B] mb-6 max-w-2xl mx-auto">
            Per qualsiasi domanda sui tuoi diritti GDPR, sulla nostra conformità
            o per esercitare i tuoi diritti, contatta direttamente il nostro
            DPO.
          </p>

          <div className="grid md:grid-cols-2 gap-6 mb-6">
            <div className="bg-white rounded-lg p-4 border border-[#C4BDB4]/20">
              <h4 className="font-semibold text-[#2A5D67] mb-2">
                Contatti DPO
              </h4>
              <div className="text-[#1E293B] space-y-1 text-sm">
                <p>
                  <strong>Dott.ssa Maria Rossi</strong>
                </p>
                <p>Email: dpo@pratikoai.it</p>
                <p>Telefono: +39 0931 123456</p>
                <p>PEC: dpo.pratikoai@pec.it</p>
              </div>
            </div>

            <div className="bg-white rounded-lg p-4 border border-[#C4BDB4]/20">
              <h4 className="font-semibold text-[#2A5D67] mb-2">
                Autorità di Controllo
              </h4>
              <div className="text-[#1E293B] space-y-1 text-sm">
                <p>
                  <strong>Garante Privacy</strong>
                </p>
                <p>Website: garanteprivacy.it</p>
                <p>Email: garante@gpdp.it</p>
                <p>Telefono: +39 06 69677 1</p>
              </div>
            </div>
          </div>

          <Button className="bg-[#2A5D67] hover:bg-[#1E293B] text-white px-6 py-3">
            <strong>Invia Richiesta Privacy</strong>
          </Button>
        </motion.div>

        {/* Legal Footer */}
        <motion.div
          initial={{ y: 30, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          transition={{ delay: 2.0 }}
          className="mt-12 text-center text-sm text-[#C4BDB4]"
        >
          <p>
            © 2025 PratikoAI S.r.l. - P.IVA: 12345678901
            <br />
            Conforme al GDPR (Regolamento UE 2016/679) e al Codice Privacy
            italiano (D.Lgs. 196/2003)
          </p>
        </motion.div>
      </motion.div>
    </div>
  );
}
