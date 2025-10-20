from typing import Any, Dict, Optional
from jinja2 import Environment, StrictUndefined, TemplateSyntaxError, UndefinedError
from jinja2.sandbox import SandboxedEnvironment
import json
import logging

logger = logging.getLogger(__name__)


class TransformationError(Exception):
    """Raised when a transformation fails"""
    pass


class FieldTransformer:
    """Executes Jinja2 transformations on V1 data to produce V2 fields"""

    def __init__(self):
        # Use sandboxed environment for security
        self.env = SandboxedEnvironment(
            undefined=StrictUndefined,
            autoescape=False
        )

        # Register custom filters if needed
        self.env.filters['to_upper'] = lambda x: str(x).upper() if x else ""
        self.env.filters['to_lower'] = lambda x: str(x).lower() if x else ""

    def transform(
        self,
        expression: str,
        context: Dict[str, Any],
        field_name: str = "unknown"
    ) -> Any:
        """
        Execute a Jinja2 transformation expression

        Args:
            expression: Jinja2 template string (e.g., "{{ firstName }} {{ lastName }}")
            context: Dictionary of available variables (V1 API responses)
            field_name: Name of the V2 field being transformed (for error messages)

        Returns:
            Transformed value

        Raises:
            TransformationError: If transformation fails
        """
        try:
            template = self.env.from_string(expression)
            result = template.render(**context)

            # Try to coerce to appropriate type
            result = self._coerce_type(result)

            logger.debug(f"Transformed {field_name}: {expression} -> {result}")
            return result

        except TemplateSyntaxError as e:
            raise TransformationError(
                f"Invalid transformation syntax for '{field_name}': {e}"
            )
        except UndefinedError as e:
            raise TransformationError(
                f"Undefined variable in transformation for '{field_name}': {e}"
            )
        except Exception as e:
            raise TransformationError(
                f"Transformation failed for '{field_name}': {e}"
            )

    def _coerce_type(self, value: str) -> Any:
        """Attempt to coerce string results to appropriate types"""
        if not isinstance(value, str):
            return value

        # Strip whitespace
        value = value.strip()

        # Try to parse as JSON if it looks like JSON (starts with { or [)
        if value and (value[0] in '{['):
            try:
                parsed = json.loads(value)
                logger.debug(f"Successfully parsed JSON: {value[:100]} -> {parsed}")
                return parsed
            except (json.JSONDecodeError, ValueError) as e:
                logger.debug(f"Failed to parse as JSON: {value[:100]}, error: {e}")
                pass

        # Try int
        try:
            if '.' not in value:
                return int(value)
        except (ValueError, AttributeError):
            pass

        # Try float
        try:
            return float(value)
        except (ValueError, AttributeError):
            pass

        # Try bool
        if value.lower() in ('true', 'false'):
            return value.lower() == 'true'

        # Return as string
        return value

    def get_nested_value(self, data: Dict[str, Any], path: str) -> Any:
        """
        Get a value from nested dict using dot notation

        Args:
            data: Dictionary to search
            path: Dot-separated path (e.g., "policy.details.type")

        Returns:
            Value at path, or None if not found
        """
        if not path:
            return data

        # Handle paths that start with a dot (e.g., ".policy_num")
        if path.startswith('.'):
            path = path[1:]

        # Handle empty path after removing leading dot
        if not path:
            return data

        keys = path.split('.')
        value = data

        for key in keys:
            if key:  # Skip empty keys
                if isinstance(value, dict):
                    value = value.get(key)
                    if value is None:
                        return None
                else:
                    return None

        return value

    def apply_mapping(
        self,
        v1_responses: Dict[str, Dict[str, Any]],
        field_mapping: 'FieldMapping',
    ) -> Any:
        """
        Apply a single field mapping to V1 responses

        Args:
            v1_responses: Dict of {v1_call_name: response_data}
            field_mapping: FieldMapping configuration

        Returns:
            Transformed value for the V2 field
        """
        # Handle stub values
        if field_mapping.source == "stub":
            return field_mapping.stub_value

        # Get source V1 response
        if field_mapping.source not in v1_responses:
            raise TransformationError(
                f"V1 source '{field_mapping.source}' not found in responses"
            )

        source_data = v1_responses[field_mapping.source]

        # If there's a transformation, execute it
        if field_mapping.transform:
            # Build context with all V1 responses available plus flattened source data
            context = v1_responses.copy()
            # Also add flattened source data for easier template access
            context.update(source_data)
            # Add 'source' as an alias for the specific source data used in templates
            context['source'] = source_data
            return self.transform(
                field_mapping.transform,
                context,
                field_mapping.v2_path
            )

        # Otherwise, direct mapping
        if not field_mapping.v1_path:
            raise TransformationError(
                f"Field mapping for '{field_mapping.v2_path}' has no v1_path and no transform"
            )

        value = self.get_nested_value(source_data, field_mapping.v1_path)

        if value is None:
            logger.warning(
                f"V1 field '{field_mapping.v1_path}' not found in source '{field_mapping.source}'"
            )

        return value