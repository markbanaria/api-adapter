from typing import Dict, Any, List
import logging
from .models import MappingConfig, FieldMapping
from .transformer import FieldTransformer, TransformationError

logger = logging.getLogger(__name__)


class ResponseBuilderError(Exception):
    """Raised when response building fails"""
    pass


class V2ResponseBuilder:
    """Builds V2 API responses from V1 data using field mappings"""

    def __init__(self):
        self.transformer = FieldTransformer()

    def _set_nested_value(self, obj: Dict[str, Any], path: str, value: Any) -> None:
        """
        Set a value in a nested dict using dot notation

        Args:
            obj: Dictionary to modify
            path: Dot-separated path (e.g., "insured.contact.email")
            value: Value to set
        """
        # Handle paths that start with a dot (e.g., ".policyNumber")
        if path.startswith('.'):
            path = path[1:]

        # Handle empty path after removing leading dot
        if not path:
            raise ResponseBuilderError("Empty path after removing leading dot")

        keys = path.split('.')
        # Filter out empty keys
        keys = [key for key in keys if key]
        current = obj

        # Navigate/create nested structure
        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            elif not isinstance(current[key], dict):
                raise ResponseBuilderError(
                    f"Cannot set nested value at '{path}': '{key}' is not a dict"
                )
            current = current[key]

        # Set the final value
        current[keys[-1]] = value

    def build_response(
        self,
        config: MappingConfig,
        v1_responses: Dict[str, Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Build a V2 response from V1 responses using field mappings

        Args:
            config: Mapping configuration
            v1_responses: Dict of {v1_call_name: response_data}

        Returns:
            V2 response object

        Raises:
            ResponseBuilderError: If response building fails
        """
        v2_response = {}

        for field_mapping in config.field_mappings:
            try:
                # Apply transformation or direct mapping
                value = self.transformer.apply_mapping(v1_responses, field_mapping)

                # Set value in nested structure
                self._set_nested_value(v2_response, field_mapping.v2_path, value)

                logger.debug(f"Mapped {field_mapping.v2_path} = {value}")

            except TransformationError as e:
                # Log transformation errors but continue with other fields
                logger.error(
                    f"Transformation failed for {field_mapping.v2_path}: {e}",
                    extra={"field": field_mapping.v2_path}
                )
                # Re-raise if it's a critical field (no stub fallback)
                if field_mapping.source != "stub":
                    raise ResponseBuilderError(
                        f"Failed to map required field '{field_mapping.v2_path}': {e}"
                    )
            except Exception as e:
                logger.error(
                    f"Unexpected error mapping {field_mapping.v2_path}: {e}",
                    extra={"field": field_mapping.v2_path}
                )
                raise ResponseBuilderError(
                    f"Failed to build field '{field_mapping.v2_path}': {e}"
                )

        return v2_response