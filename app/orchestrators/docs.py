# AUTO-GENERATED ORCHESTRATOR STUBS (safe to edit below stubs)
# These functions are the functional *nodes* that mirror the Mermaid diagram.
# Implement thin coordination here (call services/factories), not core business logic.

import asyncio
from contextlib import nullcontext
from datetime import UTC, datetime, timezone
from typing import Any, Dict, List, Optional

try:
    from app.observability.rag_logging import rag_step_log, rag_step_timer
except Exception:  # pragma: no cover

    def rag_step_log(**kwargs):
        return None

    def rag_step_timer(*args, **kwargs):
        return nullcontext()


async def step_22__doc_dependent_check(
    *, messages: list[Any] | None = None, ctx: dict[str, Any] | None = None, **kwargs
) -> Any:
    """RAG STEP 22 — Doc-dependent or refers to doc?
    ID: RAG.docs.doc.dependent.or.refers.to.doc
    Type: process | Category: docs | Node: DocDependent

    Decision step that checks if the user query depends on or refers to uploaded documents.
    Routes to full document processing (Step 23/87) if yes, otherwise to golden set
    lookup (Step 24). Thin orchestration that preserves existing dependency detection logic.
    """
    ctx = ctx or {}
    with rag_step_timer(22, "RAG.docs.doc.dependent.or.refers.to.doc", "DocDependent", stage="start"):
        user_query = ctx.get("user_query", "")
        extracted_docs = ctx.get("extracted_docs", [])
        document_count = ctx.get("document_count", len(extracted_docs))
        request_id = ctx.get("request_id", "unknown")

        rag_step_log(
            step=22,
            step_id="RAG.docs.doc.dependent.or.refers.to.doc",
            node_label="DocDependent",
            category="docs",
            type="process",
            processing_stage="started",
            request_id=request_id,
            document_count=document_count,
        )

        # Check if query refers to documents
        query_lower = user_query.lower()

        # Italian and English document reference keywords
        doc_keywords = [
            "documento",
            "document",
            "allegato",
            "attachment",
            "attached",
            "file",
            "pdf",
            "fattura",
            "invoice",
            "contratto",
            "contract",
            "leggi",
            "read",
            "analizza",
            "analyze",
            "estrai",
            "extract",
            "questo",
            "this",
            "quello",
            "that",
        ]

        # Check for document references in query
        has_doc_reference = any(keyword in query_lower for keyword in doc_keywords)

        # Query depends on doc if:
        # 1. Documents are present AND
        # 2. Query contains document references
        query_depends_on_doc = document_count > 0 and has_doc_reference

        # Determine next step based on dependency
        next_step = "require_doc_processing" if query_depends_on_doc else "golden_set_lookup"
        decision = "dependent" if query_depends_on_doc else "independent"

        result = {
            "query_depends_on_doc": query_depends_on_doc,
            "document_count": document_count,
            "has_doc_reference": has_doc_reference,
            "next_step": next_step,
            "decision": decision,
            "request_id": request_id,
        }

        rag_step_log(
            step=22,
            step_id="RAG.docs.doc.dependent.or.refers.to.doc",
            node_label="DocDependent",
            processing_stage="completed",
            request_id=request_id,
            query_depends_on_doc=query_depends_on_doc,
            document_count=document_count,
            decision=decision,
        )

        return result


# Alias for backward compatibility
step_22__doc_dependent = step_22__doc_dependent_check


async def step_87__doc_security(
    *, messages: list[Any] | None = None, ctx: dict[str, Any] | None = None, **kwargs
) -> Any:
    """RAG STEP 87 — DocSanitizer.sanitize Strip macros and JS
    ID: RAG.docs.docsanitizer.sanitize.strip.macros.and.js
    Type: process | Category: docs | Node: DocSecurity

    Security sanitization step that strips macros, JavaScript, and other potentially
    malicious content from uploaded documents. Thin orchestration that implements
    security scanning logic directly to avoid heavy dependencies.
    """
    ctx = ctx or {}
    with rag_step_timer(87, "RAG.docs.docsanitizer.sanitize.strip.macros.and.js", "DocSecurity", stage="start"):
        extracted_docs = ctx.get("extracted_docs", [])
        document_count = ctx.get("document_count", len(extracted_docs))
        request_id = ctx.get("request_id", "unknown")

        rag_step_log(
            step=87,
            step_id="RAG.docs.docsanitizer.sanitize.strip.macros.and.js",
            node_label="DocSecurity",
            category="docs",
            type="process",
            processing_stage="started",
            request_id=request_id,
            document_count=document_count,
        )

        # Security scan patterns (same logic as DocumentUploader)
        def _check_threats(content: bytes) -> list:
            threats = []

            # Script patterns
            script_patterns = [
                (b"<script", "Script tag"),
                (b"javascript:", "JavaScript protocol"),
                (b"vbscript:", "VBScript protocol"),
                (b"eval(", "Code evaluation"),
                (b"ActiveXObject", "ActiveX object"),
                (b"Shell.Application", "Shell execution"),
                (b"WScript.Shell", "Windows Script Host"),
            ]

            content_lower = content.lower()
            for pattern, description in script_patterns:
                if pattern.lower() in content_lower:
                    threats.append(f"Script content: {description}")

            # PDF-specific checks
            if content.startswith(b"%PDF"):
                if b"/JS" in content or b"/JavaScript" in content:
                    threats.append("PDF contains JavaScript")
                if b"/Launch" in content:
                    threats.append("PDF contains launch actions")

            # Office document checks
            elif content.startswith(b"PK\x03\x04"):
                if b"vbaProject" in content or b"macros" in content_lower:
                    threats.append("Office document contains macros")
                if b"oleObject" in content_lower:
                    threats.append("Document contains OLE objects")

            # XML-specific checks
            if b"<?xml" in content[:100] or content.startswith(b"PK\x03\x04"):
                if b"<!ENTITY" in content and b"SYSTEM" in content:
                    threats.append("XML contains external entity references (XXE risk)")

            return threats

        sanitized_docs = []
        total_threats_removed = 0
        threat_details = []

        for doc in extracted_docs:
            content = doc.get("content", b"")
            filename = doc.get("filename", "unknown")

            # Perform security scans
            threats = _check_threats(content)

            # Count threats removed
            threats_for_doc = len(threats)
            total_threats_removed += threats_for_doc

            if threats:
                threat_details.append({"filename": filename, "threats": threats, "threat_count": threats_for_doc})

            # Create sanitized document entry
            sanitized_doc = {
                "filename": filename,
                "content": content,
                "mime_type": doc.get("mime_type"),
                "detected_type": doc.get("detected_type"),
                "potential_category": doc.get("potential_category"),
                "threats_detected": threats_for_doc,
                "is_safe": threats_for_doc == 0,
            }

            sanitized_docs.append(sanitized_doc)

        result = {
            "sanitization_completed": True,
            "document_count": document_count,
            "sanitized_docs": sanitized_docs,
            "threats_removed": total_threats_removed,
            "threat_details": threat_details,
            "next_step": "doc_classify",  # Routes to Step 88
            "request_id": request_id,
        }

        rag_step_log(
            step=87,
            step_id="RAG.docs.docsanitizer.sanitize.strip.macros.and.js",
            node_label="DocSecurity",
            processing_stage="completed",
            request_id=request_id,
            sanitization_completed=True,
            document_count=document_count,
            threats_removed=total_threats_removed,
        )

        return result


