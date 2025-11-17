"""Legal Document Analysis Service for Italian Legal Documents.

Provides specialized analysis for legal documents like citazioni, ricorsi,
decreti ingiuntivi, and other Italian court documents.
"""

import re
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from app.core.llm.factory import RoutingStrategy, get_llm_provider
from app.core.logging import logger
from app.models.document_simple import ItalianDocumentCategory
from app.schemas.chat import Message


class LegalDocumentType(str, Enum):
    """Types of legal documents and their procedural context"""

    ATTO_INTRODUTTIVO = "atto_introduttivo"  # Citazione, ricorso
    ATTO_DIFENSIVO = "atto_difensivo"  # Comparsa, memoria
    PROVVEDIMENTO_GIUDICE = "provvedimento_giudice"  # Sentenza, ordinanza, decreto
    ATTO_STRAGIUDIZIALE = "atto_stragiudiziale"  # Diffida, precetto
    CONTRATTUALE = "contrattuale"  # Contratti


class ItalianLegalDocumentAnalyzer:
    """Specialized analyzer for Italian legal documents"""

    def __init__(self):
        self.document_analyzers = {
            ItalianDocumentCategory.CITAZIONE: self._analyze_citazione,
            ItalianDocumentCategory.RICORSO: self._analyze_ricorso,
            ItalianDocumentCategory.DECRETO_INGIUNTIVO: self._analyze_decreto_ingiuntivo,
            ItalianDocumentCategory.DIFFIDA: self._analyze_diffida,
            ItalianDocumentCategory.CONTRATTO: self._analyze_contratto,
            ItalianDocumentCategory.SENTENZA: self._analyze_sentenza,
            ItalianDocumentCategory.PRECETTO: self._analyze_precetto,
            ItalianDocumentCategory.COMPARSA: self._analyze_comparsa,
        }

    async def analyze_legal_document(
        self,
        document_category: ItalianDocumentCategory,
        extracted_text: str,
        extracted_data: dict[str, Any] | None = None,
        analysis_query: str | None = None,
    ) -> dict[str, Any]:
        """Main entry point for legal document analysis.

        Args:
            document_category: The identified category of the legal document
            extracted_text: Full text extracted from the document
            extracted_data: Any structured data already extracted
            analysis_query: Optional specific analysis request from user

        Returns:
            Comprehensive analysis including deadlines, parties, and recommendations
        """
        try:
            # Get specialized analyzer for document type
            analyzer_func = self.document_analyzers.get(document_category, self._analyze_generic_legal)

            # Perform specialized analysis
            base_analysis = await analyzer_func(extracted_text, extracted_data)

            # If user has specific query, get AI analysis
            if analysis_query:
                ai_analysis = await self._get_ai_legal_analysis(
                    document_category, extracted_text, base_analysis, analysis_query
                )
                base_analysis["ai_analysis"] = ai_analysis

            # Add compliance and risk assessment
            base_analysis["compliance_check"] = await self._check_legal_compliance(document_category, base_analysis)

            base_analysis["risk_assessment"] = self._assess_legal_risks(document_category, base_analysis)

            return {
                "success": True,
                "document_category": document_category.value,
                "legal_analysis": base_analysis,
                "timestamp": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            logger.error(f"Legal document analysis failed: {str(e)}")
            return {
                "success": False,
                "error": f"Analisi documento legale fallita: {str(e)}",
                "document_category": document_category.value,
            }

    async def _analyze_citazione(self, text: str, data: dict | None = None) -> dict[str, Any]:
        """Analyze a citazione in giudizio (court summons)"""
        analysis = {
            "document_type": LegalDocumentType.ATTO_INTRODUTTIVO,
            "procedural_stage": "Introduzione del giudizio",
        }

        # Extract tribunal information
        tribunal_match = re.search(r"Tribunale (Civile |Penale )?(di |)(\w+)", text, re.IGNORECASE)
        if tribunal_match:
            analysis["tribunale"] = tribunal_match.group(0)
            analysis["sede_tribunale"] = tribunal_match.group(3)

        # Extract case number (R.G.)
        rg_match = re.search(r"R\.?G\.?\s*n?\.?\s*(\d+/\d{2,4})", text)
        if rg_match:
            analysis["numero_rg"] = rg_match.group(1)

        # Extract hearing date
        udienza_patterns = [
            r"udienza (?:del |fissata (?:per |al |il ))(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4})",
            r"comparire .* (?:il |del )(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4})",
        ]
        for pattern in udienza_patterns:
            date_match = re.search(pattern, text, re.IGNORECASE)
            if date_match:
                analysis["data_udienza"] = self._parse_italian_date(date_match.group(1))
                break

        # Extract parties
        analysis["parti"] = self._extract_parties(text)

        # Extract claim value
        value_match = re.search(r"(?:valore|importo) (?:della causa |di |)(?:€|euro) ([\d\.,]+)", text, re.IGNORECASE)
        if value_match:
            analysis["valore_causa"] = self._parse_italian_amount(value_match.group(1))

        # Extract legal basis
        analysis["fondamento_giuridico"] = self._extract_legal_basis(text)

        # Calculate deadlines
        if "data_udienza" in analysis:
            analysis["scadenze"] = self._calculate_citazione_deadlines(analysis["data_udienza"])

        # Extract requested actions
        analysis["domande"] = self._extract_legal_claims(text)

        return analysis

    async def _analyze_ricorso(self, text: str, data: dict | None = None) -> dict[str, Any]:
        """Analyze a ricorso (appeal/petition)"""
        analysis = {"document_type": LegalDocumentType.ATTO_INTRODUTTIVO, "procedural_stage": "Impugnazione/Ricorso"}

        # Determine jurisdiction
        if "tar" in text.lower() or "tribunale amministrativo" in text.lower():
            analysis["giurisdizione"] = "amministrativa"
            analysis["tipo_ricorso"] = "ricorso_tar"
        elif "commissione tributaria" in text.lower():
            analysis["giurisdizione"] = "tributaria"
            analysis["tipo_ricorso"] = "ricorso_tributario"
        elif "cassazione" in text.lower():
            analysis["giurisdizione"] = "cassazione"
            analysis["tipo_ricorso"] = "ricorso_cassazione"
        else:
            analysis["giurisdizione"] = "ordinaria"
            analysis["tipo_ricorso"] = "ricorso_generico"

        # Extract challenged act
        atto_match = re.search(
            r"(?:impugna|contro|avverso) (?:il |la |l')(.+?)(?:notificat|del|emess)", text, re.IGNORECASE
        )
        if atto_match:
            analysis["atto_impugnato"] = atto_match.group(1).strip()

        # Extract notification date for deadline calculation
        notifica_match = re.search(
            r"notificat[oa] (?:il |in data )(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4})", text, re.IGNORECASE
        )
        if notifica_match:
            notifica_date = self._parse_italian_date(notifica_match.group(1))
            analysis["data_notifica"] = notifica_date
            analysis["scadenze"] = self._calculate_ricorso_deadlines(
                notifica_date, analysis.get("tipo_ricorso", "ricorso_generico")
            )

        # Extract parties
        analysis["ricorrente"] = self._extract_ricorrente(text)
        analysis["resistente"] = self._extract_resistente(text)

        # Extract grounds for appeal
        analysis["motivi"] = self._extract_ricorso_grounds(text)

        return analysis

    async def _analyze_decreto_ingiuntivo(self, text: str, data: dict | None = None) -> dict[str, Any]:
        """Analyze a decreto ingiuntivo (payment order)"""
        analysis = {
            "document_type": LegalDocumentType.PROVVEDIMENTO_GIUDICE,
            "procedural_stage": "Procedimento monitorio",
        }

        # Extract decree number
        decreto_match = re.search(r"decreto (?:ingiuntivo |)n\.?\s*(\d+/\d{2,4})", text, re.IGNORECASE)
        if decreto_match:
            analysis["numero_decreto"] = decreto_match.group(1)

        # Extract amount
        importo_match = re.search(r"ingiunge .* pagamento di (?:€|euro) ([\d\.,]+)", text, re.IGNORECASE)
        if importo_match:
            analysis["importo_decreto"] = self._parse_italian_amount(importo_match.group(1))

        # Extract creditor and debtor
        analysis["creditore"] = self._extract_creditore(text)
        analysis["debitore"] = self._extract_debitore(text)

        # Calculate opposition deadline (40 days from notification)
        notifica_match = re.search(
            r"notificat[oa] (?:il |in data )(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4})", text, re.IGNORECASE
        )
        if notifica_match:
            notifica_date = self._parse_italian_date(notifica_match.group(1))
            analysis["data_notifica"] = notifica_date
            analysis["scadenze"] = {
                "opposizione": {
                    "termine": (notifica_date + timedelta(days=40)).isoformat(),
                    "giorni_rimanenti": (notifica_date + timedelta(days=40) - datetime.now()).days,
                    "tipo": "Opposizione a decreto ingiuntivo",
                }
            }

        # Check if executable
        if "formula esecutiva" in text.lower() or "esecutivo" in text.lower():
            analysis["esecutivo"] = True
            analysis["azioni_possibili"] = ["opposizione tardiva", "sospensione esecuzione"]
        else:
            analysis["esecutivo"] = False
            analysis["azioni_possibili"] = ["opposizione", "pagamento", "accordo transattivo"]

        return analysis

    async def _analyze_diffida(self, text: str, data: dict | None = None) -> dict[str, Any]:
        """Analyze a diffida (formal notice/warning)"""
        analysis = {"document_type": LegalDocumentType.ATTO_STRAGIUDIZIALE, "procedural_stage": "Fase stragiudiziale"}

        # Extract parties
        analysis["diffidante"] = self._extract_sender(text)
        analysis["diffidato"] = self._extract_recipient(text)

        # Extract deadline
        termine_patterns = [
            r"entro (?:il termine di |)(\d+) giorn[io]",
            r"entro (?:e non oltre |)(?:il |)(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4})",
            r"termine di (\d+) giorn[io]",
        ]

        for pattern in termine_patterns:
            termine_match = re.search(pattern, text, re.IGNORECASE)
            if termine_match:
                if "/" in termine_match.group(1) or "-" in termine_match.group(1):
                    analysis["scadenza_adempimento"] = self._parse_italian_date(termine_match.group(1))
                else:
                    days = int(termine_match.group(1))
                    analysis["termine_giorni"] = days
                    # Assume today as start date if not specified
                    analysis["scadenza_adempimento"] = (datetime.now() + timedelta(days=days)).isoformat()
                break

        # Extract requested action
        analysis["oggetto_diffida"] = self._extract_diffida_object(text)

        # Extract consequences
        conseguenze_match = re.search(r"(?:in difetto|decorso inutilmente|in mancanza)(.{0,200})", text, re.IGNORECASE)
        if conseguenze_match:
            analysis["conseguenze_inadempimento"] = conseguenze_match.group(1).strip()

        # Legal effectiveness
        analysis["costituzione_in_mora"] = "art. 1219" in text.lower()

        return analysis

    async def _analyze_contratto(self, text: str, data: dict | None = None) -> dict[str, Any]:
        """Analyze a contratto (contract)"""
        analysis = {"document_type": LegalDocumentType.CONTRATTUALE, "procedural_stage": "Negoziale"}

        # Identify contract type
        contract_types = {
            "compravendita": ["compravendita", "vendita", "acquisto"],
            "locazione": ["locazione", "affitto", "locativo"],
            "appalto": ["appalto", "appaltatore"],
            "prestazione_servizi": ["servizi", "prestazione", "consulenza"],
            "lavoro": ["lavoro", "assunzione", "subordinato"],
        }

        for contract_type, keywords in contract_types.items():
            if any(keyword in text.lower() for keyword in keywords):
                analysis["tipo_contratto"] = contract_type
                break

        # Extract parties
        analysis["parti"] = self._extract_contract_parties(text)

        # Extract key terms
        analysis["oggetto"] = self._extract_contract_object(text)
        analysis["corrispettivo"] = self._extract_contract_price(text)
        analysis["durata"] = self._extract_contract_duration(text)

        # Extract important clauses
        analysis["clausole_rilevanti"] = self._extract_key_clauses(text)

        # Check for potentially unfair terms
        analysis["clausole_vessatorie"] = self._check_vessatorie(text)

        return analysis

    async def _analyze_sentenza(self, text: str, data: dict | None = None) -> dict[str, Any]:
        """Analyze a sentenza (judgment)"""
        analysis = {"document_type": LegalDocumentType.PROVVEDIMENTO_GIUDICE, "procedural_stage": "Decisione"}

        # Extract court and number
        sentenza_match = re.search(r"sentenza n\.?\s*(\d+/\d{2,4})", text, re.IGNORECASE)
        if sentenza_match:
            analysis["numero_sentenza"] = sentenza_match.group(1)

        # Extract decision
        if "condanna" in text.lower():
            analysis["esito"] = "condanna"
        elif "assolve" in text.lower() or "assoluzione" in text.lower():
            analysis["esito"] = "assoluzione"
        elif "rigetta" in text.lower():
            analysis["esito"] = "rigetto"
        elif "accoglie" in text.lower():
            analysis["esito"] = "accoglimento"

        # Extract dispositivo (ruling)
        dispositivo_match = re.search(r"P\.Q\.M\.(.+?)(?:Così deciso|Il Giudice)", text, re.IGNORECASE | re.DOTALL)
        if dispositivo_match:
            analysis["dispositivo"] = dispositivo_match.group(1).strip()

        # Check if final or appealable
        if "definitiva" in text.lower() or "inappellabile" in text.lower():
            analysis["definitiva"] = True
        else:
            analysis["definitiva"] = False
            analysis["impugnabile"] = True
            # Calculate appeal deadline (30 days typical)
            analysis["termine_impugnazione"] = {"giorni": 30, "tipo": "Appello"}

        return analysis

    async def _analyze_precetto(self, text: str, data: dict | None = None) -> dict[str, Any]:
        """Analyze an atto di precetto (formal demand before execution)"""
        analysis = {"document_type": LegalDocumentType.ATTO_STRAGIUDIZIALE, "procedural_stage": "Esecuzione forzata"}

        # Extract execution title
        titolo_match = re.search(r"(?:in forza|in virtù) (?:del|della) (.+?)(?:munito|notificat)", text, re.IGNORECASE)
        if titolo_match:
            analysis["titolo_esecutivo"] = titolo_match.group(1).strip()

        # Extract amount
        importo_match = re.search(r"pagamento di (?:€|euro) ([\d\.,]+)", text, re.IGNORECASE)
        if importo_match:
            analysis["importo_precetto"] = self._parse_italian_amount(importo_match.group(1))

        # Extract deadline (typically 10 days)
        analysis["termine_adempimento"] = {"giorni": 10, "scadenza": (datetime.now() + timedelta(days=10)).isoformat()}

        # Possible actions
        analysis["azioni_possibili"] = [
            "pagamento",
            "opposizione all'esecuzione",
            "opposizione agli atti esecutivi",
            "istanza di sospensione",
        ]

        return analysis

    async def _analyze_comparsa(self, text: str, data: dict | None = None) -> dict[str, Any]:
        """Analyze a comparsa di risposta (response brief)"""
        analysis = {"document_type": LegalDocumentType.ATTO_DIFENSIVO, "procedural_stage": "Costituzione in giudizio"}

        # Extract case reference
        rg_match = re.search(r"R\.?G\.?\s*n?\.?\s*(\d+/\d{2,4})", text)
        if rg_match:
            analysis["numero_rg"] = rg_match.group(1)

        # Extract defendant info
        analysis["convenuto"] = self._extract_convenuto(text)

        # Extract exceptions raised
        analysis["eccezioni"] = self._extract_exceptions(text)

        # Check for counterclaims
        if "domanda riconvenzionale" in text.lower():
            analysis["domande_riconvenzionali"] = True
            analysis["riconvenzionale"] = self._extract_counterclaims(text)

        return analysis

    async def _analyze_generic_legal(self, text: str, data: dict | None = None) -> dict[str, Any]:
        """Generic analysis for unspecified legal documents"""
        return {
            "document_type": "generico",
            "note": "Documento legale generico - analisi limitata",
            "estratto": text[:500] + "..." if len(text) > 500 else text,
        }

    # Helper methods for data extraction

    def _parse_italian_date(self, date_str: str) -> str:
        """Parse Italian date formats to ISO format"""
        date_str = date_str.replace("-", "/").replace(".", "/")
        try:
            # Try different date formats
            for fmt in ["%d/%m/%Y", "%d/%m/%y"]:
                try:
                    date_obj = datetime.strptime(date_str, fmt)
                    return date_obj.isoformat()
                except ValueError:
                    continue
            return date_str  # Return original if parsing fails
        except Exception:
            return date_str

    def _parse_italian_amount(self, amount_str: str) -> float:
        """Parse Italian currency format to float"""
        # Remove dots (thousand separators) and replace comma with dot
        amount_str = amount_str.replace(".", "").replace(",", ".")
        try:
            return float(amount_str)
        except ValueError:
            return 0.0

    def _extract_parties(self, text: str) -> dict[str, Any]:
        """Extract plaintiff and defendant from legal text"""
        parties = {}

        # Patterns for plaintiff
        attore_patterns = [
            r"(?:attore|ricorrente|istante)\s*[:]*\s*([A-Z][^,\n]{10,50})",
            r"([A-Z][^,\n]{10,50})\s*(?:rappresentat|assistit)",
        ]

        for pattern in attore_patterns:
            match = re.search(pattern, text)
            if match:
                parties["attore"] = match.group(1).strip()
                break

        # Patterns for defendant
        convenuto_patterns = [
            r"(?:convenuto|resistente|intimato)\s*[:]*\s*([A-Z][^,\n]{10,50})",
            r"contro\s+([A-Z][^,\n]{10,50})",
        ]

        for pattern in convenuto_patterns:
            match = re.search(pattern, text)
            if match:
                parties["convenuto"] = match.group(1).strip()
                break

        return parties

    def _extract_legal_basis(self, text: str) -> list[str]:
        """Extract legal articles and norms cited"""
        legal_refs = []

        # Pattern for article references
        art_pattern = r"art(?:icolo)?\.?\s*\d+(?:\s*(?:e|,)\s*\d+)*(?:\s+[a-z\.]+)?"

        for match in re.finditer(art_pattern, text, re.IGNORECASE):
            legal_refs.append(match.group(0))

        # Pattern for law references
        law_pattern = r"(?:legge|l\.)\s*(?:n\.?\s*)?\d+(?:/\d{2,4})"

        for match in re.finditer(law_pattern, text, re.IGNORECASE):
            legal_refs.append(match.group(0))

        return list(set(legal_refs))  # Remove duplicates

    def _calculate_citazione_deadlines(self, hearing_date: str) -> dict[str, Any]:
        """Calculate important deadlines for citazione"""
        deadlines = {}

        try:
            hearing = datetime.fromisoformat(hearing_date.replace("Z", "+00:00"))
            today = datetime.now()

            # Costituzione in giudizio (20 days before hearing)
            costituzione = hearing - timedelta(days=20)
            deadlines["costituzione"] = {
                "data": costituzione.isoformat(),
                "giorni_rimanenti": (costituzione - today).days,
                "tipo": "Costituzione in giudizio (art. 166 c.p.c.)",
            }

            # Chiamata terzo (if needed, same as costituzione)
            deadlines["chiamata_terzo"] = {
                "data": costituzione.isoformat(),
                "giorni_rimanenti": (costituzione - today).days,
                "tipo": "Eventuale chiamata in causa del terzo",
            }

        except Exception as e:
            logger.error(f"Error calculating deadlines: {e}")

        return deadlines

    def _calculate_ricorso_deadlines(self, notification_date: str, ricorso_type: str) -> dict[str, Any]:
        """Calculate deadlines based on ricorso type"""
        deadlines = {}

        try:
            notifica = datetime.fromisoformat(notification_date.replace("Z", "+00:00"))
            today = datetime.now()

            # Different deadlines based on type
            deadline_days = {
                "ricorso_tar": 60,
                "ricorso_tributario": 60,
                "ricorso_cassazione": 60,
                "ricorso_generico": 30,
            }

            days = deadline_days.get(ricorso_type, 30)
            scadenza = notifica + timedelta(days=days)

            deadlines["impugnazione"] = {
                "data": scadenza.isoformat(),
                "giorni_rimanenti": (scadenza - today).days,
                "tipo": f"Termine per {ricorso_type.replace('_', ' ')}",
            }

        except Exception as e:
            logger.error(f"Error calculating ricorso deadlines: {e}")

        return deadlines

    def _extract_legal_claims(self, text: str) -> list[str]:
        """Extract the legal claims/requests from document"""
        claims = []

        # Common patterns for legal requests
        patterns = [
            r"chiede(?:re)?\s+(?:che\s+)?(.{20,100})",
            r"condanna(?:re)?\s+(.{20,100})",
            r"accerta(?:re|mento)\s+(.{20,100})",
            r"dichiara(?:re|zione)\s+(.{20,100})",
        ]

        for pattern in patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                claims.append(match.group(1).strip())

        return claims[:5]  # Limit to first 5 claims

    def _extract_exceptions(self, text: str) -> list[str]:
        """Extract legal exceptions raised"""
        exceptions = []

        exception_keywords = [
            "eccepisce",
            "eccezione",
            "incompetenza",
            "prescrizione",
            "decadenza",
            "nullità",
            "difetto",
            "carenza",
        ]

        for keyword in exception_keywords:
            pattern = rf"{keyword}(?:\s+di)?(.{{20,100}})"
            for match in re.finditer(pattern, text, re.IGNORECASE):
                exceptions.append(f"{keyword}: {match.group(1).strip()}")

        return exceptions

    def _check_vessatorie(self, text: str) -> list[str]:
        """Check for potentially unfair contract terms"""
        vessatorie = []

        unfair_patterns = [
            (r"rinuncia(?:re)?\s+(?:a\s+)?(?:ogni\s+)?diritto", "Rinuncia ai diritti"),
            (r"esonera(?:re|to)?\s+da\s+(?:ogni\s+)?responsabilità", "Esonero da responsabilità"),
            (r"foro\s+(?:esclusivo|competente)", "Foro esclusivo"),
            (r"penale\s+(?:del\s+)?\d+%", "Clausola penale eccessiva"),
            (r"recesso\s+(?:solo|unicamente)\s+(?:del|per)", "Recesso unilaterale"),
        ]

        for pattern, description in unfair_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                vessatorie.append(description)

        return vessatorie

    def _extract_ricorrente(self, text: str) -> str | None:
        """Extract appellant/petitioner"""
        patterns = [r"ricorrente\s*[:]*\s*([A-Z][^,\n]{10,50})", r"([A-Z][^,\n]{10,50})\s*ricorre"]

        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1).strip()

        return None

    def _extract_resistente(self, text: str) -> str | None:
        """Extract respondent"""
        patterns = [r"resistente\s*[:]*\s*([A-Z][^,\n]{10,50})", r"contro\s+([A-Z][^,\n]{10,50})"]

        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1).strip()

        return None

    def _extract_ricorso_grounds(self, text: str) -> list[str]:
        """Extract grounds for appeal"""
        motivi = []

        # Pattern for numbered grounds
        motivi_pattern = r"(?:motiv[oi]|censura)\s*(?:n\.?\s*)?\d+[:\.\)]\s*(.{20,200})"

        for match in re.finditer(motivi_pattern, text, re.IGNORECASE):
            motivi.append(match.group(1).strip())

        return motivi[:10]  # Limit to first 10

    async def _get_ai_legal_analysis(
        self, category: ItalianDocumentCategory, text: str, base_analysis: dict[str, Any], query: str
    ) -> dict[str, Any]:
        """Get AI-powered analysis for specific legal questions"""
        system_prompt = f"""Sei un esperto avvocato italiano specializzato in analisi di documenti legali.
Stai analizzando un documento di tipo: {category.value}

Informazioni già estratte:
{base_analysis}

Fornisci un'analisi legale professionale rispondendo alla domanda specifica dell'utente.
Considera:
1. Aspetti procedurali e termini
2. Diritti e obblighi delle parti
3. Possibili azioni e strategie
4. Rischi e opportunità
5. Riferimenti normativi applicabili"""

        user_prompt = f"""Documento da analizzare:
{text[:2000]}...

Domanda specifica: {query}"""

        try:
            messages = [Message(role="system", content=system_prompt), Message(role="user", content=user_prompt)]

            provider = get_llm_provider(messages=messages, strategy=RoutingStrategy.QUALITY_FIRST)

            response = await provider.chat_completion(messages=messages, temperature=0.3)

            return {"risposta": response.content, "tipo_analisi": "approfondimento_legale"}

        except Exception as e:
            logger.error(f"AI legal analysis failed: {e}")
            return {"errore": "Analisi AI non disponibile", "dettaglio": str(e)}

    async def _check_legal_compliance(
        self, category: ItalianDocumentCategory, analysis: dict[str, Any]
    ) -> dict[str, Any]:
        """Check legal compliance and validity"""
        compliance = {"valido": True, "problemi": [], "suggerimenti": []}

        # Category-specific compliance checks
        if category == ItalianDocumentCategory.CITAZIONE:
            # Check citation requirements
            if "tribunale" not in analysis:
                compliance["problemi"].append("Tribunale competente non specificato")
                compliance["valido"] = False

            if "data_udienza" not in analysis:
                compliance["problemi"].append("Data udienza non specificata")
                compliance["valido"] = False

            if "scadenze" in analysis:
                for scadenza_key, scadenza_data in analysis["scadenze"].items():
                    if scadenza_data.get("giorni_rimanenti", 0) < 0:
                        compliance["problemi"].append(f"Termine {scadenza_key} già scaduto")
                        compliance["suggerimenti"].append("Valutare rimessione in termini")

        elif category == ItalianDocumentCategory.DECRETO_INGIUNTIVO:
            if analysis.get("esecutivo", False):
                compliance["suggerimenti"].append("Decreto già esecutivo - valutare opposizione tardiva")

            if "scadenze" in analysis:
                opp = analysis["scadenze"].get("opposizione", {})
                if opp.get("giorni_rimanenti", 0) < 5:
                    compliance["problemi"].append("Termine opposizione in scadenza")
                    compliance["suggerimenti"].append("Preparare urgentemente opposizione")

        elif category == ItalianDocumentCategory.CONTRATTO:
            if "clausole_vessatorie" in analysis and analysis["clausole_vessatorie"]:
                compliance["problemi"].append("Presenza di clausole potenzialmente vessatorie")
                compliance["suggerimenti"].append("Richiedere doppia sottoscrizione ex art. 1341 c.c.")

        return compliance

    def _assess_legal_risks(self, category: ItalianDocumentCategory, analysis: dict[str, Any]) -> dict[str, Any]:
        """Assess legal risks and urgency"""
        risk_assessment = {
            "livello_rischio": "basso",
            "urgenza": "normale",
            "fattori_rischio": [],
            "azioni_immediate": [],
        }

        # Check deadlines
        if "scadenze" in analysis:
            for scadenza_key, scadenza_data in analysis["scadenze"].items():
                giorni = scadenza_data.get("giorni_rimanenti", 999)

                if giorni < 0:
                    risk_assessment["livello_rischio"] = "critico"
                    risk_assessment["urgenza"] = "termine_scaduto"
                    risk_assessment["fattori_rischio"].append(f"Termine {scadenza_key} scaduto")
                elif giorni < 5:
                    risk_assessment["livello_rischio"] = "alto"
                    risk_assessment["urgenza"] = "urgentissima"
                    risk_assessment["azioni_immediate"].append(f"Preparare {scadenza_key} entro {giorni} giorni")
                elif giorni < 10:
                    risk_assessment["livello_rischio"] = "medio"
                    risk_assessment["urgenza"] = "urgente"

        # Category-specific risks
        if category == ItalianDocumentCategory.DECRETO_INGIUNTIVO:
            if analysis.get("esecutivo", False):
                risk_assessment["livello_rischio"] = "alto"
                risk_assessment["fattori_rischio"].append("Decreto esecutivo - rischio pignoramento")
                risk_assessment["azioni_immediate"].append("Valutare opposizione e sospensiva")

        elif category == ItalianDocumentCategory.PRECETTO:
            risk_assessment["livello_rischio"] = "alto"
            risk_assessment["urgenza"] = "urgente"
            risk_assessment["fattori_rischio"].append("Rischio esecuzione forzata imminente")
            risk_assessment["azioni_immediate"].append("Pagamento o opposizione entro 10 giorni")

        elif category == ItalianDocumentCategory.CITAZIONE:
            if "valore_causa" in analysis and analysis["valore_causa"] > 50000:
                risk_assessment["fattori_rischio"].append("Causa di valore rilevante")
                if risk_assessment["livello_rischio"] == "basso":
                    risk_assessment["livello_rischio"] = "medio"

        return risk_assessment

    # Additional helper methods...

    def _extract_creditore(self, text: str) -> str | None:
        """Extract creditor from decreto ingiuntivo"""
        patterns = [
            r"(?:a favore di|creditore)\s*[:]*\s*([A-Z][^,\n]{10,50})",
            r"([A-Z][^,\n]{10,50})\s*(?:ha chiesto|ricorrente)",
        ]

        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1).strip()

        return None

    def _extract_debitore(self, text: str) -> str | None:
        """Extract debtor from decreto ingiuntivo"""
        patterns = [
            r"(?:contro|debitore|intimato)\s*[:]*\s*([A-Z][^,\n]{10,50})",
            r"ingiunge a\s+([A-Z][^,\n]{10,50})",
        ]

        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1).strip()

        return None

    def _extract_sender(self, text: str) -> str | None:
        """Extract sender of diffida"""
        patterns = [
            r"(?:Il sottoscritto|La sottoscritta)\s+([A-Z][^,\n]{10,50})",
            r"([A-Z][^,\n]{10,50})\s+(?:diffida|invita)",
        ]

        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1).strip()

        return None

    def _extract_recipient(self, text: str) -> str | None:
        """Extract recipient of diffida"""
        patterns = [r"(?:diffida|invita)\s+([A-Z][^,\n]{10,50})", r"Spett\.le\s+([A-Z][^,\n]{10,50})"]

        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1).strip()

        return None

    def _extract_diffida_object(self, text: str) -> str | None:
        """Extract what the diffida is requesting"""
        patterns = [
            r"diffida(?:to)?\s+a\s+(.{20,200})",
            r"invita(?:to)?\s+a\s+(.{20,200})",
            r"ad\s+adempiere\s+(.{20,200})",
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()

        return None

    def _extract_contract_parties(self, text: str) -> dict[str, Any]:
        """Extract parties from contract"""
        parties = {}

        patterns = [
            r"tra\s+([A-Z][^,\n]{10,50})\s+(?:.*?)\s+e\s+([A-Z][^,\n]{10,50})",
            r"parte\s+(?:venditrice|locatrice|creditrice)\s*[:]*\s*([A-Z][^,\n]{10,50})",
            r"parte\s+(?:acquirente|conduttrice|debitrice)\s*[:]*\s*([A-Z][^,\n]{10,50})",
        ]

        for i, pattern in enumerate(patterns):
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                if i == 0:  # "tra ... e ..." pattern
                    parties["parte_1"] = match.group(1).strip()
                    parties["parte_2"] = match.group(2).strip()
                else:
                    role = "venditore" if "venditrice" in pattern else "acquirente"
                    parties[role] = match.group(1).strip()

        return parties

    def _extract_contract_object(self, text: str) -> str | None:
        """Extract contract object/purpose"""
        patterns = [
            r"(?:oggetto|avente ad oggetto)\s*[:]*\s*(.{20,200})",
            r"(?:vendita|locazione|prestazione)\s+di\s+(.{20,200})",
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()

        return None

    def _extract_contract_price(self, text: str) -> float | None:
        """Extract contract price"""
        patterns = [
            r"(?:prezzo|corrispettivo|canone)\s*(?:di|pari a)?\s*(?:€|euro)\s*([\d\.,]+)",
            r"(?:€|euro)\s*([\d\.,]+)\s*(?:quale|come)\s*(?:prezzo|corrispettivo)",
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return self._parse_italian_amount(match.group(1))

        return None

    def _extract_contract_duration(self, text: str) -> str | None:
        """Extract contract duration"""
        patterns = [
            r"durata\s*(?:di|del contratto)?\s*(?:anni|mesi)\s*(\d+)",
            r"(?:dal|a partire dal)\s*(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4})\s*(?:al|fino al)\s*(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4})",
        ]

        for i, pattern in enumerate(patterns):
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                if i == 0:
                    return f"{match.group(1)} {'anni' if 'anni' in match.group(0) else 'mesi'}"
                else:
                    return f"Dal {match.group(1)} al {match.group(2)}"

        return None

    def _extract_key_clauses(self, text: str) -> list[str]:
        """Extract important contract clauses"""
        clauses = []

        clause_keywords = [
            "risoluzione",
            "recesso",
            "penale",
            "garanzia",
            "riserva",
            "esclusiva",
            "divieto",
            "obbligo",
        ]

        for keyword in clause_keywords:
            pattern = rf"{keyword}(?:\s+di)?(.{{20,100}})"
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                clauses.append(f"{keyword}: {match.group(1).strip()}")

        return clauses[:10]  # Limit to 10 most important

    def _extract_convenuto(self, text: str) -> str | None:
        """Extract defendant from comparsa"""
        patterns = [r"per\s+([A-Z][^,\n]{10,50})\s+convenut", r"nell'interesse di\s+([A-Z][^,\n]{10,50})"]

        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1).strip()

        return None

    def _extract_counterclaims(self, text: str) -> list[str]:
        """Extract counterclaims from comparsa"""
        claims = []

        patterns = [r"domanda riconvenzionale(.{20,200})", r"in via riconvenzionale(.{20,200})"]

        for pattern in patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                claims.append(match.group(1).strip())

        return claims[:5]  # Limit to 5
