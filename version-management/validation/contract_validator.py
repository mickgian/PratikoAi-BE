#!/usr/bin/env python3
"""
PratikoAI API Contract Validation System
Advanced contract validation to ensure API compatibility between frontend and backend versions.

This system provides:
- OpenAPI specification comparison
- Breaking change detection
- Backward/forward compatibility analysis
- Semantic versioning compliance checking
- Contract evolution tracking
"""

import json
import hashlib
import asyncio
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Tuple, Set
from dataclasses import dataclass, field
from enum import Enum
import yaml
import requests
from deepdiff import DeepDiff
from jsonschema import validate, ValidationError, draft7_format_checker
import openapi_spec_validator

from ..core.version_schema import ServiceType, CompatibilityLevel, APIContract, APIEndpoint


class ContractChangeType(Enum):
    """Types of changes in API contracts."""
    BREAKING = "breaking"
    NON_BREAKING = "non_breaking"
    ADDITIVE = "additive"
    DEPRECATED = "deprecated"
    COSMETIC = "cosmetic"


class ContractViolationSeverity(Enum):
    """Severity levels for contract violations."""
    CRITICAL = "critical"      # Will break existing clients
    MAJOR = "major"           # May break some clients
    MINOR = "minor"           # Unlikely to break clients
    INFO = "info"             # Informational only


@dataclass
class ContractChange:
    """Represents a change in an API contract."""
    change_type: ContractChangeType
    severity: ContractViolationSeverity
    path: str
    description: str
    old_value: Any = None
    new_value: Any = None
    breaking_reason: Optional[str] = None
    mitigation: Optional[str] = None