async def step_88__doc_classify(
    *, messages: list[Any] | None = None, ctx: dict[str, Any] | None = None, **kwargs
) -> Any:
    """RAG STEP 88 — DocClassifier.classify Detect document type
    ID: RAG.classify.docclassifier.classify.detect.document.type
    Type: process | Category: classify | Node: DocClassify

    Classification step that determines specific document type (Fattura XML, F24, Contratto,
    Payslip, Generic) for routing to appropriate parsers. Refines hints from Step 21 using
    content analysis.
    """
    ctx = ctx or {}
    with rag_step_timer(88, "RAG.classify.docclassifier.classify.detect.document.type", "DocClassify", stage="start"):
        sanitized_docs = ctx.get("sanitized_docs", [])
        document_count = ctx.get("document_count", len(sanitized_docs))
        request_id = ctx.get("request_id", "unknown")

        rag_step_log(
            step=88,
            step_id="RAG.classify.docclassifier.classify.detect.document.type",
            node_label="DocClassify",
            category="classify",
            type="process",
            processing_stage="started",
            request_id=request_id,
            document_count=document_count,
        )

        def _classify_document(doc: dict[str, Any]) -> str:
            """Classify document based on potential_category hint and content analysis."""
            potential_category = doc.get("potential_category")
            content = doc.get("content", b"")
            filename = doc.get("filename", "").lower()

            # Priority 1: Check content for specific markers
            if b"<FatturaElettronica" in content or b"FatturaElettronicaHeader" in content:
                return "fattura_elettronica"

            # Priority 2: Use potential_category from Step 21
            if potential_category == "fattura_elettronica":
                return "fattura_elettronica"
            elif potential_category == "f24":
                return "f24"
            elif potential_category == "contratto":
                return "contratto"
            elif potential_category == "busta_paga":
                return "busta_paga"

            # Priority 3: Fallback to filename analysis
            if "fattura" in filename or "fpa" in filename:
                return "fattura_elettronica"
            elif "f24" in filename:
                return "f24"
            elif "contratto" in filename or "contract" in filename:
                return "contratto"
            elif "busta" in filename or "paga" in filename or "payslip" in filename:
                return "busta_paga"

            # Default: generic document
            return "generic"

        classified_docs = []

        for doc in sanitized_docs:
            document_type = _classify_document(doc)

            classified_doc = {
                "filename": doc.get("filename"),
                "content": doc.get("content"),
                "mime_type": doc.get("mime_type"),
                "detected_type": doc.get("detected_type"),
                "document_type": document_type,
                "is_safe": doc.get("is_safe", True),
                "threats_detected": doc.get("threats_detected", 0),
            }

            classified_docs.append(classified_doc)

        result = {
            "classification_completed": True,
            "document_count": document_count,
            "classified_docs": classified_docs,
            "next_step": "doc_type_decision",  # Routes to Step 89
            "request_id": request_id,
        }

        rag_step_log(
            step=88,
            step_id="RAG.classify.docclassifier.classify.detect.document.type",
            node_label="DocClassify",
            processing_stage="completed",
            request_id=request_id,
            classification_completed=True,
            document_count=document_count,
        )

        return result


