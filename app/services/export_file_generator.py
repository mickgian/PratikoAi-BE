"""Export File Generation Service for GDPR Data Export.

This service generates export files in various formats (JSON, CSV, ZIP) with
Italian formatting, proper encoding, and comprehensive data structure.
"""

import csv
import json
import zipfile
from datetime import date, datetime
from decimal import Decimal
from io import BytesIO, StringIO
from typing import Any, Dict, List, Optional
from uuid import UUID

from app.core.logging import logger
from app.models.data_export import DataExportRequest, ExportFormat


class ExportFileGenerator:
    """Generate export files in various formats with Italian compliance.

    Supports JSON, CSV, and ZIP formats with proper Italian formatting,
    UTF-8 encoding, and Excel compatibility.
    """

    def __init__(self):
        # Italian formatting configuration
        self.italian_config = {
            "date_format": "%d/%m/%Y",
            "datetime_format": "%d/%m/%Y %H:%M:%S",
            "decimal_separator": ",",
            "thousands_separator": ".",
            "currency_symbol": "€",
            "csv_delimiter": ";",  # Italian Excel default
            "encoding": "utf-8",
        }

    async def generate_json_export(self, data: dict[str, Any]) -> bytes:
        """Generate JSON export with Italian formatting.

        Args:
            data: Complete user data dictionary

        Returns:
            JSON content as UTF-8 encoded bytes
        """
        try:
            # Custom JSON encoder for Italian formats
            class ItalianJSONEncoder(json.JSONEncoder):
                def default(self, obj):
                    if isinstance(obj, datetime):
                        return obj.strftime(self.italian_config["datetime_format"])
                    elif isinstance(obj, date):
                        return obj.strftime(self.italian_config["date_format"])
                    elif isinstance(obj, Decimal):
                        # Format with Italian decimal separator
                        formatted = f"{obj:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
                        return f"{self.italian_config['currency_symbol']} {formatted}"
                    elif isinstance(obj, UUID):
                        return str(obj)
                    return super().default(obj)

            # Generate JSON with Italian formatting
            json_content = json.dumps(data, cls=ItalianJSONEncoder, ensure_ascii=False, indent=2, sort_keys=False)

            return json_content.encode(self.italian_config["encoding"])

        except Exception as e:
            logger.error(f"Error generating JSON export: {e}")
            raise

    async def generate_csv_exports(self, data: dict[str, Any]) -> dict[str, bytes]:
        """Generate multiple CSV files for different data categories.

        Args:
            data: Complete user data dictionary

        Returns:
            Dictionary mapping filenames to CSV content bytes
        """
        csv_files = {}

        try:
            # Generate CSV for each data category
            if "profile" in data and data["profile"]:
                csv_files["profilo.csv"] = await self._generate_profile_csv(data["profile"])

            if "queries" in data and data["queries"]:
                csv_files["domande.csv"] = await self._generate_queries_csv(data["queries"])

            if "documents" in data and data["documents"]:
                csv_files["documenti.csv"] = await self._generate_documents_csv(data["documents"])

            if "tax_calculations" in data and data["tax_calculations"]:
                csv_files["calcoli_fiscali.csv"] = await self._generate_tax_calculations_csv(data["tax_calculations"])

            if "subscriptions" in data and data["subscriptions"]:
                csv_files["abbonamenti.csv"] = await self._generate_subscriptions_csv(data["subscriptions"])

            if "invoices" in data and data["invoices"]:
                csv_files["fatture.csv"] = await self._generate_invoices_csv(data["invoices"])

            if "fatture_elettroniche" in data and data["fatture_elettroniche"]:
                csv_files["fatture_elettroniche.csv"] = await self._generate_electronic_invoices_csv(
                    data["fatture_elettroniche"]
                )

            if "faq_interactions" in data and data["faq_interactions"]:
                csv_files["interazioni_faq.csv"] = await self._generate_faq_csv(data["faq_interactions"])

            if "knowledge_searches" in data and data["knowledge_searches"]:
                csv_files["ricerche_conoscenza.csv"] = await self._generate_knowledge_searches_csv(
                    data["knowledge_searches"]
                )

            if "usage_statistics" in data and data["usage_statistics"]:
                csv_files["statistiche_uso.csv"] = await self._generate_usage_stats_csv(data["usage_statistics"])

            return csv_files

        except Exception as e:
            logger.error(f"Error generating CSV exports: {e}")
            raise

    async def _generate_profile_csv(self, profile_data: dict[str, Any]) -> bytes:
        """Generate CSV for user profile data"""
        output = StringIO()

        # Add UTF-8 BOM for Excel compatibility
        output.write("\ufeff")

        # Profile data as key-value pairs
        writer = csv.writer(output, delimiter=self.italian_config["csv_delimiter"], quoting=csv.QUOTE_MINIMAL)

        # Headers in Italian
        writer.writerow(["Campo", "Valore"])

        # Profile fields with Italian labels
        field_mapping = {
            "user_id": "ID Utente",
            "email": "Email",
            "full_name": "Nome Completo",
            "created_at": "Data Registrazione",
            "account_status": "Stato Account",
            "subscription_status": "Stato Abbonamento",
            "language": "Lingua",
            "timezone": "Fuso Orario",
            "codice_fiscale": "Codice Fiscale",
        }

        for field, italian_label in field_mapping.items():
            if field in profile_data and profile_data[field]:
                value = profile_data[field]

                # Format dates
                if field == "created_at" and isinstance(value, str):
                    try:
                        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
                        value = dt.strftime(self.italian_config["date_format"])
                    except:
                        pass

                writer.writerow([italian_label, str(value)])

        # Business info if present
        if "business_info" in profile_data:
            business = profile_data["business_info"]
            writer.writerow(["Tipo Cliente", "Azienda" if business.get("is_business") else "Privato"])
            if business.get("partita_iva"):
                writer.writerow(["Partita IVA", business["partita_iva"]])

        # Billing address if present
        if "billing_address" in profile_data:
            address = profile_data["billing_address"]
            if address.get("address"):
                writer.writerow(["Indirizzo Fatturazione", address["address"]])
            if address.get("city"):
                writer.writerow(["Città", address["city"]])
            if address.get("postal_code"):
                writer.writerow(["CAP", address["postal_code"]])

        return output.getvalue().encode(self.italian_config["encoding"])

    async def _generate_queries_csv(self, queries: list[dict[str, Any]]) -> bytes:
        """Generate CSV for query history"""
        output = StringIO()
        output.write("\ufeff")  # UTF-8 BOM

        writer = csv.DictWriter(
            output,
            fieldnames=[
                "Data",
                "Ora",
                "Domanda",
                "Tipo Domanda",
                "Tempo Risposta (ms)",
                "Token Utilizzati",
                "Costo (€)",
                "Da Cache",
                "Modello AI",
                "Contenuto Italiano",
            ],
            delimiter=self.italian_config["csv_delimiter"],
            quoting=csv.QUOTE_MINIMAL,
        )

        writer.writeheader()

        for query in queries:
            try:
                # Parse timestamp
                timestamp = datetime.fromisoformat(query["timestamp"].replace("Z", "+00:00"))

                # Format cost in euros
                cost_eur = f"{(query.get('cost_cents', 0) / 100):.2f}".replace(".", ",")

                writer.writerow(
                    {
                        "Data": timestamp.strftime(self.italian_config["date_format"]),
                        "Ora": timestamp.strftime("%H:%M:%S"),
                        "Domanda": (query["query"][:100] + "...")
                        if len(query.get("query", "")) > 100
                        else query.get("query", ""),
                        "Tipo Domanda": self._translate_query_type(query.get("query_type")),
                        "Tempo Risposta (ms)": query.get("response_time_ms", "N/D"),
                        "Token Utilizzati": query.get("tokens_used", "N/D"),
                        "Costo (€)": cost_eur,
                        "Da Cache": "Sì" if query.get("response_cached") else "No",
                        "Modello AI": query.get("model_used", "N/D"),
                        "Contenuto Italiano": "Sì" if query.get("italian_content") else "No",
                    }
                )
            except Exception as e:
                logger.warning(f"Error processing query for CSV: {e}")
                continue

        return output.getvalue().encode(self.italian_config["encoding"])

    async def _generate_documents_csv(self, documents: list[dict[str, Any]]) -> bytes:
        """Generate CSV for document analysis metadata"""
        output = StringIO()
        output.write("\ufeff")  # UTF-8 BOM

        writer = csv.DictWriter(
            output,
            fieldnames=[
                "Data Caricamento",
                "Nome File",
                "Tipo File",
                "Dimensione (MB)",
                "Tipo Analisi",
                "Categoria Documento",
                "Anno Fiscale",
                "Tempo Elaborazione (ms)",
                "Stato Analisi",
                "Entità Trovate",
                "Punteggio Confidenza",
            ],
            delimiter=self.italian_config["csv_delimiter"],
            quoting=csv.QUOTE_MINIMAL,
        )

        writer.writeheader()

        for doc in documents:
            try:
                # Parse upload date
                uploaded_at = datetime.fromisoformat(doc["uploaded_at"].replace("Z", "+00:00"))

                # Format file size
                file_size_mb = (
                    f"{(doc.get('file_size_bytes', 0) / 1024 / 1024):.2f}".replace(".", ",")
                    if doc.get("file_size_bytes")
                    else "N/D"
                )

                # Format confidence score
                confidence = (
                    f"{doc['confidence_score']:.1f}".replace(".", ",") if doc.get("confidence_score") else "N/D"
                )

                writer.writerow(
                    {
                        "Data Caricamento": uploaded_at.strftime(self.italian_config["datetime_format"]),
                        "Nome File": doc.get("filename", ""),
                        "Tipo File": doc.get("file_type", ""),
                        "Dimensione (MB)": file_size_mb,
                        "Tipo Analisi": self._translate_analysis_type(doc.get("analysis_type")),
                        "Categoria Documento": self._translate_document_category(doc.get("document_category")),
                        "Anno Fiscale": doc.get("tax_year", "N/D"),
                        "Tempo Elaborazione (ms)": doc.get("processing_time_ms", "N/D"),
                        "Stato Analisi": self._translate_analysis_status(doc.get("analysis_status")),
                        "Entità Trovate": doc.get("entities_found", "N/D"),
                        "Punteggio Confidenza": confidence,
                    }
                )
            except Exception as e:
                logger.warning(f"Error processing document for CSV: {e}")
                continue

        return output.getvalue().encode(self.italian_config["encoding"])

    async def _generate_tax_calculations_csv(self, calculations: list[dict[str, Any]]) -> bytes:
        """Generate CSV for tax calculations"""
        output = StringIO()
        output.write("\ufeff")  # UTF-8 BOM

        writer = csv.DictWriter(
            output,
            fieldnames=[
                "Data",
                "Tipo Calcolo",
                "Amount Iniziale (€)",
                "Risultato",
                "Anno Fiscale",
                "Regione",
                "Comune",
                "Parametri",
            ],
            delimiter=self.italian_config["csv_delimiter"],
            quoting=csv.QUOTE_MINIMAL,
        )

        writer.writeheader()

        for calc in calculations:
            try:
                # Parse timestamp
                timestamp = datetime.fromisoformat(calc["timestamp"].replace("Z", "+00:00"))

                # Format amounts
                input_amount = f"{calc.get('input_amount', 0):.2f}".replace(".", ",")

                # Format result (can be complex object)
                result = calc.get("result", {})
                if isinstance(result, dict):
                    result_str = "; ".join([f"{k}: {v}" for k, v in result.items()])
                else:
                    result_str = str(result)

                # Format parameters
                params = calc.get("parameters", {})
                params_str = (
                    "; ".join([f"{k}: {v}" for k, v in params.items()]) if isinstance(params, dict) else str(params)
                )

                writer.writerow(
                    {
                        "Data": timestamp.strftime(self.italian_config["datetime_format"]),
                        "Tipo Calcolo": calc.get("calculation_type", ""),
                        "Amount Iniziale (€)": input_amount,
                        "Risultato": result_str[:100] + "..." if len(result_str) > 100 else result_str,
                        "Anno Fiscale": calc.get("tax_year", "N/D"),
                        "Regione": calc.get("region", "N/D"),
                        "Comune": calc.get("municipality", "N/D"),
                        "Parametri": params_str[:100] + "..." if len(params_str) > 100 else params_str,
                    }
                )
            except Exception as e:
                logger.warning(f"Error processing tax calculation for CSV: {e}")
                continue

        return output.getvalue().encode(self.italian_config["encoding"])

    async def _generate_subscriptions_csv(self, subscriptions: list[dict[str, Any]]) -> bytes:
        """Generate CSV for subscription history"""
        output = StringIO()
        output.write("\ufeff")  # UTF-8 BOM

        writer = csv.DictWriter(
            output,
            fieldnames=[
                "Data Inizio",
                "Piano",
                "Periodo Fatturazione",
                "Prezzo Base (€)",
                "Aliquota IVA (%)",
                "Stato",
                "Inizio Periodo",
                "Fine Periodo",
                "Fine Trial",
                "Data Cancellazione",
                "Tipo Cliente",
                "Partita IVA",
            ],
            delimiter=self.italian_config["csv_delimiter"],
            quoting=csv.QUOTE_MINIMAL,
        )

        writer.writeheader()

        for sub in subscriptions:
            try:
                # Parse dates
                created_at = datetime.fromisoformat(sub["created_at"].replace("Z", "+00:00"))

                # Format dates
                def format_date_field(field_name):
                    if sub.get(field_name):
                        try:
                            dt = datetime.fromisoformat(sub[field_name].replace("Z", "+00:00"))
                            return dt.strftime(self.italian_config["date_format"])
                        except:
                            return sub[field_name]
                    return "N/D"

                # Format price
                price = f"{sub.get('base_price_eur', 0):.2f}".replace(".", ",") if sub.get("base_price_eur") else "N/D"
                iva_rate = f"{sub.get('iva_rate', 0):.1f}".replace(".", ",") if sub.get("iva_rate") else "N/D"

                writer.writerow(
                    {
                        "Data Inizio": created_at.strftime(self.italian_config["date_format"]),
                        "Piano": sub.get("plan_name", ""),
                        "Periodo Fatturazione": self._translate_billing_period(sub.get("billing_period")),
                        "Prezzo Base (€)": price,
                        "Aliquota IVA (%)": iva_rate,
                        "Stato": self._translate_subscription_status(sub.get("status")),
                        "Inizio Periodo": format_date_field("current_period_start"),
                        "Fine Periodo": format_date_field("current_period_end"),
                        "Fine Trial": format_date_field("trial_end"),
                        "Data Cancellazione": format_date_field("canceled_at"),
                        "Tipo Cliente": "Azienda" if sub.get("is_business") else "Privato",
                        "Partita IVA": sub.get("partita_iva", "N/D"),
                    }
                )
            except Exception as e:
                logger.warning(f"Error processing subscription for CSV: {e}")
                continue

        return output.getvalue().encode(self.italian_config["encoding"])

    async def _generate_invoices_csv(self, invoices: list[dict[str, Any]]) -> bytes:
        """Generate CSV for invoice data"""
        output = StringIO()
        output.write("\ufeff")  # UTF-8 BOM

        writer = csv.DictWriter(
            output,
            fieldnames=[
                "Numero Fattura",
                "Data Fattura",
                "Data Scadenza",
                "Imponibile (€)",
                "IVA (€)",
                "Totale (€)",
                "Stato Pagamento",
                "Data Pagamento",
                "Fattura Elettronica",
                "ID Stripe",
            ],
            delimiter=self.italian_config["csv_delimiter"],
            quoting=csv.QUOTE_MINIMAL,
        )

        writer.writeheader()

        for invoice in invoices:
            try:
                # Parse dates
                invoice_date = datetime.fromisoformat(invoice["invoice_date"].replace("Z", "+00:00"))

                # Format dates
                due_date = "N/D"
                if invoice.get("due_date"):
                    try:
                        dt = datetime.fromisoformat(invoice["due_date"].replace("Z", "+00:00"))
                        due_date = dt.strftime(self.italian_config["date_format"])
                    except:
                        due_date = invoice["due_date"]

                paid_date = "N/D"
                if invoice.get("paid_at"):
                    try:
                        dt = datetime.fromisoformat(invoice["paid_at"].replace("Z", "+00:00"))
                        paid_date = dt.strftime(self.italian_config["date_format"])
                    except:
                        paid_date = invoice["paid_at"]

                # Format amounts
                subtotal = f"{invoice.get('subtotal', 0):.2f}".replace(".", ",")
                iva_amount = f"{invoice.get('iva_amount', 0):.2f}".replace(".", ",")
                total_amount = f"{invoice.get('total_amount', 0):.2f}".replace(".", ",")

                writer.writerow(
                    {
                        "Numero Fattura": invoice.get("invoice_number", ""),
                        "Data Fattura": invoice_date.strftime(self.italian_config["date_format"]),
                        "Data Scadenza": due_date,
                        "Imponibile (€)": subtotal,
                        "IVA (€)": iva_amount,
                        "Totale (€)": total_amount,
                        "Stato Pagamento": self._translate_payment_status(invoice.get("payment_status")),
                        "Data Pagamento": paid_date,
                        "Fattura Elettronica": "Sì" if invoice.get("has_electronic_invoice") else "No",
                        "ID Stripe": invoice.get("stripe_invoice_id", "N/D"),
                    }
                )
            except Exception as e:
                logger.warning(f"Error processing invoice for CSV: {e}")
                continue

        return output.getvalue().encode(self.italian_config["encoding"])

    async def _generate_electronic_invoices_csv(self, electronic_invoices: list[dict[str, Any]]) -> bytes:
        """Generate CSV for electronic invoices (fatture elettroniche)"""
        output = StringIO()
        output.write("\ufeff")  # UTF-8 BOM

        writer = csv.DictWriter(
            output,
            fieldnames=[
                "Numero Fattura",
                "Data Fattura",
                "ID Trasmissione SDI",
                "Stato SDI",
                "Data Creazione",
                "Data Trasmissione",
                "Data Accettazione",
                "Hash XML",
            ],
            delimiter=self.italian_config["csv_delimiter"],
            quoting=csv.QUOTE_MINIMAL,
        )

        writer.writeheader()

        for fe in electronic_invoices:
            try:
                # Parse dates
                invoice_date = datetime.fromisoformat(fe["invoice_date"].replace("Z", "+00:00"))
                created_at = datetime.fromisoformat(fe["created_at"].replace("Z", "+00:00"))

                # Format optional dates
                def format_optional_date(field_name):
                    if fe.get(field_name):
                        try:
                            dt = datetime.fromisoformat(fe[field_name].replace("Z", "+00:00"))
                            return dt.strftime(self.italian_config["datetime_format"])
                        except:
                            return fe[field_name]
                    return "N/D"

                writer.writerow(
                    {
                        "Numero Fattura": fe.get("invoice_number", ""),
                        "Data Fattura": invoice_date.strftime(self.italian_config["date_format"]),
                        "ID Trasmissione SDI": fe.get("sdi_transmission_id", "N/D"),
                        "Stato SDI": self._translate_sdi_status(fe.get("sdi_status")),
                        "Data Creazione": created_at.strftime(self.italian_config["datetime_format"]),
                        "Data Trasmissione": format_optional_date("transmitted_at"),
                        "Data Accettazione": format_optional_date("accepted_at"),
                        "Hash XML": fe.get("xml_hash", "N/D"),
                    }
                )
            except Exception as e:
                logger.warning(f"Error processing electronic invoice for CSV: {e}")
                continue

        return output.getvalue().encode(self.italian_config["encoding"])

    async def _generate_faq_csv(self, faq_interactions: list[dict[str, Any]]) -> bytes:
        """Generate CSV for FAQ interactions"""
        output = StringIO()
        output.write("\ufeff")  # UTF-8 BOM

        writer = csv.DictWriter(
            output,
            fieldnames=[
                "Data Visualizzazione",
                "Domanda",
                "Categoria",
                "Tempo Speso (sec)",
                "Valutazione (1-5)",
                "Feedback",
                "Contenuto Italiano",
                "Argomento Fiscale",
            ],
            delimiter=self.italian_config["csv_delimiter"],
            quoting=csv.QUOTE_MINIMAL,
        )

        writer.writeheader()

        for faq in faq_interactions:
            try:
                # Parse date
                viewed_at = datetime.fromisoformat(faq["viewed_at"].replace("Z", "+00:00"))

                writer.writerow(
                    {
                        "Data Visualizzazione": viewed_at.strftime(self.italian_config["datetime_format"]),
                        "Domanda": faq.get("question", "")[:150] + "..."
                        if len(faq.get("question", "")) > 150
                        else faq.get("question", ""),
                        "Categoria": faq.get("category", "N/D"),
                        "Tempo Speso (sec)": faq.get("time_spent_seconds", "N/D"),
                        "Valutazione (1-5)": faq.get("helpful_rating", "N/D"),
                        "Feedback": faq.get("feedback", "")[:100] + "..."
                        if len(faq.get("feedback", "")) > 100
                        else faq.get("feedback", ""),
                        "Contenuto Italiano": "Sì" if faq.get("italian_content") else "No",
                        "Argomento Fiscale": "Sì" if faq.get("tax_related") else "No",
                    }
                )
            except Exception as e:
                logger.warning(f"Error processing FAQ interaction for CSV: {e}")
                continue

        return output.getvalue().encode(self.italian_config["encoding"])

    async def _generate_knowledge_searches_csv(self, searches: list[dict[str, Any]]) -> bytes:
        """Generate CSV for knowledge base searches"""
        output = StringIO()
        output.write("\ufeff")  # UTF-8 BOM

        writer = csv.DictWriter(
            output,
            fieldnames=[
                "Data Ricerca",
                "Query di Ricerca",
                "Numero Risultati",
                "Risultato Cliccato",
                "Posizione Click",
                "Categoria",
                "Query Italiana",
                "Contenuto Normativo",
            ],
            delimiter=self.italian_config["csv_delimiter"],
            quoting=csv.QUOTE_MINIMAL,
        )

        writer.writeheader()

        for search in searches:
            try:
                # Parse date
                searched_at = datetime.fromisoformat(search["searched_at"].replace("Z", "+00:00"))

                writer.writerow(
                    {
                        "Data Ricerca": searched_at.strftime(self.italian_config["datetime_format"]),
                        "Query di Ricerca": search.get("search_query", ""),
                        "Numero Risultati": search.get("results_count", 0),
                        "Risultato Cliccato": search.get("clicked_result_id", "N/D"),
                        "Posizione Click": search.get("clicked_position", "N/D"),
                        "Categoria": search.get("search_category", "N/D"),
                        "Query Italiana": "Sì" if search.get("italian_query") else "No",
                        "Contenuto Normativo": "Sì" if search.get("regulatory_content") else "No",
                    }
                )
            except Exception as e:
                logger.warning(f"Error processing knowledge search for CSV: {e}")
                continue

        return output.getvalue().encode(self.italian_config["encoding"])

    async def _generate_usage_stats_csv(self, stats: dict[str, Any]) -> bytes:
        """Generate CSV for usage statistics"""
        output = StringIO()
        output.write("\ufeff")  # UTF-8 BOM

        writer = csv.writer(output, delimiter=self.italian_config["csv_delimiter"], quoting=csv.QUOTE_MINIMAL)

        # Headers
        writer.writerow(["Categoria", "Metrica", "Valore"])

        # Query statistics
        if "query_statistics" in stats:
            query_stats = stats["query_statistics"]
            writer.writerow(["Domande", "Totale Domande", query_stats.get("total_queries", 0)])
            writer.writerow(["Domande", "Domande da Cache", query_stats.get("cached_queries", 0)])
            writer.writerow(
                [
                    "Domande",
                    "Tasso Hit Cache (%)",
                    f"{query_stats.get('cache_hit_rate', 0) * 100:.1f}".replace(".", ","),
                ]
            )
            writer.writerow(
                [
                    "Domande",
                    "Tempo Risposta Medio (ms)",
                    f"{query_stats.get('average_response_time_ms', 0):.1f}".replace(".", ","),
                ]
            )
            writer.writerow(["Domande", "Token Totali Utilizzati", query_stats.get("total_tokens_used", 0)])
            writer.writerow(
                ["Domande", "Costo Totale (€)", f"{query_stats.get('total_cost_eur', 0):.2f}".replace(".", ",")]
            )

        # Document statistics
        if "document_statistics" in stats:
            doc_stats = stats["document_statistics"]
            writer.writerow(["Documenti", "Totale Documenti", doc_stats.get("total_documents", 0)])
            writer.writerow(
                [
                    "Documenti",
                    "Tempo Elaborazione Medio (ms)",
                    f"{doc_stats.get('average_processing_time_ms', 0):.1f}".replace(".", ","),
                ]
            )
            writer.writerow(
                [
                    "Documenti",
                    "Dimensione Media File (MB)",
                    f"{doc_stats.get('average_file_size_mb', 0):.2f}".replace(".", ","),
                ]
            )

        return output.getvalue().encode(self.italian_config["encoding"])

    async def generate_manifest(self, data: dict[str, Any], export_request: DataExportRequest) -> str:
        """Generate Italian manifest file explaining the export contents.

        Args:
            data: Complete user data
            export_request: Export request configuration

        Returns:
            Manifest content as string
        """
        manifest_lines = [
            "=" * 80,
            "EXPORT DATI PERSONALI - GDPR ARTICOLO 20",
            "PratikoAI - Diritto alla Portabilità dei Dati",
            "=" * 80,
            "",
            f"Data di generazione: {datetime.utcnow().strftime(self.italian_config['datetime_format'])}",
            f"ID Export: {export_request.id}",
            f"Formato: {export_request.format.value.upper()}",
            f"Livello Privacy: {export_request.privacy_level.value}",
            "",
            "INFORMAZIONI LEGALI",
            "-" * 20,
            "Base giuridica: GDPR Articolo 20 - Diritto alla portabilità dei dati",
            "Titolare del trattamento: PratikoAI SRL",
            "Indirizzo: Via dell'Innovazione 123, 00100 Roma, IT",
            "Email: privacy@pratikoai.com",
            "Giurisdizione: Italia",
            "",
            "CONTENUTO DELL'EXPORT",
            "-" * 22,
        ]

        # List included data categories
        categories = {
            "include_profile": "✓ Dati del profilo utente",
            "include_queries": "✓ Cronologia domande e risposte",
            "include_documents": "✓ Metadati documenti analizzati",
            "include_calculations": "✓ Calcoli fiscali effettuati",
            "include_subscriptions": "✓ Cronologia abbonamenti",
            "include_invoices": "✓ Fatture e pagamenti",
            "include_usage_stats": "✓ Statistiche di utilizzo",
            "include_faq_interactions": "✓ Interazioni con FAQ",
            "include_knowledge_searches": "✓ Ricerche nella base di conoscenza",
        }

        for attr, description in categories.items():
            if getattr(export_request, attr, False):
                manifest_lines.append(description)

        # Italian specific content
        manifest_lines.extend(
            [
                "",
                "CONTENUTO SPECIFICO ITALIANO",
                "-" * 30,
            ]
        )

        if export_request.include_fatture:
            manifest_lines.append("✓ Fatture elettroniche (XML)")
        if export_request.include_f24:
            manifest_lines.append("✓ Moduli F24")
        if export_request.include_dichiarazioni:
            manifest_lines.append("✓ Dichiarazioni fiscali")

        # Privacy information
        manifest_lines.extend(
            [
                "",
                "INFORMAZIONI SULLA PRIVACY",
                "-" * 27,
            ]
        )

        if export_request.include_sensitive:
            manifest_lines.append("• Dati sensibili inclusi (come richiesto)")
        else:
            manifest_lines.append("• Dati sensibili esclusi")

        if export_request.anonymize_pii:
            manifest_lines.append("• Dati personali anonimizzati")

        if export_request.mask_codice_fiscale:
            manifest_lines.append("• Codice Fiscale mascherato (ultimi 4 caratteri visibili)")

        # File structure
        manifest_lines.extend(
            [
                "",
                "STRUTTURA FILE",
                "-" * 15,
            ]
        )

        if export_request.format in [ExportFormat.JSON, ExportFormat.BOTH]:
            manifest_lines.append("• dati_completi.json - Tutti i dati in formato JSON")

        if export_request.format in [ExportFormat.CSV, ExportFormat.BOTH]:
            manifest_lines.extend(
                [
                    "• profilo.csv - Dati del profilo",
                    "• domande.csv - Cronologia domande",
                    "• documenti.csv - Metadati documenti",
                    "• calcoli_fiscali.csv - Calcoli fiscali",
                    "• abbonamenti.csv - Cronologia abbonamenti",
                    "• fatture.csv - Fatture e pagamenti",
                    "• fatture_elettroniche.csv - Fatture elettroniche",
                    "• interazioni_faq.csv - Interazioni FAQ",
                    "• ricerche_conoscenza.csv - Ricerche base conoscenza",
                    "• statistiche_uso.csv - Statistiche di utilizzo",
                ]
            )

        # Data summary
        if data:
            manifest_lines.extend(
                [
                    "",
                    "RIEPILOGO DATI",
                    "-" * 14,
                    f"• Domande totali: {len(data.get('queries', []))}",
                    f"• Documenti analizzati: {len(data.get('documents', []))}",
                    f"• Calcoli fiscali: {len(data.get('tax_calculations', []))}",
                    f"• Abbonamenti: {len(data.get('subscriptions', []))}",
                    f"• Fatture: {len(data.get('invoices', []))}",
                    f"• Fatture elettroniche: {len(data.get('fatture_elettroniche', []))}",
                    f"• Interazioni FAQ: {len(data.get('faq_interactions', []))}",
                    f"• Ricerche: {len(data.get('knowledge_searches', []))}",
                ]
            )

        # Important notes
        manifest_lines.extend(
            [
                "",
                "NOTE IMPORTANTI",
                "-" * 16,
                "• I file CSV utilizzano il separatore ';' per compatibilità con Excel italiano",
                "• Le date sono nel formato DD/MM/YYYY",
                "• I numeri decimali utilizzano la virgola come separatore",
                "• L'encoding è UTF-8 con BOM per compatibilità Excel",
                "• I dati sui documenti includono solo metadati, non il contenuto",
                "• Le password e i token di sicurezza non sono mai inclusi",
                "• Questo export scadrà automaticamente tra 24 ore",
                "",
                "Per domande o chiarimenti, contattare: support@pratikoai.com",
                "",
                "=" * 80,
            ]
        )

        return "\n".join(manifest_lines)

    async def create_zip_export(self, files: dict[str, bytes]) -> bytes:
        """Create ZIP archive containing all export files.

        Args:
            files: Dictionary mapping filenames to file content bytes

        Returns:
            ZIP file content as bytes
        """
        try:
            zip_buffer = BytesIO()

            with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as zip_file:
                for filename, content in files.items():
                    # Add file to ZIP with proper compression
                    zip_file.writestr(filename, content)

                # Add compression info
                zip_file.comment = f"Export dati PratikoAI - {datetime.utcnow().strftime('%d/%m/%Y %H:%M')}".encode()

            zip_content = zip_buffer.getvalue()
            logger.info(f"Created ZIP export with {len(files)} files, size: {len(zip_content)} bytes")

            return zip_content

        except Exception as e:
            logger.error(f"Error creating ZIP export: {e}")
            raise

    # Translation helper methods

    def _translate_query_type(self, query_type: str | None) -> str:
        """Translate query type to Italian"""
        translations = {
            "tax_calculation": "Calcolo Fiscale",
            "document_analysis": "Analisi Documento",
            "general": "Generale",
            "legal_advice": "Consulenza Legale",
            "accounting": "Contabilità",
        }
        return translations.get(query_type, query_type or "N/D")

    def _translate_analysis_type(self, analysis_type: str | None) -> str:
        """Translate analysis type to Italian"""
        translations = {
            "italian_invoice": "Fattura Italiana",
            "f24": "Modulo F24",
            "tax_declaration": "Dichiarazione Fiscale",
            "receipt": "Ricevuta",
            "contract": "Contratto",
        }
        return translations.get(analysis_type, analysis_type or "N/D")

    def _translate_document_category(self, category: str | None) -> str:
        """Translate document category to Italian"""
        translations = {
            "fattura": "Fattura",
            "ricevuta": "Ricevuta",
            "f24": "F24",
            "dichiarazione": "Dichiarazione",
            "contratto": "Contratto",
            "documento_identita": "Documento Identità",
        }
        return translations.get(category, category or "N/D")

    def _translate_analysis_status(self, status: str | None) -> str:
        """Translate analysis status to Italian"""
        translations = {
            "completed": "Completata",
            "failed": "Fallita",
            "processing": "In Elaborazione",
            "pending": "In Attesa",
        }
        return translations.get(status, status or "N/D")

    def _translate_billing_period(self, period: str | None) -> str:
        """Translate billing period to Italian"""
        translations = {"monthly": "Mensile", "annual": "Annuale", "weekly": "Settimanale"}
        return translations.get(period, period or "N/D")

    def _translate_subscription_status(self, status: str | None) -> str:
        """Translate subscription status to Italian"""
        translations = {
            "active": "Attivo",
            "canceled": "Cancellato",
            "trialing": "In Prova",
            "past_due": "Scaduto",
            "unpaid": "Non Pagato",
            "incomplete": "Incompleto",
        }
        return translations.get(status, status or "N/D")

    def _translate_payment_status(self, status: str | None) -> str:
        """Translate payment status to Italian"""
        translations = {
            "paid": "Pagato",
            "pending": "In Attesa",
            "failed": "Fallito",
            "refunded": "Rimborsato",
            "canceled": "Cancellato",
        }
        return translations.get(status, status or "N/D")

    def _translate_sdi_status(self, status: str | None) -> str:
        """Translate SDI status to Italian"""
        translations = {
            "sent": "Inviato",
            "accepted": "Accettato",
            "rejected": "Rifiutato",
            "processing": "In Elaborazione",
            "delivered": "Consegnato",
        }
        return translations.get(status, status or "N/D")
