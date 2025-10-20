import pytest
from generator.prompt_templates import SYSTEM_PROMPT, create_mapping_prompt


def test_system_prompt():
    """Test that system prompt is defined and contains key information"""
    assert SYSTEM_PROMPT is not None
    assert "insurance" in SYSTEM_PROMPT.lower()
    assert "api mapping" in SYSTEM_PROMPT.lower()
    assert "yaml" in SYSTEM_PROMPT.lower()


def test_create_mapping_prompt_valid():
    """Test creating mapping prompt with valid specs"""
    v2_spec = {
        "paths": {
            "/api/v2/policies/{policyId}": {
                "get": {
                    "operationId": "getPolicy",
                    "parameters": [
                        {"name": "policyId", "in": "path"}
                    ]
                }
            }
        }
    }

    v1_spec = {
        "paths": {
            "/api/v1/policy/{policy_num}": {
                "get": {
                    "operationId": "getPolicyV1"
                }
            }
        }
    }

    prompt = create_mapping_prompt(v2_spec, v1_spec, "/api/v2/policies/{policyId}")

    # Verify prompt contains key sections
    assert "Task: Generate API Mapping Configuration" in prompt
    assert "Domain Context" in prompt
    assert "V2 API Endpoint (TARGET)" in prompt
    assert "V1 API Endpoints (SOURCE" in prompt
    assert "Output Format" in prompt
    assert "/api/v2/policies/{policyId}" in prompt
    assert "version: \"1.0\"" in prompt


def test_create_mapping_prompt_endpoint_not_found():
    """Test error when V2 endpoint not found in spec"""
    v2_spec = {
        "paths": {
            "/api/v2/policies": {
                "get": {"operationId": "listPolicies"}
            }
        }
    }

    v1_spec = {"paths": {}}

    with pytest.raises(ValueError) as exc_info:
        create_mapping_prompt(v2_spec, v1_spec, "/api/v2/nonexistent")

    assert "not found in spec" in str(exc_info.value)


def test_create_mapping_prompt_empty_v1_spec():
    """Test creating prompt with empty V1 spec"""
    v2_spec = {
        "paths": {
            "/api/v2/test": {
                "get": {"operationId": "test"}
            }
        }
    }

    v1_spec = {"paths": {}}

    prompt = create_mapping_prompt(v2_spec, v1_spec, "/api/v2/test")

    assert "V1 API Endpoints" in prompt
    assert "{}" in prompt  # Empty V1 endpoints


def test_create_mapping_prompt_includes_instructions():
    """Test that prompt includes all necessary instructions"""
    v2_spec = {
        "paths": {
            "/api/v2/test": {
                "post": {
                    "operationId": "createTest",
                    "requestBody": {
                        "content": {
                            "application/json": {
                                "schema": {"type": "object"}
                            }
                        }
                    }
                }
            }
        }
    }

    v1_spec = {
        "paths": {
            "/api/v1/test": {
                "post": {"operationId": "createTestV1"}
            }
        }
    }

    prompt = create_mapping_prompt(v2_spec, v1_spec, "/api/v2/test")

    # Check for important instructions
    assert "Identify Required V1 Endpoints" in prompt
    assert "Map Parameters" in prompt
    assert "Map Response Fields" in prompt
    assert "Confidence Scoring" in prompt
    assert "Jinja2" in prompt
    assert "semantic matching" in prompt
    assert "insurance fields" in prompt.lower()


def test_create_mapping_prompt_formatting():
    """Test that prompt has proper formatting for LLM consumption"""
    v2_spec = {
        "paths": {
            "/api/v2/policies/{id}": {
                "get": {"operationId": "get"},
                "put": {"operationId": "update"},
                "delete": {"operationId": "delete"}
            }
        }
    }

    v1_spec = {"paths": {}}

    prompt = create_mapping_prompt(v2_spec, v1_spec, "/api/v2/policies/{id}")

    # Check for markdown code blocks
    assert "```json" in prompt
    assert "```yaml" in prompt
    assert "```" in prompt

    # Check for section headers
    assert "## " in prompt
    assert "### " in prompt

    # Check for bullet points
    assert "- " in prompt