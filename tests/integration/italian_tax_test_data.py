"""
Italian Tax Test Data Generator.

Generates realistic Italian tax scenarios, queries, and expected outcomes
for comprehensive integration testing of PratikoAI system.
"""

import random
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from uuid import uuid4


class ItalianTaxTestDataGenerator:
    """Generate realistic Italian tax test data"""

    def __init__(self):
        self.regions = {
            "Lombardia": {
                "addizionale_regionale": 1.73,
                "cities": {
                    "Milano": {"addizionale_comunale": 0.8, "population": 1366180},
                    "Bergamo": {"addizionale_comunale": 0.7, "population": 120923},
                    "Brescia": {"addizionale_comunale": 0.6, "population": 196480},
                },
            },
            "Lazio": {
                "addizionale_regionale": 1.73,
                "cities": {
                    "Roma": {"addizionale_comunale": 0.9, "population": 2873494},
                    "Latina": {"addizionale_comunale": 0.5, "population": 125285},
                    "Frosinone": {"addizionale_comunale": 0.4, "population": 46595},
                },
            },
            "Sicilia": {
                "addizionale_regionale": 1.73,
                "cities": {
                    "Palermo": {"addizionale_comunale": 0.5, "population": 663401},
                    "Catania": {"addizionale_comunale": 0.6, "population": 311584},
                    "Messina": {"addizionale_comunale": 0.4, "population": 229648},
                },
            },
            "Veneto": {
                "addizionale_regionale": 1.73,
                "cities": {
                    "Venezia": {"addizionale_comunale": 0.7, "population": 261362},
                    "Verona": {"addizionale_comunale": 0.8, "population": 259608},
                    "Padova": {"addizionale_comunale": 0.6, "population": 214198},
                },
            },
            "Trentino-Alto Adige": {
                "addizionale_regionale": 1.23,  # Autonomous region
                "cities": {
                    "Trento": {"addizionale_comunale": 0.4, "population": 117417},
                    "Bolzano": {"addizionale_comunale": 0.3, "population": 107436},
                },
            },
        }

        self.tax_codes = {
            "IRPEF": {"acconto_prima_rata": "4001", "acconto_seconda_rata": "4033", "saldo": "4031"},
            "IRES": {"acconto_prima_rata": "2003", "acconto_seconda_rata": "2004", "saldo": "2001"},
            "IVA": {"mensile": "6001", "trimestrale": "6002", "annuale": "6003"},
            "IRAP": {"acconto": "3802", "saldo": "3801"},
        }

        self.professional_categories = {
            "dottore_commercialista": {
                "expertise": ["IRPEF", "IRES", "IVA", "consolidato_fiscale", "transfer_pricing"],
                "typical_queries_per_day": 15,
                "complexity_distribution": {"simple": 0.3, "medium": 0.5, "complex": 0.2},
            },
            "caf_operator": {
                "expertise": ["730", "detrazioni", "bonus", "rimborsi"],
                "typical_queries_per_day": 25,
                "complexity_distribution": {"simple": 0.8, "medium": 0.2, "complex": 0.0},
            },
            "consulente_del_lavoro": {
                "expertise": ["contributi", "payroll", "tfr", "cud"],
                "typical_queries_per_day": 12,
                "complexity_distribution": {"simple": 0.4, "medium": 0.4, "complex": 0.2},
            },
            "startup_consultant": {
                "expertise": ["startup_innovativa", "stock_options", "patent_box", "incentivi_rd"],
                "typical_queries_per_day": 8,
                "complexity_distribution": {"simple": 0.1, "medium": 0.4, "complex": 0.5},
            },
        }

    def generate_faq_queries(self, count: int = 50) -> list[dict[str, Any]]:
        """Generate common FAQ-style queries"""

        faq_templates = [
            # Tax calculation queries
            {
                "template": "Come calcolare l'IVA al {rate}%?",
                "variables": {"rate": [22, 10, 4, 5]},
                "expected_answer_contains": ["moltiplicare", "calcolo", "imponibile"],
                "cost": 0.0003,
                "response_time": 0.5,
                "source": "faq",
            },
            {
                "template": "Quali sono le scadenze fiscali {month} {year}?",
                "variables": {"month": ["gennaio", "luglio", "novembre"], "year": [2024, 2025]},
                "expected_answer_contains": ["scadenze", "versamento", "F24"],
                "cost": 0.0003,
                "response_time": 0.5,
                "source": "faq",
            },
            {
                "template": "Come compilare il modello {form}?",
                "variables": {"form": ["730", "F24", "Unico", "IVA"]},
                "expected_answer_contains": ["compilazione", "campi", "codici"],
                "cost": 0.0003,
                "response_time": 0.8,
                "source": "faq",
            },
            # Deduction queries
            {
                "template": "Detrazioni per {expense_type} 2024",
                "variables": {"expense_type": ["spese mediche", "ristrutturazione", "mobili", "figli"]},
                "expected_answer_contains": ["detrazioni", "limite", "documentazione"],
                "cost": 0.0003,
                "response_time": 0.6,
                "source": "faq",
            },
            {
                "template": "Bonus {bonus_type} requisiti",
                "variables": {"bonus_type": ["casa", "mobili", "facciate", "110%"]},
                "expected_answer_contains": ["requisiti", "percentuale", "limite"],
                "cost": 0.0003,
                "response_time": 0.7,
                "source": "faq",
            },
        ]

        faq_queries = []

        for _ in range(count):
            template = random.choice(faq_templates)
            query = template["template"]

            # Replace variables
            for var_name, options in template["variables"].items():
                value = random.choice(options)
                query = query.replace(f"{{{var_name}}}", str(value))

            faq_queries.append(
                {
                    "query": query,
                    "expected_answer_contains": template["expected_answer_contains"],
                    "expected_cost": template["cost"],
                    "expected_response_time": template["response_time"],
                    "expected_source": template["source"],
                    "complexity": "simple",
                }
            )

        return faq_queries

    def generate_regional_queries(self, count: int = 30) -> list[dict[str, Any]]:
        """Generate queries with regional variations"""

        regional_queries = []

        templates = [
            {
                "template": "Calcolo IRPEF per reddito €{income} residente {city} {region}",
                "complexity": "medium",
                "requires_regional_data": True,
            },
            {
                "template": "IMU {property_type} a {city} valore €{value}",
                "complexity": "medium",
                "requires_regional_data": True,
            },
            {
                "template": "Addizionale regionale {region} aliquote {year}",
                "complexity": "simple",
                "requires_regional_data": True,
            },
        ]

        for _ in range(count):
            template = random.choice(templates)

            # Pick random region and city
            region = random.choice(list(self.regions.keys()))
            city = random.choice(list(self.regions[region]["cities"].keys()))

            # Generate variables
            income = random.choice([25000, 35000, 45000, 60000, 80000])
            property_value = random.choice([150000, 200000, 300000, 500000])
            property_type = random.choice(["prima casa", "seconda casa", "ufficio"])
            year = random.choice([2024, 2025])

            query = template["template"].format(
                income=income, city=city, region=region, value=property_value, property_type=property_type, year=year
            )

            regional_queries.append(
                {
                    "query": query,
                    "region": region,
                    "city": city,
                    "complexity": template["complexity"],
                    "requires_regional_data": template["requires_regional_data"],
                    "expected_cost": 0.012 if template["complexity"] == "medium" else 0.008,
                    "expected_response_time": 2.0 if template["complexity"] == "medium" else 1.5,
                    "addizionale_regionale": self.regions[region]["addizionale_regionale"],
                    "addizionale_comunale": self.regions[region]["cities"][city]["addizionale_comunale"],
                }
            )

        return regional_queries

    def generate_professional_workflows(self) -> dict[str, list[dict[str, Any]]]:
        """Generate professional workflow scenarios"""

        workflows = {}

        for prof_type, prof_data in self.professional_categories.items():
            daily_queries = []

            # Generate typical daily queries for this professional
            for _ in range(prof_data["typical_queries_per_day"]):
                # Determine complexity based on distribution
                complexity = self._weighted_choice(prof_data["complexity_distribution"])

                # Generate appropriate query for this professional and complexity
                query_data = self._generate_professional_query(prof_type, complexity, prof_data["expertise"])
                daily_queries.append(query_data)

            workflows[prof_type] = daily_queries

        return workflows

    def generate_seasonal_scenarios(self) -> dict[str, list[dict[str, Any]]]:
        """Generate seasonal tax scenarios"""

        scenarios = {
            "july_deadline_rush": self._generate_july_deadline_queries(),
            "august_vacation": self._generate_august_vacation_queries(),
            "november_deadline": self._generate_november_deadline_queries(),
            "year_end_planning": self._generate_year_end_queries(),
        }

        return scenarios

    def generate_rss_updates(self, count: int = 20) -> list[dict[str, Any]]:
        """Generate realistic RSS updates"""

        update_templates = [
            {
                "title": "Nuove aliquote {tax} per {year}",
                "content": "Dal {date} cambiano le aliquote {tax}: {details}",
                "source": "Agenzia delle Entrate",
                "importance": 0.9,
                "affects": ["aliquote", "calcoli"],
            },
            {
                "title": "Proroga scadenze {month} per {reason}",
                "content": "Prorogate al {new_date} le scadenze fiscali di {month} a causa di {reason}",
                "source": "Ministero Economia",
                "importance": 0.8,
                "affects": ["scadenze", "versamenti"],
            },
            {
                "title": "Chiarimenti su {topic}",
                "content": "L'Agenzia delle Entrate chiarisce l'applicazione di {topic}: {clarification}",
                "source": "Agenzia delle Entrate",
                "importance": 0.7,
                "affects": ["interpretazione", "applicazione"],
            },
        ]

        updates = []

        for _ in range(count):
            template = random.choice(update_templates)

            # Generate variables
            tax = random.choice(["IVA", "IRPEF", "IRES", "IMU"])
            year = random.choice([2024, 2025])
            month = random.choice(["luglio", "novembre", "gennaio"])
            reason = random.choice(["eventi eccezionali", "calamità naturali", "emergenza sanitaria"])
            topic = random.choice(["regime forfettario", "bonus casa", "detrazioni spese"])

            # Format title safely
            title_vars = {"tax": tax, "year": year, "month": month, "reason": reason, "topic": topic}
            title = template["title"]
            for var, value in title_vars.items():
                title = title.replace(f"{{{var}}}", str(value))

            # Format content safely
            content_vars = {
                "tax": tax,
                "year": year,
                "month": month,
                "reason": reason,
                "topic": topic,
                "date": f"1° gennaio {year}",
                "new_date": "20 agosto",
                "details": "dettagli specifici della modifica",
                "clarification": "chiarimenti dettagliati",
            }
            content = template["content"]
            for var, value in content_vars.items():
                content = content.replace(f"{{{var}}}", str(value))

            updates.append(
                {
                    "title": title,
                    "content": content,
                    "source": template["source"],
                    "importance_score": template["importance"],
                    "affects_queries": template["affects"],
                    "published_date": datetime.utcnow() - timedelta(days=random.randint(0, 30)),
                    "expected_impact": "high" if template["importance"] > 0.8 else "medium",
                }
            )

        return updates

    def generate_expert_feedback_scenarios(self, count: int = 15) -> list[dict[str, Any]]:
        """Generate expert feedback scenarios"""

        categories = [
            "normativa_obsoleta",
            "interpretazione_errata",
            "caso_mancante",
            "calcolo_sbagliato",
            "troppo_generico",
        ]

        feedback_scenarios = []

        for _ in range(count):
            category = random.choice(categories)
            confidence = random.uniform(0.7, 0.98)

            # Generate scenario based on category
            if category == "normativa_obsoleta":
                scenario = {
                    "category": category,
                    "feedback_type": "incorrect",
                    "expert_answer": f"La normativa è cambiata dal {random.choice([2023, 2024])}",
                    "confidence": confidence,
                    "expected_pattern_detection": True,
                }
            elif category == "interpretazione_errata":
                scenario = {
                    "category": category,
                    "feedback_type": "incorrect",
                    "expert_answer": "L'interpretazione corretta prevede che...",
                    "confidence": confidence,
                    "expected_pattern_detection": True,
                }
            else:
                scenario = {
                    "category": category,
                    "feedback_type": random.choice(["incomplete", "incorrect"]),
                    "expert_answer": "La risposta dovrebbe includere...",
                    "confidence": confidence,
                    "expected_pattern_detection": random.choice([True, False]),
                }

            scenario.update(
                {
                    "query_id": str(uuid4()),
                    "expert_id": f"expert_{random.randint(1, 20):03d}",
                    "time_spent_seconds": random.randint(60, 300),
                }
            )

            feedback_scenarios.append(scenario)

        return feedback_scenarios

    def _weighted_choice(self, choices: dict[str, float]) -> str:
        """Choose based on weighted probabilities"""

        total = sum(choices.values())
        r = random.random() * total

        for choice, weight in choices.items():
            if r <= weight:
                return choice
            r -= weight

        return list(choices.keys())[-1]

    def _generate_professional_query(self, prof_type: str, complexity: str, expertise: list[str]) -> dict[str, Any]:
        """Generate query appropriate for professional type and complexity"""

        topic = random.choice(expertise)

        if complexity == "simple":
            templates = [f"Scadenze {topic} 2024", f"Come calcolare {topic}", f"Documenti necessari {topic}"]
            expected_cost = 0.003
            expected_time = 1.0

        elif complexity == "medium":
            templates = [
                f"Calcolo {topic} per cliente speciale",
                f"Applicazione {topic} caso complesso",
                f"Differenze {topic} tra regioni",
            ]
            expected_cost = 0.012
            expected_time = 2.0

        else:  # complex
            templates = [
                f"Ottimizzazione fiscale {topic} multinazionale",
                f"Ristrutturazione societaria {topic}",
                f"Compliance internazionale {topic}",
            ]
            expected_cost = 0.025
            expected_time = 3.0

        query = random.choice(templates)

        return {
            "query": query,
            "professional_context": prof_type,
            "complexity": complexity,
            "topic": topic,
            "expected_cost": expected_cost,
            "expected_response_time": expected_time,
            "requires_expertise": True,
        }

    def _generate_july_deadline_queries(self) -> list[dict[str, Any]]:
        """Generate July tax deadline queries"""

        july_queries = [
            "Scadenza saldo IRPEF 31 luglio",
            "Come versare F24 ultimo giorno utile",
            "Proroga versamenti luglio possibile?",
            "Sanzioni per ritardato pagamento luglio",
            "Acconto IRES prima rata luglio",
            "730 integrativo scadenze luglio",
            "F24 online orario limite 31 luglio",
            "Ravvedimento operoso dopo scadenze luglio",
        ]

        return [
            {
                "query": query,
                "context": "tax_deadline",
                "priority": "urgent",
                "expected_source": "faq",
                "expected_cost": 0.0003,
                "expected_response_time": 0.5,
            }
            for query in july_queries
        ]

    def _generate_august_vacation_queries(self) -> list[dict[str, Any]]:
        """Generate August vacation period queries"""

        vacation_queries = [
            "Tassazione affitti brevi agosto",
            "Dichiarazione redditi lavoro estero",
            "Detrazioni spese viaggio studio",
            "Regime fiscale nomadi digitali",
        ]

        return [
            {
                "query": query,
                "context": "vacation_period",
                "priority": "normal",
                "expected_cost": 0.008,
                "expected_response_time": 2.5,
            }
            for query in vacation_queries
        ]

    def _generate_november_deadline_queries(self) -> list[dict[str, Any]]:
        """Generate November deadline queries"""

        november_queries = [
            "Saldo IRAP novembre scadenza",
            "Seconda rata acconto IRPEF novembre",
            "IVA novembre versamento",
            "Contributi INPS novembre scadenze",
            "F24 novembre compilazione",
        ]

        return [
            {
                "query": query,
                "context": "november_deadline",
                "priority": "high",
                "expected_source": "faq",
                "expected_cost": 0.001,
                "expected_response_time": 0.8,
            }
            for query in november_queries
        ]

    def _generate_year_end_queries(self) -> list[dict[str, Any]]:
        """Generate year-end planning queries"""

        year_end_queries = [
            "Pianificazione fiscale fine anno",
            "Ottimizzazione tasse 2024",
            "Accantonamenti fiscali dicembre",
            "Strategie riduzione carico fiscale",
        ]

        return [
            {
                "query": query,
                "context": "year_end_planning",
                "complexity": "complex",
                "expected_cost": 0.020,
                "expected_response_time": 3.0,
            }
            for query in year_end_queries
        ]

    def get_all_test_data(self) -> dict[str, Any]:
        """Get complete test data set"""

        return {
            "faq_queries": self.generate_faq_queries(50),
            "regional_queries": self.generate_regional_queries(30),
            "professional_workflows": self.generate_professional_workflows(),
            "seasonal_scenarios": self.generate_seasonal_scenarios(),
            "rss_updates": self.generate_rss_updates(20),
            "expert_feedback": self.generate_expert_feedback_scenarios(15),
            "regions_data": self.regions,
            "tax_codes": self.tax_codes,
            "professional_categories": self.professional_categories,
        }