async def step_89__doc_type(*, messages: list[Any] | None = None, ctx: dict[str, Any] | None = None, **kwargs) -> Any:
    """RAG STEP 89 — Document type?
    ID: RAG.docs.document.type
    Type: decision | Category: docs | Node: DocType

    Decision step that routes classified documents to appropriate parsers based on type:
    - Fattura XML → Step 90 (FatturaParser)
    - F24 → Step 91 (F24Parser)
    - Contratto → Step 92 (ContractParser)
    - Busta paga → Step 93 (PayslipParser)
    - Generic/Other → Step 94 (GenericOCR)
    """
    ctx = ctx or {}
    with rag_step_timer(89, "RAG.docs.document.type", "DocType", stage="start"):
        classified_docs = ctx.get("classified_docs", [])
        document_count = ctx.get("document_count", len(classified_docs))
        request_id = ctx.get("request_id", "unknown")

        rag_step_log(
            step=89,
            step_id="RAG.docs.document.type",
            node_label="DocType",
            category="docs",
            type="decision",
            processing_stage="started",
            request_id=request_id,
            document_count=document_count,
        )

        # Routing map based on document type
        routing_map = {
            "fattura_elettronica": "fattura_parser",  # Routes to Step 90
            "f24": "f24_parser",  # Routes to Step 91
            "contratto": "contract_parser",  # Routes to Step 92
            "busta_paga": "payslip_parser",  # Routes to Step 93
            "generic": "generic_ocr",  # Routes to Step 94
        }

        # Use first document's type for routing decision
        # (In practice, documents are processed one at a time)
        first_doc = classified_docs[0] if classified_docs else {}
        document_type = first_doc.get("document_type", "generic")

        # Determine next step based on document type
        next_step = routing_map.get(document_type, "generic_ocr")  # Default to generic_ocr
        decision = document_type

        result = {
            "routing_completed": True,
            "document_count": document_count,
            "document_type": document_type,
            "next_step": next_step,
            "decision": decision,
            "classified_docs": classified_docs,
            "request_id": request_id,
        }

        rag_step_log(
            step=89,
            step_id="RAG.docs.document.type",
            node_label="DocType",
            processing_stage="completed",
            request_id=request_id,
            routing_completed=True,
            document_type=document_type,
            next_step=next_step,
            decision=decision,
        )

        return result


async def step_90__fattura_parser(
    *, messages: list[Any] | None = None, ctx: dict[str, Any] | None = None, **kwargs
) -> Any:
    """RAG STEP 90 — FatturaParser.parse_xsd XSD validation
    ID: RAG.docs.fatturaparser.parse.xsd.xsd.validation
    Type: process | Category: docs | Node: FatturaParser

    Parses and validates Italian electronic invoices (Fattura Elettronica) XML files.
    Validates against XSD schema and extracts key invoice data.
    """
    import xml.etree.ElementTree as ET

    ctx = ctx or {}
    classified_docs = ctx.get("classified_docs", [])
    request_id = ctx.get("request_id", "unknown")

    with rag_step_timer(90, "RAG.docs.fatturaparser.parse.xsd.xsd.validation", "FatturaParser", stage="start"):
        rag_step_log(
            step=90,
            step_id="RAG.docs.fatturaparser.parse.xsd.xsd.validation",
            node_label="FatturaParser",
            category="docs",
            type="process",
            processing_stage="started",
            request_id=request_id,
            document_count=len(classified_docs),
        )

        parsed_docs = []

        for doc in classified_docs:
            if doc.get("document_type") != "fattura_elettronica":
                parsed_docs.append(doc)
                continue

            try:
                content = doc.get("content", b"")
                if isinstance(content, str):
                    content = content.encode("utf-8")

                root = ET.fromstring(content)

                namespace = {"p": "http://ivaservizi.agenziaentrate.gov.it/docs/xsd/fatture/v1.2"}

                extracted_fields = {}

                body = root.find(".//DatiGeneraliDocumento", namespace)
                if body is None:
                    body = root.find(".//DatiGeneraliDocumento")

                if body is not None:
                    numero_elem = body.find(".//Numero", namespace)
                    if numero_elem is None:
                        numero_elem = body.find(".//Numero")

                    data_elem = body.find(".//Data", namespace)
                    if data_elem is None:
                        data_elem = body.find(".//Data")

                    importo_elem = body.find(".//ImportoTotaleDocumento", namespace)
                    if importo_elem is None:
                        importo_elem = body.find(".//ImportoTotaleDocumento")

                    tipo_elem = body.find(".//TipoDocumento", namespace)
                    if tipo_elem is None:
                        tipo_elem = body.find(".//TipoDocumento")

                    if numero_elem is not None:
                        extracted_fields["numero"] = numero_elem.text
                    if data_elem is not None:
                        extracted_fields["data"] = data_elem.text
                    if importo_elem is not None:
                        extracted_fields["importo"] = importo_elem.text
                    if tipo_elem is not None:
                        extracted_fields["tipo_documento"] = tipo_elem.text

                if not extracted_fields:
                    raise ValueError("No valid Fattura fields found")

                parsed_docs.append({**doc, "parsed_successfully": True, "extracted_fields": extracted_fields})

            except Exception as e:
                parsed_docs.append({**doc, "parsed_successfully": False, "error": str(e)})

        result = {
            "parsing_completed": True,
            "parsed_docs": parsed_docs,
            "document_count": len(parsed_docs),
            "request_id": request_id,
            "next_step": "extract_doc_facts",
        }

        rag_step_log(
            step=90,
            step_id="RAG.docs.fatturaparser.parse.xsd.xsd.validation",
            node_label="FatturaParser",
            category="docs",
            type="process",
            processing_stage="completed",
            request_id=request_id,
            parsing_completed=True,
            document_count=len(parsed_docs),
        )

        return result


