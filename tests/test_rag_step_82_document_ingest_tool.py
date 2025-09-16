"""
Test suite for RAG STEP 82 - DocumentIngestTool.process Process attachments.

This module tests the document ingest tool that processes file attachments
and integrates with the document processing pipeline.

Based on Mermaid diagram: DocIngest (DocumentIngestTool.process Process attachments)
"""

from unittest.mock import patch, AsyncMock, MagicMock

import pytest

from app.core.langgraph.tools.document_ingest_tool import DocumentIngestTool, DocumentIngestInput


class TestDocumentIngestTool:
    """Test document ingest tool functionality with structured logging."""
    
    @pytest.fixture
    def document_ingest_tool(self):
        """Create DocumentIngestTool instance for testing."""
        return DocumentIngestTool()
    
    @pytest.fixture
    def sample_pdf_attachment(self):
        """Create a sample PDF attachment for testing."""
        return {
            "filename": "test_document.pdf",
            "content_type": "application/pdf",
            "size": 1024000,  # 1MB
            "content": b"sample pdf content",
            "attachment_id": "attach_123"
        }
    
    @pytest.fixture
    def sample_excel_attachment(self):
        """Create a sample Excel attachment for testing."""
        return {
            "filename": "test_spreadsheet.xlsx",
            "content_type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "size": 512000,  # 512KB
            "content": b"sample excel content",
            "attachment_id": "attach_456"
        }
    
    def test_document_ingest_input_validation(self):
        """Test DocumentIngestInput validation."""
        # Valid input
        valid_input = DocumentIngestInput(
            attachments=[
                {
                    "filename": "test.pdf",
                    "content_type": "application/pdf",
                    "size": 1000000,
                    "content": b"sample content",
                    "attachment_id": "attach_123"
                }
            ],
            user_id="user_123",
            session_id="session_456"
        )
        assert valid_input.attachments[0]["filename"] == "test.pdf"
        assert valid_input.user_id == "user_123"
        assert valid_input.session_id == "session_456"
    
    def test_document_ingest_input_validation_empty_attachments(self):
        """Test DocumentIngestInput handles empty attachments."""
        with pytest.raises(ValueError):
            DocumentIngestInput(
                attachments=[],
                user_id="user_123",
                session_id="session_456"
            )
    
    @pytest.mark.asyncio
    async def test_document_ingest_process_single_pdf(self, document_ingest_tool, sample_pdf_attachment):
        """Test processing a single PDF attachment."""
        with patch('app.core.langgraph.tools.document_ingest_tool.rag_step_log') as mock_log, \
             patch('app.core.langgraph.tools.document_ingest_tool.rag_step_timer') as mock_timer, \
             patch('app.core.langgraph.tools.document_ingest_tool.DocumentProcessor') as mock_processor:
            
            # Setup timer context manager mock
            timer_context = MagicMock()
            mock_timer.return_value.__enter__ = MagicMock(return_value=timer_context)
            mock_timer.return_value.__exit__ = MagicMock(return_value=None)
            
            # Setup document processor mock
            processor_instance = AsyncMock()
            processor_instance.extract_text.return_value = {
                "text": "Sample extracted text from PDF",
                "metadata": {"pages": 1, "language": "it"}
            }
            processor_instance.classify_document.return_value = {
                "category": "financial",
                "type": "invoice",
                "confidence": 0.85
            }
            mock_processor.return_value = processor_instance
            
            # Create input
            input_data = DocumentIngestInput(
                attachments=[sample_pdf_attachment],
                user_id="user_123",
                session_id="session_456"
            )
            
            # Process document
            result = await document_ingest_tool._arun(
                attachments=input_data.attachments,
                user_id=input_data.user_id,
                session_id=input_data.session_id
            )
            
            # Verify timer was called
            mock_timer.assert_called_once()
            timer_call = mock_timer.call_args
            assert timer_call[0][0] == 82  # step
            assert timer_call[0][1] == "RAG.preflight.documentingesttool.process.process.attachments"  # step_id
            assert timer_call[0][2] == "DocIngest"  # node_label
            
            # Verify structured logging occurred
            mock_log.assert_called()
            log_calls = mock_log.call_args_list
            
            # Check initial processing log
            start_log = log_calls[0]
            assert start_log[0][0] == 82  # step
            assert start_log[0][1] == "RAG.preflight.documentingesttool.process.process.attachments"  # step_id
            assert start_log[0][2] == "DocIngest"  # node_label
            assert start_log[1]['user_id'] == "user_123"
            assert start_log[1]['session_id'] == "session_456"
            assert start_log[1]['attachment_count'] == 1
            
            # Verify document processor was called
            processor_instance.extract_text.assert_called_once()
            processor_instance.classify_document.assert_called_once()
            
            # Verify result structure
            assert "processed_documents" in result
            assert len(result["processed_documents"]) == 1
            assert result["processed_documents"][0]["filename"] == "test_document.pdf"
            assert result["processed_documents"][0]["status"] == "success"
            assert "extracted_text" in result["processed_documents"][0]
            assert "document_classification" in result["processed_documents"][0]
    
    @pytest.mark.asyncio
    async def test_document_ingest_process_multiple_attachments(self, document_ingest_tool, sample_pdf_attachment, sample_excel_attachment):
        """Test processing multiple attachments."""
        with patch('app.core.langgraph.tools.document_ingest_tool.rag_step_log') as mock_log, \
             patch('app.core.langgraph.tools.document_ingest_tool.rag_step_timer') as mock_timer, \
             patch('app.core.langgraph.tools.document_ingest_tool.DocumentProcessor') as mock_processor:
            
            # Setup timer context manager mock
            timer_context = MagicMock()
            mock_timer.return_value.__enter__ = MagicMock(return_value=timer_context)
            mock_timer.return_value.__exit__ = MagicMock(return_value=None)
            
            # Setup document processor mock
            processor_instance = AsyncMock()
            processor_instance.extract_text.return_value = {
                "text": "Sample extracted text",
                "metadata": {"language": "it"}
            }
            processor_instance.classify_document.return_value = {
                "category": "financial",
                "type": "generic",
                "confidence": 0.75
            }
            mock_processor.return_value = processor_instance
            
            # Create input with multiple attachments
            input_data = DocumentIngestInput(
                attachments=[sample_pdf_attachment, sample_excel_attachment],
                user_id="user_123",
                session_id="session_456"
            )
            
            # Process documents
            result = await document_ingest_tool._arun(
                attachments=input_data.attachments,
                user_id=input_data.user_id,
                session_id=input_data.session_id
            )
            
            # Verify logging shows correct attachment count
            mock_log.assert_called()
            start_log = mock_log.call_args_list[0]
            assert start_log[1]['attachment_count'] == 2
            
            # Verify both documents were processed
            assert len(result["processed_documents"]) == 2
            assert result["processed_documents"][0]["filename"] == "test_document.pdf"
            assert result["processed_documents"][1]["filename"] == "test_spreadsheet.xlsx"
            
            # Verify processor was called for each document
            assert processor_instance.extract_text.call_count == 2
            assert processor_instance.classify_document.call_count == 2
    
    @pytest.mark.asyncio
    async def test_document_ingest_process_with_error(self, document_ingest_tool, sample_pdf_attachment):
        """Test document processing with error handling."""
        with patch('app.core.langgraph.tools.document_ingest_tool.rag_step_log') as mock_log, \
             patch('app.core.langgraph.tools.document_ingest_tool.rag_step_timer') as mock_timer, \
             patch('app.core.langgraph.tools.document_ingest_tool.DocumentProcessor') as mock_processor:
            
            # Setup timer context manager mock
            timer_context = MagicMock()
            mock_timer.return_value.__enter__ = MagicMock(return_value=timer_context)
            mock_timer.return_value.__exit__ = MagicMock(return_value=None)
            
            # Setup document processor to raise error
            processor_instance = AsyncMock()
            processor_instance.extract_text.side_effect = Exception("Processing failed")
            mock_processor.return_value = processor_instance
            
            # Create input
            input_data = DocumentIngestInput(
                attachments=[sample_pdf_attachment],
                user_id="user_123",
                session_id="session_456"
            )
            
            # Process document
            result = await document_ingest_tool._arun(
                attachments=input_data.attachments,
                user_id=input_data.user_id,
                session_id=input_data.session_id
            )
            
            # Verify error was logged
            mock_log.assert_called()
            error_logs = [call for call in mock_log.call_args_list if call[1].get('error')]
            assert len(error_logs) > 0
            assert "Processing failed" in error_logs[0][1]['error']
            
            # Verify result shows error status
            assert len(result["processed_documents"]) == 1
            assert result["processed_documents"][0]["status"] == "error"
            assert "error" in result["processed_documents"][0]
    
    @pytest.mark.asyncio
    async def test_document_ingest_file_size_limit(self, document_ingest_tool):
        """Test document processing with file size limit validation."""
        # Create oversized attachment
        large_attachment = {
            "filename": "large_document.pdf",
            "content_type": "application/pdf",
            "size": 50 * 1024 * 1024,  # 50MB - typically too large
            "content": b"large content",
            "attachment_id": "attach_large"
        }
        
        with patch('app.core.langgraph.tools.document_ingest_tool.rag_step_log') as mock_log:
            # Create input
            input_data = DocumentIngestInput(
                attachments=[large_attachment],
                user_id="user_123",
                session_id="session_456"
            )
            
            # Process document
            result = await document_ingest_tool._arun(
                attachments=input_data.attachments,
                user_id=input_data.user_id,
                session_id=input_data.session_id
            )
            
            # Verify size limit error was logged
            mock_log.assert_called()
            error_logs = [call for call in mock_log.call_args_list if call[1].get('error')]
            assert len(error_logs) > 0
            assert "file size" in error_logs[0][1]['error'].lower()
            
            # Verify result shows error status
            assert result["processed_documents"][0]["status"] == "error"
    
    @pytest.mark.asyncio
    async def test_document_ingest_unsupported_file_type(self, document_ingest_tool):
        """Test document processing with unsupported file type."""
        # Create unsupported file attachment
        unsupported_attachment = {
            "filename": "test_file.xyz",
            "content_type": "application/octet-stream",
            "size": 1000,
            "content": b"unsupported content",
            "attachment_id": "attach_unsupported"
        }
        
        with patch('app.core.langgraph.tools.document_ingest_tool.rag_step_log') as mock_log:
            # Create input
            input_data = DocumentIngestInput(
                attachments=[unsupported_attachment],
                user_id="user_123",
                session_id="session_456"
            )
            
            # Process document
            result = await document_ingest_tool._arun(
                attachments=input_data.attachments,
                user_id=input_data.user_id,
                session_id=input_data.session_id
            )
            
            # Verify unsupported file type error was logged
            mock_log.assert_called()
            error_logs = [call for call in mock_log.call_args_list if call[1].get('error')]
            assert len(error_logs) > 0
            assert "unsupported" in error_logs[0][1]['error'].lower()
            
            # Verify result shows error status
            assert result["processed_documents"][0]["status"] == "error"


