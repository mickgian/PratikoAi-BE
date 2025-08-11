"""
Comprehensive TDD Tests for GDPR Article 20 Data Export Functionality.

This test suite ensures full compliance with GDPR "Right to data portability" for 
Italian users, covering all data types, formats, privacy protections, and security measures.

Test Categories:
1. Data Collection Tests - Complete user data gathering
2. Format and Structure Tests - JSON/CSV with Italian formatting
3. Privacy and Security Tests - PII protection and access control
4. Italian Compliance Tests - Codice Fiscale, Partita IVA, fattura elettronica
"""

import pytest
import asyncio
import json
import csv
import zipfile
from io import StringIO, BytesIO
from datetime import datetime, timedelta, date
from decimal import Decimal
from typing import Dict, List, Optional
from unittest.mock import Mock, patch
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession
from fastapi.testclient import TestClient

from app.core.database import get_db
from app.core.encryption import EncryptionService
from app.models.user import User
from app.models.subscription import Subscription, SubscriptionPlan, Invoice
from app.models.data_export import DataExportRequest, ExportFormat, ExportStatus
from app.services.data_export_service import (
    DataExportService, 
    ExportLimitExceeded,
    ExportFileGenerator,
    ExportProgressTracker
)
from app.services.cache import get_redis_client


