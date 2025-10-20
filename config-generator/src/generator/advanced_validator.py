"""
Advanced configuration validator with detailed error reporting.
Provides specific feedback for iterative AI correction.
"""

from typing import Dict, List, Any, Tuple
import yaml
import re
from pathlib import Path


class ValidationError:
    """Individual validation error with context"""
    def __init__(self, field: str, error_type: str, message: str, suggested_fix: str = None):
        self.field = field
        self.error_type = error_type
        self.message = message
        self.suggested_fix = suggested_fix

    def __str__(self):
        result = f"[{self.error_type}] {self.field}: {self.message}"
        if self.suggested_fix:
            result += f"\n  → Suggested fix: {self.suggested_fix}"
        return result


class AdvancedConfigValidator:
    """Comprehensive validator that provides detailed feedback for AI correction"""

    def __init__(self, v1_spec: Dict[str, Any], v2_spec: Dict[str, Any]):
        self.v1_spec = v1_spec
        self.v2_spec = v2_spec
        self.v1_endpoints = set(v1_spec.get("paths", {}).keys())
        self.v2_endpoints = set(v2_spec.get("paths", {}).keys())

    def validate_config(self, config: Dict[str, Any]) -> Tuple[bool, List[ValidationError]]:
        """
        Comprehensive validation with detailed error reporting.
        Returns (is_valid, list_of_errors)
        """
        errors = []

        # Basic structure validation
        errors.extend(self._validate_structure(config))

        # V1 calls validation
        errors.extend(self._validate_v1_calls(config))

        # Field mappings validation
        errors.extend(self._validate_field_mappings(config))

        # Transform syntax validation
        errors.extend(self._validate_transforms(config))

        # Cross-reference validation
        errors.extend(self._validate_cross_references(config))

        return len(errors) == 0, errors

    def _validate_structure(self, config: Dict[str, Any]) -> List[ValidationError]:
        """Validate basic YAML structure"""
        errors = []
        required_keys = ['version', 'endpoint', 'v1_calls', 'field_mappings']

        for key in required_keys:
            if key not in config:
                errors.append(ValidationError(
                    field=f"root.{key}",
                    error_type="MISSING_FIELD",
                    message=f"Required field '{key}' is missing",
                    suggested_fix=f"Add '{key}:' section to the configuration"
                ))

        # Validate endpoint structure
        if 'endpoint' in config:
            endpoint = config['endpoint']
            if not isinstance(endpoint, dict):
                errors.append(ValidationError(
                    field="endpoint",
                    error_type="INVALID_TYPE",
                    message="Endpoint must be a dictionary",
                    suggested_fix="Use 'endpoint: {v2_path: ..., v2_method: ...}'"
                ))
            else:
                for req_field in ['v2_path', 'v2_method']:
                    if req_field not in endpoint:
                        errors.append(ValidationError(
                            field=f"endpoint.{req_field}",
                            error_type="MISSING_FIELD",
                            message=f"Endpoint missing required field '{req_field}'",
                            suggested_fix=f"Add '{req_field}: value' to endpoint section"
                        ))

        return errors

    def _validate_v1_calls(self, config: Dict[str, Any]) -> List[ValidationError]:
        """Validate V1 API calls"""
        errors = []

        if 'v1_calls' not in config:
            return errors

        v1_calls = config['v1_calls']
        if not isinstance(v1_calls, list):
            errors.append(ValidationError(
                field="v1_calls",
                error_type="INVALID_TYPE",
                message="v1_calls must be a list",
                suggested_fix="Use 'v1_calls: [...]' format"
            ))
            return errors

        if len(v1_calls) == 0:
            errors.append(ValidationError(
                field="v1_calls",
                error_type="EMPTY_LIST",
                message="v1_calls cannot be empty",
                suggested_fix="Add at least one V1 API call definition"
            ))

        call_names = set()
        for i, call in enumerate(v1_calls):
            if not isinstance(call, dict):
                errors.append(ValidationError(
                    field=f"v1_calls[{i}]",
                    error_type="INVALID_TYPE",
                    message="Each V1 call must be a dictionary",
                    suggested_fix="Use '{name: ..., endpoint: ..., method: ...}' format"
                ))
                continue

            # Validate required fields
            for req_field in ['name', 'endpoint', 'method']:
                if req_field not in call:
                    errors.append(ValidationError(
                        field=f"v1_calls[{i}].{req_field}",
                        error_type="MISSING_FIELD",
                        message=f"V1 call missing required field '{req_field}'",
                        suggested_fix=f"Add '{req_field}: value' to V1 call"
                    ))

            # Check for duplicate names
            if 'name' in call:
                if call['name'] in call_names:
                    errors.append(ValidationError(
                        field=f"v1_calls[{i}].name",
                        error_type="DUPLICATE_NAME",
                        message=f"Duplicate V1 call name: '{call['name']}'",
                        suggested_fix="Use unique names for each V1 call (e.g., getPolicy_v1, getCoverage_v1)"
                    ))
                call_names.add(call['name'])

            # Validate endpoint exists in V1 spec
            if 'endpoint' in call:
                endpoint = call['endpoint']
                # Handle parameterized endpoints
                base_endpoint = re.sub(r'\{[^}]+\}', '{id}', endpoint)
                if endpoint not in self.v1_endpoints and base_endpoint not in self.v1_endpoints:
                    available = ", ".join(list(self.v1_endpoints)[:3])
                    errors.append(ValidationError(
                        field=f"v1_calls[{i}].endpoint",
                        error_type="INVALID_ENDPOINT",
                        message=f"V1 endpoint '{endpoint}' not found in V1 spec",
                        suggested_fix=f"Use one of the available V1 endpoints: {available}"
                    ))

        return errors

    def _validate_field_mappings(self, config: Dict[str, Any]) -> List[ValidationError]:
        """Validate field mappings"""
        errors = []

        if 'field_mappings' not in config:
            return errors

        field_mappings = config['field_mappings']
        if not isinstance(field_mappings, list):
            errors.append(ValidationError(
                field="field_mappings",
                error_type="INVALID_TYPE",
                message="field_mappings must be a list",
                suggested_fix="Use 'field_mappings: [...]' format"
            ))
            return errors

        if len(field_mappings) == 0:
            errors.append(ValidationError(
                field="field_mappings",
                error_type="EMPTY_LIST",
                message="field_mappings cannot be empty",
                suggested_fix="Add at least one field mapping"
            ))

        # Get valid source names from v1_calls
        valid_sources = set()
        if 'v1_calls' in config and isinstance(config['v1_calls'], list):
            valid_sources = {call.get('name') for call in config['v1_calls'] if call.get('name')}
        valid_sources.add('stub')  # stub is always valid

        for i, mapping in enumerate(field_mappings):
            if not isinstance(mapping, dict):
                errors.append(ValidationError(
                    field=f"field_mappings[{i}]",
                    error_type="INVALID_TYPE",
                    message="Each field mapping must be a dictionary",
                    suggested_fix="Use '{v2_path: ..., source: ..., v1_path: ...}' format"
                ))
                continue

            # Validate required fields
            required_fields = ['v2_path', 'source']
            for req_field in required_fields:
                if req_field not in mapping:
                    errors.append(ValidationError(
                        field=f"field_mappings[{i}].{req_field}",
                        error_type="MISSING_FIELD",
                        message=f"Field mapping missing required field '{req_field}'",
                        suggested_fix=f"Add '{req_field}: value' to field mapping"
                    ))

            # Validate source references
            if 'source' in mapping:
                source = mapping['source']
                if source not in valid_sources:
                    available = ", ".join(sorted(valid_sources))
                    errors.append(ValidationError(
                        field=f"field_mappings[{i}].source",
                        error_type="INVALID_SOURCE",
                        message=f"Source '{source}' not found in v1_calls",
                        suggested_fix=f"Use one of: {available}"
                    ))

            # Validate transform vs v1_path logic
            has_transform = 'transform' in mapping and mapping['transform'] is not None
            has_v1_path = 'v1_path' in mapping and mapping['v1_path'] is not None

            if has_transform and has_v1_path:
                errors.append(ValidationError(
                    field=f"field_mappings[{i}]",
                    error_type="CONFLICTING_FIELDS",
                    message="Cannot have both 'transform' and 'v1_path' - use one or the other",
                    suggested_fix="Set 'v1_path: null' when using transform"
                ))

            if not has_transform and not has_v1_path:
                errors.append(ValidationError(
                    field=f"field_mappings[{i}]",
                    error_type="MISSING_MAPPING",
                    message="Must have either 'transform' or 'v1_path'",
                    suggested_fix="Add either 'v1_path: .field_name' or 'transform: ...' "
                ))

            # Validate stub mappings
            if 'source' in mapping and mapping['source'] == 'stub':
                if 'stub_type' not in mapping:
                    errors.append(ValidationError(
                        field=f"field_mappings[{i}].stub_type",
                        error_type="MISSING_FIELD",
                        message="Stub mappings must include 'stub_type'",
                        suggested_fix="Add 'stub_type: null/empty_string/empty_array/configurable_default'"
                    ))
                elif mapping['stub_type'] not in ['null', 'empty_string', 'empty_array', 'configurable_default']:
                    errors.append(ValidationError(
                        field=f"field_mappings[{i}].stub_type",
                        error_type="INVALID_VALUE",
                        message=f"Invalid stub_type: '{mapping['stub_type']}'",
                        suggested_fix="Use: null, empty_string, empty_array, or configurable_default"
                    ))

        return errors

    def _validate_transforms(self, config: Dict[str, Any]) -> List[ValidationError]:
        """Validate Jinja2 transform syntax"""
        errors = []

        if 'field_mappings' not in config:
            return errors

        field_mappings = config['field_mappings']
        if not isinstance(field_mappings, list):
            return errors

        for i, mapping in enumerate(field_mappings):
            if not isinstance(mapping, dict) or 'transform' not in mapping:
                continue

            transform = mapping['transform']
            if transform is None:
                continue

            # Check for forbidden patterns
            forbidden_patterns = [
                (r"\{\{\s*['\"][^'\"]+['\"]:\s*[^}]+\}\}", "Never use {{ 'key': value }} syntax"),
                (r"\{\{[^}]*['\"][^'\"]*['\"]:[^}]*\}\}", "Objects must use literal JSON, not {{ }} syntax"),
                (r"\{\%-?\s*for\s+\w+\s+in\s+source\s*-?\%\}\{\{[^}]*['\"]:", "Use literal JSON format for arrays")
            ]

            for pattern, message in forbidden_patterns:
                if re.search(pattern, str(transform)):
                    errors.append(ValidationError(
                        field=f"field_mappings[{i}].transform",
                        error_type="FORBIDDEN_SYNTAX",
                        message=f"Transform uses forbidden syntax: {message}",
                        suggested_fix="Use literal JSON: [{% for item in source %}{ \"key\": \"{{ item.field }}\" }{% endfor %}]"
                    ))

            # Check for proper structure
            if isinstance(transform, str):
                # Should start with [ for arrays or { for objects
                stripped = transform.strip()
                if stripped.startswith('[') and not ']' in stripped[-10:]:
                    errors.append(ValidationError(
                        field=f"field_mappings[{i}].transform",
                        error_type="SYNTAX_ERROR",
                        message="Array transform appears to be missing closing bracket",
                        suggested_fix="Ensure transform ends with proper ] closing bracket"
                    ))

        return errors

    def _validate_cross_references(self, config: Dict[str, Any]) -> List[ValidationError]:
        """Validate cross-references between sections"""
        errors = []

        # Check if V2 endpoint exists
        if 'endpoint' in config and 'v2_path' in config['endpoint']:
            v2_path = config['endpoint']['v2_path']
            if v2_path not in self.v2_endpoints:
                available = ", ".join(list(self.v2_endpoints)[:3])
                errors.append(ValidationError(
                    field="endpoint.v2_path",
                    error_type="INVALID_ENDPOINT",
                    message=f"V2 endpoint '{v2_path}' not found in V2 spec",
                    suggested_fix=f"Use one of: {available}"
                ))

        return errors

    def format_errors_for_ai(self, errors: List[ValidationError]) -> str:
        """Format errors in a way that's easy for AI to understand and fix"""
        if not errors:
            return "No errors found."

        error_summary = f"Found {len(errors)} validation errors:\n\n"

        # Group errors by type
        error_groups = {}
        for error in errors:
            if error.error_type not in error_groups:
                error_groups[error.error_type] = []
            error_groups[error.error_type].append(error)

        for error_type, group_errors in error_groups.items():
            error_summary += f"## {error_type} Errors ({len(group_errors)}):\n"
            for error in group_errors:
                error_summary += f"- {error.field}: {error.message}\n"
                if error.suggested_fix:
                    error_summary += f"  → Fix: {error.suggested_fix}\n"
            error_summary += "\n"

        return error_summary