class TestDocumentIngestToolIntegration:
    """Test document ingest tool integration scenarios."""
    
    @pytest.fixture
    def document_ingest_tool(self):
        """Create DocumentIngestTool instance for testing."""
        return DocumentIngestTool()
    
    @pytest.mark.asyncio
    async def test_document_ingest_tool_as_langchain_tool(self, document_ingest_tool):
        """Test DocumentIngestTool works as a LangChain tool."""
        # Test that the tool can be called via ainvoke (LangChain interface)
        test_input = {
            "attachments": [{
                "filename": "test.pdf",
                "content_type": "application/pdf",
                "size": 1000,
                "content": b"test content",
                "attachment_id": "test_123"
            }],
            "user_id": "user_123",
            "session_id": "session_456"
        }
        
        with patch('app.observability.rag_logging.rag_step_log'), \
             patch('app.core.langgraph.tools.document_ingest_tool.rag_step_timer') as mock_timer, \
             patch('app.core.langgraph.tools.document_ingest_tool.DocumentProcessor') as mock_processor:
            
            # Setup timer context manager mock
            timer_context = MagicMock()
            mock_timer.return_value.__enter__ = MagicMock(return_value=timer_context)
            mock_timer.return_value.__exit__ = MagicMock(return_value=None)
            
            # Setup document processor mock
            processor_instance = AsyncMock()
            processor_instance.extract_text.return_value = {"text": "Sample text"}
            processor_instance.classify_document.return_value = {"category": "financial"}
            mock_processor.return_value = processor_instance
            
            # Call via LangChain interface
            result = await document_ingest_tool.ainvoke(test_input)
            
            # Verify result is valid
            assert isinstance(result, str)  # LangChain tools should return strings
            assert "processed_documents" in result  # Should contain processing results
    
    @pytest.mark.asyncio
    async def test_document_ingest_performance_timing(self, document_ingest_tool):
        """Test document ingest tool performance timing."""
        with patch('app.core.langgraph.tools.document_ingest_tool.rag_step_timer') as mock_timer, \
             patch('app.core.langgraph.tools.document_ingest_tool.DocumentProcessor') as mock_processor:
            
            # Setup timer context manager mock
            timer_context = MagicMock()
            mock_timer.return_value.__enter__ = MagicMock(return_value=timer_context)
            mock_timer.return_value.__exit__ = MagicMock(return_value=None)
            
            # Setup document processor mock
            processor_instance = AsyncMock()
            processor_instance.extract_text.return_value = {"text": "Sample text"}
            processor_instance.classify_document.return_value = {"category": "financial"}
            mock_processor.return_value = processor_instance
            
            # Test timing with attachments
            test_input = DocumentIngestInput(
                attachments=[{
                    "filename": "timing_test.pdf",
                    "content_type": "application/pdf",
                    "size": 2000,
                    "content": b"timing test content",
                    "attachment_id": "timing_123"
                }],
                user_id="user_123",
                session_id="session_456"
            )
            
            # Execute with timer
            await document_ingest_tool._arun(
                attachments=test_input.attachments,
                user_id=test_input.user_id,
                session_id=test_input.session_id
            )
            
            # Verify timer was used with correct parameters
            mock_timer.assert_called_once()
            timer_call = mock_timer.call_args
            
            # Check positional args
            assert timer_call[0][0] == 82  # step
            assert timer_call[0][1] == "RAG.preflight.documentingesttool.process.process.attachments"  # step_id
            assert timer_call[0][2] == "DocIngest"  # node_label
            
            # Check kwargs contain timing info
            assert 'user_id' in timer_call[1]
            assert 'session_id' in timer_call[1]
            assert 'attachment_count' in timer_call[1]


