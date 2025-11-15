"""Italian Document Analysis Service for AI-powered Document Understanding.

Provides AI-powered analysis of Italian tax, financial, and legal documents with
compliance checking, financial health analysis, and actionable business insights.
"""

import asyncio
import json
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from app.core.config import settings
from app.core.logging import logger
from app.models.document_simple import ItalianDocumentCategory
from app.services.legal_document_analyzer import ItalianLegalDocumentAnalyzer


class ItalianDocumentAnalyzer:
    """AI-powered analyzer for Italian tax, financial, and legal documents"""

    # Legal document categories
    LEGAL_CATEGORIES = {
        ItalianDocumentCategory.CITAZIONE,
        ItalianDocumentCategory.RICORSO,
        ItalianDocumentCategory.DECRETO_INGIUNTIVO,
        ItalianDocumentCategory.ATTO_GIUDIZIARIO,
        ItalianDocumentCategory.DIFFIDA,
        ItalianDocumentCategory.CONTRATTO,
        ItalianDocumentCategory.VERBALE,
        ItalianDocumentCategory.SENTENZA,
        ItalianDocumentCategory.ORDINANZA,
        ItalianDocumentCategory.PRECETTO,
        ItalianDocumentCategory.COMPARSA,
        ItalianDocumentCategory.MEMORIA,
    }

    def __init__(self):
        self.settings = settings
        self.llm = ChatOpenAI(
            model=self.settings.LLM_MODEL,
            api_key=self.settings.LLM_API_KEY,
            temperature=0.1,  # Low temperature for factual analysis
            max_tokens=2000,
        )
        # Initialize legal document analyzer
        self.legal_analyzer = ItalianLegalDocumentAnalyzer()

    async def analyze_document(
        self,
        document_data: dict[str, Any],
        query: str,
        analysis_type: str = "general",
        document_category: str | None = None,
        extracted_text: str | None = None,
    ) -> dict[str, Any]:
        """Analyze document with AI and provide structured response.

        Args:
          document_data: Structured data extracted from document
          query: User's analysis question
          analysis_type: Type of analysis (compliance_check, financial_analysis, etc.)
          document_category: Category of document for specialized analysis
          extracted_text: Full text extracted from document

        Returns:
          Dictionary with analysis results
        """
        try:
            # Check if this is a legal document that requires specialized analysis
            if document_category and self._is_legal_document(document_category):
                logger.info(f"Using specialized legal analysis for {document_category}")
                return await self._analyze_legal_document(
                    document_category, extracted_text or "", document_data, query
                )

            # Standard tax/financial document analysis
            # Build analysis prompt based on type
            system_prompt = self._build_system_prompt(analysis_type)
            user_prompt = self._build_user_prompt(document_data, query)

            # Execute LLM analysis
            analysis_result = await self._analyze_with_llm(system_prompt, user_prompt)

            # Post-process and validate results
            processed_result = self._post_process_analysis(analysis_result, analysis_type)

            return {
                "success": True,
                "analysis": processed_result["analysis"],
                "response": processed_result["response"],
                "confidence_score": processed_result.get("confidence_score", 85),
                "analysis_type": analysis_type,
                "timestamp": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            logger.error(f"Document analysis failed: {str(e)}")
            return {"success": False, "error": str(e), "analysis_type": analysis_type}

    async def compare_documents(self, documents_data: list[dict[str, Any]], query: str) -> dict[str, Any]:
        """Compare multiple documents and provide insights.

        Args:
          documents_data: List of document data to compare
          query: Comparison question

        Returns:
          Dictionary with comparison analysis
        """
        try:
            system_prompt = self._build_comparison_system_prompt()
            user_prompt = self._build_comparison_user_prompt(documents_data, query)

            comparison_result = await self._analyze_with_llm(system_prompt, user_prompt)

            return {
                "success": True,
                "analysis": comparison_result["analysis"],
                "response": comparison_result["response"],
                "confidence_score": comparison_result.get("confidence_score", 80),
                "comparison_type": "multi_document",
                "documents_count": len(documents_data),
                "timestamp": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            logger.error(f"Document comparison failed: {str(e)}")
            return {"success": False, "error": str(e), "comparison_type": "multi_document"}

    async def generate_insights(self, document_data: dict[str, Any], query: str) -> dict[str, Any]:
        """Generate actionable business insights from document data.

        Args:
          document_data: Structured document data
          query: Question about insights needed

        Returns:
          Dictionary with insights and recommendations
        """
        try:
            system_prompt = self._build_insights_system_prompt()
            user_prompt = self._build_insights_user_prompt(document_data, query)

            insights_result = await self._analyze_with_llm(system_prompt, user_prompt)

            return {
                "success": True,
                "analysis": insights_result["analysis"],
                "response": insights_result["response"],
                "confidence_score": insights_result.get("confidence_score", 82),
                "insights_type": "actionable_business",
                "timestamp": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            logger.error(f"Insights generation failed: {str(e)}")
            return {"success": False, "error": str(e), "insights_type": "actionable_business"}

    def _build_system_prompt(self, analysis_type: str) -> str:
        """Build system prompt based on analysis type"""
        base_prompt = """Sei un esperto consulente fiscale italiano con oltre 20 anni di esperienza.
Analizza i documenti fiscali italiani fornendo consigli precisi, conformi alla normativa italiana vigente.

Rispondi sempre in italiano, usando terminologia tecnica appropriata."""

        type_specific = {
            "compliance_check": """
FOCUS: Verifica di conformità normativa
- Controlla la correttezza formale del documento
- Identifica eventuali errori o omissioni
- Valuta la conformità con la normativa fiscale italiana
- Fornisci un punteggio di conformità (0-100)
- Elenca eventuali problemi e raccomandazioni per risolverli
""",
            "financial_analysis": """
FOCUS: Analisi della salute finanziaria
- Analizza gli indicatori finanziari chiave
- Calcola ratios e indici di performance
- Identifica punti di forza e criticità
- Fornisci un punteggio di salute finanziaria (0-100)
- Suggerisci azioni per migliorare la situazione
""",
            "general": """
FOCUS: Analisi generale del documento
- Riassumi il contenuto principale
- Identifica gli aspetti più rilevanti
- Rispondi alla domanda specifica dell'utente
- Fornisci consigli pratici e actionable
""",
        }

        return base_prompt + type_specific.get(analysis_type, type_specific["general"])

    def _build_user_prompt(self, document_data: dict[str, Any], query: str) -> str:
        """Build user prompt with document data and query"""
        return f"""DOCUMENTO DA ANALIZZARE:
{json.dumps(document_data, indent=2, ensure_ascii=False)}

DOMANDA DELL'UTENTE:
{query}

Fornisci una risposta strutturata in formato JSON con:
1. "analysis": oggetto con i risultati dell'analisi specifica
2. "response": risposta in linguaggio naturale (in italiano)
3. "confidence_score": punteggio di affidabilità (0-100)

Rispondi in modo preciso, professionale e orientato all'azione."""

    def _build_comparison_system_prompt(self) -> str:
        """Build system prompt for document comparison"""
        return """Sei un esperto consulente fiscale italiano specializzato nell'analisi comparativa.
Confronta documenti fiscali e finanziari fornendo insights sui trend e cambiamenti.

FOCUS: Analisi comparativa
- Identifica differenze significative tra i documenti
- Calcola variazioni percentuali e trend
- Evidenzia miglioramenti o peggioramenti
- Fornisci interpretazione dei cambiamenti
- Suggerisci azioni basate sui trend identificati

Rispondi sempre in italiano con terminologia tecnica appropriata."""

    def _build_comparison_user_prompt(self, documents_data: list[dict[str, Any]], query: str) -> str:
        """Build user prompt for document comparison"""
        docs_json = json.dumps(documents_data, indent=2, ensure_ascii=False)

        return f"""DOCUMENTI DA CONFRONTARE:
{docs_json}

DOMANDA DELL'UTENTE:
{query}

Fornisci un'analisi comparativa strutturata in formato JSON con:
1. "analysis": oggetto con risultati del confronto (variazioni, trend, etc.)
2. "response": spiegazione del confronto in linguaggio naturale (in italiano)
3. "confidence_score": punteggio di affidabilità (0-100)

Concentrati sui cambiamenti più significativi e le loro implicazioni."""

    def _build_insights_system_prompt(self) -> str:
        """Build system prompt for insights generation"""
        return """Sei un consulente fiscale senior italiano focalizzato sulla consulenza strategica.
Genera insights actionable per aiutare le aziende a migliorare la gestione fiscale e finanziaria.

FOCUS: Insights e raccomandazioni strategiche
- Identifica opportunità di ottimizzazione fiscale
- Suggerisci prossimi adempimenti e scadenze
- Proponi strategie per ridurre i rischi
- Fornisci timeline di azioni raccomandate
- Quantifica quando possibile i benefici potenziali

Rispondi sempre in italiano con focus su azioni concrete e misurabili."""

    def _build_insights_user_prompt(self, document_data: dict[str, Any], query: str) -> str:
        """Build user prompt for insights generation"""
        return f"""DATI DEL DOCUMENTO:
{json.dumps(document_data, indent=2, ensure_ascii=False)}

RICHIESTA DI INSIGHTS:
{query}

Genera insights actionable in formato JSON con:
1. "analysis": oggetto con insights strutturati (next_deadlines, recommendations, etc.)
2. "response": risposta pratica e orientata all'azione (in italiano)
3. "confidence_score": punteggio di affidabilità (0-100)

Focus su consigli concreti, scadenze e azioni specifiche da intraprendere."""

    async def _analyze_with_llm(self, system_prompt: str, user_prompt: str) -> dict[str, Any]:
        """Execute LLM analysis with prompts"""
        messages = [SystemMessage(content=system_prompt), HumanMessage(content=user_prompt)]

        try:
            # Call LLM
            response = await self.llm.ainvoke(messages)

            # Try to parse as JSON
            try:
                result = json.loads(response.content)
                return result
            except json.JSONDecodeError:
                # Fallback: wrap response as general analysis
                return {"analysis": {"general_response": True}, "response": response.content, "confidence_score": 75}

        except Exception as e:
            logger.error(f"LLM analysis failed: {str(e)}")
            raise

    def _post_process_analysis(self, raw_result: dict[str, Any], analysis_type: str) -> dict[str, Any]:
        """Post-process and validate analysis results"""
        # Ensure required fields exist
        processed = {
            "analysis": raw_result.get("analysis", {}),
            "response": raw_result.get("response", "Analisi completata."),
            "confidence_score": raw_result.get("confidence_score", 80),
        }

        # Add type-specific validation
        if analysis_type == "compliance_check":
            if "compliance_score" not in processed["analysis"]:
                processed["analysis"]["compliance_score"] = 80
            if "compliance_status" not in processed["analysis"]:
                score = processed["analysis"]["compliance_score"]
                processed["analysis"]["compliance_status"] = (
                    "compliant" if score >= 80 else "partial" if score >= 60 else "non_compliant"
                )

        elif analysis_type == "financial_analysis":
            if "health_score" not in processed["analysis"]:
                processed["analysis"]["health_score"] = 75
            if "financial_health" not in processed["analysis"]:
                score = processed["analysis"]["health_score"]
                processed["analysis"]["financial_health"] = (
                    "excellent" if score >= 90 else "good" if score >= 75 else "fair" if score >= 60 else "poor"
                )

        return processed

    def _is_legal_document(self, document_category: str) -> bool:
        """Check if document category is a legal document"""
        try:
            category_enum = ItalianDocumentCategory(document_category)
            return category_enum in self.LEGAL_CATEGORIES
        except ValueError:
            return False

    async def _analyze_legal_document(
        self, document_category: str, extracted_text: str, document_data: dict[str, Any], query: str
    ) -> dict[str, Any]:
        """Analyze legal document using specialized legal analyzer"""
        try:
            # Convert string category to enum
            category_enum = ItalianDocumentCategory(document_category)

            # Use specialized legal analyzer
            legal_result = await self.legal_analyzer.analyze_legal_document(
                document_category=category_enum,
                extracted_text=extracted_text,
                extracted_data=document_data,
                analysis_query=query,
            )

            if legal_result["success"]:
                # Transform legal analysis to match expected format
                return {
                    "success": True,
                    "analysis": legal_result["legal_analysis"],
                    "response": self._format_legal_response(legal_result["legal_analysis"]),
                    "confidence_score": self._calculate_legal_confidence(legal_result["legal_analysis"]),
                    "analysis_type": "legal_document",
                    "document_category": document_category,
                    "timestamp": legal_result["timestamp"],
                }
            else:
                # Fallback to general analysis
                logger.warning(
                    f"Legal analysis failed, falling back to general: {legal_result.get('error', 'Unknown error')}"
                )
                return await self._fallback_to_general_analysis(document_data, query, document_category)

        except Exception as e:
            logger.error(f"Legal document analysis error: {str(e)}")
            # Fallback to general analysis
            return await self._fallback_to_general_analysis(document_data, query, document_category)

    def _format_legal_response(self, legal_analysis: dict[str, Any]) -> str:
        """Format legal analysis into natural language response"""
        try:
            response_parts = []

            # Document type and stage
            if "document_type" in legal_analysis:
                doc_type = legal_analysis["document_type"]
                stage = legal_analysis.get("procedural_stage", "")
                response_parts.append(f"📄 **Tipo documento**: {doc_type} - {stage}")

            # Parties
            if "parti" in legal_analysis:
                parti = legal_analysis["parti"]
                if isinstance(parti, dict):
                    if "attore" in parti:
                        response_parts.append(f"👤 **Attore**: {parti['attore']}")
                    if "convenuto" in parti:
                        response_parts.append(f"👤 **Convenuto**: {parti['convenuto']}")

            # Court and case info
            if "tribunale" in legal_analysis:
                response_parts.append(f"🏛️ **Tribunale**: {legal_analysis['tribunale']}")

            if "numero_rg" in legal_analysis:
                response_parts.append(f"📋 **R.G.**: {legal_analysis['numero_rg']}")

            # Key dates and deadlines
            if "data_udienza" in legal_analysis:
                response_parts.append(f"📅 **Data udienza**: {legal_analysis['data_udienza']}")

            if "scadenze" in legal_analysis:
                response_parts.append("⏰ **Scadenze importanti**:")
                for scadenza_nome, scadenza_info in legal_analysis["scadenze"].items():
                    if isinstance(scadenza_info, dict):
                        giorni = scadenza_info.get("giorni_rimanenti", 0)
                        tipo = scadenza_info.get("tipo", scadenza_nome)
                        urgenza = "🚨 URGENTE" if giorni < 5 else "⚠️ PROSSIMA" if giorni < 15 else "📝"
                        response_parts.append(f"   • {urgenza} {tipo}: {giorni} giorni rimanenti")

            # Amount/value
            if "valore_causa" in legal_analysis:
                valore = legal_analysis["valore_causa"]
                response_parts.append(f"💰 **Valore causa**: €{valore:,.2f}")

            if "importo_decreto" in legal_analysis:
                importo = legal_analysis["importo_decreto"]
                response_parts.append(f"💰 **Importo decreto**: €{importo:,.2f}")

            # Legal basis
            if "fondamento_giuridico" in legal_analysis and legal_analysis["fondamento_giuridico"]:
                norme = ", ".join(legal_analysis["fondamento_giuridico"][:3])  # First 3 references
                response_parts.append(f"⚖️ **Base normativa**: {norme}")

            # Compliance status
            if "compliance_check" in legal_analysis:
                compliance = legal_analysis["compliance_check"]
                status = "✅ Documento valido" if compliance.get("valido", True) else "❌ Problemi rilevati"
                response_parts.append(f"🔍 **Conformità**: {status}")

                if compliance.get("problemi"):
                    response_parts.append("   **Problemi identificati**:")
                    for problema in compliance["problemi"][:3]:  # First 3 problems
                        response_parts.append(f"   • {problema}")

            # Risk assessment
            if "risk_assessment" in legal_analysis:
                risk = legal_analysis["risk_assessment"]
                livello = risk.get("livello_rischio", "basso")
                urgenza = risk.get("urgenza", "normale")

                risk_emoji = {"basso": "🟢", "medio": "🟡", "alto": "🟠", "critico": "🔴"}

                response_parts.append(f"⚠️ **Livello rischio**: {risk_emoji.get(livello, '🟡')} {livello.upper()}")

                if urgenza != "normale":
                    response_parts.append(f"🚨 **Urgenza**: {urgenza.upper()}")

                if risk.get("azioni_immediate"):
                    response_parts.append("🎯 **Azioni immediate**:")
                    for azione in risk["azioni_immediate"][:3]:  # First 3 actions
                        response_parts.append(f"   • {azione}")

            # AI analysis if present
            if "ai_analysis" in legal_analysis and legal_analysis["ai_analysis"].get("risposta"):
                ai_response = legal_analysis["ai_analysis"]["risposta"]
                response_parts.append(f"\n🤖 **Analisi approfondita**:\n{ai_response}")

            # Combine all parts
            if response_parts:
                return "\n".join(response_parts)
            else:
                return f"Documento legale di tipo {legal_analysis.get('document_type', 'generico')} analizzato. Consulta i dettagli nell'analisi strutturata."

        except Exception as e:
            logger.error(f"Error formatting legal response: {str(e)}")
            return "Analisi legale completata. I dettagli sono disponibili nella sezione analisi strutturata."

    def _calculate_legal_confidence(self, legal_analysis: dict[str, Any]) -> int:
        """Calculate confidence score for legal analysis"""
        try:
            confidence = 70  # Base confidence for legal documents

            # Add confidence based on data extracted
            if "tribunale" in legal_analysis:
                confidence += 5
            if "numero_rg" in legal_analysis:
                confidence += 5
            if "parti" in legal_analysis or "ricorrente" in legal_analysis:
                confidence += 5
            if "scadenze" in legal_analysis:
                confidence += 10
            if "compliance_check" in legal_analysis:
                confidence += 5

            # AI analysis adds confidence
            if "ai_analysis" in legal_analysis and legal_analysis["ai_analysis"].get("risposta"):
                confidence += 10

            return min(confidence, 95)  # Cap at 95%

        except Exception:
            return 75  # Default confidence for legal documents

    async def _fallback_to_general_analysis(
        self, document_data: dict[str, Any], query: str, document_category: str
    ) -> dict[str, Any]:
        """Fallback to general analysis when legal analysis fails"""
        try:
            # Use general analysis but with legal context
            system_prompt = f"""Sei un consulente esperto in documenti legali italiani.
Stai analizzando un documento di categoria: {document_category}

Anche se non puoi fare un'analisi legale specializzata, fornisci:
1. Una sintesi del contenuto del documento
2. Identificazione delle parti coinvolte
3. Date e termini rilevanti
4. Suggerimenti generali per la gestione

Rispondi sempre in italiano con linguaggio professionale."""

            user_prompt = f"""DOCUMENTO DA ANALIZZARE:
{json.dumps(document_data, indent=2, ensure_ascii=False)}

DOMANDA DELL'UTENTE:
{query}

Fornisci una risposta strutturata in formato JSON con:
1. "analysis": oggetto con i risultati dell'analisi
2. "response": risposta in linguaggio naturale (in italiano)
3. "confidence_score": punteggio di affidabilità (0-100)"""

            # Execute general analysis
            analysis_result = await self._analyze_with_llm(system_prompt, user_prompt)
            processed_result = self._post_process_analysis(analysis_result, "legal_fallback")

            return {
                "success": True,
                "analysis": processed_result["analysis"],
                "response": f"⚠️ **Analisi generale del documento legale**\n\n{processed_result['response']}\n\n💡 *Per un'analisi legale più approfondita, contatta un avvocato specializzato.*",
                "confidence_score": max(
                    processed_result.get("confidence_score", 60) - 20, 40
                ),  # Lower confidence for fallback
                "analysis_type": "legal_fallback",
                "document_category": document_category,
                "timestamp": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            logger.error(f"Fallback analysis failed: {str(e)}")
            return {
                "success": False,
                "error": f"Analisi del documento legale non riuscita: {str(e)}",
                "analysis_type": "legal_fallback",
            }