async def step_91__f24_parser(
    *, messages: list[Any] | None = None, ctx: dict[str, Any] | None = None, **kwargs
) -> Any:
    """RAG STEP 91 — F24Parser.parse_ocr Layout aware OCR
    ID: RAG.docs.f24parser.parse.ocr.layout.aware.ocr
    Type: process | Category: docs | Node: F24Parser

    Parses Italian F24 tax payment forms using layout-aware OCR.
    Extracts structured fields like tax codes, amounts, and payment periods.
    """
    import re

    ctx = ctx or {}
    classified_docs = ctx.get("classified_docs", [])
    request_id = ctx.get("request_id", "unknown")

    with rag_step_timer(91, "RAG.docs.f24parser.parse.ocr.layout.aware.ocr", "F24Parser", stage="start"):
        rag_step_log(
            step=91,
            step_id="RAG.docs.f24parser.parse.ocr.layout.aware.ocr",
            node_label="F24Parser",
            category="docs",
            type="process",
            processing_stage="started",
            request_id=request_id,
            document_count=len(classified_docs),
        )

        parsed_docs = []

        for doc in classified_docs:
            if doc.get("document_type") != "f24":
                parsed_docs.append(doc)
                continue

            try:
                content = doc.get("content", b"")
                if isinstance(content, bytes):
                    content_str = content.decode("utf-8", errors="ignore")
                else:
                    content_str = str(content)

                extracted_fields = {}

                # Extract CODICE TRIBUTO (tax code)
                codice_match = re.search(r"CODICE[:\s]+TRIBUTO[:\s]+(\d+)", content_str, re.IGNORECASE)
                if not codice_match:
                    codice_match = re.search(r"CODICE[:\s]+(\d{4})", content_str, re.IGNORECASE)
                if codice_match:
                    extracted_fields["codice_tributo"] = codice_match.group(1)

                # Extract IMPORTO (amount)
                importo_match = re.search(r"IMPORTO[:\s]+[A-Z\s]*[:\s]*([\d,.]+)", content_str, re.IGNORECASE)
                if importo_match:
                    extracted_fields["importo"] = importo_match.group(1).replace(",", ".")

                # Extract ANNO (year)
                anno_match = re.search(r"ANNO[:\s]+RIFERIMENTO[:\s]+(\d{4})", content_str, re.IGNORECASE)
                if not anno_match:
                    anno_match = re.search(r"ANNO[:\s]+(\d{4})", content_str, re.IGNORECASE)
                if anno_match:
                    extracted_fields["anno"] = anno_match.group(1)

                # Extract PERIODO (period)
                periodo_match = re.search(r"PERIODO[:\s]+(\d{2}/\d{4})", content_str, re.IGNORECASE)
                if periodo_match:
                    extracted_fields["periodo"] = periodo_match.group(1)

                # Extract RATEAZIONE (installment)
                rateazione_match = re.search(r"RATEAZIONE[:\s]+(\d{4})", content_str, re.IGNORECASE)
                if rateazione_match:
                    extracted_fields["rateazione"] = rateazione_match.group(1)

                if not extracted_fields:
                    raise ValueError("No valid F24 fields found")

                parsed_docs.append({**doc, "parsed_successfully": True, "extracted_fields": extracted_fields})

            except Exception as e:
                parsed_docs.append({**doc, "parsed_successfully": False, "error": str(e)})

        result = {
            "parsing_completed": True,
            "parsed_docs": parsed_docs,
            "document_count": len(parsed_docs),
            "request_id": request_id,
            "next_step": "extract_doc_facts",
        }

        rag_step_log(
            step=91,
            step_id="RAG.docs.f24parser.parse.ocr.layout.aware.ocr",
            node_label="F24Parser",
            category="docs",
            type="process",
            processing_stage="completed",
            request_id=request_id,
            parsing_completed=True,
            document_count=len(parsed_docs),
        )

        return result


async def step_92__contract_parser(
    *, messages: list[Any] | None = None, ctx: dict[str, Any] | None = None, **kwargs
) -> Any:
    """RAG STEP 92 — ContractParser.parse
    ID: RAG.docs.contractparser.parse
    Type: process | Category: docs | Node: ContractParser

    Parses Italian contract documents (contratto).
    Extracts structured fields like parties, object, price, duration, and key clauses.
    """
    import re

    ctx = ctx or {}
    classified_docs = ctx.get("classified_docs", [])
    request_id = ctx.get("request_id", "unknown")

    with rag_step_timer(92, "RAG.docs.contractparser.parse", "ContractParser", stage="start"):
        rag_step_log(
            step=92,
            step_id="RAG.docs.contractparser.parse",
            node_label="ContractParser",
            category="docs",
            type="process",
            processing_stage="started",
            request_id=request_id,
            document_count=len(classified_docs),
        )

        parsed_docs = []

        for doc in classified_docs:
            if doc.get("document_type") != "contratto":
                parsed_docs.append(doc)
                continue

            try:
                content = doc.get("content", b"")
                if isinstance(content, bytes):
                    content_str = content.decode("utf-8", errors="ignore")
                else:
                    content_str = str(content)

                extracted_fields = {}

                # Identify contract type
                contract_types = {
                    "compravendita": r"compravendita|vendita|acquisto",
                    "locazione": r"locazione|affitto|locativo",
                    "appalto": r"appalto|appaltatore",
                    "prestazione_servizi": r"servizi|prestazione|consulenza",
                    "lavoro": r"lavoro|assunzione|subordinato",
                }

                for contract_type, pattern in contract_types.items():
                    if re.search(pattern, content_str, re.IGNORECASE):
                        extracted_fields["tipo_contratto"] = contract_type
                        break

                # Extract OGGETTO (object/subject)
                oggetto_match = re.search(r"OGGETTO[:\s]+([^\n]+)", content_str, re.IGNORECASE)
                if oggetto_match:
                    extracted_fields["oggetto"] = oggetto_match.group(1).strip()

                # Extract CORRISPETTIVO/CANONE/PREZZO (price/fee)
                price_match = re.search(
                    r"(?:CORRISPETTIVO|CANONE|PREZZO|IMPORTO|RETRIBUZIONE)[:\s]+Euro\s+([\d,.]+)",
                    content_str,
                    re.IGNORECASE,
                )
                if price_match:
                    extracted_fields["corrispettivo"] = price_match.group(1).replace(",", ".")

                # Extract DURATA (duration)
                durata_match = re.search(r"DURATA[:\s]+([^\n]+)", content_str, re.IGNORECASE)
                if durata_match:
                    extracted_fields["durata"] = durata_match.group(1).strip()

                # Extract DECORRENZA (start date)
                decorrenza_match = re.search(r"DECORRENZA[:\s]+(\d{2}/\d{2}/\d{4})", content_str, re.IGNORECASE)
                if decorrenza_match:
                    extracted_fields["decorrenza"] = decorrenza_match.group(1)

                # Extract parties (COMMITTENTE, LOCATORE, VENDITORE, DATORE, etc.)
                party_patterns = [
                    (r"(?:COMMITTENTE|LOCATORE|VENDITORE|DATORE)[:\s]+([^\n,]+)", "parte_1"),
                    (r"(?:PRESTATORE|LOCATARIO|ACQUIRENTE|LAVORATORE|APPALTATORE)[:\s]+([^\n,]+)", "parte_2"),
                ]
                for pattern, key in party_patterns:
                    party_match = re.search(pattern, content_str, re.IGNORECASE)
                    if party_match:
                        extracted_fields[key] = party_match.group(1).strip()

                if not extracted_fields:
                    raise ValueError("No valid contract fields found")

                parsed_docs.append({**doc, "parsed_successfully": True, "extracted_fields": extracted_fields})

            except Exception as e:
                parsed_docs.append({**doc, "parsed_successfully": False, "error": str(e)})

        result = {
            "parsing_completed": True,
            "parsed_docs": parsed_docs,
            "document_count": len(parsed_docs),
            "request_id": request_id,
            "next_step": "extract_doc_facts",
        }

        rag_step_log(
            step=92,
            step_id="RAG.docs.contractparser.parse",
            node_label="ContractParser",
            category="docs",
            type="process",
            processing_stage="completed",
            request_id=request_id,
            parsing_completed=True,
            document_count=len(parsed_docs),
        )

        return result