# Integration test scenarios
@pytest.mark.asyncio
async def test_document_ingest_tool_full_flow():
    """Test complete document ingest tool flow with realistic data."""
    tool = DocumentIngestTool()
    
    # Realistic test case with Italian financial document
    attachments = [{
        "filename": "fattura_2024.pdf",
        "content_type": "application/pdf",
        "size": 125000,  # 125KB
        "content": b"sample italian invoice content",
        "attachment_id": "invoice_2024_001"
    }]
    
    with patch('app.core.langgraph.tools.document_ingest_tool.rag_step_log') as mock_log, \
         patch('app.core.langgraph.tools.document_ingest_tool.rag_step_timer') as mock_timer, \
         patch('app.core.langgraph.tools.document_ingest_tool.DocumentProcessor') as mock_processor:
        
        # Setup timer context manager mock
        timer_context = MagicMock()
        mock_timer.return_value.__enter__ = MagicMock(return_value=timer_context)
        mock_timer.return_value.__exit__ = MagicMock(return_value=None)
        
        # Setup realistic processor response
        processor_instance = AsyncMock()
        processor_instance.extract_text.return_value = {
            "text": "FATTURA N. 2024/001\nImporto: €1.250,00\nIVA: €275,00",
            "metadata": {"pages": 1, "language": "it", "encoding": "utf-8"}
        }
        processor_instance.classify_document.return_value = {
            "category": "financial",
            "type": "invoice",
            "confidence": 0.92,
            "subcategory": "sales_invoice"
        }
        mock_processor.return_value = processor_instance
        
        # Execute full flow
        result = await tool._arun(
            attachments=attachments,
            user_id="user_italian_business_001",
            session_id="session_invoice_processing_2024"
        )
        
        # Verify comprehensive logging
        assert mock_log.call_count >= 2  # Start log + completion/error logs
        
        # Verify processing results
        assert len(result["processed_documents"]) == 1
        processed_doc = result["processed_documents"][0]
        
        assert processed_doc["filename"] == "fattura_2024.pdf"
        assert processed_doc["status"] == "success"
        assert "FATTURA" in processed_doc["extracted_text"]["text"]
        assert processed_doc["document_classification"]["type"] == "invoice"
        assert processed_doc["document_classification"]["confidence"] > 0.9
        
        # Verify performance metrics were captured
        mock_timer.assert_called_once()
        timer_kwargs = mock_timer.call_args[1]
        assert timer_kwargs['user_id'] == "user_italian_business_001"
        assert timer_kwargs['attachment_count'] == 1