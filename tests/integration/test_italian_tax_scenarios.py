"""
Italian Tax Scenarios Integration Tests.

Comprehensive test scenarios specifically designed for Italian tax compliance,
covering real-world use cases that Italian tax professionals encounter daily.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Any, Dict, List
from uuid import uuid4

import pytest

from tests.integration.test_pratikoai_integration import integration_test_environment


class TestItalianTaxProfessionalWorkflows:
    """Test workflows specific to Italian tax professionals"""

    @pytest.mark.asyncio
    async def test_commercialista_daily_workflow(self, integration_test_environment):
        """Test typical daily workflow of a Dottore Commercialista"""
        services, metrics = integration_test_environment

        # Morning routine: Check tax deadlines and updates
        morning_queries = [
            "Scadenze fiscali oggi",
            "Novità normative questa settimana",
            "Aggiornamenti Agenzia delle Entrate",
        ]

        morning_start = datetime.utcnow().replace(hour=9, minute=0)  # 9 AM start

        for query in morning_queries:
            response = await services["query_processor"].process_query(
                {
                    "query": query,
                    "user_id": "commercialista_001",
                    "professional_context": "dottore_commercialista",
                    "timestamp": morning_start,
                }
            )

            assert response["success"] is True
            assert response["response_time"] < 2.0  # Fast morning briefing

            # Should use cached/FAQ responses for routine queries
            if "scadenze" in query.lower():
                assert response.get("source") in ["faq", "cache"]

        # Mid-morning: Client-specific calculations
        client_calculations = [
            {"query": "IRPEF per SRL con fatturato €250.000", "client_id": "client_srl_001", "complexity": "medium"},
            {
                "query": "Regime forfettario architetto con ricavi €60.000",
                "client_id": "client_prof_001",
                "complexity": "medium",
            },
            {
                "query": "Consolidato fiscale holding 5 società",
                "client_id": "client_holding_001",
                "complexity": "high",
            },
        ]

        total_calculation_cost = 0.0

        for calc in client_calculations:
            calc_response = await services["query_processor"].process_query(
                {
                    "query": calc["query"],
                    "user_id": "commercialista_001",
                    "client_id": calc["client_id"],
                    "professional_context": "dottore_commercialista",
                    "calculation_required": True,
                }
            )

            assert calc_response["success"] is True

            # Professional responses should have high quality
            assert calc_response.get("quality_score", 0) > 0.85

            # Should include proper citations for professional use
            assert "citations" in calc_response
            assert len(calc_response["citations"]) > 0

            cost = calc_response.get("cost", 0)
            total_calculation_cost += cost

            # Complex queries should cost more but still be reasonable
            if calc["complexity"] == "high":
                assert 0.01 <= cost <= 0.025
            else:
                assert cost <= 0.015

        # Afternoon: Research and complex advisory
        afternoon_research = [
            "CFC rules per partecipazioni in Svizzera",
            "Transfer pricing documentazione PMI",
            "Fusione per incorporazione aspetti fiscali",
        ]

        research_costs = []
        for query in afternoon_research:
            research_response = await services["query_processor"].process_query(
                {
                    "query": query,
                    "user_id": "commercialista_001",
                    "professional_context": "dottore_commercialista",
                    "research_depth": "comprehensive",
                }
            )

            assert research_response["success"] is True

            # Research should be comprehensive
            answer_length = len(research_response["answer"])
            assert answer_length > 500  # Detailed responses

            # Should include regulatory references
            assert any(
                ref in research_response["answer"].lower() for ref in ["tuir", "codice civile", "decreto", "circolare"]
            )

            research_costs.append(research_response.get("cost", 0))

        # Daily cost should be reasonable for professional
        daily_total_cost = total_calculation_cost + sum(research_costs) + 0.003  # Morning queries

        assert daily_total_cost <= 0.10  # €0.10 daily budget per professional

        print(f"✅ Commercialista daily workflow: €{daily_total_cost:.4f} total cost")

    @pytest.mark.asyncio
    async def test_caf_operator_workflow(self, integration_test_environment):
        """Test CAF (Centro di Assistenza Fiscale) operator workflow"""
        services, metrics = integration_test_environment

        # CAF operators handle many simple tax return queries
        typical_caf_queries = [
            "Come compilare 730 per pensionato",
            "Detrazioni spese mediche 2024",
            "Bonus ristrutturazione prima casa",
            "730 precompilato modifiche",
            "Rimborso IRPEF quando arriva",
            "Detrazioni figli a carico università",
            "Spese veterinarie detraibili",
            "Bonus mobili ed elettrodomestici",
            "730 coniuge separato",
            "Detrazione affitto studenti fuori sede",
        ]

        # Simulate processing 20 queries in 2 hours (typical morning)
        datetime.utcnow()
        total_processing_time = 0.0
        total_cost = 0.0

        for i, query in enumerate(typical_caf_queries * 2):  # 20 queries total
            start = datetime.utcnow()

            response = await services["query_processor"].process_query(
                {
                    "query": query,
                    "user_id": "caf_operator_001",
                    "client_id": f"citizen_{i:03d}",
                    "professional_context": "caf_operator",
                    "service_type": "tax_assistance",
                }
            )

            end = datetime.utcnow()
            processing_time = (end - start).total_seconds()
            total_processing_time += processing_time

            assert response["success"] is True

            # CAF queries should be fast (citizens waiting)
            assert processing_time < 1.5

            # Should mostly hit FAQs (common citizen questions)
            cost = response.get("cost", 0.01)
            if response.get("source") == "faq":
                assert cost <= 0.001  # Very cheap FAQ hits

            total_cost += cost

        # CAF service should be very cost-efficient
        avg_cost_per_query = total_cost / 20
        assert avg_cost_per_query <= 0.003  # Average €0.003 per citizen query

        # Total time should allow 6 queries per hour (10 minutes each including explanation)
        avg_processing_time = total_processing_time / 20
        assert avg_processing_time <= 1.0  # Under 1 second processing

        print(f"✅ CAF operator workflow: {avg_cost_per_query:.4f} avg cost, {avg_processing_time:.2f}s avg time")

    @pytest.mark.asyncio
    async def test_startup_consultant_workflow(self, integration_test_environment):
        """Test workflow for consultants specializing in startup taxation"""
        services, metrics = integration_test_environment

        startup_scenarios = [
            {
                "query": "Regime fiscale startup innovativa pre-revenue",
                "startup_stage": "pre_revenue",
                "complexity": "high",
            },
            {
                "query": "Stock options tassazione dipendenti startup",
                "startup_stage": "series_a",
                "complexity": "high",
            },
            {"query": "Patent box per software house", "startup_stage": "scaling", "complexity": "medium"},
            {
                "query": "Trasferimento sede legale in Estonia fiscalità",
                "startup_stage": "international",
                "complexity": "very_high",
            },
            {"query": "Incentivi fiscali R&D startup", "startup_stage": "development", "complexity": "medium"},
        ]

        consultant_expertise_score = 0.0
        total_research_cost = 0.0

        for scenario in startup_scenarios:
            research_response = await services["query_processor"].process_query(
                {
                    "query": scenario["query"],
                    "user_id": "startup_consultant_001",
                    "professional_context": "startup_specialist",
                    "complexity": scenario["complexity"],
                    "research_depth": "expert_level",
                }
            )

            assert research_response["success"] is True

            # Startup queries are complex and should have comprehensive answers
            answer = research_response["answer"]
            assert len(answer) > 800  # Detailed analysis

            # Should include recent regulatory changes
            assert any(year in answer for year in ["2024", "2023"])

            # Should mention relevant startup-specific terms
            startup_terms = ["startup", "innovativa", "pmi", "agevolazioni", "incentivi"]
            assert any(term in answer.lower() for term in startup_terms)

            # Quality should be very high for expert consultation
            quality = research_response.get("quality_score", 0)
            assert quality > 0.90
            consultant_expertise_score += quality

            cost = research_response.get("cost", 0)
            total_research_cost += cost

            # Complex startup queries justify higher costs
            if scenario["complexity"] == "very_high":
                assert 0.02 <= cost <= 0.05
            elif scenario["complexity"] == "high":
                assert 0.015 <= cost <= 0.03

        # Consultant should provide consistently high-quality advice
        avg_expertise = consultant_expertise_score / len(startup_scenarios)
        assert avg_expertise > 0.92

        # Total cost should be justified by expert-level service
        assert total_research_cost <= 0.15  # Up to €0.15 for complex startup consultation

        print(f"✅ Startup consultant workflow: {avg_expertise:.3f} avg quality, €{total_research_cost:.4f} cost")


class TestRegionalTaxVariationScenarios:
    """Test regional tax variations across Italian regions"""

    @pytest.mark.asyncio
    async def test_northern_italy_tax_calculations(self, integration_test_environment):
        """Test tax calculations for Northern Italian regions"""
        services, metrics = integration_test_environment

        northern_regions = [
            {
                "region": "Lombardia",
                "city": "Milano",
                "addizionale_regionale": 1.73,
                "addizionale_comunale": 0.8,
                "test_income": 50000,
            },
            {
                "region": "Veneto",
                "city": "Venezia",
                "addizionale_regionale": 1.73,
                "addizionale_comunale": 0.7,
                "test_income": 45000,
            },
            {
                "region": "Piemonte",
                "city": "Torino",
                "addizionale_regionale": 1.73,
                "addizionale_comunale": 0.8,
                "test_income": 48000,
            },
        ]

        for region_data in northern_regions:
            query = f"Calcola IRPEF completa per reddito €{region_data['test_income']} residente {region_data['city']} {region_data['region']}"

            response = await services["query_processor"].process_query(
                {
                    "query": query,
                    "region": region_data["region"],
                    "city": region_data["city"],
                    "calculation_type": "irpef_complete",
                    "include_addizionali": True,
                }
            )

            assert response["success"] is True

            # Should mention the specific region and city
            answer = response["answer"].lower()
            assert region_data["region"].lower() in answer
            assert region_data["city"].lower() in answer

            # Should include correct addizionale rates
            assert str(region_data["addizionale_regionale"]) in response["answer"]

            # Northern regions typically have higher addizionale comunale
            if region_data["addizionale_comunale"] >= 0.7:
                assert "comunale" in answer

            # Should provide complete calculation breakdown
            assert any(term in answer for term in ["scaglioni", "aliquota", "detrazioni"])

        print(f"✅ Northern Italy calculations completed for {len(northern_regions)} regions")

    @pytest.mark.asyncio
    async def test_southern_italy_tax_calculations(self, integration_test_environment):
        """Test tax calculations for Southern Italian regions"""
        services, metrics = integration_test_environment

        southern_regions = [
            {
                "region": "Sicilia",
                "city": "Palermo",
                "addizionale_regionale": 1.73,
                "addizionale_comunale": 0.5,  # Often lower in South
                "test_income": 35000,
            },
            {
                "region": "Calabria",
                "city": "Reggio Calabria",
                "addizionale_regionale": 1.73,
                "addizionale_comunale": 0.4,
                "test_income": 32000,
            },
            {
                "region": "Puglia",
                "city": "Bari",
                "addizionale_regionale": 1.73,
                "addizionale_comunale": 0.6,
                "test_income": 38000,
            },
        ]

        for region_data in southern_regions:
            query = f"Quanto pago di tasse con €{region_data['test_income']} a {region_data['city']}?"

            response = await services["query_processor"].process_query(
                {
                    "query": query,
                    "region": region_data["region"],
                    "city": region_data["city"],
                    "calculation_type": "tax_burden_complete",
                }
            )

            assert response["success"] is True

            # Should include regional context
            assert region_data["region"] in response["answer"]

            # Southern regions may have specific incentives or lower rates
            answer_lower = response["answer"].lower()

            # Should mention lower comunale rates where applicable
            if region_data["addizionale_comunale"] <= 0.5:
                # Should explain the advantage
                assert any(term in answer_lower for term in ["comunale", "addizionale", "aliquota"])

            # May mention zona economica speciale or other southern incentives
            if region_data["region"] in ["Sicilia", "Calabria"]:
                # Could mention ZES or other incentives
                pass

        print(f"✅ Southern Italy calculations completed for {len(southern_regions)} regions")

    @pytest.mark.asyncio
    async def test_autonomous_regions_special_rules(self, integration_test_environment):
        """Test special tax rules for autonomous regions"""
        services, metrics = integration_test_environment

        autonomous_regions = [
            {
                "region": "Trentino-Alto Adige",
                "province": "Trento",
                "special_rules": ["reduced_irpef", "provincial_autonomy"],
                "addizionale_regionale": 1.23,  # Reduced rate
            },
            {
                "region": "Valle d'Aosta",
                "province": "Aosta",
                "special_rules": ["tax_autonomy", "different_brackets"],
                "addizionale_regionale": 1.33,
            },
            {
                "region": "Friuli-Venezia Giulia",
                "province": "Trieste",
                "special_rules": ["regional_variations"],
                "addizionale_regionale": 1.73,
            },
        ]

        for region_data in autonomous_regions:
            query = f"Regime fiscale speciale {region_data['region']} differenze con resto Italia"

            response = await services["query_processor"].process_query(
                {
                    "query": query,
                    "region": region_data["region"],
                    "province": region_data.get("province"),
                    "special_status": "autonomous_region",
                }
            )

            assert response["success"] is True

            # Should explain autonomous status
            answer = response["answer"].lower()
            assert any(term in answer for term in ["autonoma", "speciale", "statuto"])

            # Should mention specific advantages or differences
            assert region_data["region"] in response["answer"]

            # For Trentino-Alto Adige, should mention reduced rates
            if region_data["region"] == "Trentino-Alto Adige":
                assert "1.23" in response["answer"] or "ridotta" in answer

            # Should be comprehensive for complex autonomous rules
            assert len(response["answer"]) > 400

        print(f"✅ Autonomous regions special rules tested for {len(autonomous_regions)} regions")


class TestSeasonalTaxWorkflows:
    """Test tax workflows during different Italian tax seasons"""

    @pytest.mark.asyncio
    async def test_july_tax_deadline_rush(self, integration_test_environment):
        """Test system during July tax deadline period"""
        services, metrics = integration_test_environment

        # Mock July tax deadline period
        from unittest.mock import patch

        with patch("datetime.datetime") as mock_datetime:
            # July 30th - last minute rush
            mock_datetime.utcnow.return_value = datetime(2024, 7, 30, 16, 0, 0)

            july_deadline_queries = [
                "Scadenza versamento saldo IRPEF",
                "Come versare F24 ultimo giorno",
                "Proroga pagamenti possibile?",
                "Sanzioni ritardato pagamento luglio",
                "F24 online dopo le 24 del 31 luglio",
                "Acconto IRES quando versare",
                "730 correttivo scadenze",
                "Ravvedimento operoso luglio",
            ]

            # These should be very fast (FAQ hits) during deadline rush
            rush_start = datetime.utcnow()

            for query in july_deadline_queries:
                response = await services["query_processor"].process_query(
                    {
                        "query": query,
                        "priority": "urgent",  # Deadline queries get priority
                        "context": "tax_deadline",
                    }
                )

                assert response["success"] is True
                assert response["response_time"] < 1.0  # Very fast during rush

                # Should hit FAQ/cache for common deadline questions
                assert response.get("source") in ["faq", "cache"]
                assert response.get("cost", 0.01) <= 0.001

            rush_end = datetime.utcnow()
            total_rush_time = (rush_end - rush_start).total_seconds()

            # All deadline queries should be processed quickly
            assert total_rush_time < 5.0  # All 8 queries in under 5 seconds

            print(f"✅ July deadline rush: {len(july_deadline_queries)} queries in {total_rush_time:.2f}s")

    @pytest.mark.asyncio
    async def test_august_vacation_period(self, integration_test_environment):
        """Test system behavior during August vacation period"""
        services, metrics = integration_test_environment

        from unittest.mock import patch

        with patch("datetime.datetime") as mock_datetime:
            # August 15th - peak vacation
            mock_datetime.utcnow.return_value = datetime(2024, 8, 15, 10, 0, 0)

            # Lower volume, more complex queries during vacation
            vacation_queries = [
                "Tassazione affitti brevi agosto",
                "Dichiarazione redditi da estero vacanze lavoro",
                "Detrazioni spese viaggio studio figli",
                "Regime fiscale influencer in vacanza",
            ]

            vacation_costs = []

            for query in vacation_queries:
                response = await services["query_processor"].process_query(
                    {
                        "query": query,
                        "context": "vacation_period",
                        "priority": "normal",  # Less urgent during vacation
                    }
                )

                assert response["success"] is True

                # Can afford slightly higher processing times during vacation
                assert response["response_time"] < 3.0

                # Cost optimizations during lower demand
                cost = response.get("cost", 0.01)
                vacation_costs.append(cost)

                # Answers can be more detailed during lower volume period
                assert len(response["answer"]) > 300

            # Average cost should benefit from vacation optimizations
            avg_vacation_cost = sum(vacation_costs) / len(vacation_costs)
            assert avg_vacation_cost <= 0.012  # Slightly reduced costs

            print(f"✅ August vacation period: €{avg_vacation_cost:.4f} avg cost")

    @pytest.mark.asyncio
    async def test_november_tax_deadline_period(self, integration_test_environment):
        """Test November tax deadline period"""
        services, metrics = integration_test_environment

        from unittest.mock import patch

        with patch("datetime.datetime") as mock_datetime:
            # November 30th - second major deadline
            mock_datetime.utcnow.return_value = datetime(2024, 11, 30, 14, 0, 0)

            november_queries = [
                "Scadenza saldo IRAP novembre",
                "Versamento seconda rata acconto IRPEF",
                "F24 novembre compilazione",
                "Acconto IRES seconda rata calcolo",
                "Scadenze novembre professionisti",
                "IVA novembre versamento",
                "Contributi INPS novembre scadenze",
            ]

            november_processing_times = []
            november_costs = []

            for query in november_queries:
                start_time = datetime.utcnow()

                response = await services["query_processor"].process_query(
                    {"query": query, "context": "november_deadline", "priority": "high"}
                )

                end_time = datetime.utcnow()
                processing_time = (end_time - start_time).total_seconds()

                november_processing_times.append(processing_time)
                november_costs.append(response.get("cost", 0.01))

                assert response["success"] is True
                assert processing_time < 1.5  # Fast for deadline period

                # Should include specific November deadline information
                assert "novembre" in response["answer"].lower()

            # November period should be highly optimized
            avg_nov_time = sum(november_processing_times) / len(november_processing_times)
            avg_nov_cost = sum(november_costs) / len(november_costs)

            assert avg_nov_time < 1.0
            assert avg_nov_cost <= 0.002  # Very efficient due to FAQ hits

            print(f"✅ November deadline period: {avg_nov_time:.2f}s avg time, €{avg_nov_cost:.4f} avg cost")


if __name__ == "__main__":
    # Run Italian tax scenario tests
    pytest.main([__file__, "-v", "--asyncio-mode=auto"])