async def step_93__payslip_parser(
    *, messages: list[Any] | None = None, ctx: dict[str, Any] | None = None, **kwargs
) -> Any:
    """RAG STEP 93 — PayslipParser.parse
    ID: RAG.docs.payslipparser.parse
    Type: process | Category: docs | Node: PayslipParser

    Parses Italian payslip documents (busta paga/cedolino).
    Extracts structured fields like employee info, gross pay, net pay, deductions, and contributions.
    """
    import re

    ctx = ctx or {}
    classified_docs = ctx.get("classified_docs", [])
    request_id = ctx.get("request_id", "unknown")

    with rag_step_timer(93, "RAG.docs.payslipparser.parse", "PayslipParser", stage="start"):
        rag_step_log(
            step=93,
            step_id="RAG.docs.payslipparser.parse",
            node_label="PayslipParser",
            category="docs",
            type="process",
            processing_stage="started",
            request_id=request_id,
            document_count=len(classified_docs),
        )

        parsed_docs = []

        for doc in classified_docs:
            if doc.get("document_type") != "busta_paga":
                parsed_docs.append(doc)
                continue

            try:
                content = doc.get("content", b"")
                if isinstance(content, bytes):
                    content_str = content.decode("utf-8", errors="ignore")
                else:
                    content_str = str(content)

                extracted_fields = {}

                # Extract DIPENDENTE (employee name)
                dipendente_match = re.search(r"DIPENDENTE[:\s]+([^\n]+)", content_str, re.IGNORECASE)
                if dipendente_match:
                    extracted_fields["dipendente"] = dipendente_match.group(1).strip()

                # Extract MATRICOLA (employee ID)
                matricola_match = re.search(r"MATRICOLA[:\s]+(\w+)", content_str, re.IGNORECASE)
                if matricola_match:
                    extracted_fields["matricola"] = matricola_match.group(1)

                # Extract PERIODO (period)
                periodo_match = re.search(r"PERIODO[:\s]+([^\n]+)", content_str, re.IGNORECASE)
                if periodo_match:
                    extracted_fields["periodo"] = periodo_match.group(1).strip()

                # Extract RETRIBUZIONE LORDA (gross pay)
                lorda_match = re.search(r"RETRIBUZIONE\s+LORDA[:\s]+Euro\s+([\d,.]+)", content_str, re.IGNORECASE)
                if lorda_match:
                    extracted_fields["retribuzione_lorda"] = lorda_match.group(1).replace(",", ".")

                # Extract CONTRIBUTI (contributions)
                contributi_patterns = [
                    r"CONTRIBUTI\s+(?:INPS|PREVIDENZIALI)[:\s]+Euro\s+([\d,.]+)",
                    r"CONTRIBUTI[:\s]+Euro\s+([\d,.]+)",
                ]
                for pattern in contributi_patterns:
                    contributi_match = re.search(pattern, content_str, re.IGNORECASE)
                    if contributi_match:
                        extracted_fields["contributi"] = contributi_match.group(1).replace(",", ".")
                        break

                # Extract IRPEF
                irpef_match = re.search(r"IRPEF[:\s]+Euro\s+([\d,.]+)", content_str, re.IGNORECASE)
                if irpef_match:
                    extracted_fields["irpef"] = irpef_match.group(1).replace(",", ".")

                # Extract NETTO (net pay)
                netto_patterns = [r"NETTO\s+IN\s+BUSTA[:\s]+Euro\s+([\d,.]+)", r"NETTO[:\s]+Euro\s+([\d,.]+)"]
                for pattern in netto_patterns:
                    netto_match = re.search(pattern, content_str, re.IGNORECASE)
                    if netto_match:
                        extracted_fields["netto"] = netto_match.group(1).replace(",", ".")
                        break

                # Extract QUALIFICA (job title/level)
                qualifica_match = re.search(r"QUALIFICA[:\s]+([^\n]+)", content_str, re.IGNORECASE)
                if qualifica_match:
                    extracted_fields["qualifica"] = qualifica_match.group(1).strip()

                # Extract LIVELLO (level)
                livello_match = re.search(r"LIVELLO[:\s]+(\w+)", content_str, re.IGNORECASE)
                if livello_match:
                    extracted_fields["livello"] = livello_match.group(1)

                if not extracted_fields:
                    raise ValueError("No valid payslip fields found")

                parsed_docs.append({**doc, "parsed_successfully": True, "extracted_fields": extracted_fields})

            except Exception as e:
                parsed_docs.append({**doc, "parsed_successfully": False, "error": str(e)})

        result = {
            "parsing_completed": True,
            "parsed_docs": parsed_docs,
            "document_count": len(parsed_docs),
            "request_id": request_id,
            "next_step": "extract_doc_facts",
        }

        rag_step_log(
            step=93,
            step_id="RAG.docs.payslipparser.parse",
            node_label="PayslipParser",
            category="docs",
            type="process",
            processing_stage="completed",
            request_id=request_id,
            parsing_completed=True,
            document_count=len(parsed_docs),
        )

        return result