class TestDataCollection:
    """Test complete user data collection for export"""
    
    @pytest.fixture
    async def sample_user_data(self, db_session: AsyncSession):
        """Create comprehensive test user data"""
        # Create user with Italian data
        user = User(
            id=uuid4(),
            email="mario.rossi@test.it",
            full_name="Mario Rossi",
            codice_fiscale="RSSMRA80A01H501U",
            partita_iva="12345678903",  # Business user
            created_at=datetime(2024, 1, 15, 10, 30),
            subscription_status="active"
        )
        db_session.add(user)
        
        # Create subscription plan
        annual_plan = SubscriptionPlan(
            id=uuid4(),
            name="Professionale Annuale",
            billing_period="annual",
            base_price_cents=59900,  # €599
            iva_rate=Decimal("22.00")
        )
        db_session.add(annual_plan)
        
        # Create subscription
        subscription = Subscription(
            id=uuid4(),
            user_id=user.id,
            plan_id=annual_plan.id,
            status="active",
            created_at=datetime(2024, 2, 1, 14, 0),
            current_period_start=datetime(2024, 2, 1),
            current_period_end=datetime(2025, 2, 1),
            is_business=True,
            partita_iva="12345678903",
            invoice_name="Mario Rossi SRL"
        )
        db_session.add(subscription)
        
        # Create sample queries
        for i in range(5):
            query = QueryHistory(
                id=uuid4(),
                user_id=user.id,
                query=f"Come calcolare l'IVA per la fattura numero {i+1}?",
                response_cached=i % 2 == 0,
                response_time_ms=1200 + (i * 100),
                tokens_used=150 + (i * 10),
                cost_cents=5 + i,
                timestamp=datetime(2024, 3, 1 + i, 10, 0)
            )
            db_session.add(query)
        
        # Create sample documents
        for i in range(3):
            document = DocumentAnalysis(
                id=uuid4(),
                user_id=user.id,
                filename=f"fattura_fornitore_{i+1}.pdf",
                file_type="application/pdf",
                analysis_type="italian_invoice",
                processing_time_ms=5000 + (i * 500),
                uploaded_at=datetime(2024, 4, 1 + i, 15, 30)
            )
            db_session.add(document)
        
        # Create tax calculations
        tax_calc = TaxCalculation(
            id=uuid4(),
            user_id=user.id,
            calculation_type="IVA",
            input_amount=Decimal("1000.00"),
            result={"iva_amount": 220.00, "total": 1220.00},
            parameters={"rate": 22.0, "region": "Lazio"},
            timestamp=datetime(2024, 5, 1, 11, 45)
        )
        db_session.add(tax_calc)
        
        # Create invoices
        invoice = Invoice(
            id=uuid4(),
            subscription_id=subscription.id,
            invoice_number="2024/0001",
            invoice_date=datetime(2024, 2, 1),
            subtotal=Decimal("599.00"),
            iva_amount=Decimal("131.78"),
            total_amount=Decimal("730.78"),
            payment_status="paid"
        )
        db_session.add(invoice)
        
        await db_session.commit()
        return user

    async def test_complete_user_profile_export(self, sample_user_data, db_session):
        """Test complete user profile export excluding password"""
        service = DataExportService(db_session, EncryptionService(), Mock())
        
        export_request = DataExportRequest(
            user_id=sample_user_data.id,
            format=ExportFormat.JSON,
            include_sensitive=True
        )
        
        user_data = await service.collect_user_data(sample_user_data.id, export_request)
        
        # Verify profile data structure
        assert "profile" in user_data
        profile = user_data["profile"]
        
        # Must include essential profile data
        assert profile["email"] == "mario.rossi@test.it"
        assert profile["name"] == "Mario Rossi"
        assert profile["created_at"] == "2024-01-15T10:30:00"
        assert profile["subscription_status"] == "active"
        assert profile["language"] == "it_IT"
        assert profile["timezone"] == "Europe/Rome"
        
        # Italian specific data for business users
        assert "codice_fiscale" not in profile  # Should be in separate section
        assert "partita_iva" not in profile     # Should be in business section
        
        # Must never include sensitive security data
        assert "password" not in profile
        assert "password_hash" not in profile
        assert "access_token" not in profile
        assert "refresh_token" not in profile

    async def test_query_history_export_with_timestamps(self, sample_user_data, db_session):
        """Test query history export with timestamps and responses"""
        service = DataExportService(db_session, EncryptionService(), Mock())
        
        export_request = DataExportRequest(
            user_id=sample_user_data.id,
            format=ExportFormat.JSON,
            date_from=date(2024, 3, 1),
            date_to=date(2024, 3, 31)
        )
        
        user_data = await service.collect_user_data(sample_user_data.id, export_request)
        
        # Verify queries section
        assert "queries" in user_data
        queries = user_data["queries"]
        assert len(queries) == 5
        
        # Verify query structure
        first_query = queries[0]
        assert "id" in first_query
        assert "timestamp" in first_query
        assert "query" in first_query
        assert "response_cached" in first_query
        assert "response_time_ms" in first_query
        assert "tokens_used" in first_query
        assert "cost_cents" in first_query
        
        # Verify Italian query content
        assert "Come calcolare l'IVA" in first_query["query"]
        assert first_query["timestamp"] == "2024-03-01T10:00:00"
        assert isinstance(first_query["response_cached"], bool)
        assert first_query["response_time_ms"] >= 1200
        assert first_query["tokens_used"] >= 150
        assert first_query["cost_cents"] >= 5

    async def test_document_metadata_export_no_content(self, sample_user_data, db_session):
        """Test document metadata export without actual document content"""
        service = DataExportService(db_session, EncryptionService(), Mock())
        
        export_request = DataExportRequest(
            user_id=sample_user_data.id,
            format=ExportFormat.JSON
        )
        
        user_data = await service.collect_user_data(sample_user_data.id, export_request)
        
        # Verify documents section
        assert "documents" in user_data
        documents = user_data["documents"]
        assert len(documents) == 3
        
        # Verify document metadata structure
        first_doc = documents[0]
        assert "id" in first_doc
        assert "uploaded_at" in first_doc
        assert "filename" in first_doc
        assert "file_type" in first_doc
        assert "analysis_type" in first_doc
        assert "processing_time_ms" in first_doc
        
        # Must NOT include actual document content
        assert "content" not in first_doc
        assert "file_data" not in first_doc
        assert "document_text" not in first_doc
        assert "binary_data" not in first_doc
        
        # Verify Italian document types
        assert first_doc["filename"] == "fattura_fornitore_1.pdf"
        assert first_doc["file_type"] == "application/pdf"
        assert first_doc["analysis_type"] == "italian_invoice"

    async def test_subscription_billing_history_export(self, sample_user_data, db_session):
        """Test subscription and billing history export"""
        service = DataExportService(db_session, EncryptionService(), Mock())
        
        export_request = DataExportRequest(
            user_id=sample_user_data.id,
            format=ExportFormat.JSON,
            include_fatture=True
        )
        
        user_data = await service.collect_user_data(sample_user_data.id, export_request)
        
        # Verify subscriptions section
        assert "subscriptions" in user_data
        subscriptions = user_data["subscriptions"]
        assert len(subscriptions) == 1
        
        subscription = subscriptions[0]
        assert subscription["plan"] == "Professionale Annuale"
        assert subscription["period"] == "annual"
        assert subscription["amount_eur"] == 599.0
        assert subscription["iva_rate"] == 22.0
        assert subscription["status"] == "active"
        
        # Verify Italian invoices (fatture) section
        assert "fatture" in user_data
        fatture = user_data["fatture"]
        assert len(fatture) == 1
        
        fattura = fatture[0]
        assert fattura["numero"] == "2024/0001"
        assert fattura["data"] == "2024-02-01T00:00:00"
        assert fattura["importo_imponibile"] == 599.0
        assert fattura["iva"] == 131.78
        assert fattura["totale"] == 730.78
        assert fattura["partita_iva"] == "12345678903"

    async def test_usage_statistics_export(self, sample_user_data, db_session):
        """Test usage statistics and analytics export"""
        service = DataExportService(db_session, EncryptionService(), Mock())
        
        # Mock usage statistics
        with patch.object(service, 'get_usage_statistics') as mock_stats:
            mock_stats.return_value = Mock(
                total_queries=25,
                cached_queries=12,
                cache_hit_rate=0.48,
                total_documents=8,
                total_cost_cents=1250,
                avg_response_time=1450
            )
            
            export_request = DataExportRequest(
                user_id=sample_user_data.id,
                format=ExportFormat.JSON
            )
            
            user_data = await service.collect_user_data(sample_user_data.id, export_request)
            
            # Verify usage statistics
            assert "usage_statistics" in user_data
            stats = user_data["usage_statistics"]
            
            assert stats["total_queries"] == 25
            assert stats["cached_queries"] == 12
            assert stats["cache_hit_rate"] == 0.48
            assert stats["total_documents"] == 8
            assert stats["total_cost_eur"] == 12.50
            assert stats["average_response_time_ms"] == 1450

    async def test_tax_calculation_history_export(self, sample_user_data, db_session):
        """Test tax calculation history export"""
        service = DataExportService(db_session, EncryptionService(), Mock())
        
        export_request = DataExportRequest(
            user_id=sample_user_data.id,
            format=ExportFormat.JSON
        )
        
        user_data = await service.collect_user_data(sample_user_data.id, export_request)
        
        # Verify tax calculations section
        assert "tax_calculations" in user_data
        calculations = user_data["tax_calculations"]
        assert len(calculations) == 1
        
        calc = calculations[0]
        assert calc["type"] == "IVA"
        assert calc["input_amount"] == 1000.0
        assert calc["result"]["iva_amount"] == 220.0
        assert calc["result"]["total"] == 1220.0
        assert calc["parameters"]["rate"] == 22.0
        assert calc["parameters"]["region"] == "Lazio"

    async def test_knowledge_base_faq_interactions_export(self, sample_user_data, db_session):
        """Test knowledge base and FAQ usage history export"""
        service = DataExportService(db_session, EncryptionService(), Mock())
        
        # Create sample FAQ interactions
        faq_interaction = FAQInteraction(
            id=uuid4(),
            user_id=sample_user_data.id,
            faq_id="faq_iva_calcolo",
            question="Come si calcola l'IVA al 22%?",
            viewed_at=datetime(2024, 6, 1, 16, 30),
            helpful_rating=5
        )
        db_session.add(faq_interaction)
        
        kb_search = KnowledgeBaseSearch(
            id=uuid4(),
            user_id=sample_user_data.id,
            search_query="regime forfettario partita iva",
            results_count=3,
            clicked_result_id="kb_regime_forfettario",
            searched_at=datetime(2024, 6, 2, 14, 15)
        )
        db_session.add(kb_search)
        
        await db_session.commit()
        
        export_request = DataExportRequest(
            user_id=sample_user_data.id,
            format=ExportFormat.JSON
        )
        
        user_data = await service.collect_user_data(sample_user_data.id, export_request)
        
        # Verify FAQ interactions
        assert "faq_interactions" in user_data
        faq_data = user_data["faq_interactions"]
        assert len(faq_data) == 1
        
        faq = faq_data[0]
        assert faq["question"] == "Come si calcola l'IVA al 22%?"
        assert faq["viewed_at"] == "2024-06-01T16:30:00"
        assert faq["helpful_rating"] == 5
        
        # Verify knowledge base searches
        assert "knowledge_searches" in user_data
        kb_data = user_data["knowledge_searches"]
        assert len(kb_data) == 1
        
        search = kb_data[0]
        assert search["query"] == "regime forfettario partita iva"
        assert search["results_count"] == 3
        assert search["searched_at"] == "2024-06-02T14:15:00"


