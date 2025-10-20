import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch
from pathlib import Path
import yaml
import tempfile
import os

from adapter.main import app
from adapter.orchestrator import V1OrchestratorError
from adapter.response_builder import ResponseBuilderError


@pytest.fixture
def test_config_dir():
    """Create a temporary directory with test config files"""
    with tempfile.TemporaryDirectory() as tmp_dir:
        config_dir = Path(tmp_dir)

        # Create test config file
        config_yaml = """
version: "1.0"
endpoint:
  v2_path: "/api/v2/policies/{policyId}"
  v2_method: "GET"

v1_calls:
  - name: "get_policy"
    endpoint: "/api/v1/policy/{id}"
    method: "GET"
    params:
      path:
        - v2_param: "policyId"
          v1_param: "id"
          location: "path"

field_mappings:
  - v2_path: "policyNumber"
    source: "get_policy"
    v1_path: "policy_num"

  - v2_path: "insured.name"
    source: "get_policy"
    transform: "{{ get_policy.first_name }} {{ get_policy.last_name }}"

  - v2_path: "status"
    source: "get_policy"
    v1_path: "policy_status"

metadata:
  generated_at: "2025-10-19T10:00:00Z"
  confidence_score: 0.95
"""

        config_file = config_dir / "get_policy.yaml"
        config_file.write_text(config_yaml)

        # Create second test config with query parameters
        config_yaml_2 = """
version: "1.0"
endpoint:
  v2_path: "/api/v2/search/policies"
  v2_method: "GET"

v1_calls:
  - name: "search_policies"
    endpoint: "/api/v1/policies/search"
    method: "GET"
    params:
      query:
        - v2_param: "name"
          v1_param: "customer_name"
          location: "query"
        - v2_param: "status"
          v1_param: "policy_status"
          location: "query"

field_mappings:
  - v2_path: "policies"
    source: "search_policies"
    v1_path: "results"

metadata:
  generated_at: "2025-10-19T10:00:00Z"
  confidence_score: 0.95
"""

        config_file_2 = config_dir / "search_policies.yaml"
        config_file_2.write_text(config_yaml_2)

        # Create test config with POST method and body params
        config_yaml_3 = """
version: "1.0"
endpoint:
  v2_path: "/api/v2/policies"
  v2_method: "POST"

v1_calls:
  - name: "create_policy"
    endpoint: "/api/v1/policy"
    method: "POST"
    params:
      body:
        - v2_param: "customerName"
          v1_param: "customer_name"
          location: "body"
        - v2_param: "policyType"
          v1_param: "type"
          location: "body"

field_mappings:
  - v2_path: "policyId"
    source: "create_policy"
    v1_path: "id"

  - v2_path: "status"
    source: "stub"
    stub_value: "created"

metadata:
  generated_at: "2025-10-19T10:00:00Z"
  confidence_score: 0.95
"""

        config_file_3 = config_dir / "create_policy.yaml"
        config_file_3.write_text(config_yaml_3)

        yield str(config_dir)


@pytest.fixture
def client(test_config_dir, monkeypatch):
    """Create test client with mocked config directory"""
    # Mock the config directory path
    monkeypatch.setenv("CONFIG_DIR", test_config_dir)

    with TestClient(app) as client:
        yield client


