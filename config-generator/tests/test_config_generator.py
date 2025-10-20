import pytest
from unittest.mock import Mock, patch, mock_open
from pathlib import Path
import json
import yaml
from datetime import datetime

from generator.config_generator import ConfigGenerator


@pytest.fixture
def config_generator():
    return ConfigGenerator(qwen_base_url="http://localhost:11434")


@pytest.fixture
def sample_v2_spec():
    return {
        "info": {"title": "V2 API"},
        "paths": {
            "/api/v2/policies/{policyId}": {
                "get": {
                    "operationId": "getPolicy",
                    "parameters": [{"name": "policyId", "in": "path"}]
                }
            }
        }
    }


@pytest.fixture
def sample_v1_spec():
    return {
        "info": {"title": "V1 API"},
        "paths": {
            "/api/v1/policy/{policy_num}": {
                "get": {"operationId": "getPolicyV1"}
            }
        }
    }


def test_config_generator_initialization():
    """Test ConfigGenerator initialization"""
    gen = ConfigGenerator()
    assert gen.qwen_client is not None
    assert gen.qwen_client.base_url == "http://localhost:11434"


def test_load_spec(config_generator, tmp_path):
    """Test loading OpenAPI spec from JSON file"""
    spec_file = tmp_path / "spec.json"
    spec_data = {"openapi": "3.0.0", "info": {"title": "Test"}}
    spec_file.write_text(json.dumps(spec_data))

    loaded = config_generator.load_spec(spec_file)
    assert loaded == spec_data


def test_extract_yaml_from_response_with_code_block(config_generator):
    """Test extracting YAML from response with markdown code blocks"""
    response = """Here's the config:

```yaml
version: "1.0"
endpoint:
  v2_path: "/api/v2/test"
  v2_method: "GET"
```

That's the config."""

    result = config_generator.extract_yaml_from_response(response)
    assert result == """version: "1.0"
endpoint:
  v2_path: "/api/v2/test"
  v2_method: "GET\""""


def test_extract_yaml_from_response_without_code_block(config_generator):
    """Test extracting YAML from response without code blocks"""
    response = """version: "1.0"
endpoint:
  v2_path: "/api/v2/test"
  v2_method: "GET"
field_mappings:
  - v2_path: "id"
    source: "v1_call"
    v1_path: "identifier\""""

    result = config_generator.extract_yaml_from_response(response)
    assert "version: \"1.0\"" in result
    assert "endpoint:" in result


def test_extract_yaml_from_response_no_yaml(config_generator):
    """Test extracting YAML when response contains no YAML"""
    response = "This is just plain text with no YAML content."
    result = config_generator.extract_yaml_from_response(response)
    assert result == response


def test_validate_config_valid(config_generator):
    """Test validation of valid config"""
    config = {
        "version": "1.0",
        "endpoint": {"v2_path": "/test", "v2_method": "GET"},
        "v1_calls": [{"name": "call1", "endpoint": "/v1/test"}],
        "field_mappings": [{"v2_path": "field", "source": "call1"}]
    }

    # Should not raise
    config_generator._validate_config(config)


def test_validate_config_missing_key(config_generator):
    """Test validation fails for missing required key"""
    config = {
        "version": "1.0",
        "endpoint": {"v2_path": "/test", "v2_method": "GET"},
        # Missing v1_calls
        "field_mappings": [{"v2_path": "field", "source": "call1"}]
    }

    with pytest.raises(ValueError) as exc_info:
        config_generator._validate_config(config)
    assert "missing required key: v1_calls" in str(exc_info.value)


def test_validate_config_empty_v1_calls(config_generator):
    """Test validation fails for empty V1 calls"""
    config = {
        "version": "1.0",
        "endpoint": {"v2_path": "/test", "v2_method": "GET"},
        "v1_calls": [],  # Empty
        "field_mappings": [{"v2_path": "field", "source": "call1"}]
    }

    with pytest.raises(ValueError) as exc_info:
        config_generator._validate_config(config)
    assert "no V1 calls" in str(exc_info.value)


def test_validate_config_empty_field_mappings(config_generator):
    """Test validation fails for empty field mappings"""
    config = {
        "version": "1.0",
        "endpoint": {"v2_path": "/test", "v2_method": "GET"},
        "v1_calls": [{"name": "call1", "endpoint": "/v1/test"}],
        "field_mappings": []  # Empty
    }

    with pytest.raises(ValueError) as exc_info:
        config_generator._validate_config(config)
    assert "no field mappings" in str(exc_info.value)


