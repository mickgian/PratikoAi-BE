"""Document Upload Service for TDD-based Document Processing System.

Handles file validation, security checks, and virus scanning for Italian
tax document uploads with comprehensive error handling and GDPR compliance.
"""

import hashlib
import math
import mimetypes
import os
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, BinaryIO, Dict, List, Optional

import magic
from fastapi import HTTPException, UploadFile
from fastapi.security.utils import get_authorization_scheme_param

from app.core.config import get_settings
from app.models.document_simple import DOCUMENT_CONFIG, DocumentType


class UploadValidationError(HTTPException):
    """Exception raised when document upload validation fails"""

    def __init__(self, detail: str, status_code: int = 400):
        super().__init__(status_code=status_code, detail=detail)


class DocumentUploader:
    """Service for handling secure document uploads with Italian tax document support"""

    def __init__(self):
        self.settings = get_settings()
        self.max_file_size = DOCUMENT_CONFIG["MAX_FILE_SIZE_MB"] * 1024 * 1024
        self.supported_mime_types = DOCUMENT_CONFIG["SUPPORTED_MIME_TYPES"]
        self.max_files_per_upload = DOCUMENT_CONFIG["MAX_FILES_PER_UPLOAD"]

    async def validate_file(self, upload_file: UploadFile) -> dict[str, Any]:
        """Comprehensive file validation including security checks.

        Args:
          upload_file: FastAPI UploadFile object

        Returns:
          Dictionary with validation results

        Raises:
          UploadValidationError: If validation fails
        """
        # Read file content for validation
        content = await upload_file.read()
        await upload_file.seek(0)  # Reset file pointer

        # File size validation
        file_size = len(content)
        if file_size > self.max_file_size:
            raise UploadValidationError(
                f"File too large. Maximum size is {DOCUMENT_CONFIG['MAX_FILE_SIZE_MB']}MB, "
                f"received {file_size / (1024 * 1024):.2f}MB"
            )

        if file_size == 0:
            raise UploadValidationError("File is empty")

        # MIME type validation
        detected_mime = self._detect_mime_type(content, upload_file.filename)
        if detected_mime not in self.supported_mime_types:
            raise UploadValidationError(
                f"Unsupported file type '{detected_mime}'. "
                f"Supported types: {', '.join(self.supported_mime_types.keys())}"
            )

        # File type determination
        file_type = self.supported_mime_types[detected_mime]

        # Filename sanitization and validation
        safe_filename = self._sanitize_filename(upload_file.filename or "unnamed_file")
        original_filename = upload_file.filename or "unnamed_file"

        # File signature validation
        self._validate_file_signature(content, file_type)

        # Security scanning
        virus_scan_result = await self._scan_for_viruses(content)
        if not virus_scan_result["clean"]:
            raise UploadValidationError(f"Security threat detected: {', '.join(virus_scan_result['threats'])}")

        # Generate file hash for duplicate detection
        file_hash = hashlib.sha256(content).hexdigest()

        # Encoding detection for text files
        encoding_info = {}
        if file_type == DocumentType.CSV:
            encoding_info = await self._detect_text_encoding(content)

        return {
            "is_valid": True,
            "file_type": file_type,
            "mime_type": detected_mime,
            "file_size": file_size,
            "file_hash": file_hash,
            "original_filename": original_filename,
            "safe_filename": safe_filename,
            "security_threats": virus_scan_result["threats"],
            "virus_scan": virus_scan_result,
            **encoding_info,
        }

    def _detect_mime_type(self, content: bytes, filename: str) -> str:
        """Detect MIME type from file content and filename.

        Args:
          content: File content bytes
          filename: Original filename

        Returns:
          Detected MIME type string
        """
        # Primary detection using python-magic (libmagic)
        try:
            mime = magic.from_buffer(content, mime=True)
            if mime and mime in self.supported_mime_types:
                return mime
        except Exception:
            pass

        # Fallback to mimetypes based on filename
        mime_from_filename, _ = mimetypes.guess_type(filename)
        if mime_from_filename and mime_from_filename in self.supported_mime_types:
            return mime_from_filename

        # Content-based detection fallbacks
        if content.startswith(b"%PDF"):
            return "application/pdf"
        elif content.startswith(b"PK\x03\x04") and filename.endswith((".xlsx", ".xlsm")):
            return "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        elif content.startswith((b"\xd0\xcf\x11\xe0", b"\x09\x08")) and filename.endswith(".xls"):
            return "application/vnd.ms-excel"
        elif filename.endswith(".csv"):
            return "text/csv"
        elif content.startswith((b"<?xml", b"<xml")) and filename.endswith(".xml"):
            return "application/xml"

        return "application/octet-stream"

    def _sanitize_filename(self, filename: str) -> str:
        """Sanitize filename to prevent security issues.

        Args:
          filename: Original filename

        Returns:
          Sanitized safe filename
        """
        if not filename:
            return "unnamed_file"

        # Remove path separators and dangerous characters
        filename = os.path.basename(filename)
        filename = re.sub(r"[^\w\s\-_.]", "", filename)
        filename = re.sub(r"\.{2,}", ".", filename)  # Multiple dots
        filename = filename.strip(". ")

        # Handle Windows reserved names
        reserved_names = {
            "CON",
            "PRN",
            "AUX",
            "NUL",
            "COM1",
            "COM2",
            "COM3",
            "COM4",
            "COM5",
            "COM6",
            "COM7",
            "COM8",
            "COM9",
            "LPT1",
            "LPT2",
            "LPT3",
            "LPT4",
            "LPT5",
            "LPT6",
            "LPT7",
            "LPT8",
            "LPT9",
        }
        name_part = Path(filename).stem.upper()
        if name_part in reserved_names:
            filename = f"doc_{filename}"

        # Limit length
        if len(filename) > 255:
            name = Path(filename).stem[:240]
            ext = Path(filename).suffix[:15]
            filename = f"{name}{ext}"

        return filename or "unnamed_file"

    def _validate_file_signature(self, content: bytes, file_type: DocumentType) -> None:
        """Validate file content matches expected file type signatures.

        Args:
          content: File content bytes
          file_type: Expected document type

        Raises:
          UploadValidationError: If signature doesn't match
        """
        signatures = {
            DocumentType.PDF: [b"%PDF"],
            DocumentType.EXCEL_XLSX: [b"PK\x03\x04"],  # ZIP-based format
            DocumentType.EXCEL_XLS: [b"\xd0\xcf\x11\xe0", b"\x09\x08"],  # OLE2 format
            DocumentType.CSV: [],  # Text format, no specific signature
            DocumentType.XML: [b"<?xml", b"<xml", b"\xef\xbb\xbf<?xml"],  # XML with optional BOM
        }

        expected_signatures = signatures.get(file_type, [])
        if not expected_signatures:
            return  # No signature validation needed

        # Check if content starts with any expected signature
        for signature in expected_signatures:
            if content.startswith(signature):
                return

        raise UploadValidationError(f"File content doesn't match expected format for {file_type.value}")

    async def _scan_for_viruses(self, content: bytes) -> dict[str, Any]:
        """Comprehensive virus and malware scanning with multiple detection methods.

        Args:
          content: File content bytes

        Returns:
          Dictionary with scan results
        """
        scan_start = datetime.utcnow()
        threats = []
        scan_methods = []

        # 1. Signature-based scanning
        signature_threats = self._signature_based_scan(content)
        threats.extend(signature_threats)
        if signature_threats:
            scan_methods.append("signature_detection")

        # 2. Heuristic analysis
        heuristic_threats = self._heuristic_analysis(content)
        threats.extend(heuristic_threats)
        if heuristic_threats:
            scan_methods.append("heuristic_analysis")

        # 3. Document-specific security checks
        document_threats = self._document_security_scan(content)
        threats.extend(document_threats)
        if document_threats:
            scan_methods.append("document_security")

        # 4. Content structure validation
        structure_threats = self._validate_content_structure(content)
        threats.extend(structure_threats)
        if structure_threats:
            scan_methods.append("structure_validation")

        # 5. External antivirus integration (if configured)
        external_threats = await self._external_antivirus_scan(content)
        threats.extend(external_threats)
        if external_threats:
            scan_methods.append("external_antivirus")

        scan_duration = (datetime.utcnow() - scan_start).total_seconds()

        return {
            "clean": len(threats) == 0,
            "threats": list(set(threats)),  # Remove duplicates
            "scan_time": scan_start.isoformat(),
            "scan_duration_seconds": round(scan_duration, 3),
            "scanner": "enhanced_security_scanner_v2",
            "methods_used": scan_methods,
            "threat_count": len(set(threats)),
        }

    def _signature_based_scan(self, content: bytes) -> list[str]:
        """Signature-based malware detection"""
        threats = []

        # Executable file signatures
        executable_signatures = [
            (b"MZ\x90\x00", "Windows PE executable"),
            (b"\x7fELF", "Linux ELF executable"),
            (b"\xca\xfe\xba\xbe", "Mach-O executable"),
            (b"\xfe\xed\xfa\xce", "Mach-O executable (32-bit)"),
            (b"#!/bin/", "Shell script"),
            (b"#!/usr/bin/", "Shell script"),
            (b"@echo off", "Batch script"),
            (b"PowerShell", "PowerShell script"),
        ]

        for signature, description in executable_signatures:
            if signature in content[:1024]:  # Check first 1KB
                threats.append(f"Executable content: {description}")

        # Malicious script patterns
        script_patterns = [
            (b"<script", "HTML script tag"),
            (b"javascript:", "JavaScript protocol"),
            (b"vbscript:", "VBScript protocol"),
            (b"data:text/html", "HTML data URI"),
            (b"eval(", "Code evaluation"),
            (b"document.write", "DOM manipulation"),
            (b"ActiveXObject", "ActiveX object"),
            (b"Shell.Application", "Shell execution"),
            (b"WScript.Shell", "Windows Script Host"),
        ]

        content_lower = content.lower()
        for pattern, description in script_patterns:
            if pattern.lower() in content_lower:
                threats.append(f"Script content: {description}")

        return threats

    def _heuristic_analysis(self, content: bytes) -> list[str]:
        """Heuristic malware detection based on suspicious patterns"""
        threats = []

        # High entropy check (possible encryption/obfuscation)
        if len(content) > 1000:
            entropy = self._calculate_entropy(content[:1000])
            if entropy > self.settings.MAX_DOCUMENT_ENTROPY:
                threats.append(
                    f"High entropy content: {entropy:.2f} (threshold: {self.settings.MAX_DOCUMENT_ENTROPY})"
                )

        # Suspicious string patterns
        suspicious_patterns = [
            b"CreateProcess",
            b"RegCreateKey",
            b"WriteProcessMemory",
            b"VirtualAlloc",
            b"LoadLibrary",
            b"GetProcAddress",
            b"ShellExecute",
            b"WinExec",
            b"URLDownloadToFile",
            b"InternetOpenUrl",
        ]

        suspicious_count = 0
        for pattern in suspicious_patterns:
            if pattern in content:
                suspicious_count += 1

        if suspicious_count >= 3:
            threats.append(f"Multiple suspicious API calls detected ({suspicious_count})")

        return threats

    def _document_security_scan(self, content: bytes) -> list[str]:
        """Document-specific security scanning"""
        threats = []

        # PDF-specific checks
        if content.startswith(b"%PDF"):
            # Check for JavaScript in PDF
            if (b"/JS" in content or b"/JavaScript" in content) and not self.settings.ALLOW_JAVASCRIPT_IN_PDF:
                threats.append("PDF contains JavaScript (blocked by policy)")

            # Check for embedded files
            if b"/EmbeddedFile" in content:
                threats.append("PDF contains embedded files")

            # Check for forms that can execute actions
            if b"/Launch" in content:
                threats.append("PDF contains launch actions")

            # Check for suspicious form fields
            if b"/AcroForm" in content and b"/XFA" in content:
                threats.append("PDF contains XFA forms (potential security risk)")

        # Office document checks (Excel, Word)
        elif content.startswith(b"PK\x03\x04"):  # ZIP-based Office files
            # Check for macros
            if (
                b"vbaProject" in content or b"macros" in content.lower()
            ) and not self.settings.ALLOW_MACROS_IN_DOCUMENTS:
                threats.append("Office document contains macros (blocked by policy)")

            # Check for external references
            if b"http://" in content or b"https://" in content:
                external_refs = content.count(b"http://") + content.count(b"https://")
                if external_refs > self.settings.MAX_EXTERNAL_REFERENCES:
                    threats.append(
                        f"Document contains too many external references ({external_refs}, max: {self.settings.MAX_EXTERNAL_REFERENCES})"
                    )

            # Check for OLE objects that could contain malicious content
            if b"oleObject" in content.lower():
                threats.append("Document contains OLE objects")

        # XML-specific checks (including XML-based Office documents)
        if b"<?xml" in content[:100] or content.startswith(b"PK\x03\x04"):
            # Check for XXE (XML External Entity) attacks
            if b"<!ENTITY" in content and b"SYSTEM" in content:
                threats.append("XML contains external entity references (XXE risk)")

            # Check for suspicious DTD declarations
            if b"<!DOCTYPE" in content:
                try:
                    dtd_content = content.split(b"<!DOCTYPE")[1].split(b">")[0]
                    if len(dtd_content) > 1000:
                        threats.append("XML contains complex DTD declaration")
                except (IndexError, AttributeError):
                    pass

            # Check for XSLT processing instructions
            if b"<?xml-stylesheet" in content:
                threats.append("XML contains stylesheet processing instruction")

        return threats

    def _validate_content_structure(self, content: bytes) -> list[str]:
        """Validate document structure integrity"""
        threats = []

        # Check for zip bombs (highly compressed content)
        if content.startswith(b"PK\x03\x04"):  # ZIP file
            try:
                # Simple check for compression ratio
                if len(content) < 1000 and b"compressed" in content:
                    # This is a simplified check - real implementation would safely decompress
                    threats.append("Potentially compressed bomb detected")
            except Exception:
                pass

        # Check for extremely large embedded content
        if len(content) > 50 * 1024 * 1024:  # 50MB
            # Look for patterns that suggest inflated content
            if content.count(b"\x00") > len(content) * 0.8:
                threats.append("Document contains excessive null bytes")

        # Check for truncated files
        # PDF spec allows trailing whitespace/newlines after %%EOF, so check last 1024 bytes
        if content.startswith(b"%PDF"):
            tail = content[-1024:] if len(content) > 1024 else content
            if b"%%EOF" not in tail:
                threats.append("PDF file appears truncated or malformed")

        return threats

    async def _external_antivirus_scan(self, content: bytes) -> list[str]:
        """Integration with external antivirus services"""
        threats = []

        # Check if external scanning is enabled
        if not self.settings.ENABLE_EXTERNAL_AV_SCAN:
            return threats

        # Skip if file is too large for external scanning
        if len(content) > self.settings.VIRUS_SCAN_MAX_FILE_SIZE_MB * 1024 * 1024:
            return threats

        # ClamAV integration
        if self.settings.CLAMAV_HOST and self.settings.CLAMAV_PORT:
            try:
                clamav_result = await self._scan_with_clamav(content)
                if clamav_result.get("infected"):
                    threats.append(f"ClamAV: {clamav_result['virus_name']}")
            except Exception as e:
                # Log but don't fail upload
                print(f"ClamAV scan failed: {e}")

        # VirusTotal integration
        if self.settings.VIRUSTOTAL_API_KEY:
            try:
                vt_result = await self._scan_with_virustotal(content)
                if vt_result.get("positives", 0) > 0:
                    threats.append(
                        f"VirusTotal: {vt_result['positives']}/{vt_result['total']} engines detected threats"
                    )
            except Exception as e:
                # Log but don't fail upload
                print(f"VirusTotal scan failed: {e}")

        return threats

    async def _scan_with_clamav(self, content: bytes) -> dict[str, Any]:
        """Scan file content with ClamAV daemon"""
        import asyncio
        import socket

        try:
            # Connect to ClamAV daemon
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(self.settings.CLAMAV_HOST, self.settings.CLAMAV_PORT),
                timeout=self.settings.CLAMAV_TIMEOUT,
            )

            # Send INSTREAM command
            writer.write(b"zINSTREAM\0")

            # Send file size and content in chunks
            chunk_size = 4096
            for i in range(0, len(content), chunk_size):
                chunk = content[i : i + chunk_size]
                chunk_len = len(chunk).to_bytes(4, "big")
                writer.write(chunk_len)
                writer.write(chunk)

            # Send zero-length chunk to signal end
            writer.write(b"\x00\x00\x00\x00")
            await writer.drain()

            # Read response
            response = await reader.read(1024)
            writer.close()
            await writer.wait_closed()

            response_str = response.decode("utf-8").strip()

            if "FOUND" in response_str:
                virus_name = response_str.split(":")[1].strip().replace(" FOUND", "")
                return {"infected": True, "virus_name": virus_name}
            elif "OK" in response_str:
                return {"infected": False, "virus_name": None}
            else:
                return {"infected": False, "virus_name": None, "error": response_str}

        except Exception as e:
            raise Exception(f"ClamAV connection failed: {e}")

    async def _scan_with_virustotal(self, content: bytes) -> dict[str, Any]:
        """Scan file content with VirusTotal API"""
        import hashlib

        import aiohttp

        try:
            # Calculate file hash
            file_hash = hashlib.sha256(content).hexdigest()

            headers = {"x-apikey": self.settings.VIRUSTOTAL_API_KEY}

            timeout = aiohttp.ClientTimeout(total=self.settings.VIRUSTOTAL_TIMEOUT)

            async with aiohttp.ClientSession(headers=headers, timeout=timeout) as session:
                # First, try to get existing analysis
                url = f"https://www.virustotal.com/api/v3/files/{file_hash}"

                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        stats = data["data"]["attributes"]["last_analysis_stats"]
                        return {
                            "positives": stats.get("malicious", 0) + stats.get("suspicious", 0),
                            "total": sum(stats.values()),
                            "scan_date": data["data"]["attributes"]["last_analysis_date"],
                        }

                    elif response.status == 404:
                        # File not found, upload for analysis
                        data = aiohttp.FormData()
                        data.add_field("file", content, filename="upload", content_type="application/octet-stream")

                        upload_url = "https://www.virustotal.com/api/v3/files"
                        async with session.post(upload_url, data=data) as upload_response:
                            if upload_response.status == 200:
                                upload_data = await upload_response.json()
                                analysis_id = upload_data["data"]["id"]

                                # Wait a bit and check results
                                await asyncio.sleep(5)

                                analysis_url = f"https://www.virustotal.com/api/v3/analyses/{analysis_id}"
                                async with session.get(analysis_url) as analysis_response:
                                    if analysis_response.status == 200:
                                        analysis_data = await analysis_response.json()
                                        stats = analysis_data["data"]["attributes"]["stats"]
                                        return {
                                            "positives": stats.get("malicious", 0) + stats.get("suspicious", 0),
                                            "total": sum(stats.values()),
                                            "scan_date": analysis_data["data"]["attributes"]["date"],
                                        }

                            return {"positives": 0, "total": 0, "error": "Upload failed"}

                    else:
                        return {"positives": 0, "total": 0, "error": f"API error: {response.status}"}

        except Exception as e:
            raise Exception(f"VirusTotal API failed: {e}")

    def _calculate_entropy(self, data: bytes) -> float:
        """Calculate Shannon entropy of byte data"""
        if len(data) == 0:
            return 0

        # Count frequency of each byte value
        frequency = [0] * 256
        for byte in data:
            frequency[byte] += 1

        # Calculate entropy
        entropy = 0.0
        length = len(data)

        for count in frequency:
            if count > 0:
                probability = count / length
                entropy -= probability * math.log2(probability)

        return entropy

    async def _detect_text_encoding(self, content: bytes) -> dict[str, Any]:
        """Detect text encoding for CSV files, with Italian support.

        Args:
          content: File content bytes

        Returns:
          Dictionary with encoding information
        """
        # Check for BOM (Byte Order Mark)
        has_bom = False
        encoding = "utf-8"

        if content.startswith(b"\xef\xbb\xbf"):
            has_bom = True
            encoding = "utf-8-sig"
        elif content.startswith(b"\xff\xfe"):
            has_bom = True
            encoding = "utf-16-le"
        elif content.startswith(b"\xfe\xff"):
            has_bom = True
            encoding = "utf-16-be"
        else:
            # Try to decode with common encodings
            encodings_to_try = ["utf-8", "utf-8-sig", "iso-8859-1", "windows-1252", "cp1252"]

            for enc in encodings_to_try:
                try:
                    content.decode(enc)
                    encoding = enc
                    break
                except UnicodeDecodeError:
                    continue

        return {"encoding": encoding, "has_bom": has_bom, "confidence": 0.95 if has_bom else 0.85}

    def get_storage_filename(self, document_id: str, file_type: DocumentType) -> str:
        """Generate secure storage filename using document ID.

        Args:
          document_id: Unique document identifier
          file_type: Document type

        Returns:
          Secure filename for storage
        """
        extension_map = {
            DocumentType.PDF: ".pdf",
            DocumentType.EXCEL_XLSX: ".xlsx",
            DocumentType.EXCEL_XLS: ".xls",
            DocumentType.CSV: ".csv",
            DocumentType.XML: ".xml",
        }

        extension = extension_map.get(file_type, ".bin")
        return f"{document_id}{extension}"

    def validate_upload_limits(self, files: list[UploadFile]) -> None:
        """Validate upload limits for multiple files.

        Args:
          files: List of uploaded files

        Raises:
          UploadValidationError: If limits exceeded
        """
        if len(files) > self.max_files_per_upload:
            raise UploadValidationError(
                f"Too many files. Maximum {self.max_files_per_upload} files per upload, received {len(files)}"
            )

        total_size = sum(getattr(f, "size", 0) or 0 for f in files)
        max_total_size = self.max_file_size * len(files)

        if total_size > max_total_size:
            raise UploadValidationError(
                f"Combined file size too large. Maximum {max_total_size / (1024 * 1024):.1f}MB, "
                f"received {total_size / (1024 * 1024):.1f}MB"
            )
