"""CCNL Response Formatter Service.

This service formats CCNL data and calculations into chat-friendly responses
that are easy to read and understand for users asking about labor agreements.
"""

import json
from datetime import date
from decimal import Decimal
from typing import Any, Dict, List, Optional

from app.core.logging import logger
from app.models.ccnl_data import CCNLSector, GeographicArea, WorkerCategory


class CCNLResponseFormatter:
    """Service for formatting CCNL responses for chat interfaces."""

    def __init__(self):
        # Emoji mappings for visual enhancement
        self.sector_emojis = {
            "metalmeccanico": "🔧",
            "metalworking": "🔧",
            "edilizia": "🏗️",
            "construction": "🏗️",
            "commercio": "🛒",
            "commerce": "🛒",
            "tessile": "🧵",
            "textile": "🧵",
            "chimico": "⚗️",
            "chemical": "⚗️",
            "alimentare": "🍞",
            "food": "🍞",
            "trasporti": "🚛",
            "transport": "🚛",
            "bancario": "🏦",
            "banking": "🏦",
            "assicurazioni": "📋",
            "insurance": "📋",
            "logistica": "📦",
            "logistics": "📦",
        }

        self.area_emojis = {
            "nord": "⬆️",
            "north": "⬆️",
            "centro": "🎯",
            "center": "🎯",
            "sud": "⬇️",
            "south": "⬇️",
            "isole": "🏝️",
            "islands": "🏝️",
        }

    def format_salary_response(self, result: dict[str, Any]) -> str:
        """Format salary calculation response for chat."""
        try:
            params = result.get("parameters", {})
            salary_info = result.get("salary_info", {})

            # Extract values
            sector = params.get("sector", "").lower()
            job_category = params.get("job_category", "")
            area = params.get("geographic_area", "").lower()
            experience = params.get("experience_years", 0)

            # Format monetary values
            monthly_gross = self._format_currency(salary_info.get("monthly_gross", "0"))
            annual_gross = self._format_currency(salary_info.get("annual_gross", "0"))
            thirteenth_month = self._format_currency(salary_info.get("thirteenth_month", "0"))
            total_compensation = self._format_currency(salary_info.get("total_compensation", "0"))

            # Get emojis
            sector_emoji = self.sector_emojis.get(sector, "💼")
            area_emoji = self.area_emojis.get(area, "📍") if area else ""

            # Build response
            response_parts = [
                f"## {sector_emoji} Calcolo Stipendio CCNL\n",
                f"**Settore:** {self._capitalize(sector)}",
                f"**Categoria:** {self._capitalize(job_category)}" if job_category else "",
                f"**Area:** {area_emoji} {self._capitalize(area)}" if area else "",
                f"**Esperienza:** {experience} anni" if experience > 0 else "",
                "",
                "### 💰 Retribuzione",
                f"• **Stipendio mensile lordo:** €{monthly_gross}",
                f"• **Stipendio annuale lordo:** €{annual_gross}",
                f"• **Tredicesima mensilità:** €{thirteenth_month}" if thirteenth_month != "0,00" else "",
                "",
                f"**🎯 Compenso totale annuo:** €{total_compensation}",
            ]

            # Add allowances if present
            allowances = salary_info.get("allowances", [])
            if allowances:
                response_parts.extend(
                    [
                        "",
                        "### 🎁 Indennità e Benefit",
                    ]
                )
                for allowance in allowances:
                    name = allowance.get("name", "")
                    amount = self._format_currency(str(allowance.get("amount", 0)))
                    response_parts.append(f"• **{name}:** €{amount}")

            # Add contextual information
            response_parts.extend(
                [
                    "",
                    "💡 *I valori indicati sono minimi tabellari CCNL. L'effettiva retribuzione può essere superiore in base agli accordi aziendali.*",
                ]
            )

            return "\n".join(filter(None, response_parts))

        except Exception as e:
            logger.error("salary_response_formatting_failed", error=str(e))
            return "❌ Errore nella formattazione della risposta sui salari CCNL."

    def format_leave_response(self, result: dict[str, Any]) -> str:
        """Format leave calculation response for chat."""
        try:
            params = result.get("parameters", {})
            leave_info = result.get("leave_entitlements", {})

            sector = params.get("sector", "").lower()
            job_category = params.get("job_category", "")
            experience = params.get("experience_years", 0)

            sector_emoji = self.sector_emojis.get(sector, "💼")

            response_parts = [
                f"## {sector_emoji} Ferie e Permessi CCNL\n",
                f"**Settore:** {self._capitalize(sector)}",
                f"**Categoria:** {self._capitalize(job_category)}" if job_category else "",
                f"**Esperienza:** {experience} anni" if experience > 0 else "",
                "",
                "### 🏖️ Diritti di Assenza",
            ]

            # Add leave entitlements
            leave_types = [
                ("vacation_days", "🏖️ Ferie annuali", "giorni"),
                ("sick_leave", "🏥 Malattia", "giorni"),
                ("personal_leave", "📅 Permessi personali", "ore"),
                ("maternity_leave", "👶 Congedo maternità", "settimane"),
                ("paternity_leave", "👨‍👶 Congedo paternità", "giorni"),
            ]

            for key, label, unit in leave_types:
                value = leave_info.get(key, 0)
                if value and value > 0:
                    response_parts.append(f"• **{label}:** {value} {unit}")

            response_parts.extend(
                [
                    "",
                    "💡 *I diritti possono variare in base al CCNL specifico e agli accordi aziendali. Verificare sempre il contratto applicabile.*",
                ]
            )

            return "\n".join(filter(None, response_parts))

        except Exception as e:
            logger.error("leave_response_formatting_failed", error=str(e))
            return "❌ Errore nella formattazione della risposta su ferie e permessi CCNL."

    def format_notice_period_response(self, result: dict[str, Any]) -> str:
        """Format notice period response for chat."""
        try:
            params = result.get("parameters", {})
            notice_info = result.get("notice_period_info", {})

            sector = params.get("sector", "").lower()
            job_category = params.get("job_category", "")
            experience = params.get("experience_years", 0)

            sector_emoji = self.sector_emojis.get(sector, "💼")

            employee_days = notice_info.get("employee_notice_days", 0)
            employer_days = notice_info.get("employer_notice_days", 0)
            probation_days = notice_info.get("probation_period_days", 0)

            response_parts = [
                f"## {sector_emoji} Periodi di Preavviso CCNL\n",
                f"**Settore:** {self._capitalize(sector)}",
                f"**Categoria:** {self._capitalize(job_category)}" if job_category else "",
                f"**Esperienza:** {experience} anni" if experience > 0 else "",
                "",
                "### ⏰ Tempi di Preavviso",
            ]

            if probation_days > 0:
                response_parts.append(f"• **🔄 Periodo di prova:** {probation_days} giorni (senza preavviso)")
                response_parts.append("")

            response_parts.extend(
                [
                    f"• **👤 Dimissioni dipendente:** {employee_days} giorni",
                    f"• **🏢 Licenziamento datore:** {employer_days} giorni",
                    "",
                    "### 📋 Note Importanti",
                    "• Il preavviso decorre dalla data di comunicazione",
                    "• Durante il preavviso si mantiene il diritto alla retribuzione",
                    "• In caso di mancato preavviso è dovuta un'indennità sostitutiva",
                    "",
                    "💡 *I tempi possono variare per giusta causa o giustificato motivo soggettivo/oggettivo.*",
                ]
            )

            return "\n".join(filter(None, response_parts))

        except Exception as e:
            logger.error("notice_period_response_formatting_failed", error=str(e))
            return "❌ Errore nella formattazione della risposta sui periodi di preavviso CCNL."

    def format_comparison_response(self, result: dict[str, Any]) -> str:
        """Format sector comparison response for chat."""
        try:
            params = result.get("parameters", {})
            comparison_data = result.get("comparison_data", [])

            job_category = params.get("job_category", "")
            area = params.get("geographic_area", "").lower()
            area_emoji = self.area_emojis.get(area, "📍") if area else ""

            response_parts = [
                "## 🔄 Confronto Settori CCNL\n",
                f"**Categoria:** {self._capitalize(job_category)}" if job_category else "",
                f"**Area:** {area_emoji} {self._capitalize(area)}" if area else "",
                "",
                "### 💰 Confronto Retribuzioni",
            ]

            # Sort comparisons by salary if available
            if comparison_data:
                sorted_data = sorted(
                    comparison_data,
                    key=lambda x: float(x.get("monthly_salary", 0)) if x.get("monthly_salary") else 0,
                    reverse=True,
                )

                for i, sector_data in enumerate(sorted_data, 1):
                    sector_name = sector_data.get("sector", "").lower()
                    sector_emoji = self.sector_emojis.get(sector_name, "💼")
                    monthly_salary = self._format_currency(str(sector_data.get("monthly_salary", 0)))
                    vacation_days = sector_data.get("vacation_days", 0)

                    medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."

                    response_parts.extend(
                        [
                            f"**{medal} {sector_emoji} {self._capitalize(sector_name)}**",
                            f"• Stipendio: €{monthly_salary}/mese",
                            f"• Ferie: {vacation_days} giorni/anno" if vacation_days > 0 else "",
                            "",
                        ]
                    )

            response_parts.extend(
                [
                    "### 📊 Considerazioni",
                    "• Le retribuzioni indicate sono minimi tabellari CCNL",
                    "• I contratti aziendali possono prevedere condizioni migliorative",
                    "• Benefit e welfare aziendale non sono inclusi nel confronto",
                    "",
                    "💡 *Per una valutazione completa considera anche benefit, crescita professionale e stabilità del settore.*",
                ]
            )

            return "\n".join(filter(None, response_parts))

        except Exception as e:
            logger.error("comparison_response_formatting_failed", error=str(e))
            return "❌ Errore nella formattazione del confronto settori CCNL."

    def format_search_response(self, result: dict[str, Any]) -> str:
        """Format search results response for chat."""
        try:
            search_results = result.get("results", [])
            search_terms = result.get("search_terms", "")
            total_found = result.get("total_found", 0)
            filters_applied = result.get("filters", {})

            response_parts = [
                f"## 🔍 Ricerca CCNL: '{search_terms}'\n" if search_terms else "## 🔍 Risultati Ricerca CCNL\n",
                f"**Risultati trovati:** {total_found}",
            ]

            # Add applied filters
            if any(filters_applied.values()):
                response_parts.append("**Filtri applicati:**")
                for key, value in filters_applied.items():
                    if value:
                        response_parts.append(f"• {self._capitalize(key.replace('_', ' '))}: {value}")
                response_parts.append("")

            if search_results:
                response_parts.append("### 📋 Risultati Principali")

                for i, result_item in enumerate(search_results[:5], 1):
                    title = result_item.get("title", f"Risultato {i}")
                    sector = result_item.get("sector", "").lower()
                    sector_emoji = self.sector_emojis.get(sector, "💼")

                    response_parts.extend(
                        [
                            f"**{i}. {sector_emoji} {title}**",
                            f"• Settore: {self._capitalize(sector)}" if sector else "",
                            f"• Categoria: {result_item.get('category', 'N/A')}"
                            if result_item.get("category")
                            else "",
                            "",
                        ]
                    )
            else:
                response_parts.extend(
                    [
                        "",
                        "❌ Nessun risultato trovato per i criteri specificati.",
                        "",
                        "💡 **Suggerimenti:**",
                        "• Prova con termini di ricerca più generici",
                        "• Verifica l'ortografia dei settori CCNL",
                        "• Usa sinonimi (es. 'metalmeccanico' o 'metalmeccanica')",
                    ]
                )

            return "\n".join(filter(None, response_parts))

        except Exception as e:
            logger.error("search_response_formatting_failed", error=str(e))
            return "❌ Errore nella formattazione dei risultati di ricerca CCNL."

    def format_error_response(self, error_msg: str, query_type: str = "unknown") -> str:
        """Format error response for chat."""
        error_responses = {
            "salary_calculation": "❌ Non sono riuscito a calcolare lo stipendio CCNL richiesto.",
            "leave_calculation": "❌ Non sono riuscito a calcolare ferie e permessi CCNL.",
            "notice_period": "❌ Non sono riuscito a determinare i periodi di preavviso CCNL.",
            "comparison": "❌ Non sono riuscito a effettuare il confronto tra settori CCNL.",
            "search": "❌ Non sono riuscito a completare la ricerca CCNL.",
            "sector_info": "❌ Non sono riuscito a recuperare informazioni sul settore CCNL.",
        }

        base_error = error_responses.get(query_type, "❌ Si è verificato un errore con la richiesta CCNL.")

        return f"""{base_error}

**Errore:** {error_msg}

💡 **Cosa puoi fare:**
• Verifica che il settore sia tra quelli principali (metalmeccanico, edilizia, commercio, etc.)
• Specifica la categoria lavorativa (operaio, impiegato, dirigente)
• Indica l'area geografica se necessaria (Nord, Centro, Sud)
• Riprova con parametri diversi o più specifici

🔧 Se il problema persiste, contatta il supporto tecnico."""

    def _format_currency(self, amount_str: str) -> str:
        """Format currency amount for display."""
        try:
            if not amount_str or amount_str == "0":
                return "0,00"

            # Handle Decimal string representation
            amount = float(str(amount_str).replace(",", "."))
            return f"{amount:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

        except (ValueError, TypeError):
            return "0,00"

    def _capitalize(self, text: str) -> str:
        """Capitalize text properly for Italian."""
        if not text:
            return ""

        # Handle special cases
        special_cases = {"ccnl": "CCNL", "inps": "INPS", "inail": "INAIL", "tfr": "TFR", "pmi": "PMI"}

        text_lower = text.lower()
        if text_lower in special_cases:
            return special_cases[text_lower]

        # Standard capitalization
        return " ".join(word.capitalize() for word in text.split())

    def format_ccnl_response(self, result: dict[str, Any]) -> str:
        """Main formatter that routes to appropriate method based on query type."""
        try:
            if not result.get("success", False):
                error_msg = result.get("error", "Errore sconosciuto")
                query_type = result.get("type", "unknown")
                return self.format_error_response(error_msg, query_type)

            query_type = result.get("type", result.get("query_type", "unknown"))

            if query_type == "salary_calculation":
                return self.format_salary_response(result)
            elif query_type == "leave_calculation":
                return self.format_leave_response(result)
            elif query_type == "notice_period":
                return self.format_notice_period_response(result)
            elif query_type == "comparison":
                return self.format_comparison_response(result)
            elif query_type in ["search", "sector_info"]:
                return self.format_search_response(result)
            else:
                # Generic formatting for unknown types
                return self._format_generic_response(result)

        except Exception as e:
            logger.error("ccnl_response_formatting_failed", error=str(e), result_type=result.get("type"))
            return self.format_error_response(f"Errore di formattazione: {str(e)}")

    def _format_generic_response(self, result: dict[str, Any]) -> str:
        """Format generic CCNL response when specific formatter isn't available."""
        try:
            response_parts = ["## 💼 Risposta CCNL\n"]

            # Add basic information if available
            if "sector" in result:
                sector_emoji = self.sector_emojis.get(result["sector"].lower(), "💼")
                response_parts.append(f"**Settore:** {sector_emoji} {self._capitalize(result['sector'])}")

            if "explanation" in result:
                response_parts.extend(["", result["explanation"]])

            # Add raw result as formatted JSON for complex data
            if "result" in result:
                response_parts.extend(
                    ["", "### 📊 Dettagli", f"```json\n{json.dumps(result['result'], indent=2, default=str)}\n```"]
                )

            return "\n".join(response_parts)

        except Exception as e:
            logger.error("generic_response_formatting_failed", error=str(e))
            return "❌ Errore nella formattazione della risposta CCNL."


# Global instance
ccnl_response_formatter = CCNLResponseFormatter()
