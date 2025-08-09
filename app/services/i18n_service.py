"""
Internationalization (i18n) Service for multilingual CCNL support.

This service provides Italian and English translations for all CCNL data,
supporting international companies operating in Italy.
"""

from typing import Dict, Any, Optional, List
from enum import Enum
import json
import logging

from app.models.ccnl_data import CCNLSector, WorkerCategory, LeaveType, AllowanceType

logger = logging.getLogger(__name__)


class Language(str, Enum):
    """Supported languages."""
    ITALIAN = "it"
    ENGLISH = "en"


class I18nService:
    """Service for internationalization and localization."""
    
    def __init__(self):
        self.translations = self._initialize_translations()
        self.sector_translations = self._initialize_sector_translations()
        self.default_language = Language.ITALIAN
    
    def _initialize_translations(self) -> Dict[Language, Dict[str, str]]:
        """Initialize translation dictionaries."""
        return {
            Language.ITALIAN: {
                # General terms
                "ccnl_agreement": "Contratto Collettivo Nazionale di Lavoro",
                "sector": "Settore",
                "worker_category": "Categoria Lavoratore",
                "job_level": "Livello Professionale",
                "salary": "Retribuzione",
                "monthly_salary": "Retribuzione Mensile",
                "working_hours": "Orario di Lavoro",
                "overtime": "Straordinario",
                "leave_entitlement": "Diritti di Permesso",
                "notice_period": "Periodo di Preavviso",
                "special_allowance": "Indennità Speciale",
                "valid_from": "Valido dal",
                "valid_to": "Valido fino al",
                "expires_on": "Scade il",
                "renewal_date": "Data di Rinnovo",
                
                # Worker categories
                "operaio": "Operaio",
                "impiegato": "Impiegato",
                "quadro": "Quadro",
                "dirigente": "Dirigente",
                
                # Time periods
                "daily": "giornaliero",
                "weekly": "settimanale",
                "monthly": "mensile",
                "annual": "annuale",
                "per_hour": "all'ora",
                "per_day": "al giorno",
                
                # Leave types
                "ferie": "Ferie",
                "permessi_retribuiti": "Permessi Retribuiti",
                "malattia": "Malattia",
                "maternita": "Maternità",
                "paternita": "Paternità",
                "lutto": "Lutto",
                "matrimonio": "Matrimonio",
                
                # Allowance types
                "buoni_pasto": "Buoni Pasto",
                "indennita_trasporto": "Indennità di Trasporto",
                "indennita_rischio": "Indennità di Rischio",
                "indennita_turno": "Indennità di Turno",
                "indennita_reperibilita": "Indennità di Reperibilità",
                "indennita_trasferta": "Indennità di Trasferta",
                "indennita_funzione": "Indennità di Funzione",
                "premio_produzione": "Premio di Produzione",
                "auto_aziendale": "Auto Aziendale",
                
                # Status terms
                "active": "Attivo",
                "expired": "Scaduto",
                "expiring_soon": "In Scadenza",
                "under_negotiation": "In Negoziazione",
                "renewed": "Rinnovato",
                
                # Alerts and notifications
                "alert": "Avviso",
                "notification": "Notifica",
                "warning": "Avvertimento",
                "error": "Errore",
                "info": "Informazione",
                "critical": "Critico",
                
                # Actions
                "view_details": "Visualizza Dettagli",
                "download": "Scarica",
                "export": "Esporta",
                "update": "Aggiorna",
                "renew": "Rinnova",
                "calculate": "Calcola",
                "search": "Cerca",
                "filter": "Filtra",
                
                # Contributions
                "inps_contributions": "Contributi INPS",
                "inail_contributions": "Contributi INAIL",
                "employee_contribution": "Contributo Lavoratore",
                "employer_contribution": "Contributo Datore di Lavoro",
                "total_contributions": "Contributi Totali",
                "net_salary": "Salario Netto",
                "gross_salary": "Salario Lordo"
            },
            
            Language.ENGLISH: {
                # General terms
                "ccnl_agreement": "National Collective Labor Agreement",
                "sector": "Sector",
                "worker_category": "Worker Category",
                "job_level": "Job Level",
                "salary": "Salary",
                "monthly_salary": "Monthly Salary",
                "working_hours": "Working Hours",
                "overtime": "Overtime",
                "leave_entitlement": "Leave Entitlement",
                "notice_period": "Notice Period",
                "special_allowance": "Special Allowance",
                "valid_from": "Valid from",
                "valid_to": "Valid to",
                "expires_on": "Expires on",
                "renewal_date": "Renewal Date",
                
                # Worker categories
                "operaio": "Blue-collar Worker",
                "impiegato": "White-collar Employee",
                "quadro": "Middle Management",
                "dirigente": "Executive",
                
                # Time periods
                "daily": "daily",
                "weekly": "weekly",
                "monthly": "monthly",
                "annual": "annual",
                "per_hour": "per hour",
                "per_day": "per day",
                
                # Leave types
                "ferie": "Annual Leave",
                "permessi_retribuiti": "Paid Leave",
                "malattia": "Sick Leave",
                "maternita": "Maternity Leave",
                "paternita": "Paternity Leave",
                "lutto": "Bereavement Leave",
                "matrimonio": "Wedding Leave",
                
                # Allowance types
                "buoni_pasto": "Meal Vouchers",
                "indennita_trasporto": "Transport Allowance",
                "indennita_rischio": "Risk Allowance",
                "indennita_turno": "Shift Allowance",
                "indennita_reperibilita": "On-call Allowance",
                "indennita_trasferta": "Travel Allowance",
                "indennita_funzione": "Role Allowance",
                "premio_produzione": "Production Bonus",
                "auto_aziendale": "Company Car",
                
                # Status terms
                "active": "Active",
                "expired": "Expired",
                "expiring_soon": "Expiring Soon",
                "under_negotiation": "Under Negotiation",
                "renewed": "Renewed",
                
                # Alerts and notifications
                "alert": "Alert",
                "notification": "Notification",
                "warning": "Warning",
                "error": "Error",
                "info": "Information",
                "critical": "Critical",
                
                # Actions
                "view_details": "View Details",
                "download": "Download",
                "export": "Export",
                "update": "Update",
                "renew": "Renew",
                "calculate": "Calculate",
                "search": "Search",
                "filter": "Filter",
                
                # Contributions
                "inps_contributions": "INPS Contributions",
                "inail_contributions": "INAIL Contributions",
                "employee_contribution": "Employee Contribution",
                "employer_contribution": "Employer Contribution",
                "total_contributions": "Total Contributions",
                "net_salary": "Net Salary",
                "gross_salary": "Gross Salary"
            }
        }
    
    def _initialize_sector_translations(self) -> Dict[CCNLSector, Dict[Language, Dict[str, str]]]:
        """Initialize sector-specific translations."""
        return {
            CCNLSector.METALMECCANICI_INDUSTRIA: {
                Language.ITALIAN: {
                    "name": "Metalmeccanici - Industria",
                    "description": "Settore metalmeccanico industriale",
                    "typical_companies": "Stabilimenti industriali, fabbriche di macchinari"
                },
                Language.ENGLISH: {
                    "name": "Metalworking - Industry",
                    "description": "Industrial metalworking sector",
                    "typical_companies": "Industrial plants, machinery factories"
                }
            },
            
            CCNLSector.COMMERCIO_TERZIARIO: {
                Language.ITALIAN: {
                    "name": "Commercio e Terziario",
                    "description": "Settore commerciale e dei servizi",
                    "typical_companies": "Negozi, centri commerciali, servizi"
                },
                Language.ENGLISH: {
                    "name": "Commerce and Services",
                    "description": "Commercial and service sector",
                    "typical_companies": "Retail stores, shopping centers, services"
                }
            },
            
            CCNLSector.EDILIZIA_INDUSTRIA: {
                Language.ITALIAN: {
                    "name": "Edilizia - Industria",
                    "description": "Settore delle costruzioni industriali",
                    "typical_companies": "Imprese di costruzioni, edilizia civile"
                },
                Language.ENGLISH: {
                    "name": "Construction - Industry",
                    "description": "Industrial construction sector",
                    "typical_companies": "Construction companies, civil engineering"
                }
            },
            
            CCNLSector.ICT: {
                Language.ITALIAN: {
                    "name": "Tecnologie dell'Informazione",
                    "description": "Settore informatico e telecomunicazioni",
                    "typical_companies": "Aziende software, servizi IT, telecomunicazioni"
                },
                Language.ENGLISH: {
                    "name": "Information Technology",
                    "description": "IT and telecommunications sector",
                    "typical_companies": "Software companies, IT services, telecommunications"
                }
            },
            
            CCNLSector.SANITA_PRIVATA: {
                Language.ITALIAN: {
                    "name": "Sanità Privata",
                    "description": "Settore sanitario privato",
                    "typical_companies": "Cliniche private, case di cura, poliambulatori"
                },
                Language.ENGLISH: {
                    "name": "Private Healthcare",
                    "description": "Private healthcare sector",
                    "typical_companies": "Private clinics, nursing homes, medical centers"
                }
            }
            
            # Additional sectors would be added here...
        }
    
    def translate(self, key: str, language: Language = None) -> str:
        """Translate a key to the specified language."""
        if language is None:
            language = self.default_language
        
        translations = self.translations.get(language, {})
        return translations.get(key, key)  # Return key if translation not found
    
    def translate_sector(self, sector: CCNLSector, field: str, language: Language = None) -> str:
        """Translate sector-specific information."""
        if language is None:
            language = self.default_language
        
        sector_data = self.sector_translations.get(sector, {})
        language_data = sector_data.get(language, {})
        
        # Fallback to Italian if English translation not available
        if not language_data and language == Language.ENGLISH:
            language_data = sector_data.get(Language.ITALIAN, {})
        
        return language_data.get(field, f"{sector.value}_{field}")
    
    def translate_worker_category(self, category: WorkerCategory, language: Language = None) -> str:
        """Translate worker category."""
        return self.translate(category.value, language)
    
    def translate_leave_type(self, leave_type: LeaveType, language: Language = None) -> str:
        """Translate leave type."""
        return self.translate(leave_type.value, language)
    
    def translate_allowance_type(self, allowance_type: AllowanceType, language: Language = None) -> str:
        """Translate allowance type."""
        return self.translate(allowance_type.value, language)
    
    def format_currency(self, amount: float, language: Language = None) -> str:
        """Format currency according to language preferences."""
        if language == Language.ENGLISH:
            return f"€{amount:,.2f}"
        else:  # Italian
            return f"€ {amount:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    
    def format_date(self, date_obj, language: Language = None) -> str:
        """Format date according to language preferences."""
        if language == Language.ENGLISH:
            return date_obj.strftime("%B %d, %Y")
        else:  # Italian
            months_it = {
                1: "gennaio", 2: "febbraio", 3: "marzo", 4: "aprile",
                5: "maggio", 6: "giugno", 7: "luglio", 8: "agosto",
                9: "settembre", 10: "ottobre", 11: "novembre", 12: "dicembre"
            }
            return f"{date_obj.day} {months_it[date_obj.month]} {date_obj.year}"
    
    def get_localized_ccnl_summary(self, sector: CCNLSector, language: Language = None) -> Dict[str, str]:
        """Get localized summary of a CCNL sector."""
        return {
            "sector_name": self.translate_sector(sector, "name", language),
            "description": self.translate_sector(sector, "description", language),
            "typical_companies": self.translate_sector(sector, "typical_companies", language),
            "worker_category_label": self.translate("worker_category", language),
            "salary_label": self.translate("monthly_salary", language),
            "working_hours_label": self.translate("working_hours", language),
            "leave_entitlement_label": self.translate("leave_entitlement", language)
        }
    
    def get_localized_job_level(self, job_level_data: Dict[str, Any], language: Language = None) -> Dict[str, str]:
        """Get localized job level information."""
        # This would typically involve translating job descriptions and requirements
        # For now, we return the Italian version with English labels
        
        if language == Language.ENGLISH:
            return {
                "level_code": job_level_data.get("level_code", ""),
                "level_name": job_level_data.get("level_name", ""),  # Could be translated
                "category": self.translate_worker_category(job_level_data.get("category"), language),
                "description": job_level_data.get("description", ""),  # Could be translated
                "experience_required": f"{job_level_data.get('minimum_experience_months', 0)} months minimum experience"
            }
        else:
            return {
                "level_code": job_level_data.get("level_code", ""),
                "level_name": job_level_data.get("level_name", ""),
                "category": self.translate_worker_category(job_level_data.get("category"), language),
                "description": job_level_data.get("description", ""),
                "experience_required": f"{job_level_data.get('minimum_experience_months', 0)} mesi di esperienza minima"
            }
    
    def get_supported_languages(self) -> List[Language]:
        """Get list of supported languages."""
        return list(Language)
    
    def set_default_language(self, language: Language):
        """Set the default language."""
        self.default_language = language
        logger.info(f"Default language set to {language.value}")
    
    def validate_translations(self) -> Dict[str, List[str]]:
        """Validate translation completeness."""
        italian_keys = set(self.translations[Language.ITALIAN].keys())
        english_keys = set(self.translations[Language.ENGLISH].keys())
        
        missing_english = italian_keys - english_keys
        missing_italian = english_keys - italian_keys
        
        return {
            "missing_english_translations": list(missing_english),
            "missing_italian_translations": list(missing_italian),
            "translation_completeness": {
                "italian": len(self.translations[Language.ITALIAN]),
                "english": len(self.translations[Language.ENGLISH])
            }
        }
    
    def export_translations(self, language: Language) -> Dict[str, str]:
        """Export translations for external use (e.g., frontend)."""
        return self.translations.get(language, {})
    
    def import_translations(self, language: Language, translations: Dict[str, str]):
        """Import translations from external source."""
        if language not in self.translations:
            self.translations[language] = {}
        
        self.translations[language].update(translations)
        logger.info(f"Imported {len(translations)} translations for {language.value}")


# Global instance
i18n_service = I18nService()