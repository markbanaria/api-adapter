import pytest
from pathlib import Path
from adapter.config_loader import ConfigLoader
from adapter.models import MappingConfig, FieldMapping
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


def test_valid_jinja2_transform():
    """Test that valid Jinja2 syntax passes validation"""
    mapping = FieldMapping(
        v2_path="fullName",
        source="get_customer",
        transform="{{ first_name }} {{ last_name }}"
    )
    assert mapping.transform == "{{ first_name }} {{ last_name }}"


def test_stub_mapping():
    """Test that stub mappings work correctly"""
    mapping = FieldMapping(
        v2_path="newField",
        source="stub",
        stub_value=None,
        stub_type="null"
    )
    assert mapping.source == "stub"
    assert mapping.stub_value is None
    assert mapping.stub_type == "null"


def test_file_not_found(tmp_path):
    """Test handling of missing config file"""
    loader = ConfigLoader(tmp_path)

    with pytest.raises(FileNotFoundError, match="Config file not found"):
        loader.load_config("nonexistent.yaml")


def test_invalid_yaml_syntax(tmp_path):
    """Test handling of invalid YAML syntax"""
    invalid_yaml = """
version: "1.0
endpoint:
  v2_path: "/api/v2/test"
  invalid: yaml: syntax:
"""
    config_file = tmp_path / "invalid.yaml"
    config_file.write_text(invalid_yaml)

    loader = ConfigLoader(tmp_path)

    with pytest.raises(ValueError, match="Invalid config"):
        loader.load_config("invalid.yaml")


def test_missing_required_fields(tmp_path):
    """Test validation of required fields"""
    config_yaml = """
version: "1.0"
endpoint:
  v2_path: "/api/v2/test"
# Missing v1_calls and field_mappings
"""
    config_file = tmp_path / "incomplete.yaml"
    config_file.write_text(config_yaml)

    loader = ConfigLoader(tmp_path)

    with pytest.raises(ValueError, match="Invalid config"):
        loader.load_config("incomplete.yaml")


def test_load_all_configs(tmp_path):
    """Test loading all YAML files in directory"""
    config1_yaml = """
version: "1.0"
endpoint:
  v2_path: "/api/v2/test1"
  v2_method: "GET"
v1_calls:
  - name: "get_data1"
    endpoint: "/api/v1/data1"
    method: "GET"
field_mappings:
  - v2_path: "field1"
    source: "get_data1"
    v1_path: "old_field1"
"""

    config2_yaml = """
version: "1.0"
endpoint:
  v2_path: "/api/v2/test2"
  v2_method: "POST"
v1_calls:
  - name: "get_data2"
    endpoint: "/api/v1/data2"
    method: "GET"
field_mappings:
  - v2_path: "field2"
    source: "get_data2"
    v1_path: "old_field2"
"""

    (tmp_path / "config1.yaml").write_text(config1_yaml)
    (tmp_path / "config2.yaml").write_text(config2_yaml)

    loader = ConfigLoader(tmp_path)
    configs = loader.load_all_configs()

    assert len(configs) == 2
    assert "config1" in configs
    assert "config2" in configs


def test_get_config_for_endpoint(tmp_path):
    """Test retrieving config by endpoint"""
    config_yaml = """
version: "1.0"
endpoint:
  v2_path: "/api/v2/policies/{id}"
  v2_method: "GET"
v1_calls:
  - name: "get_policy"
    endpoint: "/api/v1/policy/{id}"
    method: "GET"
field_mappings:
  - v2_path: "policyNumber"
    source: "get_policy"
    v1_path: "policy_num"
"""
    (tmp_path / "policies.yaml").write_text(config_yaml)

    loader = ConfigLoader(tmp_path)
    loader.load_all_configs()

    config = loader.get_config_for_endpoint("/api/v2/policies/{id}", "GET")
    assert config.endpoint.v2_path == "/api/v2/policies/{id}"

    with pytest.raises(KeyError, match="No config found"):
        loader.get_config_for_endpoint("/api/v2/nonexistent", "GET")


def test_v1_call_name_validation():
    """Test that V1 call names must be valid identifiers"""
    from adapter.models import V1ApiCall

    # Valid names should pass
    valid_call = V1ApiCall(name="get_policy", endpoint="/api/v1/policy")
    assert valid_call.name == "get_policy"

    # Invalid names should fail
    with pytest.raises(ValidationError, match="must be alphanumeric"):
        V1ApiCall(name="invalid-name", endpoint="/api/v1/policy")

    with pytest.raises(ValidationError, match="must be alphanumeric"):
        V1ApiCall(name="invalid name", endpoint="/api/v1/policy")