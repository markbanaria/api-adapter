# User Story 005: V2 Response Builder

## Story
As a developer, I want a response builder that can construct V2 API responses from V1 data using field mappings and transformations.

## Acceptance Criteria
- [ ] ResponseBuilder can construct nested V2 response objects
- [ ] Supports dot notation for nested field paths (e.g., "insured.name")
- [ ] Applies all field mappings from config
- [ ] Handles missing/optional fields gracefully
- [ ] Integrates with FieldTransformer for transformations
- [ ] Returns properly structured JSON responses
- [ ] Unit tests cover simple and complex response structures

## Technical Details

### Response Builder (backend/src/adapter/response_builder.py)

```python
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
        keys = path.split('.')
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
```

### Unit Tests (backend/tests/test_response_builder.py)

```python
import pytest
from adapter.response_builder import V2ResponseBuilder, ResponseBuilderError
from adapter.models import MappingConfig, EndpointConfig, V1ApiCall, FieldMapping


@pytest.fixture
def response_builder():
    return V2ResponseBuilder()


def test_set_nested_value_simple(response_builder):
    """Test setting a simple top-level value"""
    obj = {}
    response_builder._set_nested_value(obj, "name", "John Doe")
    
    assert obj == {"name": "John Doe"}


def test_set_nested_value_deep(response_builder):
    """Test setting a deeply nested value"""
    obj = {}
    response_builder._set_nested_value(obj, "insured.contact.email", "john@example.com")
    
    assert obj == {
        "insured": {
            "contact": {
                "email": "john@example.com"
            }
        }
    }


def test_set_nested_value_multiple_fields(response_builder):
    """Test setting multiple nested values"""
    obj = {}
    response_builder._set_nested_value(obj, "insured.name", "John Doe")
    response_builder._set_nested_value(obj, "insured.age", 35)
    response_builder._set_nested_value(obj, "policy.number", "POL123")
    
    assert obj == {
        "insured": {
            "name": "John Doe",
            "age": 35
        },
        "policy": {
            "number": "POL123"
        }
    }


def test_build_response_simple_mapping(response_builder):
    """Test building a simple V2 response"""
    config = MappingConfig(
        version="1.0",
        endpoint=EndpointConfig(v2_path="/api/v2/test", v2_method="GET"),
        v1_calls=[
            V1ApiCall(name="get_data", endpoint="/v1/data", method="GET")
        ],
        field_mappings=[
            FieldMapping(
                v2_path="policyNumber",
                source="get_data",
                v1_path="policy_num"
            ),
            FieldMapping(
                v2_path="status",
                source="get_data",
                v1_path="policy_status"
            )
        ]
    )
    
    v1_responses = {
        "get_data": {
            "policy_num": "POL12345",
            "policy_status": "active"
        }
    }
    
    result = response_builder.build_response(config, v1_responses)
    
    assert result == {
        "policyNumber": "POL12345",
        "status": "active"
    }


def test_build_response_nested_fields(response_builder):
    """Test building a V2 response with nested fields"""
    config = MappingConfig(
        version="1.0",
        endpoint=EndpointConfig(v2_path="/api/v2/test", v2_method="GET"),
        v1_calls=[
            V1ApiCall(name="get_policy", endpoint="/v1/policy", method="GET")
        ],
        field_mappings=[
            FieldMapping(
                v2_path="insured.name",
                source="get_policy",
                transform="{{ get_policy.first_name }} {{ get_policy.last_name }}"
            ),
            FieldMapping(
                v2_path="insured.age",
                source="get_policy",
                v1_path="customer_age"
            ),
            FieldMapping(
                v2_path="policy.number",
                source="get_policy",
                v1_path="policy_num"
            )
        ]
    )
    
    v1_responses = {
        "get_policy": {
            "first_name": "Jane",
            "last_name": "Smith",
            "customer_age": 42,
            "policy_num": "POL99999"
        }
    }
    
    result = response_builder.build_response(config, v1_responses)
    
    assert result == {
        "insured": {
            "name": "Jane Smith",
            "age": 42
        },
        "policy": {
            "number": "POL99999"
        }
    }


def test_build_response_multiple_v1_sources(response_builder):
    """Test building V2 response from multiple V1 sources"""
    config = MappingConfig(
        version="1.0",
        endpoint=EndpointConfig(v2_path="/api/v2/test", v2_method="GET"),
        v1_calls=[
            V1ApiCall(name="get_policy", endpoint="/v1/policy", method="GET"),
            V1ApiCall(name="get_coverage", endpoint="/v1/coverage", method="GET")
        ],
        field_mappings=[
            FieldMapping(
                v2_path="policyNumber",
                source="get_policy",
                v1_path="policy_num"
            ),
            FieldMapping(
                v2_path="coverageAmount",
                source="get_coverage",
                v1_path="amount"
            ),
            FieldMapping(
                v2_path="coverageType",
                source="get_coverage",
                v1_path="type"
            )
        ]
    )
    
    v1_responses = {
        "get_policy": {
            "policy_num": "POL12345"
        },
        "get_coverage": {
            "amount": 500000,
            "type": "whole_life"
        }
    }
    
    result = response_builder.build_response(config, v1_responses)
    
    assert result == {
        "policyNumber": "POL12345",
        "coverageAmount": 500000,
        "coverageType": "whole_life"
    }


def test_build_response_with_stub(response_builder):
    """Test building V2 response with stub field"""
    config = MappingConfig(
        version="1.0",
        endpoint=EndpointConfig(v2_path="/api/v2/test", v2_method="GET"),
        v1_calls=[
            V1ApiCall(name="get_policy", endpoint="/v1/policy", method="GET")
        ],
        field_mappings=[
            FieldMapping(
                v2_path="policyNumber",
                source="get_policy",
                v1_path="policy_num"
            ),
            FieldMapping(
                v2_path="digitalSignatureUrl",
                source="stub",
                stub_value=None,
                stub_type="null"
            )
        ]
    )
    
    v1_responses = {
        "get_policy": {
            "policy_num": "POL12345"
        }
    }
    
    result = response_builder.build_response(config, v1_responses)
    
    assert result == {
        "policyNumber": "POL12345",
        "digitalSignatureUrl": None
    }


def test_build_response_transformation_error(response_builder):
    """Test that transformation errors are handled"""
    config = MappingConfig(
        version="1.0",
        endpoint=EndpointConfig(v2_path="/api/v2/test", v2_method="GET"),
        v1_calls=[
            V1ApiCall(name="get_data", endpoint="/v1/data", method="GET")
        ],
        field_mappings=[
            FieldMapping(
                v2_path="computed",
                source="get_data",
                transform="{{ get_data.nonexistent_field }}"
            )
        ]
    )
    
    v1_responses = {
        "get_data": {"other_field": "value"}
    }
    
    with pytest.raises(ResponseBuilderError, match="Failed to map required field"):
        response_builder.build_response(config, v1_responses)
```

## Testing Checklist
- [ ] Simple field mapping works
- [ ] Nested field creation works (dot notation)
- [ ] Multiple nested fields work
- [ ] Multiple V1 sources aggregated correctly
- [ ] Stub fields handled correctly
- [ ] Transformations applied correctly
- [ ] Transformation errors handled properly
- [ ] Missing V1 fields logged as warnings

## Definition of Done
- V2ResponseBuilder class implemented
- Nested object creation works via dot notation
- Integration with FieldTransformer complete
- All unit tests passing (>90% coverage)
- Clear error messages for failures