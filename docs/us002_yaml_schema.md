# User Story 002: YAML Configuration Schema & Validator

## Story
As a developer, I want a well-defined YAML schema and validator so that mapping configurations are consistently structured and validated before use.

## Acceptance Criteria
- [ ] Pydantic models define the complete config schema
- [ ] YAML files can be loaded and validated against schema
- [ ] Validation errors provide clear, actionable messages
- [ ] Example YAML config file created for each test scenario
- [ ] Unit tests cover all validation cases (valid/invalid configs)

## Technical Details

### Pydantic Models (backend/src/adapter/models.py)

```python
from typing import List, Optional, Dict, Any, Literal
from pydantic import BaseModel, Field, field_validator
from datetime import datetime


class ParamMapping(BaseModel):
    """Maps a parameter from V2 to V1 with optional location shift"""
    v2_param: str
    v1_param: str
    location: Literal["path", "query", "body"] = "query"


class V1ApiCall(BaseModel):
    """Configuration for a single V1 API call"""
    name: str = Field(..., description="Unique identifier for this V1 call")
    endpoint: str = Field(..., description="V1 API endpoint path")
    method: Literal["GET", "POST", "PUT", "DELETE", "PATCH"] = "GET"
    params: Optional[Dict[Literal["path", "query", "body"], List[ParamMapping]]] = None
    
    @field_validator('name')
    @classmethod
    def name_must_be_valid_identifier(cls, v: str) -> str:
        if not v.replace('_', '').isalnum():
            raise ValueError('name must be alphanumeric with underscores')
        return v


class FieldMapping(BaseModel):
    """Maps a V2 field to V1 source(s) with optional transformation"""
    v2_path: str = Field(..., description="JSONPath to V2 field (dot notation)")
    source: str = Field(..., description="V1 call name or 'stub'")
    v1_path: Optional[str] = Field(None, description="JSONPath to V1 field")
    transform: Optional[str] = Field(None, description="Jinja2 transformation expression")
    stub_value: Optional[Any] = Field(None, description="Default value if source is 'stub'")
    stub_type: Optional[Literal["null", "configurable_default", "empty_string", "empty_array"]] = None
    
    @field_validator('transform')
    @classmethod
    def transform_uses_jinja2(cls, v: Optional[str]) -> Optional[str]:
        if v and ('{{' not in v or '}}' not in v):
            raise ValueError('transform must use Jinja2 syntax with {{ }}')
        return v


class AmbiguousMapping(BaseModel):
    """Represents an ambiguous mapping with multiple proposals"""
    v2_field: str
    proposals: List[Dict[str, Any]] = Field(..., description="List of {v1_field, confidence}")


class Metadata(BaseModel):
    """Metadata about config generation"""
    generated_at: datetime
    confidence_score: float = Field(..., ge=0.0, le=1.0)
    ambiguous_mappings: Optional[List[AmbiguousMapping]] = None
    generator_version: str = "0.1.0"


class EndpointConfig(BaseModel):
    """V2 endpoint configuration"""
    v2_path: str = Field(..., description="V2 API endpoint path")
    v2_method: Literal["GET", "POST", "PUT", "DELETE", "PATCH"] = "GET"


class MappingConfig(BaseModel):
    """Root configuration model"""
    version: str = "1.0"
    endpoint: EndpointConfig
    v1_calls: List[V1ApiCall] = Field(..., min_length=1)
    field_mappings: List[FieldMapping] = Field(..., min_length=1)
    metadata: Optional[Metadata] = None
    
    @field_validator('field_mappings')
    @classmethod
    def validate_source_references(cls, v: List[FieldMapping], info) -> List[FieldMapping]:
        """Ensure all field mapping sources reference existing V1 calls or 'stub'"""
        if 'v1_calls' not in info.data:
            return v
            
        v1_call_names = {call.name for call in info.data['v1_calls']}
        for mapping in v:
            if mapping.source != 'stub' and mapping.source not in v1_call_names:
                raise ValueError(f"Field mapping source '{mapping.source}' not found in v1_calls")
        return v
```

### Config Loader (backend/src/adapter/config_loader.py)