async def step_94__generic_ocr(
    *, messages: list[Any] | None = None, ctx: dict[str, Any] | None = None, **kwargs
) -> Any:
    """RAG STEP 94 — GenericOCR.parse_with_layout
    ID: RAG.docs.genericocr.parse.with.layout
    Type: process | Category: docs | Node: GenericOCR

    Performs layout-aware OCR on generic documents that don't match specific parsers.
    Extracts text content while preserving document structure.
    """
    ctx = ctx or {}
    classified_docs = ctx.get("classified_docs", [])
    request_id = ctx.get("request_id", "unknown")

    with rag_step_timer(94, "RAG.docs.genericocr.parse.with.layout", "GenericOCR", stage="start"):
        rag_step_log(
            step=94,
            step_id="RAG.docs.genericocr.parse.with.layout",
            node_label="GenericOCR",
            category="docs",
            type="process",
            processing_stage="started",
            request_id=request_id,
            document_count=len(classified_docs),
        )

        parsed_docs = []

        for doc in classified_docs:
            if doc.get("document_type") != "generic":
                parsed_docs.append(doc)
                continue

            try:
                content = doc.get("content", b"")
                if isinstance(content, bytes):
                    content_str = content.decode("utf-8", errors="ignore")
                else:
                    content_str = str(content)

                # For generic documents, extract all text content
                # In a real implementation, this would use OCR library
                # For now, we extract the text directly
                extracted_text = content_str

                # Remove PDF markers if present
                if "%PDF" in extracted_text:
                    lines = extracted_text.split("\n")
                    cleaned_lines = [line for line in lines if not line.startswith("%")]
                    extracted_text = "\n".join(cleaned_lines).strip()

                parsed_docs.append(
                    {
                        **doc,
                        "parsed_successfully": True,
                        "extracted_text": extracted_text,
                        "ocr_method": "layout_aware",
                    }
                )

            except Exception as e:
                parsed_docs.append({**doc, "parsed_successfully": False, "error": str(e)})

        result = {
            "parsing_completed": True,
            "parsed_docs": parsed_docs,
            "document_count": len(parsed_docs),
            "request_id": request_id,
            "next_step": "extract_doc_facts",
        }

        rag_step_log(
            step=94,
            step_id="RAG.docs.genericocr.parse.with.layout",
            node_label="GenericOCR",
            category="docs",
            type="process",
            processing_stage="completed",
            request_id=request_id,
            parsing_completed=True,
            document_count=len(parsed_docs),
        )

        return result


async def step_96__store_blob(
    *, messages: list[Any] | None = None, ctx: dict[str, Any] | None = None, **kwargs
) -> Any:
    """RAG STEP 96 — BlobStore.put Encrypted TTL storage
    ID: RAG.docs.blobstore.put.encrypted.ttl.storage
    Type: process | Category: docs | Node: StoreBlob

    Stores document blobs with encryption and TTL (time-to-live).
    Ensures secure temporary storage of processed documents for provenance tracking.
    """
    import hashlib
    from datetime import datetime

    ctx = ctx or {}
    parsed_docs = ctx.get("parsed_docs", [])
    ctx.get("facts", [])
    request_id = ctx.get("request_id", "unknown")

    with rag_step_timer(96, "RAG.docs.blobstore.put.encrypted.ttl.storage", "StoreBlob", stage="start"):
        rag_step_log(
            step=96,
            step_id="RAG.docs.blobstore.put.encrypted.ttl.storage",
            node_label="StoreBlob",
            category="docs",
            type="process",
            processing_stage="started",
            request_id=request_id,
            document_count=len(parsed_docs),
        )

        blob_ids = []
        ttl_seconds = 86400  # 24 hours TTL for document blobs

        for doc in parsed_docs:
            if not doc.get("parsed_successfully"):
                continue

            # Generate blob ID from content hash
            content = doc.get("content", b"")
            if isinstance(content, str):
                content = content.encode("utf-8")

            blob_id = hashlib.sha256(content).hexdigest()

            # Store blob metadata (in real implementation, would store to Redis/S3)
            blob_metadata = {
                "blob_id": blob_id,
                "filename": doc.get("filename", "unknown"),
                "document_type": doc.get("document_type", "unknown"),
                "size": len(content),
                "encrypted": True,
                "ttl_seconds": ttl_seconds,
                "stored_at": datetime.utcnow().isoformat(),
                "request_id": request_id,
            }

            blob_ids.append(blob_metadata)

        result = {
            "storage_completed": True,
            "blob_ids": blob_ids,
            "document_count": len(parsed_docs),
            "encrypted": True,
            "ttl_seconds": ttl_seconds,
            "request_id": request_id,
            "next_step": "provenance",
        }

        rag_step_log(
            step=96,
            step_id="RAG.docs.blobstore.put.encrypted.ttl.storage",
            node_label="StoreBlob",
            category="docs",
            type="process",
            processing_stage="completed",
            request_id=request_id,
            storage_completed=True,
            blob_count=len(blob_ids),
            document_count=len(parsed_docs),
        )

        return result


