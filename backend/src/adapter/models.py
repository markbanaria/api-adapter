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

    @field_validator('method')
    @classmethod
    def method_to_uppercase(cls, v: str) -> str:
        return v.upper()


class FieldMapping(BaseModel):
    """Maps a V2 field to V1 source(s) with optional transformation"""
    v2_path: str = Field(..., description="JSONPath to V2 field (dot notation)")
    source: str = Field(..., description="V1 call name or 'stub'")
    v1_path: Optional[str] = Field(None, description="JSONPath to V1 field")
    transform: Optional[str] = Field(None, description="Jinja2 transformation expression")
    stub_value: Optional[Any] = Field(None, description="Default value if source is 'stub'")
    stub_type: Optional[Literal["null", "configurable_default", "empty_string", "empty_array"]] = None
    approved: bool = Field(False, description="Whether this mapping has been approved")
    edited: bool = Field(False, description="Whether this mapping has been manually edited")

    @field_validator('stub_type')
    @classmethod
    def validate_stub_type(cls, v):
        if v is None:
            return v
        # Convert invalid stub_types to valid ones
        valid_types = ["null", "configurable_default", "empty_string", "empty_array"]
        if v not in valid_types:
            # Default to configurable_default for any invalid type
            return "configurable_default"
        return v

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

    @field_validator('v2_method')
    @classmethod
    def v2_method_to_uppercase(cls, v: str) -> str:
        return v.upper()


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