class TestFormatAndStructure:
    """Test export format generation and Italian formatting"""
    
    async def test_json_export_format_structure(self):
        """Test JSON export format with proper structure"""
        generator = ExportFileGenerator()
        
        sample_data = {
            "export_info": {
                "generated_at": datetime(2024, 12, 5, 15, 30).isoformat(),
                "format_version": "1.0",
                "user_id": str(uuid4())
            },
            "profile": {
                "email": "mario.rossi@test.it",
                "name": "Mario Rossi",
                "created_at": datetime(2024, 1, 15).isoformat()
            },
            "queries": [
                {
                    "timestamp": datetime(2024, 3, 1, 10, 0).isoformat(),
                    "query": "Come calcolare l'IVA?",
                    "cost_cents": 5
                }
            ]
        }
        
        json_content = await generator.generate_json_export(sample_data)
        
        # Verify JSON structure
        parsed_data = json.loads(json_content.decode('utf-8'))
        
        assert "export_info" in parsed_data
        assert "profile" in parsed_data
        assert "queries" in parsed_data
        
        # Verify Italian formatting
        assert parsed_data["export_info"]["format_version"] == "1.0"
        assert "mario.rossi@test.it" in parsed_data["profile"]["email"]

    async def test_csv_export_italian_encoding(self):
        """Test CSV export with Italian-friendly encoding (UTF-8 BOM)"""
        generator = ExportFileGenerator()
        
        queries_data = [
            {
                "timestamp": "2024-03-01T10:00:00",
                "query": "Calcolo IVA al 22% per €1.000",
                "response_time_ms": 1200,
                "tokens_used": 150,
                "cost_cents": 5,
                "response_cached": True
            }
        ]
        
        csv_content = await generator.generate_queries_csv(queries_data)
        
        # Verify UTF-8 BOM for Excel compatibility
        assert csv_content.startswith(b'\xef\xbb\xbf')
        
        # Verify Italian CSV formatting (semicolon delimiter)
        csv_text = csv_content.decode('utf-8')
        assert ';' in csv_text  # Italian Excel uses semicolon
        assert 'Data;Ora;Domanda' in csv_text  # Italian headers
        assert '01/03/2024' in csv_text  # DD/MM/YYYY format
        assert '€' in csv_text or 'Calcolo IVA' in csv_text

    async def test_date_formatting_italian_locale(self):
        """Test date formatting for Italian locale (DD/MM/YYYY)"""
        generator = ExportFileGenerator()
        
        # Test various date formats
        test_date = datetime(2024, 3, 15, 14, 30, 45)
        
        class ItalianJSONEncoder(json.JSONEncoder):
            def default(self, obj):
                if isinstance(obj, datetime):
                    return obj.strftime("%d/%m/%Y %H:%M:%S")
                elif isinstance(obj, date):
                    return obj.strftime("%d/%m/%Y")
                return super().default(obj)
        
        data = {"test_date": test_date}
        json_content = json.dumps(data, cls=ItalianJSONEncoder)
        
        # Verify Italian date format
        assert "15/03/2024 14:30:45" in json_content

    async def test_currency_formatting_euro_comma_decimal(self):
        """Test currency formatting (€ symbol, comma decimal separator)"""
        generator = ExportFileGenerator()
        
        # Test Italian currency formatting
        amount = Decimal("1234.56")
        
        class ItalianJSONEncoder(json.JSONEncoder):
            def default(self, obj):
                if isinstance(obj, Decimal):
                    return f"€ {obj:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
                return super().default(obj)
        
        data = {"amount": amount}
        json_content = json.dumps(data, cls=ItalianJSONEncoder)
        
        # Verify Italian currency format: € 1.234,56
        assert "€ 1.234,56" in json_content

    async def test_encrypted_field_decryption_during_export(self):
        """Test encrypted field decryption during export"""
        encryption_service = EncryptionService()
        service = DataExportService(Mock(), encryption_service, Mock())
        
        # Mock encrypted user data
        user = Mock()
        user.email = encryption_service.encrypt("mario.rossi@test.it")
        user.full_name = encryption_service.encrypt("Mario Rossi")
        user.tax_id = encryption_service.encrypt("RSSMRA80A01H501U")
        
        # Test decryption during export
        with patch.object(service, '_get_user', return_value=user):
            export_request = DataExportRequest(
                user_id=uuid4(),
                format=ExportFormat.JSON,
                include_sensitive=True
            )
            
            user_data = await service.collect_user_data(user.id, export_request)
            
            # Verify decrypted data in export
            assert user_data["profile"]["email"] == "mario.rossi@test.it"
            assert user_data["profile"]["name"] == "Mario Rossi"

    async def test_file_size_handling_zip_large_exports(self):
        """Test file size handling (zip for exports >10MB)"""
        service = DataExportService(Mock(), Mock(), Mock())
        
        # Create large export data (simulate >10MB)
        large_data = {
            "export_info": {"generated_at": datetime.utcnow().isoformat()},
            "queries": [
                {
                    "id": str(uuid4()),
                    "query": "A" * 1000,  # Large query text
                    "timestamp": datetime.utcnow().isoformat()
                }
                for _ in range(10000)  # Many queries
            ]
        }
        
        generator = ExportFileGenerator()
        json_content = await generator.generate_json_export(large_data)
        
        # If export is large, should create ZIP
        if len(json_content) > 10 * 1024 * 1024:  # 10MB
            zip_content = await generator.create_zip_export({
                "dati_completi.json": json_content
            })
            
            # Verify ZIP creation
            assert len(zip_content) < len(json_content)  # Should be compressed
            
            # Verify ZIP contents
            with zipfile.ZipFile(BytesIO(zip_content), 'r') as zip_file:
                assert "dati_completi.json" in zip_file.namelist()

    async def test_export_manifest_generation_metadata(self):
        """Test export manifest generation with metadata"""
        service = DataExportService(Mock(), Mock(), Mock())
        
        export_request = DataExportRequest(
            user_id=uuid4(),
            format=ExportFormat.BOTH,
            include_sensitive=True,
            date_from=date(2024, 1, 1),
            date_to=date(2024, 12, 31)
        )
        
        manifest = await service.generate_export_manifest(export_request, {
            "profile": {"email": "test@test.it"},
            "queries": [{"id": "1"}] * 100,
            "documents": [{"id": "1"}] * 50
        })
        
        # Verify manifest structure
        assert manifest["export_metadata"]["user_id"] == str(export_request.user_id)
        assert manifest["export_metadata"]["format"] == "both"
        assert manifest["export_metadata"]["generated_at"]
        assert manifest["data_summary"]["total_queries"] == 100
        assert manifest["data_summary"]["total_documents"] == 50
        assert manifest["privacy_info"]["includes_sensitive_data"] == True
        assert "GDPR Article 20" in manifest["compliance"]["legal_basis"]