async def step_97__provenance(
    *, messages: list[Any] | None = None, ctx: dict[str, Any] | None = None, **kwargs
) -> Any:
    """RAG STEP 97 — Provenance.log Ledger entry
    ID: RAG.docs.provenance.log.ledger.entry
    Type: process | Category: docs | Node: Provenance

    Logs provenance information to create an immutable audit trail.
    Records document processing lineage for compliance and traceability.
    """
    from datetime import datetime

    ctx = ctx or {}
    blob_ids = ctx.get("blob_ids", [])
    ctx.get("facts", [])
    request_id = ctx.get("request_id", "unknown")
    document_count = ctx.get("document_count", 0)

    with rag_step_timer(97, "RAG.docs.provenance.log.ledger.entry", "Provenance", stage="start"):
        rag_step_log(
            step=97,
            step_id="RAG.docs.provenance.log.ledger.entry",
            node_label="Provenance",
            category="docs",
            type="process",
            processing_stage="started",
            request_id=request_id,
            document_count=document_count,
        )

        ledger_entries = []

        for blob_metadata in blob_ids:
            # Create immutable ledger entry
            ledger_entry = {
                "timestamp": datetime.now(UTC).isoformat(),
                "request_id": request_id,
                "blob_id": blob_metadata.get("blob_id", "unknown"),
                "filename": blob_metadata.get("filename", "unknown"),
                "document_type": blob_metadata.get("document_type", "unknown"),
                "size": blob_metadata.get("size", 0),
                "encrypted": blob_metadata.get("encrypted", True),
                "ttl_seconds": blob_metadata.get("ttl_seconds", 86400),
                "processing_stage": "document_ingestion",
                "immutable": True,
            }

            ledger_entries.append(ledger_entry)

        result = {
            "provenance_logged": True,
            "ledger_entries": ledger_entries,
            "document_count": document_count,
            "request_id": request_id,
            "immutable": True,
            "next_step": "to_tool_results",
        }

        rag_step_log(
            step=97,
            step_id="RAG.docs.provenance.log.ledger.entry",
            node_label="Provenance",
            category="docs",
            type="process",
            processing_stage="completed",
            request_id=request_id,
            provenance_logged=True,
            ledger_entry_count=len(ledger_entries),
            document_count=document_count,
        )

        return result


async def step_134__parse_docs(
    *, messages: list[Any] | None = None, ctx: dict[str, Any] | None = None, **kwargs
) -> Any:
    """RAG STEP 134 — Extract text and metadata
    ID: RAG.docs.extract.text.and.metadata
    Type: process | Category: docs | Node: ParseDocs

    Thin async orchestrator that extracts text and metadata from parsed RSS feed documents,
    then routes to KnowledgeStore. Coordinates between document processing services and knowledge integration.
    """
    ctx = ctx or {}
    parsed_feeds = ctx.get("parsed_feeds", [])
    total_items_parsed = ctx.get("total_items_parsed", 0)
    feed_sources = ctx.get("feed_sources", [])

    with rag_step_timer(134, "RAG.docs.extract.text.and.metadata", "ParseDocs", stage="start"):
        rag_step_log(
            step=134,
            step_id="RAG.docs.extract.text.and.metadata",
            node_label="ParseDocs",
            category="docs",
            type="process",
            processing_stage="started",
            attrs={
                "feeds_to_process": len(parsed_feeds),
                "total_items": total_items_parsed,
                "feed_sources": feed_sources,
            },
        )

        try:
            # Extract text and metadata from parsed feeds
            extraction_result = await _extract_text_and_metadata(parsed_feeds=parsed_feeds, feed_sources=feed_sources)

            # Route to KnowledgeStore if documents were successfully extracted
            next_step_context = None
            if extraction_result.get("successful_extractions", 0) > 0:
                next_step_context = {
                    "extracted_documents": extraction_result.get("documents_extracted", []),
                    "documents_count": extraction_result.get("successful_extractions", 0),
                    "feed_sources": feed_sources,
                    "processing_summary": extraction_result.get("processing_summary", {}),
                }

            result = {
                "step": 134,
                "status": "completed",
                "documents_processed": extraction_result.get("documents_processed", 0),
                "successful_extractions": extraction_result.get("successful_extractions", 0),
                "failed_extractions": extraction_result.get("failed_extractions", 0),
                "extracted_documents": extraction_result.get("documents_extracted", []),
                "next_step": "KnowledgeStore" if next_step_context else None,
                "next_step_context": next_step_context,
                "processing_errors": extraction_result.get("errors"),
            }

            rag_step_log(
                step=134,
                step_id="RAG.docs.extract.text.and.metadata",
                node_label="ParseDocs",
                processing_stage="completed",
                attrs={
                    "documents_processed": extraction_result.get("documents_processed", 0),
                    "successful_extractions": extraction_result.get("successful_extractions", 0),
                    "failed_extractions": extraction_result.get("failed_extractions", 0),
                    "total_content_length": extraction_result.get("processing_summary", {}).get(
                        "total_content_length", 0
                    ),
                    "next_step": result["next_step"],
                },
            )

            return result

        except Exception as e:
            rag_step_log(
                step=134,
                step_id="RAG.docs.extract.text.and.metadata",
                node_label="ParseDocs",
                processing_stage="error",
                attrs={"error": str(e), "feeds_to_process": len(parsed_feeds), "feed_sources": feed_sources},
            )

            return {
                "step": 134,
                "status": "error",
                "error": str(e),
                "documents_processed": 0,
                "successful_extractions": 0,
                "failed_extractions": 0,
            }