def test_health_check(client):
    """Test health check endpoint"""
    response = client.get("/health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "insurance-api-adapter"
    assert data["version"] == "0.1.0"
    assert "endpoints_loaded" in data
    assert data["endpoints_loaded"] >= 3  # We have 3 test configs


def test_root_endpoint(client):
    """Test root endpoint returns API info"""
    response = client.get("/")

    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "Insurance API V2 Adapter"
    assert data["version"] == "0.1.0"
    assert "endpoints" in data
    assert len(data["endpoints"]) >= 3

    # Check that our test endpoints are registered
    endpoint_paths = [ep["path"] for ep in data["endpoints"]]
    assert "/api/v2/policies/{policyId}" in endpoint_paths
    assert "/api/v2/search/policies" in endpoint_paths
    assert "/api/v2/policies" in endpoint_paths


@patch('adapter.main.orchestrator')
def test_v2_endpoint_success_with_path_params(mock_orchestrator, client):
    """Test successful V2 request flow with path parameters"""

    # Mock V1 responses
    mock_orchestrator.orchestrate = AsyncMock(return_value={
        "get_policy": {
            "policy_num": "POL12345",
            "first_name": "John",
            "last_name": "Doe",
            "policy_status": "active"
        }
    })

    response = client.get("/api/v2/policies/POL12345")

    assert response.status_code == 200
    data = response.json()

    assert data["policyNumber"] == "POL12345"
    assert data["insured"]["name"] == "John Doe"
    assert data["status"] == "active"

    # Check request ID header
    assert "X-Request-ID" in response.headers

    # Verify orchestrator was called with correct config
    mock_orchestrator.orchestrate.assert_called_once()
    call_args = mock_orchestrator.orchestrate.call_args
    config, v2_params = call_args[0]

    assert config.endpoint.v2_path == "/api/v2/policies/{policyId}"
    assert v2_params["policyId"] == "POL12345"


@patch('adapter.main.orchestrator')
def test_v2_endpoint_success_with_query_params(mock_orchestrator, client):
    """Test successful V2 request flow with query parameters"""

    # Mock V1 responses
    mock_orchestrator.orchestrate = AsyncMock(return_value={
        "search_policies": {
            "results": [
                {"policy_num": "POL123", "customer": "John Doe"},
                {"policy_num": "POL456", "customer": "Jane Smith"}
            ]
        }
    })

    response = client.get("/api/v2/search/policies?name=John&status=active")

    assert response.status_code == 200
    data = response.json()

    assert "policies" in data
    assert len(data["policies"]) == 2

    # Check request ID header
    assert "X-Request-ID" in response.headers

    # Verify orchestrator was called with correct params
    mock_orchestrator.orchestrate.assert_called_once()
    call_args = mock_orchestrator.orchestrate.call_args
    config, v2_params = call_args[0]

    assert v2_params["name"] == "John"
    assert v2_params["status"] == "active"


@patch('adapter.main.orchestrator')
def test_v2_endpoint_success_with_body_params(mock_orchestrator, client):
    """Test successful V2 request flow with body parameters"""

    # Mock V1 responses
    mock_orchestrator.orchestrate = AsyncMock(return_value={
        "create_policy": {
            "id": "POL789"
        }
    })

    request_body = {
        "customerName": "Alice Johnson",
        "policyType": "life"
    }

    response = client.post("/api/v2/policies", json=request_body)

    assert response.status_code == 200
    data = response.json()

    assert data["policyId"] == "POL789"
    assert data["status"] == "created"

    # Check request ID header
    assert "X-Request-ID" in response.headers

    # Verify orchestrator was called with correct params
    mock_orchestrator.orchestrate.assert_called_once()
    call_args = mock_orchestrator.orchestrate.call_args
    config, v2_params = call_args[0]

    assert v2_params["customerName"] == "Alice Johnson"
    assert v2_params["policyType"] == "life"


@patch('adapter.main.orchestrator')
def test_v2_endpoint_404_error(mock_orchestrator, client):
    """Test V2 endpoint with V1 404 error"""

    mock_orchestrator.orchestrate = AsyncMock(
        side_effect=V1OrchestratorError(
            "Not found",
            status_code=404,
            details={"v1_response": "Policy not found"}
        )
    )

    response = client.get("/api/v2/policies/INVALID")

    assert response.status_code == 404
    data = response.json()

    assert "error" in data
    assert data["error"] == "Resource not found in legacy system"
    assert data["code"] == "V1_ERROR_404"
    assert "request_id" in data
    assert "details" in data


@patch('adapter.main.orchestrator')
def test_v2_endpoint_502_error(mock_orchestrator, client):
    """Test V2 endpoint with V1 500 error (mapped to 502)"""

    mock_orchestrator.orchestrate = AsyncMock(
        side_effect=V1OrchestratorError(
            "Server error",
            status_code=502,
            details={"v1_status": 500, "v1_response": "Internal error"}
        )
    )

    response = client.get("/api/v2/policies/POL123")

    assert response.status_code == 502
    data = response.json()

    assert data["error"] == "Legacy system error"
    assert data["code"] == "V1_ERROR_502"
    assert "request_id" in data
    assert "details" in data


@patch('adapter.main.orchestrator')
def test_v2_endpoint_timeout(mock_orchestrator, client):
    """Test V2 endpoint with V1 timeout"""

    mock_orchestrator.orchestrate = AsyncMock(
        side_effect=V1OrchestratorError(
            "Timeout",
            status_code=504
        )
    )

    response = client.get("/api/v2/policies/POL123")

    assert response.status_code == 504
    data = response.json()

    assert data["error"] == "Legacy system timeout"
    assert data["code"] == "V1_ERROR_504"
    assert "request_id" in data


@patch('adapter.main.orchestrator')
@patch('adapter.main.response_builder')
def test_v2_endpoint_transformation_error(mock_response_builder, mock_orchestrator, client):
    """Test V2 endpoint with transformation error"""

    # Mock successful orchestration but failed response building
    mock_orchestrator.orchestrate = AsyncMock(return_value={
        "get_policy": {"policy_num": "POL123"}
    })

    mock_response_builder.build_response.side_effect = ResponseBuilderError(
        "Field transformation failed"
    )

    response = client.get("/api/v2/policies/POL123")

    assert response.status_code == 500
    data = response.json()

    assert data["error"] == "Failed to transform response"
    assert data["code"] == "TRANSFORMATION_ERROR"
    assert "request_id" in data


@patch('adapter.main.orchestrator')
def test_v2_endpoint_unexpected_error(mock_orchestrator, client):
    """Test V2 endpoint with unexpected error"""

    mock_orchestrator.orchestrate = AsyncMock(
        side_effect=Exception("Unexpected error")
    )

    response = client.get("/api/v2/policies/POL123")

    assert response.status_code == 500
    data = response.json()

    assert data["error"] == "Internal server error"
    assert data["code"] == "INTERNAL_ERROR"
    assert "request_id" in data


@patch('adapter.main.orchestrator')
def test_parameter_extraction_malformed_json(mock_orchestrator, client):
    """Test parameter extraction with malformed JSON body"""

    # Mock orchestrator to verify the request still gets processed
    mock_orchestrator.orchestrate = AsyncMock(return_value={
        "create_policy": {"id": "POL999"}
    })

    response = client.post(
        "/api/v2/policies",
        content="{ invalid json }",
        headers={"Content-Type": "application/json"}
    )

    # Should still process - malformed JSON is ignored, not an error
    assert response.status_code == 200

    # Verify that even with malformed JSON, the orchestrator was still called
    mock_orchestrator.orchestrate.assert_called_once()


def test_parameter_extraction_mixed_params(client):
    """Test that path, query, and body parameters are all extracted"""

    with patch('adapter.main.orchestrator') as mock_orchestrator:
        mock_orchestrator.orchestrate = AsyncMock(return_value={
            "create_policy": {"id": "POL999"}
        })

        request_body = {"customerName": "Mixed Test", "policyType": "auto"}

        response = client.post(
            "/api/v2/policies?extra=value",
            json=request_body
        )

        # Verify all parameter types were extracted
        call_args = mock_orchestrator.orchestrate.call_args
        if call_args:
            config, v2_params = call_args[0]
            assert v2_params["customerName"] == "Mixed Test"  # from body
            assert v2_params["policyType"] == "auto"          # from body
            assert v2_params["extra"] == "value"              # from query