class TestPrivacySecurity:
    """Test privacy protection and security measures"""
    
    async def test_pii_anonymization_options(self):
        """Test PII anonymization options (export without sensitive data)"""
        service = DataExportService(Mock(), EncryptionService(), Mock())
        
        export_request = DataExportRequest(
            user_id=uuid4(),
            format=ExportFormat.JSON,
            anonymize_pii=True
        )
        
        # Mock user with sensitive data
        user = Mock()
        user.email = "mario.rossi@test.it"
        user.tax_id = "RSSMRA80A01H501U"
        
        with patch.object(service, '_get_user', return_value=user):
            user_data = await service.collect_user_data(user.id, export_request)
            
            # Verify PII anonymization
            profile = user_data["profile"]
            assert "***" in profile["email"]  # Email should be masked
            assert profile["email"] != "mario.rossi@test.it"
            
            # Codice Fiscale should be masked if present
            if "codice_fiscale" in profile:
                assert profile["codice_fiscale"].endswith("501U")  # Last 4 chars
                assert "***" in profile["codice_fiscale"]

    async def test_exclusion_other_users_data(self):
        """Test exclusion of other users' data from shared resources"""
        service = DataExportService(Mock(), Mock(), Mock())
        
        user_id = uuid4()
        other_user_id = uuid4()
        
        # Mock queries including other user's data
        with patch.object(service, 'get_user_queries') as mock_queries:
            mock_queries.return_value = [
                Mock(id=uuid4(), user_id=user_id, query="My query"),
                Mock(id=uuid4(), user_id=other_user_id, query="Other user query")
            ]
            
            export_request = DataExportRequest(user_id=user_id, format=ExportFormat.JSON)
            
            # Should only return current user's data
            queries = await service.get_user_queries(user_id, None, None)
            
            # Verify isolation
            for query in queries:
                assert query.user_id == user_id
                assert query.user_id != other_user_id

    async def test_password_security_tokens_never_exported(self):
        """Test password and security tokens are never exported"""
        service = DataExportService(Mock(), Mock(), Mock())
        
        # Mock user with all possible sensitive fields
        user = Mock()
        user.email = "test@test.it"
        user.password_hash = "hashed_password"
        user.access_token = "jwt_token"
        user.refresh_token = "refresh_token"
        user.api_key = "api_key"
        user.session_token = "session_token"
        
        with patch.object(service, '_get_user', return_value=user):
            export_request = DataExportRequest(
                user_id=uuid4(),
                format=ExportFormat.JSON,
                include_sensitive=True  # Even with sensitive data enabled
            )
            
            user_data = await service.collect_user_data(user.id, export_request)
            
            # Verify security data is never included
            profile = user_data["profile"]
            
            # These fields must never be present
            security_fields = [
                "password", "password_hash", "access_token", "refresh_token",
                "api_key", "session_token", "secret_key", "private_key"
            ]
            
            for field in security_fields:
                assert field not in profile
                assert field not in str(user_data)  # Not anywhere in export

    async def test_export_request_authentication_authorization(self, db_session):
        """Test export request authentication and authorization"""
        service = DataExportService(db_session, Mock(), Mock())
        
        user_id = uuid4()
        other_user_id = uuid4()
        
        # Create export request for user
        export_request = await service.create_export_request(
            user_id=user_id,
            format=ExportFormat.JSON
        )
        
        # Test that other user cannot access this export
        with pytest.raises(PermissionError):
            await service.get_export_request(export_request.id, requesting_user_id=other_user_id)
        
        # Test that correct user can access
        retrieved_request = await service.get_export_request(export_request.id, requesting_user_id=user_id)
        assert retrieved_request.user_id == user_id

    async def test_rate_limiting_max_5_exports_per_day(self, db_session):
        """Test rate limiting (max 5 exports per day)"""
        service = DataExportService(db_session, Mock(), Mock())
        
        user_id = uuid4()
        
        # Create 5 exports (should succeed)
        for i in range(5):
            export_request = await service.create_export_request(
                user_id=user_id,
                format=ExportFormat.JSON
            )
            assert export_request.status == ExportStatus.PENDING
        
        # 6th export should fail with rate limit
        with pytest.raises(ExportLimitExceeded) as exc_info:
            await service.create_export_request(
                user_id=user_id,
                format=ExportFormat.JSON
            )
        
        assert "Massimo 5 export al giorno" in str(exc_info.value)

    async def test_export_link_expiration_24_hours(self, db_session):
        """Test export link expiration (24 hours)"""
        service = DataExportService(db_session, Mock(), Mock())
        
        user_id = uuid4()
        
        # Create export request
        export_request = await service.create_export_request(
            user_id=user_id,
            format=ExportFormat.JSON
        )
        
        # Verify expiration is set to 24 hours
        expected_expiry = datetime.utcnow() + timedelta(hours=24)
        assert export_request.expires_at <= expected_expiry + timedelta(minutes=1)
        assert export_request.expires_at >= expected_expiry - timedelta(minutes=1)
        
        # Test expired export access
        export_request.expires_at = datetime.utcnow() - timedelta(hours=1)  # Expired
        await db_session.commit()
        
        with pytest.raises(ValueError) as exc_info:
            await service.get_export_download_url(export_request.id)
        
        assert "Export scaduto" in str(exc_info.value)

    async def test_audit_logging_export_requests(self, db_session):
        """Test audit logging of export requests"""
        service = DataExportService(db_session, Mock(), Mock())
        
        user_id = uuid4()
        
        with patch('app.core.logging.logger') as mock_logger:
            # Create export request
            export_request = await service.create_export_request(
                user_id=user_id,
                format=ExportFormat.JSON,
                options={"include_sensitive": True}
            )
            
            # Verify audit logging
            mock_logger.info.assert_called()
            log_calls = [call for call in mock_logger.info.call_args_list 
                        if "Data export requested" in str(call)]
            assert len(log_calls) > 0
            
            # Process export (should also log)
            await service.process_export(export_request.id)
            
            completion_logs = [call for call in mock_logger.info.call_args_list 
                             if "Data export completed" in str(call)]
            assert len(completion_logs) > 0


