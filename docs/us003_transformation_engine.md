# User Story 003: Jinja2 Transformation Engine

## Story
As a developer, I want a safe and flexible transformation engine that can execute Jinja2 expressions to map and transform V1 data to V2 format.

## Acceptance Criteria
- [ ] Transformer class can execute Jinja2 templates safely (sandboxed)
- [ ] Supports field combination (e.g., `{{ firstName }} {{ lastName }}`)
- [ ] Supports simple arithmetic (e.g., `{{ monthly_premium * 12 }}`)
- [ ] Supports conditional logic (e.g., `{{ 'active' if status == 1 else 'inactive' }}`)
- [ ] Handles nested object access via dot notation
- [ ] Provides clear error messages for transformation failures
- [ ] Unit tests cover all transformation patterns

## Technical Details

### Transformer Class (backend/src/adapter/transformer.py)

```python
from typing import Any, Dict, Optional
from jinja2 import Environment, StrictUndefined, TemplateSyntaxError, UndefinedError
from jinja2.sandbox import SandboxedEnvironment
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
        keys = path.split('.')
        value = data
        
        for key in keys:
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
            # Build context with all V1 responses available
            context = v1_responses.copy()
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
```

### Unit Tests (backend/tests/test_transformer.py)

```python
import pytest
from adapter.transformer import FieldTransformer, TransformationError
from adapter.models import FieldMapping


@pytest.fixture
def transformer():
    return FieldTransformer()


def test_simple_field_combination(transformer):
    """Test combining two fields with a space"""
    context = {
        "get_policy": {
            "firstName": "John",
            "lastName": "Doe"
        }
    }
    
    result = transformer.transform(
        "{{ get_policy.firstName }} {{ get_policy.lastName }}",
        context,
        "insured.name"
    )
    
    assert result == "John Doe"


def test_arithmetic_transformation(transformer):
    """Test simple arithmetic"""
    context = {
        "get_policy": {
            "monthly_premium": 100
        }
    }
    
    result = transformer.transform(
        "{{ get_policy.monthly_premium * 12 }}",
        context,
        "premium.annual"
    )
    
    assert result == 1200


def test_conditional_transformation(transformer):
    """Test if-else conditional"""
    context = {
        "get_policy": {
            "status": 1
        }
    }
    
    result = transformer.transform(
        "{{ 'active' if get_policy.status == 1 else 'inactive' }}",
        context,
        "policyStatus"
    )
    
    assert result == "active"


def test_nested_object_access(transformer):
    """Test accessing nested objects"""
    data = {
        "policy": {
            "details": {
                "type": "whole_life"
            }
        }
    }
    
    result = transformer.get_nested_value(data, "policy.details.type")
    assert result == "whole_life"


def test_missing_field_returns_none(transformer):
    """Test that missing nested fields return None"""
    data = {"policy": {"name": "Test"}}
    
    result = transformer.get_nested_value(data, "policy.details.type")
    assert result is None


def test_undefined_variable_error(transformer):
    """Test that undefined variables raise clear errors"""
    context = {"get_policy": {"name": "Test"}}
    
    with pytest.raises(TransformationError, match="Undefined variable"):
        transformer.transform(
            "{{ get_policy.nonexistent }}",
            context,
            "test_field"
        )


def test_apply_mapping_direct(transformer):
    """Test direct field mapping without transformation"""
    v1_responses = {
        "get_policy": {
            "policy_num": "POL12345"
        }
    }
    
    mapping = FieldMapping(
        v2_path="policyNumber",
        source="get_policy",
        v1_path="policy_num"
    )
    
    result = transformer.apply_mapping(v1_responses, mapping)
    assert result == "POL12345"


def test_apply_mapping_with_transform(transformer):
    """Test field mapping with transformation"""
    v1_responses = {
        "get_policy": {
            "first_name": "Jane",
            "last_name": "Smith"
        }
    }
    
    mapping = FieldMapping(
        v2_path="insured.name",
        source="get_policy",
        transform="{{ get_policy.first_name }} {{ get_policy.last_name }}"
    )
    
    result = transformer.apply_mapping(v1_responses, mapping)
    assert result == "Jane Smith"


def test_apply_mapping_stub(transformer):
    """Test stub field mapping"""
    v1_responses = {}
    
    mapping = FieldMapping(
        v2_path="digitalSignatureUrl",
        source="stub",
        stub_value=None,
        stub_type="null"
    )
    
    result = transformer.apply_mapping(v1_responses, mapping)
    assert result is None


def test_type_coercion_int(transformer):
    """Test automatic type coercion to int"""
    context = {"value": "42"}
    result = transformer.transform("{{ value }}", context)
    assert result == 42
    assert isinstance(result, int)


def test_type_coercion_float(transformer):
    """Test automatic type coercion to float"""
    context = {"value": "3.14"}
    result = transformer.transform("{{ value }}", context)
    assert result == 3.14
    assert isinstance(result, float)


def test_type_coercion_bool(transformer):
    """Test automatic type coercion to bool"""
    context = {"value": "true"}
    result = transformer.transform("{{ value }}", context)
    assert result is True
    assert isinstance(result, bool)
```

## Testing Checklist
- [ ] Simple string concatenation works
- [ ] Arithmetic operations work (*, /, +, -)
- [ ] Conditional logic works (if/else)
- [ ] Nested object access works
- [ ] Missing fields handled gracefully
- [ ] Undefined variables raise clear errors
- [ ] Type coercion works (str → int/float/bool)
- [ ] Stub mappings return configured values
- [ ] Direct mappings work without transforms

## Definition of Done
- FieldTransformer class implemented with sandboxed Jinja2
- All transformation patterns tested and working
- Error handling provides actionable messages
- Unit tests achieve >95% coverage
- No unsafe eval() or exec() usage