@patch.object(ConfigGenerator, 'load_spec')
def test_generate_config_success(mock_load, config_generator, tmp_path, sample_v2_spec, sample_v1_spec):
    """Test successful config generation"""
    # Setup mocks
    mock_load.side_effect = [sample_v2_spec, sample_v1_spec]

    yaml_response = """version: "1.0"
endpoint:
  v2_path: "/api/v2/policies/{policyId}"
  v2_method: "GET"
v1_calls:
  - name: "get_policy"
    endpoint: "/api/v1/policy/{policy_num}"
    method: "GET"
field_mappings:
  - v2_path: "policyNumber"
    source: "get_policy"
    v1_path: "policy_num\""""

    with patch.object(config_generator.qwen_client, 'generate', return_value=yaml_response):
        output_path = tmp_path / "output.yaml"

        # Generate config
        config = config_generator.generate_config(
            v2_spec_path=Path("v2.json"),
            v1_spec_path=Path("v1.json"),
            v2_endpoint_path="/api/v2/policies/{policyId}",
            output_path=output_path
        )

        # Verify config structure
        assert config["version"] == "1.0"
        assert config["endpoint"]["v2_path"] == "/api/v2/policies/{policyId}"
        assert len(config["v1_calls"]) == 1
        assert len(config["field_mappings"]) == 1

        # Verify metadata added
        assert "metadata" in config
        assert "generated_at" in config["metadata"]

        # Verify file saved
        assert output_path.exists()
        saved_config = yaml.safe_load(output_path.read_text())
        assert saved_config["version"] == "1.0"


@patch.object(ConfigGenerator, 'load_spec')
def test_generate_config_invalid_yaml(mock_load, config_generator, tmp_path, sample_v2_spec, sample_v1_spec):
    """Test error handling for invalid YAML response"""
    mock_load.side_effect = [sample_v2_spec, sample_v1_spec]

    with patch.object(config_generator.qwen_client, 'generate', return_value="Invalid YAML: {this is not valid}"):
        output_path = tmp_path / "output.yaml"

        with pytest.raises(ValueError) as exc_info:
            config_generator.generate_config(
                v2_spec_path=Path("v2.json"),
                v1_spec_path=Path("v1.json"),
                v2_endpoint_path="/api/v2/policies/{policyId}",
                output_path=output_path
            )

        # The error could be either YAML parse error or validation error
        assert ("not valid YAML" in str(exc_info.value) or
                "missing required key" in str(exc_info.value))


@patch.object(ConfigGenerator, 'load_spec')
def test_generate_config_with_ambiguous_mappings(mock_load, config_generator, tmp_path, sample_v2_spec, sample_v1_spec):
    """Test handling of ambiguous mappings in response"""
    mock_load.side_effect = [sample_v2_spec, sample_v1_spec]

    yaml_response = """version: "1.0"
endpoint:
  v2_path: "/api/v2/policies/{policyId}"
  v2_method: "GET"
v1_calls:
  - name: "get_policy"
    endpoint: "/api/v1/policy"
field_mappings:
  - v2_path: "id"
    source: "get_policy"
    v1_path: "policy_id"
metadata:
  confidence_score: 0.85
  ambiguous_mappings:
    - v2_field: "status"
      proposals:
        - v1_field: "policy_status"
          confidence: 0.7
        - v1_field: "status_code"
          confidence: 0.3"""

    with patch.object(config_generator.qwen_client, 'generate', return_value=yaml_response):
        output_path = tmp_path / "output.yaml"

        config = config_generator.generate_config(
            v2_spec_path=Path("v2.json"),
            v1_spec_path=Path("v1.json"),
            v2_endpoint_path="/api/v2/policies/{policyId}",
            output_path=output_path
        )

        assert config["metadata"]["confidence_score"] == 0.85
        assert len(config["metadata"]["ambiguous_mappings"]) == 1
        assert config["metadata"]["ambiguous_mappings"][0]["v2_field"] == "status"


def test_close(config_generator):
    """Test closing Qwen client"""
    with patch.object(config_generator.qwen_client, 'close') as mock_close:
        config_generator.close()
        mock_close.assert_called_once()