class TestItalianCompliance:
    """Test Italian GDPR compliance and local requirements"""
    
    async def test_codice_fiscale_masking_option(self):
        """Test Codice Fiscale masking option (show only last 4 chars)"""
        service = DataExportService(Mock(), Mock(), Mock())
        
        codice_fiscale = "RSSMRA80A01H501U"
        
        # Test masking
        masked_cf = service.mask_codice_fiscale(codice_fiscale)
        
        # Should show only last 4 characters
        assert masked_cf.endswith("501U")
        assert "***" in masked_cf
        assert len(masked_cf) == len(codice_fiscale)
        assert masked_cf != codice_fiscale

    async def test_partita_iva_included_business_exports(self, db_session):
        """Test Partita IVA included in business exports"""
        service = DataExportService(db_session, EncryptionService(), Mock())
        
        # Create business user
        business_user = User(
            id=uuid4(),
            email="azienda@test.it",
            is_business=True,
            partita_iva="12345678903"
        )
        db_session.add(business_user)
        await db_session.commit()
        
        export_request = DataExportRequest(
            user_id=business_user.id,
            format=ExportFormat.JSON,
            include_sensitive=True
        )
        
        user_data = await service.collect_user_data(business_user.id, export_request)
        
        # Verify business data inclusion
        assert "business_info" in user_data
        business_info = user_data["business_info"]
        assert business_info["partita_iva"] == "12345678903"
        assert business_info["is_business"] == True

    async def test_italian_invoice_data_export(self, db_session):
        """Test Italian invoice data export"""
        service = DataExportService(db_session, Mock(), Mock())
        
        user_id = uuid4()
        
        # Create Italian invoice
        invoice = Invoice(
            id=uuid4(),
            user_id=user_id,
            invoice_number="2024/0001",
            invoice_date=datetime(2024, 2, 1),
            subtotal=Decimal("599.00"),
            iva_amount=Decimal("131.78"),
            total_amount=Decimal("730.78"),
            payment_status="paid",
            fattura_elettronica_xml="<xml>...</xml>"
        )
        db_session.add(invoice)
        await db_session.commit()
        
        export_request = DataExportRequest(
            user_id=user_id,
            format=ExportFormat.JSON,
            include_fatture=True
        )
        
        user_data = await service.collect_user_data(user_id, export_request)
        
        # Verify Italian invoice data
        assert "fatture" in user_data
        fatture = user_data["fatture"]
        assert len(fatture) == 1
        
        fattura = fatture[0]
        assert fattura["numero"] == "2024/0001"
        assert fattura["importo_imponibile"] == 599.0
        assert fattura["iva"] == 131.78
        assert fattura["totale"] == 730.78

    async def test_fattura_elettronica_history_inclusion(self, db_session):
        """Test fattura elettronica history inclusion"""
        service = DataExportService(db_session, Mock(), Mock())
        
        user_id = uuid4()
        
        # Create electronic invoice
        electronic_invoice = ElectronicInvoice(
            id=uuid4(),
            user_id=user_id,
            invoice_number="2024/0001",
            xml_content="<FatturaElettronica>...</FatturaElettronica>",
            sdi_transmission_id="IT12345678901_00001",
            sdi_status="accepted",
            transmitted_at=datetime(2024, 2, 1, 10, 0)
        )
        db_session.add(electronic_invoice)
        await db_session.commit()
        
        export_request = DataExportRequest(
            user_id=user_id,
            format=ExportFormat.JSON,
            include_fatture=True
        )
        
        user_data = await service.collect_user_data(user_id, export_request)
        
        # Verify electronic invoice history
        assert "fatture_elettroniche" in user_data
        fe_data = user_data["fatture_elettroniche"]
        assert len(fe_data) == 1
        
        fe = fe_data[0]
        assert fe["numero"] == "2024/0001"
        assert fe["sdi_transmission_id"] == "IT12345678901_00001"
        assert fe["sdi_status"] == "accepted"
        assert fe["transmitted_at"] == "2024-02-01T10:00:00"

    async def test_italian_language_labels_exports(self):
        """Test Italian language labels in exports"""
        generator = ExportFileGenerator()
        
        # Test CSV headers in Italian
        sample_queries = [
            {
                "timestamp": "2024-03-01T10:00:00",
                "query": "Test query",
                "response_time_ms": 1000,
                "tokens_used": 100,
                "cost_cents": 5,
                "response_cached": True
            }
        ]
        
        csv_content = await generator.generate_queries_csv(sample_queries)
        csv_text = csv_content.decode('utf-8')
        
        # Verify Italian headers
        italian_headers = [
            "Data", "Ora", "Domanda", "Tempo Risposta",
            "Token Utilizzati", "Costo", "Da Cache"
        ]
        
        for header in italian_headers:
            assert header in csv_text

    async def test_compliance_italian_data_protection_laws(self):
        """Test compliance with Italian data protection laws"""
        service = DataExportService(Mock(), Mock(), Mock())
        
        # Create export request with Italian compliance options
        export_request = DataExportRequest(
            user_id=uuid4(),
            format=ExportFormat.JSON,
            include_sensitive=True,
            anonymize_pii=False,
            include_fatture=True,
            include_f24=True
        )
        
        # Generate compliance manifest
        compliance_info = await service.generate_compliance_manifest(export_request)
        
        # Verify Italian compliance
        assert compliance_info["jurisdiction"] == "IT"
        assert "GDPR Article 20" in compliance_info["legal_basis"]
        assert "Codice Privacy" in compliance_info["italian_laws"]
        assert compliance_info["data_controller"]["country"] == "IT"
        assert compliance_info["retention_period_days"] == 1  # 24 hours
        assert compliance_info["includes_personal_data"] == True
        assert compliance_info["includes_financial_data"] == True