@dataclass
class ContractValidationResult:
    """Result of contract validation."""
    is_compatible: bool
    compatibility_level: CompatibilityLevel
    changes: List[ContractChange] = field(default_factory=list)
    breaking_changes: List[ContractChange] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    summary: Dict[str, int] = field(default_factory=dict)
    validation_time: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class APIContractValidator:
    """Advanced API contract validator with breaking change detection."""
    
    def __init__(self):
        self.breaking_change_rules = self._load_breaking_change_rules()
    
    def _load_breaking_change_rules(self) -> Dict[str, Any]:
        """Load rules for detecting breaking changes."""
        return {
            "endpoint_removal": {
                "severity": ContractViolationSeverity.CRITICAL,
                "description": "Removing an endpoint breaks existing clients"
            },
            "method_removal": {
                "severity": ContractViolationSeverity.CRITICAL,
                "description": "Removing HTTP methods breaks existing clients"
            },
            "required_parameter_addition": {
                "severity": ContractViolationSeverity.CRITICAL,
                "description": "Adding required parameters breaks existing clients"
            },
            "parameter_type_change": {
                "severity": ContractViolationSeverity.MAJOR,
                "description": "Changing parameter types may break clients"
            },
            "response_schema_breaking": {
                "severity": ContractViolationSeverity.MAJOR,
                "description": "Breaking response schema changes affect client parsing"
            },
            "enum_value_removal": {
                "severity": ContractViolationSeverity.MAJOR,
                "description": "Removing enum values breaks clients using them"
            },
            "property_removal": {
                "severity": ContractViolationSeverity.MAJOR,
                "description": "Removing response properties breaks client expectations"
            },
            "required_property_addition": {
                "severity": ContractViolationSeverity.MINOR,
                "description": "Adding required response properties may affect clients"
            }
        }
    
    async def validate_contract_evolution(self, 
                                        old_contract: APIContract, 
                                        new_contract: APIContract) -> ContractValidationResult:
        """Validate the evolution of an API contract."""
        
        result = ContractValidationResult(
            is_compatible=True,
            compatibility_level=CompatibilityLevel.FULLY_COMPATIBLE
        )
        
        # Convert contracts to OpenAPI specifications for comparison
        old_spec = self._contract_to_openapi(old_contract)
        new_spec = self._contract_to_openapi(new_contract)
        
        # Validate OpenAPI specifications
        await self._validate_openapi_specs(old_spec, new_spec, result)
        
        # Compare endpoints
        await self._compare_endpoints(old_spec, new_spec, result)
        
        # Compare schemas
        await self._compare_schemas(old_spec, new_spec, result)
        
        # Analyze overall compatibility
        await self._analyze_compatibility(result)
        
        # Generate summary
        result.summary = self._generate_summary(result)
        
        return result
    
    def _contract_to_openapi(self, contract: APIContract) -> Dict[str, Any]:
        """Convert APIContract to OpenAPI specification."""
        openapi_spec = {
            "openapi": "3.0.3",
            "info": {
                "title": f"{contract.service_type.value.title()} API",
                "version": contract.version,
                "description": f"API contract for {contract.service_type.value}"
            },
            "paths": {},
            "components": {
                "schemas": contract.schemas
            }
        }
        
        # Convert endpoints to OpenAPI paths
        for endpoint in contract.endpoints:
            path = endpoint.path
            method = endpoint.method.lower()
            
            if path not in openapi_spec["paths"]:
                openapi_spec["paths"][path] = {}
            
            # Build operation object
            operation = {
                "summary": f"{method.upper()} {path}",
                "operationId": f"{method}_{path.replace('/', '_').replace('{', '').replace('}', '')}"
            }
            
            # Add parameters
            if endpoint.parameters:
                operation["parameters"] = endpoint.parameters
            
            # Add request body
            if endpoint.request_schema:
                operation["requestBody"] = {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": endpoint.request_schema
                        }
                    }
                }
            
            # Add responses
            if endpoint.response_schema:
                operation["responses"] = {
                    "200": {
                        "description": "Successful response",
                        "content": {
                            "application/json": {
                                "schema": endpoint.response_schema
                            }
                        }
                    }
                }
            else:
                operation["responses"] = {
                    "200": {
                        "description": "Successful response"
                    }
                }
            
            # Add deprecation info
            if endpoint.deprecated_in_version:
                operation["deprecated"] = True
                operation["x-deprecated-in"] = endpoint.deprecated_in_version
                if endpoint.removed_in_version:
                    operation["x-removed-in"] = endpoint.removed_in_version
            
            openapi_spec["paths"][path][method] = operation
        
        return openapi_spec
    
    async def _validate_openapi_specs(self, old_spec: Dict[str, Any], 
                                    new_spec: Dict[str, Any], 
                                    result: ContractValidationResult):
        """Validate that both OpenAPI specifications are valid."""
        
        # Validate old specification
        try:
            openapi_spec_validator.validate_spec(old_spec)
        except Exception as e:
            result.warnings.append(f"Old API specification has validation errors: {str(e)}")
        
        # Validate new specification
        try:
            openapi_spec_validator.validate_spec(new_spec)
        except Exception as e:
            result.warnings.append(f"New API specification has validation errors: {str(e)}")
            result.is_compatible = False
    
    async def _compare_endpoints(self, old_spec: Dict[str, Any], 
                               new_spec: Dict[str, Any], 
                               result: ContractValidationResult):
        """Compare endpoints between old and new specifications."""
        
        old_paths = old_spec.get("paths", {})
        new_paths = new_spec.get("paths", {})
        
        # Check for removed endpoints
        for path in old_paths:
            if path not in new_paths:
                change = ContractChange(
                    change_type=ContractChangeType.BREAKING,
                    severity=ContractViolationSeverity.CRITICAL,
                    path=path,
                    description=f"Endpoint {path} was removed",
                    breaking_reason="Clients using this endpoint will fail",
                    mitigation="Deprecate endpoint before removal"
                )
                result.changes.append(change)
                result.breaking_changes.append(change)
                result.is_compatible = False
                continue
            
            # Compare methods for existing endpoints
            old_methods = set(old_paths[path].keys())
            new_methods = set(new_paths[path].keys())
            
            # Check for removed methods
            removed_methods = old_methods - new_methods
            for method in removed_methods:
                change = ContractChange(
                    change_type=ContractChangeType.BREAKING,
                    severity=ContractViolationSeverity.CRITICAL,
                    path=f"{method.upper()} {path}",
                    description=f"HTTP method {method.upper()} was removed from {path}",
                    breaking_reason="Clients using this method will receive 405 Method Not Allowed",
                    mitigation="Keep method and return 410 Gone with deprecation notice"
                )
                result.changes.append(change)
                result.breaking_changes.append(change)
                result.is_compatible = False
            
            # Check for added methods (non-breaking)
            added_methods = new_methods - old_methods
            for method in added_methods:
                change = ContractChange(
                    change_type=ContractChangeType.ADDITIVE,
                    severity=ContractViolationSeverity.INFO,
                    path=f"{method.upper()} {path}",
                    description=f"New HTTP method {method.upper()} added to {path}",
                    new_value=method
                )
                result.changes.append(change)
            
            # Compare existing methods
            common_methods = old_methods & new_methods
            for method in common_methods:
                await self._compare_method_operation(
                    path, method, 
                    old_paths[path][method], 
                    new_paths[path][method], 
                    result
                )
        
        # Check for new endpoints (non-breaking)
        new_endpoints = set(new_paths.keys()) - set(old_paths.keys())
        for path in new_endpoints:
            change = ContractChange(
                change_type=ContractChangeType.ADDITIVE,
                severity=ContractViolationSeverity.INFO,
                path=path,
                description=f"New endpoint {path} added",
                new_value=list(new_paths[path].keys())
            )
            result.changes.append(change)
    
    async def _compare_method_operation(self, path: str, method: str,
                                      old_operation: Dict[str, Any],
                                      new_operation: Dict[str, Any],
                                      result: ContractValidationResult):
        """Compare a specific method operation between versions."""
        
        endpoint_path = f"{method.upper()} {path}"
        
        # Check for deprecation changes
        old_deprecated = old_operation.get("deprecated", False)
        new_deprecated = new_operation.get("deprecated", False)
        
        if not old_deprecated and new_deprecated:
            change = ContractChange(
                change_type=ContractChangeType.DEPRECATED,
                severity=ContractViolationSeverity.MINOR,
                path=endpoint_path,
                description=f"Endpoint {endpoint_path} is now deprecated",
                mitigation="Plan for endpoint removal in future version"
            )
            result.changes.append(change)
        
        # Compare parameters
        await self._compare_parameters(endpoint_path, old_operation, new_operation, result)
        
        # Compare request body
        await self._compare_request_body(endpoint_path, old_operation, new_operation, result)
        
        # Compare responses
        await self._compare_responses(endpoint_path, old_operation, new_operation, result)
    
    async def _compare_parameters(self, endpoint_path: str,
                                old_operation: Dict[str, Any],
                                new_operation: Dict[str, Any],
                                result: ContractValidationResult):
        """Compare parameters between operations."""
        
        old_params = {p["name"]: p for p in old_operation.get("parameters", [])}
        new_params = {p["name"]: p for p in new_operation.get("parameters", [])}
        
        # Check for removed parameters
        removed_params = set(old_params.keys()) - set(new_params.keys())
        for param_name in removed_params:
            old_param = old_params[param_name]
            severity = ContractViolationSeverity.CRITICAL if old_param.get("required", False) else ContractViolationSeverity.MINOR
            
            change = ContractChange(
                change_type=ContractChangeType.BREAKING if severity == ContractViolationSeverity.CRITICAL else ContractChangeType.NON_BREAKING,
                severity=severity,
                path=f"{endpoint_path}/parameters/{param_name}",
                description=f"Parameter '{param_name}' was removed",
                old_value=old_param,
                breaking_reason="Required parameters cannot be removed" if old_param.get("required") else None
            )
            result.changes.append(change)
            
            if severity == ContractViolationSeverity.CRITICAL:
                result.breaking_changes.append(change)
                result.is_compatible = False
        
        # Check for new required parameters (breaking)
        added_params = set(new_params.keys()) - set(old_params.keys())
        for param_name in added_params:
            new_param = new_params[param_name]
            if new_param.get("required", False):
                change = ContractChange(
                    change_type=ContractChangeType.BREAKING,
                    severity=ContractViolationSeverity.CRITICAL,
                    path=f"{endpoint_path}/parameters/{param_name}",
                    description=f"New required parameter '{param_name}' was added",
                    new_value=new_param,
                    breaking_reason="Adding required parameters breaks existing clients",
                    mitigation="Make parameter optional with sensible default"
                )
                result.changes.append(change)
                result.breaking_changes.append(change)
                result.is_compatible = False
            else:
                change = ContractChange(
                    change_type=ContractChangeType.ADDITIVE,
                    severity=ContractViolationSeverity.INFO,
                    path=f"{endpoint_path}/parameters/{param_name}",
                    description=f"New optional parameter '{param_name}' was added",
                    new_value=new_param
                )
                result.changes.append(change)
        
        # Check for parameter type changes
        common_params = set(old_params.keys()) & set(new_params.keys())
        for param_name in common_params:
            old_param = old_params[param_name]
            new_param = new_params[param_name]
            
            # Compare parameter schemas
            old_schema = old_param.get("schema", {})
            new_schema = new_param.get("schema", {})
            
            if old_schema.get("type") != new_schema.get("type"):
                change = ContractChange(
                    change_type=ContractChangeType.BREAKING,
                    severity=ContractViolationSeverity.MAJOR,
                    path=f"{endpoint_path}/parameters/{param_name}/type",
                    description=f"Parameter '{param_name}' type changed from {old_schema.get('type')} to {new_schema.get('type')}",
                    old_value=old_schema.get("type"),
                    new_value=new_schema.get("type"),
                    breaking_reason="Type changes require client code updates"
                )
                result.changes.append(change)
                result.breaking_changes.append(change)
    
    async def _compare_request_body(self, endpoint_path: str,
                                  old_operation: Dict[str, Any],
                                  new_operation: Dict[str, Any],
                                  result: ContractValidationResult):
        """Compare request body schemas."""
        
        old_body = old_operation.get("requestBody", {})
        new_body = new_operation.get("requestBody", {})
        
        # If request body was removed
        if old_body and not new_body:
            change = ContractChange(
                change_type=ContractChangeType.BREAKING,
                severity=ContractViolationSeverity.MAJOR,
                path=f"{endpoint_path}/requestBody",
                description="Request body requirement was removed",
                breaking_reason="Clients sending request bodies may receive unexpected responses"
            )
            result.changes.append(change)
            result.breaking_changes.append(change)
            return
        
        # If request body was added
        if not old_body and new_body:
            severity = ContractViolationSeverity.CRITICAL if new_body.get("required", False) else ContractViolationSeverity.INFO
            change = ContractChange(
                change_type=ContractChangeType.BREAKING if severity == ContractViolationSeverity.CRITICAL else ContractChangeType.ADDITIVE,
                severity=severity,
                path=f"{endpoint_path}/requestBody",
                description="Request body requirement was added",
                breaking_reason="Required request body breaks existing clients" if new_body.get("required") else None
            )
            result.changes.append(change)
            if severity == ContractViolationSeverity.CRITICAL:
                result.breaking_changes.append(change)
                result.is_compatible = False
            return
        
        # Compare existing request bodies
        if old_body and new_body:
            await self._compare_schemas_deep(
                f"{endpoint_path}/requestBody",
                old_body.get("content", {}).get("application/json", {}).get("schema", {}),
                new_body.get("content", {}).get("application/json", {}).get("schema", {}),
                result,
                is_request=True
            )
    
    async def _compare_responses(self, endpoint_path: str,
                               old_operation: Dict[str, Any],
                               new_operation: Dict[str, Any],
                               result: ContractValidationResult):
        """Compare response schemas."""
        
        old_responses = old_operation.get("responses", {})
        new_responses = new_operation.get("responses", {})
        
        # Check for removed response codes
        removed_codes = set(old_responses.keys()) - set(new_responses.keys())
        for code in removed_codes:
            change = ContractChange(
                change_type=ContractChangeType.BREAKING,
                severity=ContractViolationSeverity.MAJOR,
                path=f"{endpoint_path}/responses/{code}",
                description=f"Response code {code} was removed",
                breaking_reason="Clients expecting this response code may not handle its absence"
            )
            result.changes.append(change)
            result.breaking_changes.append(change)
        
        # Compare existing response codes
        common_codes = set(old_responses.keys()) & set(new_responses.keys())
        for code in common_codes:
            old_response = old_responses[code]
            new_response = new_responses[code]
            
            # Compare response schemas
            old_schema = old_response.get("content", {}).get("application/json", {}).get("schema", {})
            new_schema = new_response.get("content", {}).get("application/json", {}).get("schema", {})
            
            if old_schema and new_schema:
                await self._compare_schemas_deep(
                    f"{endpoint_path}/responses/{code}",
                    old_schema,
                    new_schema,
                    result,
                    is_request=False
                )
    
    async def _compare_schemas_deep(self, path: str, old_schema: Dict[str, Any], 
                                  new_schema: Dict[str, Any], result: ContractValidationResult,
                                  is_request: bool = False):
        """Deep comparison of JSON schemas."""
        
        # Use DeepDiff for detailed comparison
        diff = DeepDiff(old_schema, new_schema, ignore_order=True)
        
        # Analyze dictionary changes
        if "dictionary_item_removed" in diff:
            for removed_path in diff["dictionary_item_removed"]:
                # Extract the property path
                prop_path = removed_path.replace("root", path)
                
                # Check if it's a required property
                is_required_removal = "required" in removed_path and not is_request
                severity = ContractViolationSeverity.MAJOR if is_required_removal else ContractViolationSeverity.MINOR
                
                change = ContractChange(
                    change_type=ContractChangeType.BREAKING if severity == ContractViolationSeverity.MAJOR else ContractChangeType.NON_BREAKING,
                    severity=severity,
                    path=prop_path,
                    description=f"Property was removed: {removed_path}",
                    breaking_reason="Removing response properties breaks client parsing" if not is_request else None
                )
                result.changes.append(change)
                
                if severity == ContractViolationSeverity.MAJOR:
                    result.breaking_changes.append(change)
        
        # Analyze type changes
        if "type_changes" in diff:
            for type_path, type_change in diff["type_changes"].items():
                prop_path = type_path.replace("root", path)
                
                change = ContractChange(
                    change_type=ContractChangeType.BREAKING,
                    severity=ContractViolationSeverity.MAJOR,
                    path=prop_path,
                    description=f"Type changed from {type_change['old_type'].__name__} to {type_change['new_type'].__name__}",
                    old_value=type_change["old_value"],
                    new_value=type_change["new_value"],
                    breaking_reason="Type changes require client code updates"
                )
                result.changes.append(change)
                result.breaking_changes.append(change)
        
        # Analyze value changes (for enums, constraints, etc.)
        if "values_changed" in diff:
            for value_path, value_change in diff["values_changed"].items():
                prop_path = value_path.replace("root", path)
                
                # Determine severity based on the type of change
                severity = ContractViolationSeverity.MINOR
                if "enum" in value_path:
                    severity = ContractViolationSeverity.MAJOR  # Enum changes are more significant
                
                change = ContractChange(
                    change_type=ContractChangeType.BREAKING if severity == ContractViolationSeverity.MAJOR else ContractChangeType.NON_BREAKING,
                    severity=severity,
                    path=prop_path,
                    description=f"Value changed from {value_change['old_value']} to {value_change['new_value']}",
                    old_value=value_change["old_value"],
                    new_value=value_change["new_value"],
                    breaking_reason="Enum value changes may break client validation" if "enum" in value_path else None
                )
                result.changes.append(change)
                
                if severity == ContractViolationSeverity.MAJOR:
                    result.breaking_changes.append(change)
    
    async def _compare_schemas(self, old_spec: Dict[str, Any], 
                             new_spec: Dict[str, Any], 
                             result: ContractValidationResult):
        """Compare component schemas between specifications."""
        
        old_schemas = old_spec.get("components", {}).get("schemas", {})
        new_schemas = new_spec.get("components", {}).get("schemas", {})
        
        # Check for removed schemas
        removed_schemas = set(old_schemas.keys()) - set(new_schemas.keys())
        for schema_name in removed_schemas:
            change = ContractChange(
                change_type=ContractChangeType.BREAKING,
                severity=ContractViolationSeverity.MAJOR,
                path=f"/components/schemas/{schema_name}",
                description=f"Schema '{schema_name}' was removed",
                breaking_reason="Removing schemas breaks clients using them"
            )
            result.changes.append(change)
            result.breaking_changes.append(change)
        
        # Compare existing schemas
        common_schemas = set(old_schemas.keys()) & set(new_schemas.keys())
        for schema_name in common_schemas:
            await self._compare_schemas_deep(
                f"/components/schemas/{schema_name}",
                old_schemas[schema_name],
                new_schemas[schema_name],
                result
            )
    
    async def _analyze_compatibility(self, result: ContractValidationResult):
        """Analyze overall compatibility based on changes."""
        
        critical_count = sum(1 for c in result.breaking_changes if c.severity == ContractViolationSeverity.CRITICAL)
        major_count = sum(1 for c in result.breaking_changes if c.severity == ContractViolationSeverity.MAJOR)
        
        if critical_count > 0:
            result.compatibility_level = CompatibilityLevel.INCOMPATIBLE
            result.is_compatible = False
        elif major_count > 0:
            result.compatibility_level = CompatibilityLevel.LIMITED_COMPATIBLE
            result.is_compatible = False
        elif len(result.breaking_changes) > 0:
            result.compatibility_level = CompatibilityLevel.BACKWARD_COMPATIBLE
        else:
            result.compatibility_level = CompatibilityLevel.FULLY_COMPATIBLE
    
    def _generate_summary(self, result: ContractValidationResult) -> Dict[str, int]:
        """Generate summary statistics."""
        
        return {
            "total_changes": len(result.changes),
            "breaking_changes": len(result.breaking_changes),
            "additive_changes": sum(1 for c in result.changes if c.change_type == ContractChangeType.ADDITIVE),
            "deprecated_items": sum(1 for c in result.changes if c.change_type == ContractChangeType.DEPRECATED),
            "critical_issues": sum(1 for c in result.changes if c.severity == ContractViolationSeverity.CRITICAL),
            "major_issues": sum(1 for c in result.changes if c.severity == ContractViolationSeverity.MAJOR),
            "minor_issues": sum(1 for c in result.changes if c.severity == ContractViolationSeverity.MINOR)
        }
    
    async def validate_against_live_api(self, contract: APIContract, base_url: str) -> ContractValidationResult:
        """Validate a contract against a live API implementation."""
        
        result = ContractValidationResult(
            is_compatible=True,
            compatibility_level=CompatibilityLevel.FULLY_COMPATIBLE
        )
        
        # Test each endpoint
        for endpoint in contract.endpoints:
            await self._test_live_endpoint(base_url, endpoint, result)
        
        # Analyze results
        await self._analyze_compatibility(result)
        result.summary = self._generate_summary(result)
        
        return result
    
    async def _test_live_endpoint(self, base_url: str, endpoint: APIEndpoint, 
                                result: ContractValidationResult):
        """Test a single endpoint against live API."""
        
        url = f"{base_url.rstrip('/')}{endpoint.path}"
        method = endpoint.method.upper()
        
        try:
            # Prepare test request
            kwargs = {"timeout": 10}
            if endpoint.request_schema:
                # Generate test data based on schema
                test_data = self._generate_test_data(endpoint.request_schema)
                kwargs["json"] = test_data
            
            # Make request
            if method == "GET":
                response = requests.get(url, **kwargs)
            elif method == "POST":
                response = requests.post(url, **kwargs)
            elif method == "PUT":
                response = requests.put(url, **kwargs)
            elif method == "DELETE":
                response = requests.delete(url, **kwargs)
            elif method == "PATCH":
                response = requests.patch(url, **kwargs)
            else:
                result.warnings.append(f"Unsupported method {method} for {endpoint.path}")
                return
            
            # Validate response
            if response.status_code < 400:
                if endpoint.response_schema:
                    try:
                        response_data = response.json()
                        validate(response_data, endpoint.response_schema, format_checker=draft7_format_checker)
                    except ValidationError as e:
                        change = ContractChange(
                            change_type=ContractChangeType.BREAKING,
                            severity=ContractViolationSeverity.MAJOR,
                            path=f"{method} {endpoint.path}/response",
                            description=f"Response validation failed: {e.message}",
                            breaking_reason="Response doesn't match contract"
                        )
                        result.changes.append(change)
                        result.breaking_changes.append(change)
                        result.is_compatible = False
                    except json.JSONDecodeError:
                        result.warnings.append(f"Non-JSON response from {method} {endpoint.path}")
            else:
                result.warnings.append(f"Error response {response.status_code} from {method} {endpoint.path}")
                
        except requests.RequestException as e:
            change = ContractChange(
                change_type=ContractChangeType.BREAKING,
                severity=ContractViolationSeverity.CRITICAL,
                path=f"{method} {endpoint.path}",
                description=f"Endpoint not accessible: {str(e)}",
                breaking_reason="Endpoint is not available"
            )
            result.changes.append(change)
            result.breaking_changes.append(change)
            result.is_compatible = False
    
    def _generate_test_data(self, schema: Dict[str, Any]) -> Any:
        """Generate test data based on JSON schema."""
        
        schema_type = schema.get("type", "object")
        
        if schema_type == "object":
            properties = schema.get("properties", {})
            required = schema.get("required", [])
            
            data = {}
            for prop_name, prop_schema in properties.items():
                if prop_name in required:
                    data[prop_name] = self._generate_test_data(prop_schema)
            
            return data
        
        elif schema_type == "array":
            items_schema = schema.get("items", {})
            return [self._generate_test_data(items_schema)]
        
        elif schema_type == "string":
            if "enum" in schema:
                return schema["enum"][0]
            return "test_string"
        
        elif schema_type == "integer":
            return 42
        
        elif schema_type == "number":
            return 3.14
        
        elif schema_type == "boolean":
            return True
        
        else:
            return None