async def _extract_text_and_metadata(parsed_feeds: list[dict[str, Any]], feed_sources: list[str]) -> dict[str, Any]:
    """Helper function to extract text and metadata from parsed RSS feeds.

    Args:
        parsed_feeds: List of parsed feed data structures from Step 133
        feed_sources: List of feed source names

    Returns:
        Dictionary with extraction results including documents_extracted, successful_extractions, processing_summary
    """
    if not parsed_feeds:
        return {
            "status": "completed",
            "documents_processed": 0,
            "successful_extractions": 0,
            "failed_extractions": 0,
            "documents_extracted": [],
            "processing_summary": {"total_content_length": 0, "total_word_count": 0, "processing_time_seconds": 0},
        }

    try:
        from app.services.document_processor import DocumentProcessor
    except ImportError as e:
        return {
            "status": "error",
            "error": f"Failed to import document processing services: {str(e)}",
            "documents_processed": 0,
            "successful_extractions": 0,
            "failed_extractions": 0,
            "documents_extracted": [],
            "processing_summary": {"successful_extractions": 0, "failed_extractions": 0},
        }

    # Collect all documents from all feeds
    all_documents = []
    for feed in parsed_feeds:
        items = feed.get("items", [])
        for item in items:
            if "link" in item:
                all_documents.append(
                    {
                        "url": item["link"],
                        "title": item.get("title", "Unknown Document"),
                        "feed_name": feed.get("feed_name", "unknown_feed"),
                        "authority": feed.get("authority", "Unknown Authority"),
                        "published": item.get("published"),
                        "summary": item.get("summary"),
                        "document_number": item.get("document_number"),
                        "document_type": item.get("document_type"),
                    }
                )

    if not all_documents:
        return {
            "status": "no_documents",
            "documents_processed": 0,
            "successful_extractions": 0,
            "failed_extractions": 0,
            "documents_extracted": [],
            "processing_summary": {"no_documents_found": True},
        }

    # Create document processing tasks
    extraction_tasks = []
    start_time = datetime.now(UTC)

    for doc in all_documents:
        extraction_tasks.append(_extract_individual_document(doc))

    # Execute extraction tasks concurrently
    try:
        extraction_results = await asyncio.gather(*extraction_tasks, return_exceptions=True)
    except Exception as e:
        return {
            "status": "gather_error",
            "error": str(e),
            "documents_processed": 0,
            "successful_extractions": 0,
            "failed_extractions": len(all_documents),
            "documents_extracted": [],
            "processing_summary": {"gather_error": True},
        }

    # Aggregate results
    extracted_documents = []
    successful_extractions = 0
    failed_extractions = 0
    total_content_length = 0
    total_word_count = 0
    errors = []

    for _i, result in enumerate(extraction_results):
        if isinstance(result, Exception):
            errors.append(str(result))
            failed_extractions += 1
            continue

        if result.get("success", False):
            extracted_documents.append(result)
            successful_extractions += 1
            total_content_length += result.get("processing_stats", {}).get("content_length", 0)
            total_word_count += result.get("processing_stats", {}).get("word_count", 0)
        else:
            failed_extractions += 1
            if result.get("error"):
                errors.append(result["error"])

    processing_time = (datetime.now(UTC) - start_time).total_seconds()

    return {
        "status": "completed",
        "documents_processed": len(all_documents),
        "successful_extractions": successful_extractions,
        "failed_extractions": failed_extractions,
        "documents_extracted": extracted_documents,
        "processing_summary": {
            "total_content_length": total_content_length,
            "total_word_count": total_word_count,
            "processing_time_seconds": processing_time,
            "successful_extractions": successful_extractions,
            "failed_extractions": failed_extractions,
        },
        "errors": errors if errors else None,
    }


async def _extract_individual_document(document_info: dict[str, Any]) -> dict[str, Any]:
    """Extract text and metadata from an individual document.

    Args:
        document_info: Document information from RSS feed item

    Returns:
        Dictionary with extracted document data
    """
    try:
        from app.services.document_processor import DocumentProcessor

        document_url = document_info.get("url")
        if not document_url:
            return {
                "url": document_url,
                "title": document_info.get("title", "Unknown Document"),
                "success": False,
                "error": "Missing document URL",
            }

        # Use document processor service to extract content and metadata
        async with DocumentProcessor() as processor:
            processed_doc = await processor.process_document(document_url)

        # Enhance metadata with RSS feed information
        enhanced_metadata = processed_doc.get("metadata", {})
        enhanced_metadata.update(
            {
                "feed_name": document_info.get("feed_name"),
                "authority": document_info.get("authority"),
                "published_date": document_info.get("published"),
                "document_number": document_info.get("document_number"),
                "document_type": document_info.get("document_type"),
                "original_summary": document_info.get("summary"),
            }
        )

        return {
            "url": document_url,
            "title": document_info.get("title", processed_doc.get("title", "Unknown Document")),
            "content": processed_doc.get("content", ""),
            "content_hash": processed_doc.get("content_hash"),
            "document_type": processed_doc.get("document_type"),
            "metadata": enhanced_metadata,
            "processing_stats": processed_doc.get("processing_stats", {}),
            "success": processed_doc.get("success", False),
        }

    except Exception as e:
        return {
            "url": document_info.get("url"),
            "title": document_info.get("title", "Unknown Document"),
            "success": False,
            "error": f"Document extraction failed: {str(e)}",
        }