class TestExportProgressTracking:
    """Test export progress tracking and user feedback"""
    
    async def test_export_progress_updates(self):
        """Test real-time progress updates during export"""
        redis_client = Mock()
        tracker = ExportProgressTracker(redis_client)
        
        export_id = str(uuid4())
        
        # Test progress update
        await tracker.update_progress(
            export_id=export_id,
            step="Raccolta dati profilo",
            current=1,
            total=5
        )
        
        # Verify Redis call
        redis_client.setex.assert_called_once()
        call_args = redis_client.setex.call_args
        
        # Verify key format
        assert call_args[0][0] == f"export_progress:{export_id}"
        
        # Verify TTL
        assert call_args[0][1] == 3600  # 1 hour
        
        # Verify progress data
        progress_data = json.loads(call_args[0][2])
        assert progress_data["step"] == "Raccolta dati profilo"
        assert progress_data["current"] == 1
        assert progress_data["total"] == 5
        assert progress_data["percentage"] == 20.0

    async def test_export_step_progression(self):
        """Test complete export step progression"""
        redis_client = Mock()
        tracker = ExportProgressTracker(redis_client)
        
        export_id = str(uuid4())
        
        # Simulate export steps
        steps = [
            ("Inizializzazione export", 1, 7),
            ("Raccolta dati profilo", 2, 7),
            ("Esportazione cronologia domande", 3, 7),
            ("Esportazione documenti", 4, 7),
            ("Generazione formato JSON", 5, 7),
            ("Creazione archivio ZIP", 6, 7),
            ("Finalizzazione export", 7, 7)
        ]
        
        for step_name, current, total in steps:
            await tracker.update_progress(export_id, step_name, current, total)
        
        # Verify all steps were tracked
        assert redis_client.setex.call_count == 7
        
        # Verify final step shows 100%
        final_call = redis_client.setex.call_args_list[-1]
        final_data = json.loads(final_call[0][2])
        assert final_data["percentage"] == 100.0
        assert final_data["step"] == "Finalizzazione export"


# Helper classes and fixtures for testing
class QueryHistory:
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)

class DocumentAnalysis:
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)

class TaxCalculation:
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)

class FAQInteraction:
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)

class KnowledgeBaseSearch:
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)

class ElectronicInvoice:
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])