# Example usage and testing
if __name__ == "__main__":
    async def main():
        validator = APIContractValidator()
        
        # Create test contracts
        old_contract = APIContract(
            version="1.0.0",
            service_type=ServiceType.BACKEND,
            endpoints=[
                APIEndpoint(
                    path="/api/v1/users/{id}",
                    method="GET",
                    response_schema={
                        "type": "object",
                        "properties": {
                            "id": {"type": "integer"},
                            "name": {"type": "string"},
                            "email": {"type": "string"}
                        },
                        "required": ["id", "name", "email"]
                    }
                )
            ]
        )
        
        new_contract = APIContract(
            version="1.1.0",
            service_type=ServiceType.BACKEND,
            endpoints=[
                APIEndpoint(
                    path="/api/v1/users/{id}",
                    method="GET",
                    response_schema={
                        "type": "object",
                        "properties": {
                            "id": {"type": "integer"},
                            "name": {"type": "string"},
                            "email": {"type": "string"},
                            "created_at": {"type": "string", "format": "date-time"}
                        },
                        "required": ["id", "name", "email"]  # Note: created_at not required
                    }
                )
            ]
        )
        
        # Validate contract evolution
        result = await validator.validate_contract_evolution(old_contract, new_contract)
        
        print("Contract Validation Result:")
        print(f"Compatible: {result.is_compatible}")
        print(f"Compatibility Level: {result.compatibility_level.value}")
        print(f"Total Changes: {len(result.changes)}")
        print(f"Breaking Changes: {len(result.breaking_changes)}")
        
        for change in result.changes:
            print(f"  - {change.change_type.value}: {change.description}")
    
    asyncio.run(main())