```python
import yaml
from pathlib import Path
from typing import Dict
from .models import MappingConfig


class ConfigLoader:
    """Loads and validates YAML mapping configurations"""
    
    def __init__(self, config_dir: Path):
        self.config_dir = Path(config_dir)
        self._configs: Dict[str, MappingConfig] = {}
    
    def load_config(self, config_file: str) -> MappingConfig:
        """Load and validate a single config file"""
        config_path = self.config_dir / config_file
        
        if not config_path.exists():
            raise FileNotFoundError(f"Config file not found: {config_path}")
        
        with open(config_path, 'r') as f:
            raw_config = yaml.safe_load(f)
        
        try:
            config = MappingConfig(**raw_config)
            return config
        except Exception as e:
            raise ValueError(f"Invalid config in {config_file}: {e}")
    
    def load_all_configs(self) -> Dict[str, MappingConfig]:
        """Load all YAML files in config directory"""
        for config_file in self.config_dir.glob("*.yaml"):
            endpoint_id = config_file.stem
            self._configs[endpoint_id] = self.load_config(config_file.name)
        return self._configs
    
    def get_config_for_endpoint(self, v2_path: str, method: str) -> MappingConfig:
        """Retrieve config for a specific V2 endpoint"""
        for config in self._configs.values():
            if config.endpoint.v2_path == v2_path and config.endpoint.v2_method == method:
                return config
        raise KeyError(f"No config found for {method} {v2_path}")
```

### Example Config (backend/configs/example-simple-rename.yaml)

```yaml
version: "1.0"

endpoint:
  v2_path: "/api/v2/policies/{policyId}"
  v2_method: "GET"

v1_calls:
  - name: "get_policy"
    endpoint: "/api/v1/policy"
    method: "GET"
    params:
      query:
        - v2_param: "policyId"
          v1_param: "policy_id"
          location: "path"

field_mappings:
  - v2_path: "policyNumber"
    source: "get_policy"
    v1_path: "policy_num"
    transform: null
    
  - v2_path: "status"
    source: "get_policy"
    v1_path: "policy_status"
    transform: null

metadata:
  generated_at: "2025-10-19T10:00:00Z"
  confidence_score: 0.95
  generator_version: "0.1.0"
```

### Unit Tests (backend/tests/test_config_loader.py)

```python
import pytest
from pathlib import Path
from adapter.config_loader import ConfigLoader
from adapter.models import MappingConfig
from pydantic import ValidationError


def test_load_valid_config(tmp_path):
    """Test loading a valid config file"""
    config_yaml = """
version: "1.0"
endpoint:
  v2_path: "/api/v2/test"
  v2_method: "GET"
v1_calls:
  - name: "get_data"
    endpoint: "/api/v1/data"
    method: "GET"
field_mappings:
  - v2_path: "field1"
    source: "get_data"
    v1_path: "old_field1"
"""
    config_file = tmp_path / "test.yaml"
    config_file.write_text(config_yaml)
    
    loader = ConfigLoader(tmp_path)
    config = loader.load_config("test.yaml")
    
    assert isinstance(config, MappingConfig)
    assert config.endpoint.v2_path == "/api/v2/test"
    assert len(config.v1_calls) == 1
    assert len(config.field_mappings) == 1


def test_invalid_source_reference(tmp_path):
    """Test that invalid source references are caught"""
    config_yaml = """
version: "1.0"
endpoint:
  v2_path: "/api/v2/test"
  v2_method: "GET"
v1_calls:
  - name: "get_data"
    endpoint: "/api/v1/data"
    method: "GET"
field_mappings:
  - v2_path: "field1"
    source: "nonexistent_call"
    v1_path: "old_field1"
"""
    config_file = tmp_path / "invalid.yaml"
    config_file.write_text(config_yaml)
    
    loader = ConfigLoader(tmp_path)
    
    with pytest.raises(ValueError, match="not found in v1_calls"):
        loader.load_config("invalid.yaml")


def test_transform_validation():
    """Test Jinja2 transform syntax validation"""
    with pytest.raises(ValidationError, match="must use Jinja2 syntax"):
        FieldMapping(
            v2_path="test",
            source="src",
            transform="invalid_syntax"
        )
```

## Testing Checklist
- [ ] Valid config loads without errors
- [ ] Invalid YAML syntax throws clear error
- [ ] Missing required fields throws validation error
- [ ] Invalid source reference throws error
- [ ] Invalid transform syntax throws error
- [ ] All example configs validate successfully

## Definition of Done
- Pydantic models implemented and documented
- ConfigLoader class complete with error handling
- At least 3 example YAML configs created
- All unit tests passing (>90% coverage)
- Validation error messages are developer-friendly
