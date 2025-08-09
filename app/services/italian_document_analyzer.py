"""
Italian Document Analysis Service for AI-powered Document Understanding.

Provides AI-powered analysis of Italian tax documents with compliance checking,
financial health analysis, and actionable business insights.
"""

import json
import asyncio
from datetime import datetime
from typing import Dict, Any, List, Optional, Union

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

from app.core.config import settings
from app.core.logging import logger


class ItalianDocumentAnalyzer:
  """AI-powered analyzer for Italian tax and financial documents"""
  
  def __init__(self):
    self.settings = settings
    self.llm = ChatOpenAI(
      model=self.settings.LLM_MODEL,
      api_key=self.settings.LLM_API_KEY,
      temperature=0.1,  # Low temperature for factual analysis
      max_tokens=2000
    )
  
  async def analyze_document(
    self, 
    document_data: Dict[str, Any], 
    query: str,
    analysis_type: str = "general"
  ) -> Dict[str, Any]:
    """
    Analyze document with AI and provide structured response.
    
    Args:
      document_data: Structured data extracted from document
      query: User's analysis question
      analysis_type: Type of analysis (compliance_check, financial_analysis, etc.)
      
    Returns:
      Dictionary with analysis results
    """
    try:
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
        "timestamp": datetime.utcnow().isoformat()
      }
      
    except Exception as e:
      logger.error(f"Document analysis failed: {str(e)}")
      return {
        "success": False,
        "error": str(e),
        "analysis_type": analysis_type
      }
  
  async def compare_documents(
    self, 
    documents_data: List[Dict[str, Any]], 
    query: str
  ) -> Dict[str, Any]:
    """
    Compare multiple documents and provide insights.
    
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
        "timestamp": datetime.utcnow().isoformat()
      }
      
    except Exception as e:
      logger.error(f"Document comparison failed: {str(e)}")
      return {
        "success": False,
        "error": str(e),
        "comparison_type": "multi_document"
      }
  
  async def generate_insights(
    self, 
    document_data: Dict[str, Any], 
    query: str
  ) -> Dict[str, Any]:
    """
    Generate actionable business insights from document data.
    
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
        "timestamp": datetime.utcnow().isoformat()
      }
      
    except Exception as e:
      logger.error(f"Insights generation failed: {str(e)}")
      return {
        "success": False,
        "error": str(e),
        "insights_type": "actionable_business"
      }
  
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
"""
    }
    
    return base_prompt + type_specific.get(analysis_type, type_specific["general"])
  
  def _build_user_prompt(self, document_data: Dict[str, Any], query: str) -> str:
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
  
  def _build_comparison_user_prompt(
    self, 
    documents_data: List[Dict[str, Any]], 
    query: str
  ) -> str:
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
  
  def _build_insights_user_prompt(
    self, 
    document_data: Dict[str, Any], 
    query: str
  ) -> str:
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
  
  async def _analyze_with_llm(
    self, 
    system_prompt: str, 
    user_prompt: str
  ) -> Dict[str, Any]:
    """Execute LLM analysis with prompts"""
    messages = [
      SystemMessage(content=system_prompt),
      HumanMessage(content=user_prompt)
    ]
    
    try:
      # Call LLM
      response = await self.llm.ainvoke(messages)
      
      # Try to parse as JSON
      try:
        result = json.loads(response.content)
        return result
      except json.JSONDecodeError:
        # Fallback: wrap response as general analysis
        return {
          "analysis": {"general_response": True},
          "response": response.content,
          "confidence_score": 75
        }
        
    except Exception as e:
      logger.error(f"LLM analysis failed: {str(e)}")
      raise
  
  def _post_process_analysis(
    self, 
    raw_result: Dict[str, Any], 
    analysis_type: str
  ) -> Dict[str, Any]:
    """Post-process and validate analysis results"""
    # Ensure required fields exist
    processed = {
      "analysis": raw_result.get("analysis", {}),
      "response": raw_result.get("response", "Analisi completata."),
      "confidence_score": raw_result.get("confidence_score", 80)
    }
    
    # Add type-specific validation
    if analysis_type == "compliance_check":
      if "compliance_score" not in processed["analysis"]:
        processed["analysis"]["compliance_score"] = 80
      if "compliance_status" not in processed["analysis"]:
        score = processed["analysis"]["compliance_score"]
        processed["analysis"]["compliance_status"] = (
          "compliant" if score >= 80 else 
          "partial" if score >= 60 else 
          "non_compliant"
        )
    
    elif analysis_type == "financial_analysis":
      if "health_score" not in processed["analysis"]:
        processed["analysis"]["health_score"] = 75
      if "financial_health" not in processed["analysis"]:
        score = processed["analysis"]["health_score"]
        processed["analysis"]["financial_health"] = (
          "excellent" if score >= 90 else
          "good" if score >= 75 else
          "fair" if score >= 60 else
          "poor"
        )
    
    return processed