# Singleton instance for easy import
italian_tax_data = ItalianTaxTestDataGenerator()


def get_test_data_for_category(category: str) -> Any:
    """Get test data for specific category"""

    all_data = italian_tax_data.get_all_test_data()
    return all_data.get(category, [])


def get_random_queries(count: int, complexity: str | None = None) -> list[dict[str, Any]]:
    """Get random queries filtered by complexity"""

    all_data = italian_tax_data.get_all_test_data()
    all_queries = all_data["faq_queries"] + all_data["regional_queries"]

    if complexity:
        filtered_queries = [q for q in all_queries if q.get("complexity") == complexity]
        return random.sample(filtered_queries, min(count, len(filtered_queries)))

    return random.sample(all_queries, min(count, len(all_queries)))


def get_peak_load_scenario() -> dict[str, Any]:
    """Get peak load test scenario"""

    return {
        "concurrent_users": 50,
        "query_mix": {
            "simple": 0.6,  # 60% simple FAQ queries
            "medium": 0.3,  # 30% medium complexity
            "complex": 0.1,  # 10% complex queries
        },
        "duration_minutes": 10,
        "expected_success_rate": 0.95,
        "max_p95_response_time": 3.0,
        "max_avg_cost_per_query": 0.005,
    }


if __name__ == "__main__":
    # Generate and display sample test data
    generator = ItalianTaxTestDataGenerator()

    print("=== Sample FAQ Queries ===")
    faqs = generator.generate_faq_queries(5)
    for faq in faqs:
        print(f"Q: {faq['query']}")
        print(f"   Expected: {faq['expected_cost']}€, {faq['expected_response_time']}s")
        print()

    print("=== Sample Regional Queries ===")
    regionals = generator.generate_regional_queries(3)
    for query in regionals:
        print(f"Q: {query['query']}")
        print(f"   Region: {query['region']}, City: {query['city']}")
        print(f"   Expected: {query['expected_cost']}€, {query['expected_response_time']}s")
        print()

    print("=== Sample RSS Updates ===")
    updates = generator.generate_rss_updates(3)
    for update in updates:
        print(f"Title: {update['title']}")
        print(f"Source: {update['source']}, Impact: {update['expected_impact']}")
        print()
